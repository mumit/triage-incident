"""Describe development comparisons from portable predictions, without APIs."""

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.evaluate import quantile  # noqa: E402
from triage_bench.study_evidence import verify  # noqa: E402


def analyze(snapshot):
    keys = {case['id']: case for case in snapshot['cases']}
    runs = snapshot['runs']
    scores, predictions = {}, {}
    for name, section in runs.items():
        predictions[name] = {row['id']: row for row in section['predictions']}
        scores[name] = {}
        for record_id, key in keys.items():
            row = predictions[name].get(record_id, {})
            scores[name][record_id] = (row.get('status') == 'ok' and
                                     all(row.get('predictions', {}).get(field) in accepted
                                         for field, accepted in key['accepted_answers'].items()))
    families = defaultdict(list)
    for record_id, key in keys.items():
        families[key['incident_family_id']].append(record_id)
    result = {'evaluation_use': snapshot['evaluation_use'],
              'family_correct': {family: {name: sum(scores[name][record_id] for record_id in ids)
                                          for name in runs} for family, ids in families.items()},
              'comparisons': {}, 'repeat_consistency': {}, 'workflow_composition': {}}
    names = [name for name in runs if 'repeat' not in name]
    for left in names:
        for right in names:
            if left >= right:
                continue
            differences = [sum(int(scores[left][i]) - int(scores[right][i]) for i in ids) / len(ids)
                           for ids in families.values()]
            rng = random.Random(17)
            bootstrap = [sum(rng.choice(differences) for _ in differences) / len(differences) for _ in range(2000)]
            result['comparisons'][f'{left} minus {right}'] = {
                'accuracy_difference': (sum(scores[left].values()) - sum(scores[right].values())) / len(keys),
                'family_bootstrap_95_interval': [quantile(bootstrap, .025), quantile(bootstrap, .975)],
                'left_only_correct': sum(scores[left][i] and not scores[right][i] for i in keys),
                'right_only_correct': sum(scores[right][i] and not scores[left][i] for i in keys),
            }
    for name in runs:
        if name.endswith('_repeat') and name[:-7] in runs:
            original = name[:-7]
            matched = [i for i in keys if predictions[name].get(i, {}).get('status') == 'ok'
                       and predictions[original].get(i, {}).get('status') == 'ok']
            result['repeat_consistency'][original] = {
                'matched_successful_records': len(matched),
                'changed_final_decisions': sum(predictions[name][i]['predictions'] != predictions[original][i]['predictions'] for i in matched),
            }
        if 'workflow' in name:
            counts = defaultdict(int)
            for row in predictions[name].values():
                if row.get('status') != 'ok':
                    continue
                answers = row.get('intermediate_answers', {})
                gate = answers.get('disposition', {}).get('choice')
                counts[f'gate_{gate}'] += 1
                if gate == 'investigate_domain':
                    count = sum(answers[f'supports_{domain}']['noul'] >= .5 for domain in ('ran', 'transport', 'power', 'core'))
                    counts[f'investigate_with_{count}_supported_domains'] += 1
            result['workflow_composition'][name] = dict(counts)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', required=True, type=Path)
    parser.add_argument('--inputs', required=True, type=Path)
    parser.add_argument('--labels', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    result = analyze(verify(args.evidence, args.inputs, args.labels))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
