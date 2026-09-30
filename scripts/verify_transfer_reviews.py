"""Verify first-valid continuation selection and every archived review attempt."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.llm_review import verify_evidence,verify_run  # noqa: E402
from triage_bench.dataset import read_jsonl  # noqa: E402


def verify(path,inputs,labels):
    evidence=verify_evidence(path,inputs,labels)
    records={r['id']:r for r in read_jsonl(inputs)}
    selected={}
    for attempt in evidence['metadata']['review_attempts']:
        if (hashlib.sha256(attempt['prediction_text'].encode()).hexdigest()!=attempt['sha256']
                or [json.loads(line) for line in attempt['prediction_text'].splitlines()]!=attempt['rows']):
            raise ValueError('Archived attempt response hash differs')
        if (hashlib.sha256(attempt['input_text'].encode()).hexdigest()!=attempt['metadata']['input_sha256']
                or [json.loads(line) for line in attempt['input_text'].splitlines()]!=attempt['inputs']):
            raise ValueError('Archived attempt input hash differs')
        for record in attempt['inputs']:
            if records.get(record['id'])!=record:raise ValueError('Attempt changed incident facts')
        verify_run(attempt['inputs'],attempt['rows'],attempt['metadata'],attempt['metadata']['input_sha256'])
        for row in attempt['rows']:
            if row['id'] not in selected or (selected[row['id']]['status']!='ok' and row['status']=='ok'):
                selected[row['id']]=row
    if [selected[r['id']] for r in records.values() if r['id'] in selected] != evidence['reviews']:
        raise ValueError('Consolidated review differs from first valid attempt')
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('evidence','inputs','labels'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();e=verify(a.evidence,a.inputs,a.labels)
    print('Verified all attempts and first-valid selection:',len(e['reviews']),'reviews')
