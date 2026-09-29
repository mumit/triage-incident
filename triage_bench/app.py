"""Loopback-only comparison app. API secrets stay in server memory."""
import argparse
import copy
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from .dataset import ROOT, read_jsonl, write_jsonl
from .evaluate import evaluate
from .runner import run

PROVIDERS = ['baseline', 'encoder', 'encoder_guarded', 'jev', 'kev', 'laya', 'clm', 'llm']
SPLITS = ['validation', 'test', 'challenge']


def load_env(path):
    """Small KEY=value loader: no shell evaluation; existing environment wins."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        if not sep or not key.replace('_', '').isalnum():
            raise ValueError('Invalid .env line; use KEY=value without shell expressions.')
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        os.environ.setdefault(key, value)


def profiles():
    return {
        'baseline': dict(model='keyword-baseline', endpoint='', context_tokens=8192,
                         deployment='Local deterministic rules', api_key=''),
        'encoder': dict(model='MiniLM-L6-v2 + trained head', endpoint='', context_tokens=256,
                        deployment='Local frozen encoder; raw seven-class decision', api_key=''),
        'encoder_guarded': dict(model='MiniLM-L6-v2 + trained head + policy guards', endpoint='', context_tokens=256,
                                deployment='Local frozen encoder; explicit freshness and topology vetoes', api_key=''),
        'jev': dict(model=os.getenv('JEV_MODEL', 'jev-latest'), endpoint=os.getenv('JEV_ENDPOINT', 'https://api.typesafe.ai/v1/systemone'),
                    context_tokens=int(os.getenv('JEV_CONTEXT_TOKENS', '8192')), deployment='Hosted Jev API', api_key=os.getenv('TYPESAFE_API_KEY', '')),
        'kev': dict(model=os.getenv('KEV_MODEL', 'kev-latest'), endpoint=os.getenv('KEV_ENDPOINT', 'http://127.0.0.1:8009/v1/systemone'),
                    context_tokens=int(os.getenv('KEV_CONTEXT_TOKENS', '8192')), deployment='Local Kev-4B; record checkpoint revision, backend and precision', api_key=os.getenv('KEV_API_KEY', '')),
        'laya': dict(model=os.getenv('LAYA_MODEL', 'laya-multilingual'), endpoint=os.getenv('LAYA_ENDPOINT', 'http://127.0.0.1:8000/v1/systemone'),
                     context_tokens=8192, deployment='Local Laya multilingual; inspect server health for device and revision', api_key=os.getenv('LAYA_API_KEY', '')),
        'clm': dict(model=os.getenv('CLM_MODEL', 'clm-mlx-bf16'), endpoint=os.getenv('CLM_ENDPOINT', 'http://127.0.0.1:8700/v1/systemone'),
                    context_tokens=8192, deployment='CLM-8B / MLX bf16 / Apple Silicon; record chip and revisions', api_key=os.getenv('CLM_API_KEY', '')),
        'llm': dict(model=os.getenv('LLM_MODEL', 'gpt-6-luna'), endpoint=os.getenv('LLM_BASE_URL', ''),
                    context_tokens=int(os.getenv('LLM_CONTEXT_TOKENS', '32768')),
                    deployment='Fuel iX proxy / OpenAI-compatible chat completions',
                    api_key=os.getenv('FUELIX_BEARER_TOKEN', ''),
                    reasoning_effort=os.getenv('LLM_REASONING_EFFORT', 'none'))}


class App:
    def __init__(self, root=ROOT):
        self.root = Path(root)
        self.profiles = profiles()
        self.lock = threading.RLock()
        self.jobs = {}
        self.stops = {}
        self.run_root = self.root / 'runs' / 'app'
        self.run_root.mkdir(parents=True, exist_ok=True)
        for path in self.run_root.glob('*/job.json'):
            try:
                job = json.loads(path.read_text())
                if job['status'] in ['running', 'queued']:
                    job['status'] = 'interrupted'
                self.jobs[job['id']] = job
            except (OSError, ValueError, KeyError):
                continue

    def config(self):
        with self.lock:
            return {name: {**{k:v for k,v in cfg.items() if k != 'api_key'},
                           'key_configured': bool(cfg['api_key'])} for name,cfg in self.profiles.items()}

    def configure(self, payload):
        name = payload.get('provider')
        if name not in PROVIDERS or name in {'baseline', 'encoder', 'encoder_guarded'}:
            raise ValueError('Choose Jev, Kev, Laya, CLM or LLM.')
        endpoint = str(payload.get('endpoint', '')).strip()
        url = urlparse(endpoint)
        if url.username or url.password or url.query or url.fragment or not url.hostname:
            raise ValueError('Use an endpoint without credentials or query parameters.')
        if url.scheme != 'https' and not (url.scheme == 'http' and url.hostname in ['localhost','127.0.0.1','::1']):
            raise ValueError('Use HTTPS or a loopback HTTP endpoint.')
        model = str(payload.get('model','')).strip()
        capacity = int(payload.get('context_tokens',8192))
        if not model or not 512 <= capacity <= 1000000:
            raise ValueError('Supply a model name and a valid context capacity.')
        reasoning_effort = str(payload.get('reasoning_effort', 'none'))
        if name == 'llm' and reasoning_effort not in {'default', 'none', 'low', 'medium', 'high'}:
            raise ValueError('Choose a valid LLM reasoning effort.')
        with self.lock:
            previous = self.profiles[name]
            key = str(payload.get('api_key','')).strip()
            if any(ord(c) < 32 for c in key):
                raise ValueError('API key contains invalid control characters.')
            if not key and endpoint == previous['endpoint'] and not payload.get('clear_key'):
                key = previous['api_key']
            self.profiles[name] = dict(model=model, endpoint=endpoint, context_tokens=capacity,
                deployment=str(payload.get('deployment','Unspecified deployment')).strip(), api_key=key)
            if name == 'llm':
                self.profiles[name]['reasoning_effort'] = reasoning_effort
        return self.config()

    def incidents(self, split):
        if split not in SPLITS:
            raise ValueError('Unknown evaluation split.')
        keys = {k['id']: k for k in read_jsonl(self.root / 'data' / f'{split}.labels.jsonl')}
        return [{'id':r['id'], 'input':r['input'], 'labels':keys[r['id']]['labels'],
                 'accepted_answers':keys[r['id']]['accepted_answers'],
                 'family':keys[r['id']]['incident_family_id'], 'pair_id':keys[r['id']].get('pair_id')}
                for r in read_jsonl(self.root / 'data' / f'{split}.inputs.jsonl')]

    def save(self, job):
        path = self.run_root / job['id'] / 'job.json'
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(job, indent=2) + '\n')
        temp.replace(path)

    def encoder_model_dir(self):
        return Path(os.getenv('ENCODER_MODEL_DIR', str(self.root / 'runs/encoder/minilm-v1')))

    def start(self, payload):
        split = payload.get('split', 'validation')
        chosen = payload.get('providers', [])
        if not isinstance(chosen,list) or not chosen or len(chosen)!=len(set(chosen)) or any(p not in PROVIDERS for p in chosen):
            raise ValueError('Select at least one distinct supported model.')
        if split not in SPLITS:
            raise ValueError('Unknown split.')
        records = read_jsonl(self.root / 'data' / f'{split}.inputs.jsonl')
        keys = read_jsonl(self.root / 'data' / f'{split}.labels.jsonl')
        record_id = payload.get('record_id')
        if record_id:
            records = [r for r in records if r['id']==record_id]
        else:
            count = int(payload.get('count', 5))
            if not 1 <= count <= len(records):
                raise ValueError('Invalid sample size.')
            if split == 'challenge':
                if count % 2:
                    raise ValueError('Challenge batches require an even count to keep pairs together.')
                pair_ids = list(dict.fromkeys(k['pair_id'] for k in keys))[:count//2]
                selected_ids = {k['id'] for k in keys if k['pair_id'] in pair_ids}
                records = [r for r in records if r['id'] in selected_ids]
            else:
                records = records[:count]
        if not records:
            raise ValueError('Incident not found.')
        ids = {r['id'] for r in records}
        keys = [k for k in keys if k['id'] in ids]
        with self.lock:
            if any(j['status'] in ['running','queued'] for j in self.jobs.values()):
                raise ValueError('Another comparison is running. Finish or cancel it first.')
            config = {name:copy.deepcopy(self.profiles[name]) for name in chosen}
            if 'jev' in chosen and not config['jev']['api_key']:
                raise ValueError('Add your Jev API key in Settings first.')
            if 'llm' in chosen:
                if not config['llm']['endpoint']:
                    raise ValueError('Add your Fuel iX base URL in Settings first.')
                if not config['llm']['api_key']:
                    raise ValueError('Add your Fuel iX bearer token in Settings first.')
            if any(name in chosen for name in ('encoder', 'encoder_guarded')):
                if not (self.encoder_model_dir() / 'head.npz').is_file():
                    raise ValueError('Train the local encoder first with scripts/train_encoder.py.')
            job_id = uuid.uuid4().hex[:16]
            directory = self.run_root / job_id
            directory.mkdir()
            write_jsonl(directory/'inputs.jsonl',records)
            write_jsonl(directory/'labels.jsonl',keys)
            job = dict(id=job_id, split=split, count=len(records), providers=chosen,
                       created_at=datetime.now(timezone.utc).isoformat(), status='queued',
                       completed=0, total=len(records)*len(chosen), current_provider=None, results={})
            self.jobs[job_id] = job
            self.stops[job_id] = threading.Event()
            self.save(job)
            threading.Thread(target=self.worker,args=(job_id,config),daemon=True).start()
            return copy.deepcopy(job)

    def worker(self, job_id, config):
        directory = self.run_root / job_id
        with self.lock:
            job = self.jobs[job_id]
            job['status']='running'
        stop = self.stops[job_id]
        for name, cfg in config.items():
            if stop.is_set(): break
            with self.lock:
                job['current_provider']=name
                before=job['completed']
            def progress(done, total, row):
                with self.lock:
                    job['completed']=before+done
            output = directory/f'{name}.jsonl'
            try:
                if name in {'encoder', 'encoder_guarded'}:
                    from .encoder import predict_file
                    predict_file(directory/'inputs.jsonl', output, self.encoder_model_dir(),
                                 guards='policy-v1' if name == 'encoder_guarded' else 'none',
                                 progress=progress, stop_event=stop)
                    meta = json.loads(output.with_suffix('.meta.json').read_text())
                    meta['deployment'] = cfg['deployment']
                else:
                    meta = run(directory/'inputs.jsonl',output,provider=name,stop_event=stop,progress=progress,timeout=300,**cfg)
                metrics = evaluate(directory/'labels.jsonl',output,directory/f'{name}.metrics.json')
                rows = read_jsonl(output)
                public_rows = [{k:v for k,v in row.items() if k!='raw_response'} for row in rows]
                result = {'metrics':metrics,'metadata':meta,'predictions':public_rows}
            except Exception as exc:
                # Never emit request bodies or credential-bearing tracebacks to browser/logs.
                result={'error':f'Comparison failed ({type(exc).__name__}). Check deployment settings and server availability.'}
            with self.lock:
                job['results'][name]=result
                self.save(job)
        with self.lock:
            errors = any('error' in r or r.get('metadata',{}).get('failed_records',0) for r in job['results'].values())
            job['status']='cancelled' if stop.is_set() else ('completed_with_errors' if errors else 'completed')
            job['current_provider']=None
            self.save(job)

    def snapshot(self, job_id):
        with self.lock:
            if job_id not in self.jobs: raise ValueError('Unknown comparison.')
            return copy.deepcopy(self.jobs[job_id])

    def cancel(self, job_id):
        with self.lock:
            if job_id not in self.stops: raise ValueError('No running comparison with that ID.')
            self.stops[job_id].set()
        return {'ok':True}


def handler_for(app):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def trusted(self):
            expected = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            if self.headers.get('Host') not in expected: return False
            origin=self.headers.get('Origin')
            return not origin or origin in {'http://'+host for host in expected}

        def send(self, status, body, content_type='application/json'):
            data=body if isinstance(body,bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if not self.trusted(): return self.send(403,{'error':'Local origin required.'})
            path=urlparse(self.path)
            try:
                if path.path=='/api/config': return self.send(200,app.config())
                if path.path=='/api/incidents': return self.send(200,app.incidents(parse_qs(path.query).get('split',['validation'])[0]))
                if path.path=='/api/jobs':
                    with app.lock:
                        jobs=[{k:v for k,v in j.items() if k!='results'} for j in app.jobs.values()]
                    return self.send(200,sorted(jobs,key=lambda j:j['created_at'],reverse=True))
                if path.path.startswith('/api/jobs/'):
                    return self.send(200,app.snapshot(path.path.split('/')[-1]))
                assets={'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript'),'/style.css':('style.css','text/css')}
                if path.path in assets:
                    filename,mime=assets[path.path]
                    return self.send(200,(Path(__file__).parent/'web'/filename).read_bytes(),mime)
                return self.send(404,{'error':'Not found.'})
            except (ValueError,KeyError) as exc:
                self.send(400,{'error':str(exc)})

        def do_POST(self):
            if not self.trusted(): return self.send(403,{'error':'Local origin required.'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send(415,{'error':'Use JSON.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=65536: raise ValueError('Invalid request size.')
                data=json.loads(self.rfile.read(size))
                if not isinstance(data,dict): raise ValueError('Expected a JSON object.')
                if self.path=='/api/config': return self.send(200,app.configure(data))
                if self.path=='/api/jobs': return self.send(202,app.start(data))
                if self.path=='/api/cancel': return self.send(200,app.cancel(data.get('id')))
                return self.send(404,{'error':'Not found.'})
            except (ValueError,TypeError,KeyError) as exc:
                self.send(400,{'error':str(exc)})
    return Handler


def main():
    parser=argparse.ArgumentParser(description='Northstar model comparison app')
    parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    load_env(ROOT/'.env')
    app=App()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler_for(app))
    print(f'Northstar comparison app: http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=='__main__': main()
