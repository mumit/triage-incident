"""Reconcile blind reviews without changing incident inputs or benchmark keys."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.llm_review import reconcile, sha, verify_evidence  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/workflow-study/draft.inputs.jsonl')
    parser.add_argument('--labels', type=Path, default=ROOT / 'data/workflow-study/draft.labels.jsonl')
    parser.add_argument('--primary-dir', type=Path, required=True)
    parser.add_argument('--secondary-evidence', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--verify-dir', type=Path)
    args = parser.parse_args()
    if bool(args.output_dir) == bool(args.verify_dir):
        parser.error('Choose output-dir or verify-dir')
    primary_path = args.primary_dir / 'evidence.json'
    primary = verify_evidence(primary_path, args.inputs, args.labels)
    secondary = verify_evidence(args.secondary_evidence, args.primary_dir / 'adjudication.inputs.jsonl',
                                args.primary_dir / 'adjudication.labels.jsonl')
    artifacts = json.loads((args.primary_dir / 'artifacts.json').read_text())
    if any(sha(args.primary_dir / name) != checksum for name, checksum in artifacts.items()):
        raise ValueError('Primary exported artifacts changed')
    result = reconcile(primary, secondary)
    records = {record['id']: record for record in read_jsonl(args.inputs)}
    candidates = [case for case in result['cases'] if case['status'] == 'candidate']
    input_text = ''.join(json.dumps(records[case['id']]) + '\n' for case in candidates)
    label_text = ''.join(json.dumps({'id': case['id'], 'incident_family_id': case['incident_family_id'],
        'pair_id': case['pair_id'], 'split': 'development_candidate', 'labels': case['answers'],
        'accepted_answers': {field: [answer] for field, answer in case['answers'].items()},
        'review_status': 'LLM-reviewed candidate; no specialist review', 'review_models': case['review_models']}) + '\n'
        for case in candidates)
    result.update(primary_evidence_sha256=sha(primary_path), secondary_evidence_sha256=sha(args.secondary_evidence))
    if args.verify_dir:
        if json.loads((args.verify_dir / 'reconciliation.json').read_text()) != result:
            raise ValueError('Reconciliation differs from saved reviews')
        if ((args.verify_dir / 'candidate.inputs.jsonl').read_text() != input_text
                or (args.verify_dir / 'candidate.labels.jsonl').read_text() != label_text):
            raise ValueError('Candidate exports differ from reconciled reviews')
    else:
        args.output_dir.mkdir(parents=True, exist_ok=False)
        (args.output_dir / 'reconciliation.json').write_text(json.dumps(result, indent=2) + '\n')
        (args.output_dir / 'candidate.inputs.jsonl').write_text(input_text)
        (args.output_dir / 'candidate.labels.jsonl').write_text(label_text)
    print(json.dumps({key: value for key, value in result.items() if key != 'cases'}, indent=2))


if __name__ == '__main__':
    main()
