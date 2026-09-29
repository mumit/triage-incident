"""Finish a rate-limited LLM app run without repeating successful incidents.

Uses the bearer token already held by the running local app. Each missing or
failed incident is requested separately and paced; source job IDs are retained.
"""
import argparse
import copy
import json
import time
import urllib.request
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from triage_bench.dataset import read_jsonl, write_jsonl  # noqa: E402
from triage_bench.evaluate import evaluate  # noqa: E402


def app_json(base, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {'Content-Type': 'application/json'} if data is not None else {}
    request = urllib.request.Request(base + path, data=data, headers=headers,
                                     method='POST' if data is not None else 'GET')
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partial-job', required=True)
    parser.add_argument('--output', required=True, type=Path,
                        help='Directory for the composite run and source manifest')
    parser.add_argument('--app-url', default='http://127.0.0.1:8765')
    parser.add_argument('--min-start-interval', type=float, default=3.5)
    args = parser.parse_args()
    args.output = args.output.resolve()
    partial_dir = ROOT / 'runs' / 'app' / args.partial_job
    partial = json.loads((partial_dir / 'job.json').read_text())
    if partial['providers'] != ['llm'] or partial['split'] not in ('validation', 'test', 'challenge'):
        raise ValueError('Expected an LLM-only app run')
    split = partial['split']
    inputs = read_jsonl(partial_dir / 'inputs.jsonl')
    original = read_jsonl(partial_dir / 'llm.jsonl')
    success = {row['id']: row for row in original if row['status'] == 'ok'}
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / 'sources.json'
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest['partial_job'] != args.partial_job:
            raise ValueError('Output directory belongs to another run')
    else:
        manifest = {'partial_job': args.partial_job, 'split': split, 'record_jobs': {}}
        save_json(manifest_path, manifest)
    expected_meta = partial['results']['llm']['metadata']
    previous_start = 0.0
    total = len(inputs)
    print(f'Reusing {len(success)} successful responses from {args.partial_job}; {total - len(success)} remain.', flush=True)
    for number, record in enumerate(inputs, 1):
        record_id = record['id']
        if record_id in success:
            continue
        while True:
            job_id = manifest['record_jobs'].get(record_id)
            if job_id is None:
                delay = args.min_start_interval - (time.monotonic() - previous_start)
                if delay > 0:
                    time.sleep(delay)
                previous_start = time.monotonic()
                job = app_json(args.app_url, '/api/jobs',
                               {'split': split, 'providers': ['llm'], 'record_id': record_id})
                job_id = job['id']
            while True:
                job = app_json(args.app_url, '/api/jobs/' + job_id)
                if job['status'] not in ('queued', 'running'):
                    break
                time.sleep(.5)
            row_path = ROOT / 'runs' / 'app' / job_id / 'llm.jsonl'
            rows = read_jsonl(row_path) if row_path.exists() else []
            row = rows[0] if len(rows) == 1 else None
            if (job['status'] == 'completed' and row and row['status'] == 'ok' and
                    row['id'] == record_id):
                meta = job['results']['llm']['metadata']
                for key in ('requested_model', 'prompt_sha256', 'policy_sha256',
                            'question_schema_sha256', 'reasoning_effort'):
                    if meta.get(key) != expected_meta.get(key):
                        raise ValueError(f'{job_id} changed {key}')
                manifest['record_jobs'][record_id] = job_id
                save_json(manifest_path, manifest)
                success[record_id] = row
                if number % 20 == 0 or len(success) == total:
                    print(f'{len(success)}/{total} successful', flush=True)
                break
            error = row.get('error') if row else job['results'].get('llm', {}).get('error')
            if error == 'HTTP 429':
                retries = manifest.setdefault('rate_limit_retries', {}).get(record_id, 0) + 1
                manifest['rate_limit_retries'][record_id] = retries
                save_json(manifest_path, manifest)
                if retries > 6:
                    raise RuntimeError(f'Rate limit persisted for {record_id} after six retries')
                delay = min(120, 15 * 2 ** (retries - 1))
                print(f'Rate limited on {record_id}; waiting {delay}s before retry.', flush=True)
                time.sleep(delay)
                continue
            raise RuntimeError(f'{job_id} failed on {record_id}: {error}')
    ordered = [success[record['id']] for record in inputs]
    output = args.output / 'llm.jsonl'
    write_jsonl(output, ordered)
    labels = args.output / 'labels.jsonl'
    labels.write_bytes((partial_dir / 'labels.jsonl').read_bytes())
    inputs_path = args.output / 'inputs.jsonl'
    inputs_path.write_bytes((partial_dir / 'inputs.jsonl').read_bytes())
    metrics = evaluate(labels, output, args.output / 'llm.metrics.json')
    metadata = copy.deepcopy(expected_meta)
    metadata.update(records=total, attempted_records=total, successful_records=total,
                    failed_records=0, cancelled=False, wall_seconds=None,
                    execution='Composite of one partial app run and paced single-incident app runs; no model decisions retried after success')
    save_json(args.output / 'llm.meta.json', metadata)
    composite = {'id': str(args.output.relative_to(ROOT)), 'split': split,
                 'count': total, 'providers': ['llm'], 'status': 'completed',
                 'results': {'llm': {'metadata': metadata, 'metrics': metrics}},
                 'source_jobs': manifest}
    save_json(args.output / 'job.json', composite)
    print(f'Composite complete: {metrics["all_fields_accuracy"]:.1%} joint accuracy, '
          f'{metrics["failed_records"]} failed, {metrics["missing_records"]} missing.', flush=True)


if __name__ == '__main__':
    main()
