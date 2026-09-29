"""Append completed app runs to the portable full-evaluation evidence snapshot.

Run from the repository root with one full-split job ID for each split. A unique
comparison name lets multiple checkpoints use the same generic app provider.
"""
import argparse
import json
import random
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.evaluate import evaluate, quantile  # noqa: E402


def joint_interval(cases, provider):
    groups = defaultdict(list)
    for case in cases:
        prediction = case['predictions'][provider]
        correct = all(prediction.get(field) in accepted
                      for field, accepted in case['accepted_answers'].items())
        groups[case['incident_family_id']].append(int(correct))
    values = list(groups.values())
    rng = random.Random(17)
    draws = []
    for _ in range(10000):
        sample = [rng.choice(values) for _ in values]
        draws.append(sum(map(sum, sample)) / sum(map(len, sample)))
    return [quantile(draws, .025), quantile(draws, .975)]


def paired_joint_difference(cases, provider, comparator):
    groups = defaultdict(list)
    for case in cases:
        def correct(name):
            return int(all(case['predictions'][name].get(field) in accepted
                           for field, accepted in case['accepted_answers'].items()))
        groups[case['incident_family_id']].append(correct(provider) - correct(comparator))
    values = list(groups.values())
    rng = random.Random(17)
    draws = []
    for _ in range(10000):
        sample = [rng.choice(values) for _ in values]
        draws.append(sum(map(sum, sample)) / sum(map(len, sample)))
    return {
        'joint_accuracy_difference': sum(map(sum, values)) / sum(map(len, values)),
        'family_bootstrap_95_percent_interval': [quantile(draws, .025), quantile(draws, .975)],
        'resampling': '10,000 draws of authored families with replacement; seed 17',
    }


