"""Fit fixed-L2 frozen encoder heads with and without structured features."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.transfer_encoder import train  # noqa: E402

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('train-inputs','train-labels','dev-inputs','dev-labels','output-dir'):
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args()
    train(a.train_inputs,a.train_labels,a.dev_inputs,a.dev_labels,a.output_dir)
