import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from triage_bench import workflow
from triage_bench.dataset import ROOT, read_jsonl
from triage_bench.runner import run


class WorkflowTests(unittest.TestCase):
    def response(self, gate='investigate_domain', supports=('power',)):
        answers = {'disposition': {'choice': gate}}
        for domain in workflow.DOMAINS:
            answers[f'supports_{domain}'] = {'noul': .9 if domain in supports else .1}
        return {'answers': answers, 'model': 'jev-fixture'}

    def packet(self):
        return read_jsonl(ROOT / 'data/validation.inputs.jsonl')[0]['input']

    def test_request_allowlist_keeps_relevant_evidence_and_excludes_labels(self):
        record = {'input': self.packet(), 'labels': {'answer': 'LABEL_SENTINEL'},
                  'incident_family_id': 'FAMILY_SENTINEL'}
        record['input']['change_record']['label_rationale'] = 'RATIONALE_SENTINEL'
        request = workflow.request_body(record, 'jev-fixture')
        text = json.dumps(request)
        for sentinel in ('LABEL_SENTINEL', 'FAMILY_SENTINEL', 'RATIONALE_SENTINEL'):
            self.assertNotIn(sentinel, text)
        self.assertIn('observed_at', text)
        self.assertIn('edges', text)
        self.assertEqual(len(request['questions']), 5)

    def test_unique_domain_maps_to_consistent_disposition(self):
        prediction, probabilities, confidence = workflow.normalize(self.response(), self.packet())
        self.assertEqual(prediction['initial_owner'], 'power')
        self.assertEqual(prediction['next_check'], 'inspect_power')
        self.assertEqual(prediction['insufficient_evidence'], 'no')
        self.assertEqual((probabilities, confidence), ({}, {}))

    def test_conflicting_or_absent_domains_gather_evidence(self):
        for supports in ((), ('power', 'transport')):
            prediction, _, _ = workflow.normalize(self.response(supports=supports), self.packet())
            self.assertEqual(prediction['initial_owner'], 'noc')
            self.assertEqual(prediction['next_check'], 'gather_evidence')
            self.assertEqual(prediction['insufficient_evidence'], 'yes')

    def test_gate_maps_recovery_and_change_without_domain_assignment(self):
        for gate, check, flag in (('monitor', 'monitor', 'no'),
                                   ('verify_change', 'verify_change', 'yes'),
                                   ('gather_evidence', 'gather_evidence', 'yes')):
            prediction, _, _ = workflow.normalize(self.response(gate), self.packet())
            self.assertEqual((prediction['initial_owner'], prediction['next_check'],
                              prediction['insufficient_evidence']), ('noc', check, flag))

    def test_malformed_primitive_is_not_a_successful_decision(self):
        for invalid in (True, -1, 2, float('nan')):
            response = self.response()
            response['answers']['supports_ran']['noul'] = invalid
            with self.assertRaises(ValueError):
                workflow.normalize(response, self.packet())

    def test_runner_preserves_intermediates_and_counts_invalid_response(self):
        payloads = []
        responses = [self.response(), self.response()]
        del responses[1]['answers']['supports_core']

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                payloads.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                response = json.dumps(responses[len(payloads) - 1]).encode()
                self.send_response(200)
                self.send_header('Content-Length', str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            with tempfile.TemporaryDirectory() as directory:
                output = Path(directory) / 'predictions.jsonl'
                meta = run(ROOT / 'data/validation.inputs.jsonl', output, provider='jev',
                           model='jev-fixture', endpoint=f'http://127.0.0.1:{server.server_port}/v1/systemone',
                           context_tokens=8192, deployment='local test fixture', limit=2,
                           decision_workflow=workflow)
                rows = read_jsonl(output)
                self.assertEqual(meta['failed_records'], 1)
                self.assertEqual(rows[0]['raw_response']['answers'], responses[0]['answers'])
                self.assertEqual(rows[1]['status'], 'error')
                self.assertEqual(meta['question_schema_sha256'], workflow.metadata()['workflow_question_sha256'])
                self.assertTrue(meta['no_autoregressive_calls'])
                self.assertEqual(len(payloads[0]['questions']), 5)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
