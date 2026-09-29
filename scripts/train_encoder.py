"""Train the frozen MiniLM incident classifier on the Northstar training set."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.encoder import fit_head  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'runs/encoder/minilm-v1')
    args = parser.parse_args()
    result = fit_head(ROOT / 'data/train.inputs.jsonl', ROOT / 'data/train.labels.jsonl',
                      ROOT / 'data/validation.inputs.jsonl', ROOT / 'data/validation.labels.jsonl', args.output)
    print(json.dumps({'output': str(args.output), 'validation_correct': result['validation_correct'],
                      'validation_rows': result['validation_rows']}, indent=2))


if __name__ == '__main__':
    main()
