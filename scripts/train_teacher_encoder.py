"""Train a separate teacher-reviewed encoder head; select settings on development."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.teacher_encoder import train  # noqa: E402
from triage_bench.teacher_training import validate  # noqa: E402

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('train-inputs','train-labels','dev-inputs','dev-labels','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    validate(args.train_inputs,args.train_labels,args.dev_inputs,args.dev_labels)
    train(args.train_inputs,args.train_labels,args.dev_inputs,args.dev_labels,args.output_dir)

if __name__=='__main__':
    main()
