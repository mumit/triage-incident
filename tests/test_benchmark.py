import copy
import io
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import patch

from triage_bench.dataset import generate, read_jsonl, write_jsonl
from triage_bench.evaluate import evaluate
from triage_bench.llm import normalize as normalize_llm, request_body as llm_request_body
from triage_bench.policy import OPTIONS, questions
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
        llm_body=json.dumps(llm_request_body(poisoned,'gpt-6-luna'))
        self.assertNotIn('ANSWER_KEY_SENTINEL',llm_body)
        self.assertNotIn('FAMILY_SENTINEL',llm_body)
        self.assertNotIn(poisoned['id'],llm_body)

    def test_evidence_flag_uses_binary_question(self):
        self.assertEqual(questions()['insufficient_evidence']['type'],'noul')
        self.assertEqual(set(questions()['insufficient_evidence']['criteria']),{'false','true'})

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

    def test_accepted_alternative_is_correct_in_accuracy_and_confusion(self):
        key=copy.deepcopy(self.keys[0])
        canonical=key['labels']['initial_owner']
        alternative=next(choice for choice in OPTIONS['initial_owner'] if choice!=canonical)
        key['accepted_answers']['initial_owner']=[canonical,alternative]
        predictions={**key['labels'],'initial_owner':alternative}
        write_jsonl(self.root/'alternative.labels.jsonl',[key])
        write_jsonl(self.root/'alternative.predictions.jsonl',[
            {'id':key['id'],'status':'ok','predictions':predictions}])
        metrics=evaluate(self.root/'alternative.labels.jsonl',self.root/'alternative.predictions.jsonl')
        owner=metrics['fields']['initial_owner']
        self.assertEqual(metrics['all_fields_accuracy'],1)
        self.assertEqual(owner['accuracy'],1)
        self.assertEqual(owner['confusion_matrix'][alternative][alternative],1)
        self.assertEqual(owner['confusion_matrix'][canonical][alternative],0)

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
        answers={f:{'choice':next(iter(c)), 'probabilities':{v:1/len(c) for v in c},
                    'confidence':0.77} for f,c in OPTIONS.items() if f!='insufficient_evidence'}
        answers['insufficient_evidence']={'type':'noul','noul':0.77}
        return {'model':'fixture-model','answers':answers}

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

    def test_two_decimal_distribution_is_normalized_but_large_error_rejected(self):
        response=self.response()
        values=list(OPTIONS['next_check'])
        response['answers']['next_check']['probabilities']={c:(0.33 if i<3 else 0) for i,c in enumerate(values)}
        _,probabilities,_=normalize(response)
        self.assertAlmostEqual(sum(probabilities['next_check'].values()),1)
        self.assertAlmostEqual(probabilities['next_check'][values[0]],1/3)
        response['answers']['next_check']['probabilities']={c:(0.30 if i<3 else 0) for i,c in enumerate(values)}
        with self.assertRaisesRegex(ValueError,'outside rounding tolerance'):
            normalize(response)

    def test_binary_probability_maps_to_yes_and_no(self):
        response=self.response()
        predictions,probabilities,_=normalize(response)
        self.assertEqual(predictions['insufficient_evidence'],'yes')
        self.assertAlmostEqual(probabilities['insufficient_evidence']['yes'],.77)
        response['answers']['insufficient_evidence']['noul']=.2
        predictions,probabilities,_=normalize(response)
        self.assertEqual(predictions['insufficient_evidence'],'no')
        self.assertAlmostEqual(probabilities['insufficient_evidence']['no'],.8)

    def test_runner_records_rounded_distribution_and_binary_answer(self):
        response=self.response()
        values=list(OPTIONS['next_check'])
        response['answers']['next_check']['probabilities']={c:(0.33 if i<3 else 0) for i,c in enumerate(values)}
        requests=[]
        class Opener:
            def open(self, request, timeout):
                requests.append(json.loads(request.data))
                return io.BytesIO(json.dumps(response).encode())
        path=self.root/'rounded.jsonl'
        with patch('triage_bench.runner.urllib.request.build_opener',return_value=Opener()):
            meta=run(self.root/'data/test.inputs.jsonl',path,provider='laya',model='fixture-model',
                endpoint='http://127.0.0.1:8000/v1/systemone',limit=1,
                context_tokens=16384,deployment='fixture')
        row=read_jsonl(path)[0]
        self.assertEqual(row['status'],'ok')
        self.assertEqual(row['predictions']['insufficient_evidence'],'yes')
        self.assertAlmostEqual(row['probability_original_sums']['next_check'],.99)
        self.assertAlmostEqual(sum(row['probabilities']['next_check'].values()),1)
        self.assertEqual(requests[0]['questions']['insufficient_evidence']['type'],'noul')
        self.assertIn('question_schema_sha256',meta)

    def test_nonfinite_confidence_rejected(self):
        response=self.response()
        response['answers']['initial_owner']['confidence']=float('nan')
        with self.assertRaisesRegex(ValueError,'Invalid confidence'):
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
            for provider in ['jev','kev','laya','clm']:
                path=self.root/f'{provider}.jsonl'
                run(self.root/'data/test.inputs.jsonl',path,provider=provider,model='fixture-model',
                    endpoint=f'http://127.0.0.1:{server.server_port}/v1/systemone',limit=1,
                    context_tokens=16384,deployment='local HTTP fixture, not a model')
                row=read_jsonl(path)[0]
                self.assertEqual(row['status'],'ok')
                self.assertEqual(row['resolved_model'],'fixture-model')
            self.assertEqual(len(captured),4)
            self.assertTrue(all(set(c)=={'model','state','questions'} for c in captured))
            self.assertTrue(all(c['questions']['insufficient_evidence']['type']=='noul' for c in captured))
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_llm_chat_contract_and_zero_shot_scoring(self):
        captured=[]
        expected=self.keys[0]['labels']
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
                captured.append((self.path,self.headers.get('Authorization'),self.headers.get('User-Agent'),
                                 self.headers.get('Accept'),body))
                response={'model':'gpt-6-luna','choices':[{'finish_reason':'stop','message':{'content':json.dumps(expected)}}],
                          'usage':{'prompt_tokens':1200,'completion_tokens':80},
                          'diagnostic_echo':'fixture-bearer-secret'}
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            def log_message(self,*args): pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            output=self.root/'llm.jsonl'
            meta=run(self.root/'data/test.inputs.jsonl',output,provider='llm',model='gpt-6-luna',
                     endpoint=f'http://127.0.0.1:{server.server_port}/v1',limit=1,
                     context_tokens=32768,deployment='fixture',api_key='fixture-bearer-secret')
            row=read_jsonl(output)[0]
            self.assertEqual((row['status'],row['predictions']),('ok',expected))
            self.assertEqual(row['probabilities'],{})
            self.assertEqual(captured[0][0],'/v1/chat/completions')
            self.assertEqual(captured[0][1],'Bearer fixture-bearer-secret')
            self.assertEqual(captured[0][2],'NorthstarIncidentBench/0.1')
            self.assertEqual(captured[0][3],'application/json')
            self.assertEqual(captured[0][4]['reasoning_effort'],'none')
            self.assertEqual(captured[0][4]['model'],'gpt-6-luna')
            self.assertEqual([m['role'] for m in captured[0][4]['messages']],['system','user'])
            self.assertIn('prompt_sha256',meta)
            self.assertNotIn('fixture-bearer-secret',output.read_text())
            self.assertNotIn('fixture-bearer-secret',output.with_suffix('.meta.json').read_text())
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_llm_invalid_choice_is_error(self):
        response={'choices':[{'message':{'content':json.dumps({
            'initial_owner':'invented','priority':'P2','next_check':'monitor','insufficient_evidence':'no'})}}]}
        with self.assertRaisesRegex(ValueError,'Invalid choice for initial_owner'):
            normalize_llm(response)

    def test_llm_retries_a_rate_limit_without_scoring_a_failure(self):
        requests=[]
        expected=self.keys[0]['labels']
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                requests.append(self.path)
                if len(requests)==1:
                    self.send_response(429);self.send_header('Retry-After','0');self.end_headers()
                else:
                    response={'model':'fixture','choices':[{'finish_reason':'stop',
                              'message':{'content':json.dumps(expected)}}]}
                    self.send_response(200);self.send_header('Content-Type','application/json')
                    self.end_headers();self.wfile.write(json.dumps(response).encode())
            def log_message(self,*args):pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch('triage_bench.runner.time.sleep') as wait:
                output=self.root/'rate-limit.jsonl'
                run(self.root/'data/test.inputs.jsonl',output,provider='llm',model='fixture',
                    endpoint=f'http://127.0.0.1:{server.server_port}/v1',limit=1,
                    context_tokens=32768,deployment='fixture')
            row=read_jsonl(output)[0]
            self.assertEqual(row['status'],'ok')
            self.assertEqual(row['rate_limit_retries'],1)
            self.assertEqual(len(requests),2)
            wait.assert_called_once_with(1)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_nonfinite_provider_metadata_is_record_error(self):
        response=self.response()
        response['usage']={'input_tokens':float('inf')}
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                self.rfile.read(int(self.headers['Content-Length']))
                self.send_response(200); self.send_header('Content-Type','application/json'); self.end_headers()
                self.wfile.write(json.dumps(response).encode())
            def log_message(self,*args): pass
        server=HTTPServer(('127.0.0.1',0),Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        try:
            path=self.root/'nonfinite.jsonl'
            run(self.root/'data/test.inputs.jsonl',path,provider='laya',model='fixture-model',
                endpoint=f'http://127.0.0.1:{server.server_port}/v1/systemone',limit=1,
                context_tokens=16384,deployment='fixture')
            row=read_jsonl(path)[0]
            self.assertEqual(row['status'],'error')
            self.assertNotIn('Infinity',path.read_text())
            self.assertNotIn('NaN',path.read_text())
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
