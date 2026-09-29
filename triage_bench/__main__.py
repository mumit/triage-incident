import argparse
import json
from pathlib import Path
from .dataset import ROOT, generate, read_jsonl, write_jsonl
from .evaluate import evaluate
from .runner import run, request_body
from .validate import validate


def main():
    parser = argparse.ArgumentParser(description='Northstar Networks synthetic incident benchmark')
    sub = parser.add_subparsers(dest='command', required=True)
    g = sub.add_parser('generate'); g.add_argument('--output',type=Path,default=ROOT/'data')
    v = sub.add_parser('validate'); v.add_argument('--data',type=Path,default=ROOT/'data')
    r = sub.add_parser('run')
    r.add_argument('--inputs',required=True,type=Path); r.add_argument('--output',required=True,type=Path)
    r.add_argument('--provider',choices=['baseline','jev','kev','laya','clm','llm'],default='baseline')
    r.add_argument('--model'); r.add_argument('--endpoint'); r.add_argument('--key-env')
    r.add_argument('--limit',type=int); r.add_argument('--timeout',type=float,default=60)
    r.add_argument('--context-tokens',type=int); r.add_argument('--deployment')
    r.add_argument('--reasoning-effort',choices=['default','none','low','medium','high'],default='none')
    e = sub.add_parser('evaluate')
    e.add_argument('--labels',required=True,type=Path); e.add_argument('--predictions',required=True,type=Path)
    e.add_argument('--output',required=True,type=Path)
    x = sub.add_parser('export-training')
    x.add_argument('--split',choices=['train','validation'],default='train')
    x.add_argument('--data',type=Path,default=ROOT/'data'); x.add_argument('--output',required=True,type=Path)
    args = vars(parser.parse_args()); command = args.pop('command')
    if command=='generate': result=generate(**args)
    elif command=='validate': result=validate(args['data'])
    elif command=='run': result=run(**args)
    elif command=='evaluate':
        result=evaluate(args['labels'],args['predictions'],args['output'])
        result={k:v for k,v in result.items() if k!='fields'}
    else:
        records=read_jsonl(args['data']/f'{args["split"]}.inputs.jsonl')
        labels={k['id']:k for k in read_jsonl(args['data']/f'{args["split"]}.labels.jsonl')}
        rows=[]
        for record in records:
            body=request_body(record,'training-export'); body.pop('model')
            rows.append({'id':record['id'],**body,'answers':labels[record['id']]['labels'],
                         'accepted_answers':labels[record['id']]['accepted_answers']})
        write_jsonl(args['output'],rows)
        result={'records':len(rows),'format':'Model-neutral supervised examples; adapt to the trainer of your chosen model.'}
    print(json.dumps(result,indent=2))
    if command == 'run' and result.get('failed_records', 0):
        raise SystemExit(2)


if __name__=='__main__':
    main()
