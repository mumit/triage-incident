"""Run the frozen encoder reference on a new study's public inputs."""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.encoder import predict_file  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model-dir', type=Path, default=ROOT / 'runs/encoder/minilm-v1')
    args = parser.parse_args()
    expected = json.loads((ROOT / 'examples/encoder-evaluation.evidence.json').read_text())['head_sha256']
    if hashlib.sha256((args.model_dir / 'head.npz').read_bytes()).hexdigest() != expected:
        raise ValueError('Head differs from the frozen encoder reference; use a separate variant')
    rows = predict_file(args.inputs, args.output, args.model_dir, guards='none')
    print(json.dumps({'records': len(rows), 'output': str(args.output),
                      'reference_head_sha256': expected}, indent=2))


if __name__ == '__main__':
    main()
