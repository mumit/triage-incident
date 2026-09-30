"""Fit the five predefined L2 candidates, recording convergence and every head."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.encoder_regularization import train  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('train-inputs','train-labels','dev-inputs','dev-labels','output-dir'):
        parser.add_argument('--'+name, type=Path, required=True)
    a = parser.parse_args()
    result = train(a.train_inputs, a.train_labels, a.dev_inputs, a.dev_labels, a.output_dir)
    if not all(t['converged'] for t in result['trials']):
        sys.exit(2)


if __name__ == '__main__':
    main()