def add_split(snapshot, split, job_id, provider, name):
    directory = ROOT / 'runs' / 'app' / job_id
    if not directory.exists():
        directory = Path(job_id)
        if not directory.is_absolute():
            directory = ROOT / directory
    job = json.loads((directory / 'job.json').read_text())
    if job['status'] != 'completed' or job['split'] != split or job['providers'] != [provider]:
        raise ValueError(f'{job_id} is not a completed {split} run of {provider} alone')
    result = job['results'][provider]
    metadata = result['metadata']
    recorded = result['metrics']
    output = directory / f'{provider}.jsonl'
    labels = directory / 'labels.jsonl'
    rescored = evaluate(labels, output)
    if rescored != recorded or recorded['failed_records'] or recorded['missing_records']:
        raise ValueError(f'{job_id} metrics mismatch or incomplete run')
    section = snapshot['splits'][split]
    if (metadata['input_sha256'] != section['input_sha256'] or
            recorded['label_sha256'] != section['label_sha256'] or
            recorded['records'] != section['records']):
        raise ValueError(f'{job_id} does not match the frozen {split} inputs and labels')
    cases = section['cases']
    rows = read_jsonl(output)
    by_id = {row['id']: row for row in rows}
    if len(by_id) != len(rows) or set(by_id) != {case['id'] for case in cases}:
        raise ValueError(f'{job_id} has incomplete or duplicate predictions')
    for case in cases:
        case['predictions'][name] = by_id[case['id']]['predictions']
    joint = sum(all(case['predictions'][name].get(field) in accepted
                    for field, accepted in case['accepted_answers'].items()) for case in cases)
    if joint / len(cases) != recorded['all_fields_accuracy']:
        raise ValueError(f'{job_id} joint score mismatch')
    usage = {'prompt_tokens': 0, 'completion_tokens': 0, 'reasoning_tokens': 0}
    for row in rows:
        detail = row.get('usage') or {}
        usage['prompt_tokens'] += detail.get('prompt_tokens') or 0
        usage['completion_tokens'] += detail.get('completion_tokens') or 0
        usage['reasoning_tokens'] += (detail.get('completion_tokens_details') or {}).get('reasoning_tokens') or 0
    entry = {
        'run_id': job['id'],
        'predictions_path': str(output.relative_to(ROOT)),
        'prediction_sha256': recorded['prediction_sha256'],
        'requested_model': metadata['requested_model'],
        'resolved_models': sorted({row['resolved_model'] for row in rows if row.get('resolved_model')}),
        'deployment': metadata['deployment'],
        'records': recorded['records'],
        'failed_records': recorded['failed_records'],
        'joint_correct': joint,
        'joint_family_bootstrap_95_percent_interval': joint_interval(cases, name),
        'owner_next_check_correct': sum(
            all(case['predictions'][name].get(field) in case['accepted_answers'][field]
                for field in ('initial_owner', 'next_check')) for case in cases),
        'field_correct': {field: round(value['accuracy'] * len(cases))
                          for field, value in recorded['fields'].items()},
        'field_macro_f1': {field: value['macro_f1'] for field, value in recorded['fields'].items()},
        'field_brier_score': {field: value['brier_score'] for field, value in recorded['fields'].items()},
        'priority_confusion': recorded['fields']['priority']['confusion_matrix'],
        'evidence_confusion': recorded['fields']['insufficient_evidence']['confusion_matrix'],
        'p1_missed': round(recorded['p1_miss_rate'] * recorded['p1_records']),
        'p1_records': recorded['p1_records'],
        'paired_families': recorded['paired_families'],
        'pair_all_fields_accuracy': recorded['pair_all_fields_accuracy'],
        'latency_ms': recorded['successful_latency_ms'],
        'wall_seconds': metadata['wall_seconds'],
        'request_protocol': metadata.get('request_protocol'),
        'prompt_sha256': metadata.get('prompt_sha256'),
        'reasoning_effort': metadata.get('reasoning_effort'),
        'declared_context_tokens': metadata['declared_context_tokens'],
        'token_usage': usage,
    }
    if job.get('source_jobs'):
        entry['source_manifest_path'] = str((directory / 'sources.json').relative_to(ROOT))
    section['models'][name] = entry
    return entry


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--name', required=True, help='Unique comparison name, e.g. gpt6_luna')
    parser.add_argument('--provider', default='llm', help='App provider key')
    for split in ('validation', 'test', 'challenge'):
        parser.add_argument(f'--{split}', required=True, help=f'Completed full {split} job ID')
    parser.add_argument('--evidence', type=Path,
                        default=ROOT / 'examples' / 'full-zero-shot-evaluation.evidence.json')
    args = parser.parse_args()
    snapshot = json.loads(args.evidence.read_text())
    if args.name in snapshot['protocol']['providers']:
        raise ValueError(f'{args.name} already exists in the comparison')
    entries = {split: add_split(snapshot, split, getattr(args, split), args.provider, args.name)
               for split in ('validation', 'test', 'challenge')}
    if len({entry['requested_model'] for entry in entries.values()}) != 1:
        raise ValueError('Model identifier changed between splits')
    if len({entry['prompt_sha256'] for entry in entries.values()}) != 1:
        raise ValueError('Prompt changed between splits')
    snapshot['protocol']['providers'].append(args.name)
    snapshot['protocol'].setdefault('additional_provider_protocols', {})[args.name] = {
        'app_provider': args.provider,
        'request_protocol': entries['validation']['request_protocol'],
        'prompt_sha256': entries['validation']['prompt_sha256'],
        'reasoning_effort': entries['validation']['reasoning_effort'],
        'declared_context_tokens': entries['validation']['declared_context_tokens'],
    }
    snapshot.setdefault('paired_comparisons', {})[args.name] = {
        split: {other: paired_joint_difference(snapshot['splits'][split]['cases'], args.name, other)
                for other in ('baseline', 'jev', 'kev')
                if other in snapshot['splits'][split]['models']}
        for split in ('validation', 'test')
    }
    snapshot['updated_at'] = datetime.now(timezone.utc).isoformat()
    temporary = args.evidence.with_suffix('.tmp')
    temporary.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False) + '\n')
    temporary.replace(args.evidence)
    for split, entry in entries.items():
        print(split, entry['joint_correct'], '/', entry['records'],
              'P1 missed', entry['p1_missed'], '/', entry['p1_records'])


if __name__ == '__main__':
    main()
