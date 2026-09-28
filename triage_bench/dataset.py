"""Reproducible generation with separate public inputs and answer keys."""
import copy
import hashlib
import json
import random
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .policy import VERSION, priority
from .scenarios import scenarios

ROOT = Path(__file__).resolve().parents[1]


def read_jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]


def write_jsonl(path, rows):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(r, sort_keys=True, ensure_ascii=False) + '\n' for r in rows))


def stamp(dt):
    return dt.isoformat().replace('+00:00', 'Z')


def topology(split, count, prefix):
    # Distinct structural graph patterns across splits, unrelated to target labels.
    sites = [f'{prefix}-S{i:02d}' for i in range(count)]
    if split == 'train':
        edges = [[s, f'{prefix}-A0'] for s in sites] + [[f'{prefix}-A0', f'{prefix}-U0']]
        pattern = 'single-aggregation'
    elif split == 'validation':
        edges = [[s, f'{prefix}-A0'] for s in sites] + [[f'{prefix}-A0', f'{prefix}-A1'], [f'{prefix}-A1', f'{prefix}-U0']]
        pattern = 'aggregation-chain'
    else:
        edges = [[s, f'{prefix}-A0'] for s in sites] + [[f'{prefix}-A0', f'{prefix}-U0'], [f'{prefix}-A0', f'{prefix}-U1']]
        pattern = 'dual-upstream'
    return {'pattern': pattern, 'edges': edges, 'note': 'Illustrative inventory excerpt, not a complete traffic or protection map.'}


def make_record(s, index, rng):
    split = s['split']
    # Stable opaque IDs prevent family/label information entering requests.
    opaque = hashlib.sha256(f'{s["family"]}:{index}:20260928'.encode()).hexdigest()[:12]
    incident_id = 'NS-' + opaque
    now = datetime(2026, 1, 5, tzinfo=timezone.utc) + timedelta(minutes=rng.randrange(100000))
    n = rng.choice([2, 4, 9, 10, 12, 18])
    if s['owner'] in {'ran', 'power'}:
        n = 2 if s['family'] in {'radio_handover', 'radio_neighbor'} else 1
    status = s['status']
    impact = {'status': status, 'affected_sites': None if status == 'unknown' else (0 if status == 'none' else n),
              'basis': 'Current independent service checks' if status != 'unknown' else 'Not independently verified'}
    # Different surface formats, never crossing family splits.
    wrappers = ['Operator observation: {}', 'Shift update — {}', 'Investigation notes: {}', '{}']
    evidence = wrappers[index % len(wrappers)].format(s['evidence'])
    packet = {
        'operator': 'Northstar Networks', 'decision_timestamp': stamp(now),
        'ticket': {'title': 'Network service observation', 'description': evidence},
        'observations': [{'observed_at': stamp(now - timedelta(minutes=rng.choice([1, 2, 3]))),
                          'source': 'Synthetic operations evidence feed', 'detail': s['evidence']}],
        'service_impact': impact,
        'topology': topology(split, n, opaque[:5]),
        'change_record': {'status': 'See operator evidence; absence of a record is not proof of no change.'},
        'operator_note': rng.choice(['Please determine the next diagnostic check.',
                                    'Assign an initial investigating domain using the current evidence.',
                                    'Review before assigning a fault domain.'])}
    if 'independent' in s['evidence'] and s['owner'] in {'core', 'noc'}:
        # These cases must not accidentally claim a shared access dependency.
        packet['topology'] = {'pattern': split + '-independent-access',
                             'edges': [[f'{opaque[:5]}-S{i}', f'{opaque[:5]}-A{i}'] for i in range(n)],
                             'note': 'Distinct documented access paths; shared services may exist beyond this excerpt.'}
    labels = {'initial_owner': s['owner'], 'priority': priority(impact), 'next_check': s['check'],
              'insufficient_evidence': 'yes' if s['uncertain'] else 'no'}
    key = {'id': incident_id, 'split': split, 'incident_family_id': s['family'],
           'topology_family_id': split + ':' + s['family'], 'labels': labels,
           'accepted_answers': {k: [v] for k, v in labels.items()},
           'label_rationale': {'domain_and_check': s['evidence'],
                               'priority': f"Apply policy {VERSION} to status={status}, affected_sites={impact['affected_sites']}.",
                               'uncertainty': 'Initial investigation only; no confirmed root cause is labeled.'},
           'generation': {'version': '0.1.0', 'realization': index, 'seed': 20260928}}
    return {'id': incident_id, 'policy_version': VERSION, 'input': packet}, key


