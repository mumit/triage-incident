"""Evaluate saved transfer runs on old, new and combined development separately."""

import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.dataset import read_jsonl,write_jsonl  # noqa: E402
from triage_bench.teacher_encoder import sha  # noqa: E402
from triage_bench.study_evidence import summarize  # noqa: E402
from scripts.teacher_encoder_evidence import export  # noqa: E402


def evaluate(release,runroot,output):
    release=Path(release);runroot=Path(runroot);output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    old_inputs=ROOT/'examples/review/development-v2-reviewed-release/candidate.inputs.jsonl'
    old_labels=ROOT/'examples/review/development-v2-reviewed-release/candidate.labels.jsonl'
    cohorts={'old-development':(old_inputs,old_labels),
             'new-development':(release/'new-development.inputs.jsonl',release/'new-development.labels.jsonl'),
             'combined-development':(release/'development.inputs.jsonl',release/'development.labels.jsonl'),
             'training':(release/'train.inputs.jsonl',release/'train.labels.jsonl')}
    models=['previous-head','expanded-structured','expanded-text-only','finetuned-17','finetuned-29','luna-classifier']
    summary={}
    for cohort,(inputs,labels) in cohorts.items():
        records=read_jsonl(inputs);ids={r['id'] for r in records};runs={}
        for model in models:
            if cohort=='training' and model in ('previous-head','luna-classifier'):continue
            source=runroot/model/('training.predictions.jsonl' if cohort=='training' else 'development.predictions.jsonl')
            if not source.exists():continue
            rows=[r for r in read_jsonl(source) if r['id'] in ids]
            path=output/'sliced'/cohort/(model+'.jsonl');write_jsonl(path,rows)
            metadata=json.loads(source.with_suffix('.meta.json').read_text())
            metadata={**metadata,'source_input_sha256':metadata['input_sha256'],'source_prediction_sha256':sha(source),
                      'input_sha256':sha(inputs),'subset':'Post-inference ID selection only; no modified predictions',
                      'records':len(records),'failed_records':sum(r['status']!='ok' for r in rows)}
            path.with_suffix('.meta.json').write_text(json.dumps(metadata,indent=2)+'\n')
            runs[model]=path
        snapshot=export(inputs,labels,runs,output/(cohort+'.evidence.json'),
                        'training diagnostic' if cohort=='training' else 'development selection; not holdout')
        summary[cohort]={name:r['summary'] for name,r in snapshot['runs'].items()}
        for name,s in summary[cohort].items():print(cohort,name,s['all_four_correct'],'/',s['records'],'pairs',s['complete_pairs'],'/',s['pairs'])
    (output/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('release','run-root','output-dir'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();evaluate(a.release,a.run_root,a.output_dir)
