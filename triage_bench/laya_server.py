"""A small loopback server that pins Laya and rejects context truncation."""
import argparse
import importlib.metadata
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8000)
    parser.add_argument('--device',choices=['cpu','mps','cuda'],default=None)
    parser.add_argument('--revision',default=None,help='Hugging Face revision; default resolves main to a commit once at startup')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    os.environ.setdefault('HF_HOME',str(root/'.cache'/'huggingface'))
    os.environ.setdefault('USE_TF','0')
    import laya
    import torch
    from huggingface_hub import HfApi
    model_id='convaiinnovations/laya'
    revision=HfApi().model_info(model_id,revision=args.revision or 'main').sha
    device=args.device or ('mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu')
    print(f'Loading Laya multilingual revision {revision} on {device}...',flush=True)
    agent=laya.load(model_id,subfolder='multilingual',revision=revision,device=device)
    capacity,head_capacity=8192,512
    identity=f'laya-multilingual@{revision}'
    metadata=dict(model=identity,device=device,max_len=capacity,head_max_len=head_capacity,
                  laya_version=importlib.metadata.version('laya'),torch_version=torch.__version__)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,value):
            data=json.dumps(value).encode()
            self.send_response(status); self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            if self.path=='/health': return self.send(200,metadata)
            self.send(404,{'error':'Not found'})
        def do_POST(self):
            if self.path!='/v1/systemone': return self.send(404,{'error':'Not found'})
            if self.headers.get('Origin') or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send(403,{'error':'Use a server-side JSON client.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=262144: raise ValueError('Invalid request size')
                body=json.loads(self.rfile.read(size))
                if body.get('model') not in ['laya-multilingual',identity]: raise ValueError('This server hosts laya-multilingual only.')
                state=body['state']; questions=body['questions']
                if not isinstance(state,str) or not isinstance(questions,dict) or not 1<=len(questions)<=8:
                    raise ValueError('Expected text state and 1–8 questions.')
                state_tokens=len(agent.tok.encode(state,add_special_tokens=False))
                for question in questions.values():
                    question_tokens=len(agent.tok.encode(json.dumps(question),add_special_tokens=False))
                    if question_tokens+64>head_capacity or state_tokens+question_tokens+256>capacity:
                        raise ValueError('Input exceeds tokenizer preflight budget; refused instead of truncating.')
                result=agent.predict(state,questions,max_len=capacity,head_max_len=head_capacity)
                result['model']=identity
                result['deployment']=metadata
                self.send(200,result)
            except (ValueError,KeyError,TypeError) as exc:
                self.send(422,{'error':str(exc)})
            except Exception as exc:
                print(f'Inference error: {type(exc).__name__}: {exc}',flush=True)
                self.send(500,{'error':'Local model inference failed; inspect the server terminal.'})
    server=HTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Laya ready: http://127.0.0.1:{args.port}/v1/systemone',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()


if __name__=='__main__': main()
