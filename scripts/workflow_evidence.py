"""Export or verify case-level workflow development evidence without model calls."""

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.study_evidence import export, verify  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/workflow-study/draft.inputs.jsonl')
    parser.add_argument('--labels', type=Path, default=ROOT / 'data/workflow-study/draft.labels.jsonl')
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--run', nargs=2, action='append', metavar=('NAME', 'PREDICTIONS'))
    args = parser.parse_args()
    if args.run:
        names = [name for name, _ in args.run]
        if len(set(names)) != len(names):
            parser.error('Run names must be unique')
        snapshot = export(args.inputs, args.labels, dict(args.run), args.evidence)
    else:
        snapshot = verify(args.evidence, args.inputs, args.labels)
    for name, run in snapshot['runs'].items():
        summary = run['summary']
        print(f'{name}: {summary["all_four_correct"]}/{summary["records"]} all four; '
              f'{summary["complete_pairs"]}/{summary["pairs"]} complete pairs; '
              f'{summary["failed_records"]} failed; {summary["missing_records"]} missing')


if __name__ == '__main__':
    main()
