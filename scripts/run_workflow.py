"""Preview or run the next study's decomposed Jev workflow on public inputs."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench import workflow  # noqa: E402
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.runner import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--model', default='jev-1.13.0')
    parser.add_argument('--endpoint', default='https://api.typesafe.ai/v1/systemone')
    parser.add_argument('--context-tokens', type=int, default=8192)
    parser.add_argument('--limit', type=int)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    if args.dry_run:
        records = read_jsonl(args.inputs)
        if args.limit is not None:
            records = records[:args.limit]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open('x') as stream:
            for record in records:
                stream.write(json.dumps({'id': record['id'], 'request': workflow.request_body(record, args.model)}, ensure_ascii=False) + '\n')
        print(json.dumps({'requests': len(records), 'output': str(args.output), **workflow.metadata()}, indent=2))
    else:
        result = run(args.inputs, args.output, provider='jev', model=args.model, endpoint=args.endpoint,
                     key_env='TYPESAFE_API_KEY', limit=args.limit, context_tokens=args.context_tokens,
                     deployment='Hosted Jev; compact decomposed workflow v1', decision_workflow=workflow)
        print(json.dumps(result, indent=2))
        if result['failed_records']:
            raise SystemExit(2)


if __name__ == '__main__':
    main()
