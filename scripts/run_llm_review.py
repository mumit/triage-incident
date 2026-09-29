"""Run blind offline review of public incident facts through Fuel iX."""

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.app import load_env  # noqa: E402
from triage_bench.llm_review import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/workflow-study/draft.inputs.jsonl')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--env-file', type=Path)
    parser.add_argument('--model', default='gpt-6-luna')
    parser.add_argument('--base-url')
    parser.add_argument('--reasoning-effort', default='none', choices=('default', 'none', 'low', 'medium', 'high'))
    parser.add_argument('--min-interval', type=float, default=3.5)
    args = parser.parse_args()
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('--env-file does not exist')
        load_env(args.env_file)
    key = os.getenv('FUELIX_BEARER_TOKEN', '')
    endpoint = args.base_url or os.getenv('LLM_BASE_URL', '')
    if not key or not endpoint:
        parser.error('Configure FUELIX_BEARER_TOKEN and LLM_BASE_URL or --base-url')
    meta = run(args.inputs, args.output, args.model, endpoint, key, args.reasoning_effort,
               min_interval=args.min_interval,
               progress=lambda index, count, row: print(f'{index}/{count}: {row["status"]}', flush=True))
    print(f'Saved {meta["successful_records"]} valid reviews; {meta["failed_records"]} failed. No labels read.')
    if meta['failed_records']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
