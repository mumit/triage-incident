"""Recompute committed encoder scores from case predictions and answer keys."""

import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'examples/encoder-evaluation.evidence.json'
FIELDS = ('initial_owner', 'priority', 'next_check', 'insufficient_evidence')


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def main():
    snapshot = json.loads(EVIDENCE.read_text())
    assert snapshot['protocol']['no_autoregressive_calls'] is True
    assert snapshot['encoder_parameters'] < 25_000_000
    for split, section in snapshot['splits'].items():
        labels = ROOT / f'data/{split}.labels.jsonl'
        inputs = ROOT / f'data/{split}.inputs.jsonl'
        assert hashlib.sha256(labels.read_bytes()).hexdigest() == section['label_sha256']
        assert hashlib.sha256(inputs.read_bytes()).hexdigest() == section['input_sha256']
        keys = {item['id']: item for item in read_jsonl(labels)}
        cases = section['cases']
        assert len(keys) == len(cases) == section['records']
        assert set(keys) == {case['id'] for case in cases}
        for variant, claimed in section['models'].items():
            fields = dict.fromkeys(FIELDS, 0)
            complete = severe_missed = severe_total = guarded = 0
            pairs = defaultdict(list)
            for case in cases:
                key = keys[case['id']]
                assert case['incident_family_id'] == key['incident_family_id']
                predicted = case['predictions'][variant]
                assert set(predicted) == set(FIELDS)
                correct = {field: predicted[field] in key['accepted_answers'][field]
                           for field in FIELDS}
                for field, ok in correct.items():
                    fields[field] += ok
                joint = all(correct.values())
                complete += joint
                if key['labels']['priority'] == 'P1':
                    severe_total += 1
                    severe_missed += not correct['priority']
                if split == 'challenge':
                    assert case['pair_id'] == key['pair_id']
                    pairs[case['pair_id']].append(joint)
                if variant == 'guarded' and 'guard_reason' in case:
                    guarded += 1
            assert complete == claimed['all_four_correct'], (split, variant, 'joint')
            assert fields == claimed['field_correct'], (split, variant, 'fields')
            assert (severe_missed, severe_total) == (claimed['p1_missed'], claimed['p1_records'])
            assert guarded == claimed['guarded_records'], (split, variant, 'guards')
            assert (sum(all(rows) for rows in pairs.values()) if pairs else None) == claimed['complete_pairs']
            if pairs:
                assert len(pairs) == 12 and all(len(rows) == 2 for rows in pairs.values())
            print(f'{split} {variant}: {complete}/{len(cases)} fully correct'
                  + (f'; {claimed["complete_pairs"]}/12 pairs' if pairs else ''))


if __name__ == '__main__':
    main()
