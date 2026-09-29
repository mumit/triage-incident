"""Verify the committed full-evaluation snapshot and report table without raw runs."""

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'examples/full-zero-shot-evaluation.evidence.json'
REPORT = ROOT / 'docs/incident-triage-technical-report.md'
FIELDS = ('initial_owner', 'priority', 'next_check', 'insufficient_evidence')
PROVIDERS = {
    'GPT-6 Luna': 'gpt6_luna',
    'Rules baseline': 'baseline',
    'Jev': 'jev',
    'Kev-4B': 'kev',
    'Laya': 'laya',
    'CLM-8B': 'clm',
}


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def verify_split(split, section, providers):
    inputs = ROOT / f'data/{split}.inputs.jsonl'
    labels = ROOT / f'data/{split}.labels.jsonl'
    for path, key in ((inputs, 'input_sha256'), (labels, 'label_sha256')):
        assert hashlib.sha256(path.read_bytes()).hexdigest() == section[key], path
    keys = read_jsonl(labels)
    cases = section['cases']
    assert len(cases) == len(keys) == section['records'], split
    assert len({case['id'] for case in cases}) == len(cases), split
    assert len({case['incident_family_id'] for case in cases}) == section['families'], split
    key_by_id = {key['id']: key for key in keys}
    assert set(key_by_id) == {case['id'] for case in cases}, split
    assert set(section['models']) == providers, split
    for case in cases:
        key = key_by_id[case['id']]
        for name in ('labels', 'accepted_answers', 'incident_family_id'):
            assert case[name] == key[name], (split, case['id'], name)
        assert set(case['predictions']) == providers, (split, case['id'])
        if split == 'challenge':
            assert case['pair_id'] == key['pair_id'], case['id']

    results = {}
    for provider, saved in section['models'].items():
        field_correct = dict.fromkeys(FIELDS, 0)
        joint = owner_check = p1_missed = p1_records = 0
        pairs = defaultdict(list)
        for case in cases:
            prediction = case['predictions'][provider]
            assert set(prediction) == set(FIELDS), (split, provider, case['id'])
            correct = {field: prediction[field] in case['accepted_answers'][field]
                       for field in FIELDS}
            for field, accepted in correct.items():
                field_correct[field] += accepted
            complete = all(correct.values())
            joint += complete
            owner_check += correct['initial_owner'] and correct['next_check']
            if case['labels']['priority'] == 'P1':
                p1_records += 1
                p1_missed += not correct['priority']
            if split == 'challenge':
                pairs[case['pair_id']].append(complete)
        assert saved['records'] == len(cases) and saved['failed_records'] == 0, (split, provider)
        assert saved['joint_correct'] == joint, (split, provider, 'joint')
        assert saved['field_correct'] == field_correct, (split, provider, 'fields')
        assert saved['owner_next_check_correct'] == owner_check, (split, provider, 'owner/check')
        assert (saved['p1_missed'], saved['p1_records']) == (p1_missed, p1_records), (split, provider, 'P1')
        complete_pairs = None
        if split == 'challenge':
            assert len(pairs) == 12 and all(len(rows) == 2 for rows in pairs.values())
            complete_pairs = sum(all(rows) for rows in pairs.values())
            assert saved['paired_families'] == len(pairs), provider
            assert saved['pair_all_fields_accuracy'] == complete_pairs / len(pairs), provider
        results[provider] = (joint, complete_pairs)
    return results


def verify_report(results, records):
    lines = REPORT.read_text().splitlines()
    for display, provider in PROVIDERS.items():
        rows = [line for line in lines if line.startswith(f'| {display} |')]
        assert len(rows) == 1, display
        cells = [cell.strip() for cell in rows[0].strip('|').split('|')][1:]
        assert len(cells) == 4, display
        for split, cell in zip(('validation', 'test', 'challenge'), cells[:3]):
            match = re.fullmatch(r'(\d+)(?: \((\d+\.\d+)%\))?', cell)
            assert match, (display, split, cell)
            assert int(match[1]) == results[split][provider][0], (display, split)
            if match[2] is not None:
                expected = 100 * results[split][provider][0] / records[split]
                assert abs(float(match[2]) - expected) <= 0.05, (display, split, 'percent')
        assert int(cells[3]) == results['challenge'][provider][1], (display, 'pairs')


def main():
    snapshot = json.loads(EVIDENCE.read_text())
    providers = set(PROVIDERS.values())
    assert set(snapshot['protocol']['providers']) == providers
    results = {split: verify_split(split, snapshot['splits'][split], providers)
               for split in ('validation', 'test', 'challenge')}
    verify_report(results, {split: snapshot['splits'][split]['records'] for split in results})
    print('Verified dataset hashes, case labels, provider scores, P1 misses, challenge pairs, and report table.')


if __name__ == '__main__':
    main()
