"""Generate a blind incident review pack or validate reviewer responses.

No model predictions, draft labels, or author rationales appear in the pack.
Validation never changes dataset labels or marks reviewed drafts as holdout.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.policy import OPTIONS, TEXT, priority  # noqa: E402


def create(inputs, output_dir):
    records = read_jsonl(inputs)
    if not records or len({r['id'] for r in records}) != len(records):
        raise ValueError('Review inputs must have distinct incident IDs')
    output_dir.mkdir(parents=True, exist_ok=False)
    responses = {
        'purpose': 'Specialist review of development drafts; never a holdout qualification',
        'input_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
        'reviewer': {'name': '', 'network_operations_experience': ''},
        'cases': [{'id': r['id'], 'decision': 'pending',
                   'accepted_answers': {field: [] for field in OPTIONS},
                   'rationale': '', 'input_corrections': '', 'related_mechanisms': ''}
                  for r in records],
    }
    (output_dir / 'responses.json').write_text(json.dumps(responses, indent=2) + '\n')
    lines = ['# Incident review pack', '',
             'These fictional incidents are development drafts. Review each case from the facts available at its decision time. No draft labels or model answers are shown.', '',
             'Enter answers in `responses.json`. Use `approve`, `revise`, or `reject` for each case. An approved case needs one or more accepted values for each field and an evidence-based rationale. For revisions, state the necessary input or policy correction. Do not infer missing evidence. If more than one initial diagnostic action is valid, record those alternatives.', '',
             'State your name and relevant network operations experience. Review tooling validates completeness and policy consistency; it cannot authenticate expertise. These already-inspected drafts remain development data after review.', '',
             '## Policy', '', TEXT, '', '## Allowed answers', '']
    for field, options in OPTIONS.items():
        lines.extend([f'### {field}', ''])
        lines.extend(f'- `{key}`: {description}' for key, description in options.items())
        lines.append('')
    for index, record in enumerate(records, 1):
        packet = record['input']
        visible = {key: packet[key] for key in ('decision_timestamp', 'observations', 'service_impact', 'topology', 'change_record') if key in packet}
        lines.extend([f'## Case {index}: {record["id"]}', '', '```json',
                      json.dumps(visible, indent=2), '```', ''])
    (output_dir / 'review.md').write_text('\n'.join(lines))
    return len(records)


def validate(inputs, responses_path):
    review = json.loads(responses_path.read_text())
    if review['input_sha256'] != hashlib.sha256(inputs.read_bytes()).hexdigest():
        raise ValueError('Review inputs changed')
    source_records = read_jsonl(inputs)
    records = {r['id']: r['input'] for r in source_records}
    if not records or len(records) != len(source_records):
        raise ValueError('Review inputs must have distinct incident IDs')
    cases = review['cases']
    if len(cases) != len(records) or {case['id'] for case in cases} != set(records):
        raise ValueError('Review must include each incident exactly once')
    if not all(nonblank_text(review['reviewer'].get(field)) for field in ('name', 'network_operations_experience')):
        raise ValueError('Reviewer name and network operations experience are required')
    counts = dict.fromkeys(('approve', 'revise', 'reject', 'pending'), 0)
    for case in cases:
        decision = case['decision']
        if decision not in counts:
            raise ValueError(f'Unknown review decision for {case["id"]}')
        counts[decision] += 1
        if decision == 'pending':
            continue
        if not nonblank_text(case.get('rationale')):
            raise ValueError(f'Review rationale required for {case["id"]}')
        if decision == 'revise' and not nonblank_text(case.get('input_corrections')):
            raise ValueError(f'Input correction required for {case["id"]}')
        if decision == 'approve':
            if case.get('input_corrections', '') != '':
                raise ValueError(f'Approval must use unchanged inputs for {case["id"]}; use revise for corrections')
            answers = case['accepted_answers']
            if set(answers) != set(OPTIONS):
                raise ValueError(f'All decision fields required for {case["id"]}')
            for field, allowed in OPTIONS.items():
                values = answers[field]
                if (not isinstance(values, list) or not values
                        or any(not isinstance(value, str) for value in values)
                        or len(set(values)) != len(values)
                        or any(value not in allowed for value in values)):
                    raise ValueError(f'Invalid accepted {field} answers for {case["id"]}')
            if answers['priority'] != [priority(records[case['id']]['service_impact'])]:
                raise ValueError(f'Priority conflicts with the stated impact policy for {case["id"]}; revise the input instead')
    return {'review_counts': counts, 'complete': counts['pending'] == 0,
            'use': 'Reviewed drafts remain development data; labels are not automatically updated',
            'reviewer_identity': 'self-reported; not authenticated by this tool'}


def nonblank_text(value):
    return isinstance(value, str) and bool(value.strip())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inputs', type=Path, default=ROOT / 'data/workflow-study/draft.inputs.jsonl')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-dir', type=Path)
    group.add_argument('--responses', type=Path)
    args = parser.parse_args()
    if args.output_dir:
        print(f'Created blind review pack for {create(args.inputs, args.output_dir)} development incidents')
    else:
        result = validate(args.inputs, args.responses)
        print(json.dumps(result, indent=2))
        if not result['complete']:
            raise SystemExit(2)


if __name__ == '__main__':
    main()
