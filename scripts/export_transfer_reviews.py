"""Rebuild auditable first-valid review evidence from preserved attempts."""

import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.resume_transfer_reviews import consolidate  # noqa: E402
from scripts.verify_transfer_reviews import verify  # noqa: E402
from triage_bench.llm_review import export  # noqa: E402


def export_all(output):
    output=Path(output)
    jobs=[('luna-train','data/encoder-transfer-v1/train.inputs.jsonl','data/encoder-transfer-v1/train.reference.labels.jsonl'),
          ('luna-development','data/encoder-transfer-v1/development.inputs.jsonl','data/encoder-transfer-v1/development.reference.labels.jsonl'),
          ('sol-development','data/encoder-transfer-v1/development.inputs.jsonl','data/encoder-transfer-v1/development.reference.labels.jsonl'),
          ('sol-training-audit','examples/encoder-transfer/training-audit-inputs/inputs.jsonl','examples/encoder-transfer/training-audit-inputs/reference.labels.jsonl')]
    for name,inputs,labels in jobs:
        inputs=ROOT/inputs;labels=ROOT/labels
        attempts=sorted((ROOT/'runs/encoder-transfer').glob(name+'-[0-9][0-9]/review.jsonl'))
        path=ROOT/'runs/encoder-transfer'/(name+'-auditable')/'review.jsonl'
        if not path.exists():
            consolidate(inputs,attempts,path)
        evidence=export(inputs,labels,path,output/(name+'-01'))
        verify(output/(name+'-01/evidence.json'),inputs,labels)
        print(name,evidence['comparison']['all_four_agree'],'/',evidence['comparison']['records'],'reference agreement;',
              evidence['comparison']['requires_adjudication'],'flags',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output-dir',type=Path,required=True)
    export_all(p.parse_args().output_dir)
