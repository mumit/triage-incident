"""Offline diagnostic: revalidate saved V2 responses, preserving original errors."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench import llm_review, llm_review_v2  # noqa: E402
from triage_bench.dataset import read_jsonl  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    meta = json.loads(args.source.with_suffix('.meta.json').read_text())
    if meta['request_protocol'] != llm_review_v2.PROTOCOL or meta['input_sha256'] != llm_review.sha(args.inputs):
        raise ValueError('Offline diagnostic requires V2 responses on the same inputs')
    if meta['prediction_sha256'] != llm_review.sha(args.source):
        raise ValueError('Source review changed')
    if args.output.exists() or args.output.with_suffix('.meta.json').exists():
        raise FileExistsError('Choose a new output path')
    rows = read_jsonl(args.source)
    derived = llm_review.revalidate_rows(read_jsonl(args.inputs), rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in derived))
    args.output.with_suffix('.original.jsonl').write_bytes(args.source.read_bytes())
    args.output.with_suffix('.original.meta.json').write_bytes(args.source.with_suffix('.meta.json').read_bytes())
    args.output.with_suffix('.source.py').write_bytes(args.source.with_suffix('.source.py').read_bytes())
    args.output.with_suffix('.runner.py').write_bytes(Path(llm_review.__file__).read_bytes())
    meta.update(source_prediction_sha256=meta['prediction_sha256'], prediction_sha256=llm_review.sha(args.output),
                runner_source_sha256=llm_review.sha(llm_review.__file__),
                derivation='Offline V2 response revalidation; no model calls or label reads. Original statuses/errors and raw responses preserved.',
                latency_scope='Copied source request latency; excludes offline response revalidation',
                successful_records=sum(row['status']=='ok' for row in derived),
                failed_records=sum(row['status']!='ok' for row in derived))
    args.output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    print(f'Validated {meta["successful_records"]}/{meta["records"]}; original outcomes preserved; no model calls')


if __name__ == '__main__':
    main()
