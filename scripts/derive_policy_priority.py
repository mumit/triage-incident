"""Offline diagnostic: replace only saved model priority with the stated policy.

Reads public inputs and saved predictions, never labels. No new model call.
The original zero-shot predictions remain unchanged.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.policy import TEXT, priority  # noqa: E402


def derive(inputs, source, output):
    inputs, source, output = Path(inputs), Path(source), Path(output)
    if output.exists() or output.with_suffix('.meta.json').exists():
        raise FileExistsError(output)
    meta = json.loads(source.with_suffix('.meta.json').read_text())
    input_hash = hashlib.sha256(inputs.read_bytes()).hexdigest()
    if meta['input_sha256'] != input_hash:
        raise ValueError('Source predictions have different inputs')
    packets = {record['id']: record['input'] for record in read_jsonl(inputs)}
    rows = read_jsonl(source)
    if len({row['id'] for row in rows}) != len(rows) or any(row['id'] not in packets for row in rows):
        raise ValueError('Invalid source prediction IDs')
    changed = 0
    for row in rows:
        if row.get('status') == 'ok':
            policy_priority = priority(packets[row['id']]['service_impact'])
            changed += row['predictions']['priority'] != policy_priority
            row['source_priority'] = row['predictions']['priority']
            row['predictions']['priority'] = policy_priority
            row.get('probabilities', {}).pop('priority', None)
            row.get('provider_confidence', {}).pop('priority', None)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        stream.write(''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in rows))
    meta.update(
        request_protocol='offline-policy-priority-diagnostic-v1',
        source_prediction_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        source_request_protocol=meta.get('request_protocol', 'original-typed-decisions'),
        derivation_source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        policy_sha256=hashlib.sha256(TEXT.encode()).hexdigest(),
        derivation='Only priority replaced from public structured impact. No new model calls.',
        changed_priorities=changed,
        latency_scope='Copied source model-call latency; excludes offline policy derivation',
    )
    output.with_suffix('.meta.json').write_text(json.dumps(meta, indent=2) + '\n')
    return changed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    changed = derive(args.inputs, args.source, args.output)
    print(f'Changed {changed} saved priority predictions; no new model calls')


if __name__ == '__main__':
    main()
