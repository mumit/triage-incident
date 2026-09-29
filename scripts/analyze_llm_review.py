"""Compare completed blind reviews with provisional labels, or verify evidence."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.llm_review import export, verify_evidence  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/workflow-study/draft.inputs.jsonl')
    parser.add_argument('--labels', type=Path, default=ROOT / 'data/workflow-study/draft.labels.jsonl')
    parser.add_argument('--predictions', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--evidence', type=Path)
    args = parser.parse_args()
    if args.evidence:
        if args.predictions or args.output_dir:
            parser.error('Verification does not accept predictions or output-dir')
        snapshot = verify_evidence(args.evidence, args.inputs, args.labels)
    else:
        if not args.predictions or not args.output_dir:
            parser.error('Export requires --predictions and --output-dir')
        snapshot = export(args.inputs, args.labels, args.predictions, args.output_dir)
    print(json.dumps({key: value for key, value in snapshot['comparison'].items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
