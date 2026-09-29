"""Qwen3 last-token embedding endpoint for the upstream CLM head on Apple Silicon.

No generation, chat template or output projection is used. Model downloads occur
only when this explicitly launched server starts, never when importing this module.
"""
import argparse
import base64
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def validate_embedding_request(body, capacity):
    if body.get('model') != 'qwen3-8b':
        raise ValueError('This endpoint serves qwen3-8b embeddings only.')
    texts=body.get('input')
    if isinstance(texts,str): texts=[texts]
    if not isinstance(texts,list) or not 1<=len(texts)<=64 or any(not isinstance(t,str) or not t for t in texts):
        raise ValueError('input must contain 1–64 nonempty strings.')
    encoding=body.get('encoding_format','float')
    if encoding not in ['float','base64']: raise ValueError('Unsupported encoding format.')
    requested=body.get('truncate_prompt_tokens',capacity)
    if not isinstance(requested,int) or isinstance(requested,bool) or not 1<=requested<=capacity:
        raise ValueError('Invalid requested token budget.')
    return texts,encoding,requested


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',default='czl/CLM-v0.1-8B-MLX')
    parser.add_argument('--revision',default=None)
    parser.add_argument('--port',type=int,default=8092)
    parser.add_argument('--max-tokens',type=int,default=8192)
    parser.add_argument('--instance-id',default=None,help='Startup identity for a supervising script')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    os.environ.setdefault('HF_HOME',str(root/'.cache'/'huggingface'))
    import mlx.core as mx
    import numpy as np
    from mlx_lm import load
    from huggingface_hub import HfApi, snapshot_download
    revision=HfApi().model_info(args.model,revision=args.revision or 'main').sha
    print(f'Loading {args.model}@{revision}. First start downloads weights.',flush=True)
    directory=snapshot_download(args.model,revision=revision,
        allow_patterns=['*.safetensors','*.json','*.model','*.txt'])
    model,tokenizer=load(directory,tokenizer_config={'trust_remote_code':False})
    metadata=dict(model=args.model,revision=revision,runtime='MLX',pooling='last real token after final norm; L2 normalized',
                  dimensions=4096,max_tokens=args.max_tokens,batch_policy='one text at a time; no KV cache',
                  instance_id=args.instance_id)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,value):
            data=json.dumps(value).encode()
            self.send_response(status);self.send_header('Content-Type','application/json')
            self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            if self.path=='/health': return self.send(200,metadata)
            if self.path=='/v1/models': return self.send(200,{'data':[{'id':'qwen3-8b','object':'model'}]})
            self.send(404,{'error':'Not found'})
        def do_POST(self):
            if self.path!='/v1/embeddings':return self.send(404,{'error':'Not found'})
            if self.headers.get('Origin') or self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.send(403,{'error':'Use a server-side JSON client.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1048576:raise ValueError('Invalid request size.')
                texts,encoding,budget=validate_embedding_request(json.loads(self.rfile.read(size)),args.max_tokens)
                token_rows=[tokenizer.encode(text,add_special_tokens=False) for text in texts]
                if any(not tokens or len(tokens)>budget for tokens in token_rows):
                    raise ValueError('Input exceeds token budget; refused instead of truncating.')
                data=[]
                for i,tokens in enumerate(token_rows):
                    # One unpadded row avoids last-padding-token mistakes. model.model is the
                    # Qwen3 backbone and returns post-final-normalization hidden states.
                    hidden=model.model(mx.array([tokens]))
                    vector=hidden[0,-1,:].astype(mx.float32)
                    vector=vector/(mx.linalg.norm(vector)+1e-12)
                    mx.eval(vector)
                    array=np.asarray(vector,dtype=np.float32)
                    if array.shape!=(4096,) or not np.isfinite(array).all():
                        raise ValueError('Encoder does not meet the CLM 4096-dimensional contract.')
                    value=base64.b64encode(array.astype('<f4').tobytes()).decode() if encoding=='base64' else array.tolist()
                    data.append({'object':'embedding','index':i,'embedding':value})
                    del hidden,vector
                    mx.clear_cache()
                count=sum(map(len,token_rows))
                self.send(200,{'object':'list','model':'qwen3-8b','data':data,
                               'usage':{'prompt_tokens':count,'total_tokens':count},'deployment':metadata})
            except (ValueError,KeyError,TypeError) as exc:
                self.send(422,{'error':str(exc)})
            except Exception as exc:
                print(f'Embedding error: {type(exc).__name__}: {exc}',flush=True)
                self.send(500,{'error':'MLX inference failed; inspect the server terminal.'})
    server=HTTPServer(('127.0.0.1',args.port),Handler)
    print(f'MLX embeddings ready: http://127.0.0.1:{args.port}/v1/embeddings',flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()


if __name__=='__main__':main()
