import json
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from triage_bench.app import App, handler_for
from triage_bench.dataset import ROOT, read_jsonl
from triage_bench.mlx_embeddings import validate_embedding_request
from triage_bench.runner import run


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        (self.root/'data').symlink_to(ROOT/'data',target_is_directory=True)
        self.app=App(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def await_job(self,job_id):
        deadline=time.monotonic()+10
        while time.monotonic()<deadline:
            job=self.app.snapshot(job_id)
            if job['status'] not in ['queued','running']:return job
            time.sleep(.02)
        self.fail('Job did not complete')

    def test_baseline_batch_scores_only_selected_records(self):
        job=self.await_job(self.app.start({'providers':['baseline'],'count':5})['id'])
        self.assertEqual(job['status'],'completed')
        self.assertEqual(job['completed'],5)
        m=job['results']['baseline']['metrics']
        self.assertEqual(m['records'],5)
        self.assertEqual(m['missing_records'],0)
        self.assertEqual(len(job['results']['baseline']['predictions']),5)

    def test_single_record(self):
        incident=self.app.incidents('test')[8]
        job=self.await_job(self.app.start({'split':'test','providers':['baseline'],'record_id':incident['id']})['id'])
        self.assertEqual(job['count'],1)
        self.assertEqual(job['results']['baseline']['predictions'][0]['id'],incident['id'])

    def test_challenge_batch_keeps_pairs_together(self):
        job=self.await_job(self.app.start({'split':'challenge','providers':['baseline'],'count':4})['id'])
        self.assertEqual(job['results']['baseline']['metrics']['paired_families'],2)

    def test_odd_challenge_batch_rejected(self):
        with self.assertRaisesRegex(ValueError,'even'):
            self.app.start({'split':'challenge','providers':['baseline'],'count':3})

    def test_secret_never_returned_and_endpoint_change_clears_it(self):
        cfg=self.app.config()['jev']
        self.app.configure({'provider':'jev',**cfg,'api_key':'fixture-secret-not-real'})
        self.assertNotIn('fixture-secret-not-real',json.dumps(self.app.config()))
        self.assertTrue(self.app.config()['jev']['key_configured'])
        self.app.configure({'provider':'jev',**cfg,'endpoint':'https://example.org/v1/systemone'})
        self.assertFalse(self.app.config()['jev']['key_configured'])

    def test_no_key_jev_run_rejected_before_job_creation(self):
        self.app.profiles['jev']['api_key']=''
        with self.assertRaisesRegex(ValueError,'API key'):
            self.app.start({'providers':['jev'],'count':1})
        self.assertFalse(self.app.jobs)

    def test_external_plain_http_rejected(self):
        with self.assertRaisesRegex(ValueError,'HTTPS'):
            self.app.configure({'provider':'laya','model':'x','endpoint':'http://example.org/v1/systemone'})

    def test_history_survives_restart(self):
        job=self.await_job(self.app.start({'providers':['baseline'],'count':1})['id'])
        restored=App(self.root)
        self.assertEqual(restored.snapshot(job['id'])['status'],'completed')

    def test_runner_cancellation_keeps_missing_records_explicit(self):
        stop=threading.Event();stop.set()
        result=run(ROOT/'data/test.inputs.jsonl',self.root/'cancelled.jsonl',stop_event=stop)
        self.assertTrue(result['cancelled'])
        self.assertEqual(result['attempted_records'],0)
        self.assertEqual(read_jsonl(self.root/'cancelled.jsonl'),[])

    def test_http_assets_and_cross_origin_protection(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),handler_for(self.app))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            with urllib.request.urlopen(base) as response:
                self.assertIn(b'Incident Lab',response.read())
                self.assertIn("frame-ancestors 'none'",response.headers['Content-Security-Policy'])
            req=urllib.request.Request(base+'/api/jobs',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://example.org'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
            self.assertEqual(error.exception.code,403)
            req=urllib.request.Request(base+'/api/config',headers={'Host':'rebound.example.org'})
            with self.assertRaises(urllib.error.HTTPError) as error:urllib.request.urlopen(req)
            self.assertEqual(error.exception.code,403)
        finally:
            server.shutdown();server.server_close();thread.join()

    def test_embedding_request_matches_clm_contract(self):
        texts,encoding,budget=validate_embedding_request({'model':'qwen3-8b','input':['state','action'],'encoding_format':'base64','truncate_prompt_tokens':8192},8192)
        self.assertEqual((texts,encoding,budget),(['state','action'],'base64',8192))

    def test_embedding_request_rejects_wrong_encoder(self):
        with self.assertRaises(ValueError):validate_embedding_request({'model':'Qwen3-Embedding-8B','input':['x']},8192)
        with self.assertRaises(ValueError):validate_embedding_request({'model':'qwen3-8b','input':['x'],'truncate_prompt_tokens':99999},8192)


if __name__=='__main__':unittest.main()
