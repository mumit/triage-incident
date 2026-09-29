"""Create corrected synthetic development inputs without overwriting the drafts.

Reference answers remain provisional. Changes are development authoring, not
independent evidence or a claim of specialist review.
"""

import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.llm_review import sha  # noqa: E402


def build(output):
    inputs = ROOT / 'data/workflow-study/draft.inputs.jsonl'
    labels = ROOT / 'data/workflow-study/draft.labels.jsonl'
    source = read_jsonl(inputs)
    keys = {row['id']: row for row in read_jsonl(labels)}
    records, references, changes = [], [], []
    for original in source:
        record = copy.deepcopy(original)
        packet = record['input']
        key = copy.deepcopy(keys[record['id']])
        family = key['incident_family_id']
        edits = []

        def replace(field, value, reason):
            previous = copy.deepcopy(packet[field])
            packet[field] = value
            edits.append({'path': '/' + field, 'before': previous, 'after': value, 'reason': reason})

        change = {'status': 'unknown',
                  'detail': 'No relevant change activity or work scope has been independently established at decision time.'}
        if family == 'unrelated_change_radio':
            change = {'status': 'completed', 'scope': ['billing portal'],
                      'detail': 'Verified implementation scope is the billing portal on infrastructure unrelated to the affected radio sectors.'}
        elif family == 'maintenance_scope_mismatch':
            change = {'status': 'in_progress', 'scope': ['S0', 'S1'],
                      'started_at': '2026-04-01T09:45:00Z', 'ended_at': '2026-04-01T10:15:00Z',
                      'detail': ('Approved planned service suspension at S0 and S1 only. Actual work scope was independently verified as matching the approved scope.'
                                 if record['id'].endswith('-a') else
                                 'Approved planned service suspension at S0 and S1 only. The actual implementation scope has not been independently verified; S2 and S3 are also unreachable.')}
        elif family == 'core_certificate' and record['id'].endswith('-b'):
            change = {'status': 'completed', 'scope': ['shared registration endpoint'],
                      'started_at': '2026-03-31T09:00:00Z', 'ended_at': '2026-03-31T09:20:00Z',
                      'detail': 'The approved renewal record names the shared registration endpoint used by the affected sites. The deployment record does not establish which endpoint instances actually received the renewed certificate; that implementation scope is unverified.'}
        replace('change_record', change, 'Replace procedural placeholder with explicit fictional change facts; preserve unknown implementation scope.')
        if family == 'mixed_dc_voltage':
            observations = copy.deepcopy(packet['observations'])
            observations[0]['detail'] = observations[0]['detail'].replace(
                'The affected services remain down.',
                'The affected services remain impaired, with partial service availability at the two sites.')
            replace('observations', observations, 'Align ambiguous service wording with the unchanged structured degraded impact; preserve domain evidence and its negation.')
        if family == 'core_certificate' and record['id'].endswith('-b'):
            observations = copy.deepcopy(packet['observations'])
            observations[0]['detail'] += ' The approved renewal scope includes the affected registration endpoint, but the deployment record leaves actual endpoint coverage unverified.'
            replace('observations', observations, 'Add relevant approved change scope and unknown actual implementation scope; this is a new synthetic development fact, not independent adjudication.')
        record['id'] += '-v2'
        record['development_version'] = 'workflow-development-v2'
        key.update(id=record['id'], split='development_v2', review_status='provisional references; awaiting blind LLM review')
        records.append(record)
        references.append(key)
        changes.append({'source_id': original['id'], 'id': record['id'],
                        'incident_family_id': family, 'pair_id': key['pair_id'], 'edits': edits})
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    for name, rows in [('development.inputs.jsonl', records), ('reference.labels.jsonl', references)]:
        (output / name).write_text(''.join(json.dumps(row, ensure_ascii=False, sort_keys=True) + '\n' for row in rows))
    (output / 'changes.json').write_text(json.dumps(changes, indent=2, ensure_ascii=False) + '\n')
    manifest = {'version': 'workflow-development-v2', 'evaluation_use': 'corrected, developer-inspected synthetic development; never a holdout',
                'author': 'AI coding agent; changes informed by prior Luna/Sol review',
                'reference_status': 'provisional original answer sets; not independent adjudication',
                'records': len(records), 'families': len({key['incident_family_id'] for key in references}),
                'source_input_sha256': sha(inputs), 'source_label_sha256': sha(labels),
                'generation_source_sha256': sha(__file__),
                'sha256': {name: sha(output / name) for name in ('development.inputs.jsonl', 'reference.labels.jsonl', 'changes.json')}}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.output_dir), indent=2))


if __name__ == '__main__':
    main()
