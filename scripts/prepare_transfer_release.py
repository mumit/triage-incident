"""Combine accepted new teacher training and development releases with old data."""

import argparse
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.export_teacher_training import build  # noqa: E402
from triage_bench.dataset import read_jsonl,write_jsonl  # noqa: E402
from triage_bench.teacher_encoder import sha  # noqa: E402
from triage_bench.teacher_training import validate  # noqa: E402


def prepare(evidence_root,output):
    evidence_root=Path(evidence_root);output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    source=ROOT/'data/encoder-transfer-v1'
    newtrain=output/'new-training';newdev=output/'new-development'
    audit=evidence_root/'training-audit-inputs'
    train_manifest=build(source/'train.inputs.jsonl',source/'train.reference.labels.jsonl',
                         evidence_root/'luna-train-01/evidence.json',evidence_root/'sol-training-audit-01/evidence.json',
                         audit/'inputs.jsonl',audit/'reference.labels.jsonl',newtrain)
    dev_manifest=build(source/'development.inputs.jsonl',source/'development.reference.labels.jsonl',
                       evidence_root/'luna-development-01/evidence.json',evidence_root/'sol-development-01/evidence.json',
                       source/'development.inputs.jsonl',source/'development.reference.labels.jsonl',newdev)
    # The shared exporter names its outputs "train". Its raw subrelease keeps
    # that schema; combined and new-development files below explicitly mark use.
    oldtrain=ROOT/'examples/teacher-training/release-v1'
    olddev=ROOT/'examples/review/development-v2-reviewed-release'
    for split,new,old,oldprefix in [('train',newtrain,oldtrain,'train'),('development',newdev,olddev,'candidate')]:
        records=read_jsonl(old/(oldprefix+'.inputs.jsonl'))+read_jsonl(new/'train.inputs.jsonl')
        keys=read_jsonl(old/(oldprefix+'.labels.jsonl'))+read_jsonl(new/'train.labels.jsonl')
        for key in keys:
            key['split']='transfer_training' if split=='train' else 'transfer_development'
        write_jsonl(output/(split+'.inputs.jsonl'),records)
        write_jsonl(output/(split+'.labels.jsonl'),keys)
        if split=='development':
            write_jsonl(output/'new-development.inputs.jsonl',read_jsonl(new/'train.inputs.jsonl'))
            newkeys=read_jsonl(new/'train.labels.jsonl')
            for key in newkeys:key['split']='transfer_development'
            write_jsonl(output/'new-development.labels.jsonl',newkeys)
    validate(output/'train.inputs.jsonl',output/'train.labels.jsonl',output/'development.inputs.jsonl',output/'development.labels.jsonl')
    manifest={'use':'Expanded teacher-labeled synthetic training and inspected development; not holdout',
              'new_training':train_manifest,'new_development':dev_manifest,
              'records':{s:len(read_jsonl(output/(s+'.inputs.jsonl'))) for s in ('train','development')},
              'families':{s:len({k['incident_family_id'] for k in read_jsonl(output/(s+'.labels.jsonl'))}) for s in ('train','development')},
              'sha256':{p.name:sha(p) for p in output.iterdir() if p.is_file()}}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--evidence-root',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();print(json.dumps(prepare(a.evidence_root,a.output_dir),indent=2))
