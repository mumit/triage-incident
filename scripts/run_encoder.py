"""Run the trained encoder on public incident inputs and optionally score it."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.encoder import predict_file  # noqa: E402
from triage_bench.evaluate import evaluate  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--split', choices=('validation', 'test', 'challenge'), required=True)
    parser.add_argument('--model-dir', type=Path, default=ROOT / 'runs/encoder/minilm-v1')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--guards', choices=('none', 'policy-v1'), default='none')
    args = parser.parse_args()
    inputs = ROOT / f'data/{args.split}.inputs.jsonl'
    predict_file(inputs, args.output, args.model_dir, guards=args.guards)
    metrics = evaluate(ROOT / f'data/{args.split}.labels.jsonl', args.output,
                       args.output.with_suffix('.metrics.json'))
    print(json.dumps({'split': args.split, 'records': metrics['records'],
                      'all_fields_correct': round(metrics['all_fields_accuracy'] * metrics['records']),
                      'all_fields_accuracy': metrics['all_fields_accuracy'],
                      'p1_miss_rate': metrics['p1_miss_rate'],
                      'pair_all_fields_accuracy': metrics['pair_all_fields_accuracy'],
                      'latency_ms': metrics['successful_latency_ms']}, indent=2))


if __name__ == '__main__':
    main()