def challenge_records():
    """Twelve paired families, each changing one material evidence field."""
    records, keys = [], []
    for i in range(12):
        typ = i % 4
        family = f'challenge-{i:02d}'
        s = dict(split='challenge', family=family, owner='transport', check='inspect_transport',
                 uncertain=False, status='outage', evidence='Current independent optical diagnostics identify loss of signal on the common aggregation span. Site power is normal.')
        r, k = make_record(s, 0, random.Random(400 + i))
        # Keep observations in exactly one location for one-field interventions.
        r['input']['ticket']['description'] = 'Review the supplied current observations.'
        if typ == 0:
            r['input']['service_impact']['affected_sites'] = 9
            k['labels']['priority'] = 'P2'
            changed_path = 'input.service_impact.affected_sites'
        elif typ == 1:
            r['input']['observations'][0]['detail'] = 'Current independent diagnostics identify an open DC breaker supplying the affected equipment. Upstream transport checks pass.'
            k['labels'].update(initial_owner='power', next_check='inspect_power')
            changed_path = 'input.observations[0].detail'
        elif typ == 2:
            r['input']['observations'][0]['detail'] = 'Current independent service checks confirm recovery for the full observation interval. No active fault evidence remains.'
            r['input']['service_impact'] = {'status': 'none', 'affected_sites': 0, 'basis': 'Current independent service checks'}
            k['labels'].update(initial_owner='noc', next_check='monitor', priority='P4')
            changed_path = 'input.observations[0].detail'
        else:
            r['input']['observations'][0]['detail'] = 'Current optical diagnostics confirm loss of signal at uplink A0. All four sites in the topology excerpt are unreachable; their independent power telemetry is normal. Radio diagnostics are unavailable.'
            r['input']['service_impact'] = {'status': 'outage', 'affected_sites': 4, 'basis': 'Current independent service checks'}
            r['input']['topology'] = {'pattern': 'challenge-dependency', 'edges': [[f'S{j}', 'A0'] for j in range(4)], 'note': 'Complete upstream dependencies for these four sites.'}
            k['labels']['priority'] = 'P2'
            changed_path = 'input.topology'
        r2, k2 = copy.deepcopy(r), copy.deepcopy(k)
        r2['id'] += '-b'
        k2['id'] = r2['id']
        if typ == 0:
            r2['input']['service_impact']['affected_sites'] = 10
            k2['labels']['priority'] = 'P1'
        elif typ == 1:
            r2['input']['observations'][0]['detail'] = 'The only DC breaker observation is 75 minutes old. Current independent domain telemetry is unavailable.'
            k2['labels'].update(initial_owner='noc', next_check='gather_evidence', insufficient_evidence='yes')
        elif typ == 2:
            r2['input']['observations'][0]['detail'] = 'Current independent service checks confirm recovery, but a configuration change occurred just before the alarm. No active fault evidence remains.'
            # Irrelevant temporal association should NOT change a recovered disposition.
        else:
            r2['input']['topology'] = {'pattern': 'challenge-dependency', 'edges': [[f'S{j}', f'A{j+1}'] for j in range(4)], 'note': 'Complete upstream dependencies for these four sites; none depends on A0.'}
            k2['labels'].update(initial_owner='noc', next_check='gather_evidence', insufficient_evidence='yes')
        for item, key in [(r, k), (r2, k2)]:
            key['accepted_answers'] = {a: [b] for a, b in key['labels'].items()}
            key['incident_family_id'] = f'challenge-archetype-{typ}'
            key['topology_family_id'] = f'challenge-archetype-{typ}'
            key['pair_id'] = family
            key['changed_path'] = changed_path
            key['pair_kind'] = 'invariance' if typ == 2 else 'decision_change'
            key['label_rationale'] = {'evidence': item['input']['observations'][0]['detail'],
                                       'priority': 'Apply the published priority rule to service_impact.'}
            records.append(item)
            keys.append(key)
    return records, keys


def generate(output=ROOT / 'data'):
    output = Path(output)
    rng = random.Random(20260928)
    grouped = {s: ([], []) for s in ['train', 'validation', 'test', 'challenge']}
    for s in scenarios():
        for i in range(20):
            record, key = make_record(s, i, rng)
            grouped[s['split']][0].append(record)
            grouped[s['split']][1].append(key)
    grouped['challenge'] = challenge_records()
    manifest = {'version': '0.1.0', 'seed': 20260928, 'policy_version': VERSION,
                'synthetic': True, 'operator': 'Northstar Networks', 'splits': {}}
    for split, (records, keys) in grouped.items():
        order = list(range(len(records)))
        rng.shuffle(order)
        records, keys = [records[i] for i in order], [keys[i] for i in order]
        write_jsonl(output / f'{split}.inputs.jsonl', records)
        write_jsonl(output / f'{split}.labels.jsonl', keys)
        manifest['splits'][split] = {'records': len(records),
            'independent_scenario_families': len({k['incident_family_id'] for k in keys}),
            'owners': dict(Counter(k['labels']['initial_owner'] for k in keys)),
            'priorities': dict(Counter(k['labels']['priority'] for k in keys))}
    manifest['sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.jsonl'))}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest
