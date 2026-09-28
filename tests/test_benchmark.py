import copy
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from triage_bench.dataset import generate, read_jsonl, write_jsonl
from triage_bench.evaluate import evaluate
from triage_bench.policy import OPTIONS
from triage_bench.runner import normalize, request_body, run
from triage_bench.validate import validate


class BenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        generate(self.root/'data')
        self.records = read_jsonl(self.root/'data/test.inputs.jsonl')
        self.keys = read_jsonl(self.root/'data/test.labels.jsonl')

    def tearDown(self):
        self.temp.cleanup()

    def test_reproducible_and_disjoint(self):
        first = (self.root/'data/manifest.json').read_bytes()
        generate(self.root/'data')
        self.assertEqual(first,(self.root/'data/manifest.json').read_bytes())
        self.assertEqual(validate(self.root/'data')['test'],220)

    def test_never_send_labels_or_metadata(self):
        poisoned=copy.deepcopy(self.records[0])
        poisoned['labels']={'secret':'ANSWER_KEY_SENTINEL'}
        poisoned['incident_family_id']='FAMILY_SENTINEL'
        body=json.dumps(request_body(poisoned,'test-model'))
        self.assertNotIn('ANSWER_KEY_SENTINEL',body)
        self.assertNotIn('FAMILY_SENTINEL',body)
        self.assertNotIn(poisoned['id'],body)

    def test_local_radio_and_power_impacts_are_bounded(self):
        for split in ['train','validation','test']:
            records={r['id']:r for r in read_jsonl(self.root/f'data/{split}.inputs.jsonl')}
            for key in read_jsonl(self.root/f'data/{split}.labels.jsonl'):
                if key['labels']['initial_owner'] in {'ran','power'}:
                    self.assertLessEqual(records[key['id']]['input']['service_impact']['affected_sites'],2)

    def test_future_evidence_rejected(self):
        self.records[0]['input']['observations'][0]['observed_at']='2099-01-01T00:00:00Z'
        write_jsonl(self.root/'data/test.inputs.jsonl',self.records)
        with self.assertRaisesRegex(AssertionError,'future'):
            validate(self.root/'data')

    def test_priority_boundary_and_stale_pairs(self):
        keys=read_jsonl(self.root/'data/challenge.labels.jsonl')
        self.assertEqual(len({k['incident_family_id'] for k in keys}),4)
        groups={}
        for key in keys: groups.setdefault(key['pair_id'],[]).append(key)
        for pair in groups.values():
            fields={f for f in OPTIONS if pair[0]['labels'][f]!=pair[1]['labels'][f]}
            if 'priority' in fields:
                self.assertEqual(fields,{'priority'})
                self.assertEqual({k['labels']['priority'] for k in pair},{'P1','P2'})
            elif fields:
                self.assertIn({k['labels']['initial_owner'] for k in pair},[{'power','noc'},{'transport','noc'}])
            else:
                self.assertEqual(pair[0]['pair_kind'],'invariance')

    def test_perfect_predictions_score_one(self):
        rows=[{'id':k['id'],'status':'ok','predictions':k['labels']} for k in self.keys]
        write_jsonl(self.root/'perfect.jsonl',rows)
        m=evaluate(self.root/'data/test.labels.jsonl',self.root/'perfect.jsonl')
        self.assertEqual(m['all_fields_accuracy'],1)
        self.assertIsNone(m['fields']['initial_owner']['brier_score'])

    def test_missing_predictions_count_as_errors(self):
        write_jsonl(self.root/'empty.jsonl',[])
        m=evaluate(self.root/'data/test.labels.jsonl',self.root/'empty.jsonl')
        self.assertEqual(m['missing_records'],220)
        self.assertEqual(m['all_fields_accuracy'],0)
        self.assertEqual(m['p1_miss_rate'],1)

    def test_duplicate_predictions_rejected(self):
        row={'id':self.keys[0]['id'],'status':'error'}
        write_jsonl(self.root/'duplicate.jsonl',[row,row])
        with self.assertRaisesRegex(ValueError,'Duplicate'):
            evaluate(self.root/'data/test.labels.jsonl',self.root/'duplicate.jsonl')

    def response(self):
        return {'model':'fixture-model', 'answers':{f:{'choice':next(iter(c)),
            'probabilities':{v:1/len(c) for v in c}, 'confidence':0.77} for f,c in OPTIONS.items()}}

    def test_partial_distribution_rejected(self):
        response=self.response()
        del response['answers']['initial_owner']['probabilities']['ran']
        with self.assertRaisesRegex(ValueError,'Incomplete'):
            normalize(response)

    def test_nonfinite_distribution_rejected(self):
        response=self.response()
        response['answers']['initial_owner']['probabilities']['ran']=float('nan')
        with self.assertRaisesRegex(ValueError,'Invalid probability'):
            normalize(response)

    def test_confidence_is_separate_from_probability(self):
        predictions,probs,confidence=normalize(self.response())
        self.assertEqual(confidence['initial_owner'],.77)
        self.assertEqual(probs['initial_owner'][predictions['initial_owner']],.2)

    def test_real_http_contract_with_fixture_server(self):
        captured=[]
        response=self.response()
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                captured.append(json.loads(self.rfile.read(int(self.headers['Content-Length']))))
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            def log_message(self,*args): pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            for provider in ['jev','laya','clm']:
                path=self.root/f'{provider}.jsonl'
                run(self.root/'data/test.inputs.jsonl',path,provider=provider,model='fixture-model',
                    endpoint=f'http://127.0.0.1:{server.server_port}/v1/systemone',limit=1,
                    context_tokens=16384,deployment='local HTTP fixture, not a model')
                row=read_jsonl(path)[0]
                self.assertEqual(row['status'],'ok')
                self.assertEqual(row['resolved_model'],'fixture-model')
            self.assertEqual(len(captured),3)
            self.assertTrue(all(set(c)=={'model','state','questions'} for c in captured))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_small_context_fails_without_network(self):
        path=self.root/'small.jsonl'
        run(self.root/'data/test.inputs.jsonl',path,provider='laya',model='example',
            endpoint='http://127.0.0.1:1/v1/systemone',limit=1,context_tokens=512,deployment='test')
        row=read_jsonl(path)[0]
        self.assertEqual(row['status'],'error')
        self.assertIn('Context preflight failed',row['error'])

    def test_existing_run_cannot_be_overwritten(self):
        path=self.root/'baseline.jsonl'
        run(self.root/'data/test.inputs.jsonl',path,limit=1)
        with self.assertRaisesRegex(ValueError,'immutable'):
            run(self.root/'data/test.inputs.jsonl',path,limit=1)


if __name__=='__main__': unittest.main()
