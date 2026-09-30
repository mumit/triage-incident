"""Export or verify teacher-encoder predictions and failure-inclusive metrics."""

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.dataset import read_jsonl, write_jsonl  # noqa: E402
from triage_bench.study_evidence import sha, summarize  # noqa: E402


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def export(inputs, labels, runs, output, use):
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    records, keys = read_jsonl(inputs), read_jsonl(labels)
    if (len({r['id'] for r in records}) != len(records)
            or {r['id'] for r in records} != {k['id'] for k in keys}):
        raise ValueError('Input and label IDs differ or duplicate')
    if any('LLM' not in k.get('review_status', '') for k in keys):
        raise ValueError('Teacher-label provenance required')
    snapshot = {'protocol': 'northstar-teacher-encoder-evidence-v1', 'use': use,
                'label_provenance': 'LLM-reviewed synthetic labels; no specialist adjudication',
                'input_sha256': sha(inputs), 'label_sha256': sha(labels), 'cases': keys, 'runs': {}}
    for name, path in runs.items():
        path = Path(path)
        meta = json.loads(path.with_suffix('.meta.json').read_text())
        if meta['input_sha256'] != sha(inputs):
            raise ValueError('Prediction inputs differ')
        rows = read_jsonl(path)
        snapshot['runs'][name] = {'predictions': rows, 'predictions_canonical_sha256': digest(rows),
                                  'metadata': meta, 'summary': summarize(labels, path)}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(snapshot, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return snapshot


def verify(inputs, labels, evidence):
    snapshot = json.loads(Path(evidence).read_text())
    if (snapshot['protocol'] != 'northstar-teacher-encoder-evidence-v1'
            or snapshot['use'] not in ('training diagnostic', 'development selection; not holdout')
            or snapshot['input_sha256'] != sha(inputs) or snapshot['label_sha256'] != sha(labels)
            or snapshot['cases'] != read_jsonl(labels)):
        raise ValueError('Evidence protocol, use, or dataset identity differs')
    with tempfile.TemporaryDirectory() as directory:
        for run in snapshot['runs'].values():
            if (run['metadata']['input_sha256'] != sha(inputs)
                    or digest(run['predictions']) != run['predictions_canonical_sha256']):
                raise ValueError('Prediction identity differs')
            path = Path(directory)/'predictions.jsonl'
            write_jsonl(path, run['predictions'])
            if summarize(labels, path) != run['summary']:
                raise ValueError('Metrics differ from saved predictions')
    return snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('inputs', 'labels', 'evidence'):
        parser.add_argument('--'+name, type=Path, required=True)
    parser.add_argument('--use', choices=('training diagnostic', 'development selection; not holdout'))
    parser.add_argument('--run', nargs=2, action='append', metavar=('NAME', 'PREDICTIONS'))
    args = parser.parse_args()
    if args.run:
        if not args.use or len(dict(args.run)) != len(args.run):
            parser.error('Export requires use and unique run names')
        snapshot = export(args.inputs, args.labels, dict(args.run), args.evidence, args.use)
    else:
        snapshot = verify(args.inputs, args.labels, args.evidence)
    for name, run in snapshot['runs'].items():
        s = run['summary']
        print(f'{name}: {s["all_four_correct"]}/{s["records"]}; {s["complete_pairs"]}/{s["pairs"]} pairs; '
              f'{s["failed_records"]} failed; {s["missing_records"]} missing')


if __name__ == '__main__':
    main()
