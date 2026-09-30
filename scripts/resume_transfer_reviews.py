"""Resume interrupted transfer reviews serially, preserving every attempt.

Selection uses the first structurally valid response, never agreement with labels.
Input issues still enter the family exclusion filter after review consolidation.
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.app import load_env  # noqa: E402
from triage_bench.dataset import read_jsonl,write_jsonl  # noqa: E402
from triage_bench import llm_review,llm_review_v2  # noqa: E402


def consolidate(inputs,attempts,output):
    records=read_jsonl(inputs);selected={};sources=[]
    for path in attempts:
        rows=read_jsonl(path);meta=json.loads(path.with_suffix('.meta.json').read_text())
        subset=path.parent/'inputs.jsonl'
        attempt_inputs=read_jsonl(subset) if subset.exists() else records
        expected_hash=llm_review.sha(subset) if subset.exists() else llm_review.sha(inputs)
        llm_review.verify_run(attempt_inputs,rows,meta,expected_hash)
        if any(r not in records for r in attempt_inputs):
            raise ValueError('Continuation changed original incident facts')
        sources.append({'path':str(path),'sha256':llm_review.sha(path),'metadata':meta,
                        'inputs':attempt_inputs,'input_text':subset.read_text() if subset.exists() else Path(inputs).read_text(),
                        'rows':rows,'prediction_text':path.read_text()})
        for row in rows:
            if row['id'] not in selected or (selected[row['id']]['status']!='ok' and row['status']=='ok'):
                selected[row['id']]=row
    rows=[selected[r['id']] for r in records if r['id'] in selected]
    meta={**sources[0]['metadata'],'input_sha256':llm_review.sha(inputs),'records':len(records),
          'failed_records':sum(r['status']!='ok' for r in rows),'successful_records':sum(r['status']=='ok' for r in rows),
          'missing_records':len(records)-len(rows),'execution':'First valid response across preserved initial and serial continuation attempts; no label-based selection',
          'review_attempts':sources,'interrupted':False,'wall_seconds':None}
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=False)
    write_jsonl(output,rows);meta['prediction_sha256']=llm_review.sha(output)
    output.with_suffix('.meta.json').write_text(json.dumps(meta,indent=2)+'\n')
    shutil.copyfile(attempts[0].with_suffix('.source.py'),output.with_suffix('.source.py'))
    shutil.copyfile(attempts[0].with_suffix('.runner.py'),output.with_suffix('.runner.py'))
    llm_review.verify_run(records,rows,meta,llm_review.sha(inputs))
    return meta


def resume(env_file):
    load_env(env_file);key=os.getenv('FUELIX_BEARER_TOKEN','');endpoint=os.getenv('LLM_BASE_URL','')
    if not key or not endpoint:raise ValueError('Fuel iX token and base URL required')
    jobs=[('luna-train','data/encoder-transfer-v1/train.inputs.jsonl','gpt-6-luna'),
          ('luna-development','data/encoder-transfer-v1/development.inputs.jsonl','gpt-6-luna'),
          ('sol-development','data/encoder-transfer-v1/development.inputs.jsonl','gpt-6-sol'),
          ('sol-training-audit','examples/encoder-transfer/training-audit-inputs/inputs.jsonl','gpt-6-sol')]
    # Allow the previous overlapping streams' rate window to expire.
    print('Cooling down for 45 seconds before serial continuation',flush=True);time.sleep(45)
    for name,inputs,model in jobs:
        inputs=ROOT/inputs;records=read_jsonl(inputs)
        attempts=[ROOT/'runs/encoder-transfer'/(name+'-01')/'review.jsonl']
        for number in range(2,5):
            valid={r['id'] for path in attempts for r in read_jsonl(path) if r['status']=='ok'}
            pending=[r for r in records if r['id'] not in valid]
            if not pending:break
            directory=ROOT/'runs/encoder-transfer'/f'{name}-{number:02d}'
            directory.mkdir(parents=True,exist_ok=False)
            subset=directory/'inputs.jsonl';write_jsonl(subset,pending)
            path=directory/'review.jsonl'
            meta=llm_review.run(subset,path,model,endpoint,key,min_interval=8 if number==2 else 15,
                               review_protocol=llm_review_v2,
                               progress=lambda index,count,row:print(f'{name} continuation {number}: {index}/{count} {row["status"]}',flush=True))
            attempts.append(path)
            if meta['failed_records']:
                print('Preserving failed continuation; cooling down before next attempt',flush=True);time.sleep(45)
        final=ROOT/'runs/encoder-transfer'/(name+'-consolidated')/'review.jsonl'
        meta=consolidate(inputs,attempts,final)
        print(name,'consolidated',meta['successful_records'],'valid;',meta['failed_records'],'failed;',meta['missing_records'],'missing',flush=True)
        if meta['failed_records'] or meta['missing_records']:
            raise RuntimeError('Required reviews incomplete after bounded serial continuation')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--env-file',type=Path,required=True)
    resume(p.parse_args().env_file)
