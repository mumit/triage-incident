import copy
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from triage_bench import llm_review, llm_review_v2
from triage_bench.dataset import ROOT, read_jsonl


class LLMReviewTests(unittest.TestCase):
    def record(self):
        return read_jsonl(ROOT / 'data/workflow-study/draft.inputs.jsonl')[0]

    def review(self):
        record = self.record()
        return {'answers': {'initial_owner': 'power', 'priority': 'P3',
                            'next_check': 'inspect_power', 'insufficient_evidence': 'no'},
                'evidence': {field: [{'path': '/observations/0/detail',
                                     'quote': record['input']['observations'][0]['detail']}]
                             for field in llm_review.OPTIONS},
                'rationale': 'Current independent measurements support power investigation.',
                'input_issues': [], 'unresolved_questions': []}

    def response(self, review=None):
        return {'model': 'review-fixture', 'usage': {'prompt_tokens': 10, 'completion_tokens': 10},
                'choices': [{'finish_reason': 'stop', 'message': {'content': json.dumps(review or self.review())}}]}

    def test_blind_request_excludes_labels_families_and_nested_metadata(self):
        record = self.record()
        record.update(labels='LABEL_SENTINEL', incident_family_id='FAMILY_SENTINEL', predictions='MODEL_SENTINEL')
        record['input']['observations'][0]['label_rationale'] = 'NESTED_SENTINEL'
        text = json.dumps(llm_review.request_body(record, 'review-fixture'))
        for sentinel in ('LABEL_SENTINEL', 'FAMILY_SENTINEL', 'MODEL_SENTINEL', 'NESTED_SENTINEL', record['id']):
            self.assertNotIn(sentinel, text)
        self.assertIn('observed_at', text)
        self.assertIn('edges', text)

    def test_citation_must_exist_and_finish_must_be_normal(self):
        packet = llm_review.public_packet(self.record())
        self.assertEqual(llm_review.normalize(self.response(), packet), self.review())
        for path, quote in (('/observations/0/detail', 'INVENTED_EVIDENCE'),
                            ('/observations/100/detail', 'text'), ('/labels/answer', 'power')):
            review = self.review()
            review['evidence']['initial_owner'] = [{'path': path, 'quote': quote}]
            with self.assertRaises(ValueError):
                llm_review.normalize(self.response(review), packet)
        response = self.response()
        response['choices'][0]['finish_reason'] = 'length'
        with self.assertRaisesRegex(ValueError, 'finish normally'):
            llm_review.normalize(response, packet)

    def test_reference_disagreement_and_input_issue_are_not_auto_accepted(self):
        record = self.record()
        answers = self.review()['answers']
        key = {'id': record['id'], 'incident_family_id': 'family',
               'accepted_answers': {field: [answer] for field, answer in answers.items()}}
        row = {'id': record['id'], 'status': 'ok', 'review': self.review()}
        result = llm_review.compare([record], [key], [row])
        self.assertEqual(result['candidate_label_records'], 1)
        row['review']['input_issues'] = [{'path': '/service_impact/status',
                                         'issue': 'Clarify impact', 'suggested_correction': 'Confirm status'}]
        result = llm_review.compare([record], [key], [row])
        self.assertEqual(result['all_four_agree'], 1)
        self.assertEqual(result['candidate_label_records'], 0)
        row['review'] = self.review()
        row['review']['answers']['initial_owner'] = 'core'
        result = llm_review.compare([record], [key], [row])
        self.assertEqual(result['all_four_agree'], 0)
        self.assertEqual(result['requires_adjudication'], 1)
        self.assertIn('initial_owner', result['cases'][0]['differences'])
        self.assertEqual(llm_review.compare([record], [key], [])['missing_records'], 1)

    def test_policy_errors_remain_flagged(self):
        review = self.review()
        review['answers'].update(priority='P1', next_check='inspect_core')
        issues = llm_review.policy_issues(review['answers'], llm_review.public_packet(self.record()))
        self.assertEqual(len(issues), 2)

    def test_v2_graph_citations_compare_json_structure_without_relaxing_strings(self):
        packet = llm_review.public_packet(self.record())
        review = self.review()
        citation = {'path': '/topology/edges', 'quote': json.dumps(packet['topology']['edges'], separators=(',', ':'))}
        review['evidence']['initial_owner'] = [citation]
        response = self.response(review)
        with self.assertRaisesRegex(ValueError, 'Citation quote'):
            llm_review.normalize(response, packet)
        self.assertEqual(llm_review_v2.normalize(response, packet), review)
        citation['quote'] = '[["invented", "edge"]]'
        with self.assertRaisesRegex(ValueError, 'Citation quote'):
            llm_review_v2.normalize(self.response(review), packet)
        citation.update(path='/service_impact/status', quote=json.dumps(packet['service_impact']['status']))
        self.assertEqual(llm_review_v2.normalize(self.response(review), packet), review)
        with self.assertRaisesRegex(ValueError, 'Citation quote'):
            llm_review.normalize(self.response(review), packet)
        citation.update(path='/service_impact/affected_sites', quote='true')
        with self.assertRaisesRegex(ValueError, 'Citation quote'):
            llm_review_v2.normalize(self.response(review), packet)
        packet['service_impact']['affected_sites'] = 12
        citation['quote'] = '2'
        with self.assertRaisesRegex(ValueError, 'Citation quote'):
            llm_review_v2.normalize(self.response(review), packet)
        citation.update(path='/observations/0/detail', quote='INVENTED_EVIDENCE')
        with self.assertRaisesRegex(ValueError, 'Citation quote'):
            llm_review_v2.normalize(self.response(review), packet)

    def test_second_review_cannot_override_input_issues_or_disagreement(self):
        record = self.record()
        row = {'id': record['id'], 'status': 'ok', 'review': self.review(),
               'predictions': self.review()['answers'], 'policy_issues': [], 'resolved_model': 'luna-fixture'}
        primary = {'metadata': {'requested_model': 'luna'}, 'reviews': [row],
                   'comparison': {'cases': [{'id': record['id'], 'incident_family_id': 'family',
                        'pair_id': None, 'differences': {'priority': {}}, 'requires_adjudication': True}]}}
        other = copy.deepcopy(row)
        other['resolved_model'] = 'sol-fixture'
        secondary = {'metadata': {'requested_model': 'sol'}, 'reviews': [other]}
        self.assertEqual(llm_review.reconcile(primary, secondary)['candidate_records'], 1)
        other['review']['input_issues'] = [{'issue': 'conflicting impact'}]
        self.assertEqual(llm_review.reconcile(primary, secondary)['pending_records'], 1)
        other['review']['input_issues'] = []
        other['predictions']['priority'] = 'P2'
        self.assertEqual(llm_review.reconcile(primary, secondary)['pending_records'], 1)
        secondary['metadata']['requested_model'] = 'luna'
        with self.assertRaisesRegex(ValueError, 'different requested model'):
            llm_review.reconcile(primary, secondary)

    def test_all_case_reconciliation_does_not_skip_unflagged_model_disagreement(self):
        record = self.record()
        row = {'id': record['id'], 'status': 'ok', 'review': self.review(),
               'predictions': self.review()['answers'], 'policy_issues': [], 'resolved_model': 'luna-fixture'}
        primary = {'metadata': {'requested_model': 'luna', 'request_protocol': llm_review_v2.PROTOCOL},
                   'reviews': [row], 'comparison': {'cases': [{'id': record['id'], 'incident_family_id': 'family',
                        'pair_id': None, 'differences': {}, 'requires_adjudication': False}]}}
        other = copy.deepcopy(row)
        other['resolved_model'] = 'sol-fixture'
        secondary = {'metadata': {'requested_model': 'sol', 'request_protocol': llm_review_v2.PROTOCOL}, 'reviews': [other]}
        self.assertEqual(llm_review.reconcile(primary, secondary, all_cases=True)['candidate_records'], 1)
        other['predictions']['initial_owner'] = 'noc'
        self.assertEqual(llm_review.reconcile(primary, secondary, all_cases=True)['pending_records'], 1)
        secondary['metadata']['request_protocol'] = llm_review.PROTOCOL
        with self.assertRaisesRegex(ValueError, 'same review protocol'):
            llm_review.reconcile(primary, secondary, all_cases=True)

    def test_offline_revalidation_preserves_source_failure_and_raw_response(self):
        record = self.record()
        review = self.review()
        review['evidence']['priority'] = [{'path': '/service_impact/status', 'quote': '"degraded"'}]
        row = {'id': record['id'], 'status': 'error', 'error': 'Citation quote not present',
               'raw_response': self.response(review), 'latency_ms': 123}
        derived = llm_review.revalidate_rows([record], [row])[0]
        self.assertEqual(row['status'], 'error')
        self.assertEqual(derived['status'], 'ok')
        self.assertEqual(derived['source_status'], 'error')
        self.assertEqual(derived['source_error'], row['error'])
        self.assertEqual(derived['raw_response'], row['raw_response'])
        self.assertEqual(derived['latency_ms'], 123)

    def test_transport_preserves_failure_redacts_secrets_and_exports_without_rewriting_labels(self):
        payloads = []
        response = self.response()
        response['echo'] = 'secret-fixture'

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                payloads.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                if len(payloads) == 2:
                    self.send_response(429)
                    self.end_headers()
                    return
                body = json.dumps(response).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                records = [self.record(), copy.deepcopy(self.record())]
                records[1]['id'] = 'second-case'
                inputs = root / 'inputs.jsonl'
                inputs.write_text(''.join(json.dumps(record) + '\n' for record in records))
                output = root / 'review.jsonl'
                meta = llm_review.run(inputs, output, 'review-fixture',
                    f'http://127.0.0.1:{server.server_port}/v1', 'secret-fixture', min_interval=0)
                self.assertEqual(meta['failed_records'], 1)
                self.assertEqual(len(payloads), 2)
                self.assertNotIn('secret-fixture', output.read_text())
                rows = read_jsonl(output)
                self.assertEqual(rows[1]['error'], 'HTTP 429')
                answers = self.review()['answers']
                labels = root / 'labels.jsonl'
                keys = [{'id': record['id'], 'incident_family_id': 'family',
                         'accepted_answers': {field: [answer] for field, answer in answers.items()}}
                        for record in records]
                labels.write_text(''.join(json.dumps(key) + '\n' for key in keys))
                original_labels = labels.read_bytes()
                snapshot = llm_review.export(inputs, labels, output, root / 'export')
                self.assertEqual(snapshot['comparison']['candidate_label_records'], 1)
                self.assertEqual(labels.read_bytes(), original_labels)
                evidence = root / 'export/evidence.json'
                llm_review.verify_evidence(evidence, inputs, labels)
                snapshot['reviews'][0]['review']['answers']['priority'] = 'P1'
                evidence.write_text(json.dumps(snapshot))
                with self.assertRaisesRegex(ValueError, 'saved provider response'):
                    llm_review.verify_evidence(evidence, inputs, labels)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
