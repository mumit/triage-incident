"""Dataset integrity checks independent of the generator's label assignment."""
import hashlib
import json
from datetime import datetime
from pathlib import Path
from .dataset import read_jsonl
from .policy import OPTIONS, VERSION


def validate(root):
    root = Path(root)
    manifest = json.loads((root/'manifest.json').read_text())
    seen_ids, seen_families, seen_packets = set(), set(), set()
    counts = {}
    for split in ['train','validation','test','challenge']:
        records = read_jsonl(root/f'{split}.inputs.jsonl')
        keys = read_jsonl(root/f'{split}.labels.jsonl')
        by_id = {k['id']:k for k in keys}
        assert len(by_id)==len(keys), 'duplicate answer key'
        assert {r['id'] for r in records}==set(by_id), 'input/label mismatch'
        families = {k['incident_family_id'] for k in keys}
        assert not families & seen_families, 'family leakage'
        seen_families |= families
        pairs = {}
        for record in records:
            assert set(record)=={'id','policy_version','input'}, 'non-input metadata in public record'
            assert record['policy_version']==VERSION
            assert record['id'] not in seen_ids, 'duplicate ID'
            seen_ids.add(record['id'])
            encoded = json.dumps(record['input'],sort_keys=True)
            assert encoded not in seen_packets, 'duplicate packet'
            seen_packets.add(encoded)
            packet = record['input']
            assert packet['operator']=='Northstar Networks'
            now = datetime.fromisoformat(packet['decision_timestamp'].replace('Z','+00:00'))
            for observation in packet['observations']:
                assert datetime.fromisoformat(observation['observed_at'].replace('Z','+00:00')) <= now, 'future evidence'
            key = by_id[record['id']]
            assert key['split']==split
            for field, options in OPTIONS.items():
                assert key['labels'][field] in options, 'invalid label'
                assert key['labels'][field] in key['accepted_answers'][field]
                assert set(key['accepted_answers'][field]) <= set(options)
            status, n = packet['service_impact']['status'], packet['service_impact']['affected_sites']
            assert status in ['none','unknown','outage','degraded']
            assert (n is None if status=='unknown' else isinstance(n,int) and n >= 0)
            if status in ['outage','degraded']:
                assert n>0
            expected = {'none':'P4','unknown':'P3'}.get(status)
            if status=='outage': expected = 'P1' if n>=10 else 'P2'
            if status=='degraded': expected = 'P2' if n>=10 else 'P3'
            assert key['labels']['priority']==expected, 'priority disagreement'
            domain = key['labels']['initial_owner']
            if domain!='noc':
                assert key['labels']['next_check']=='inspect_'+('radio' if domain=='ran' else domain)
                assert key['labels']['insufficient_evidence']=='no'
            if 'pair_id' in key:
                pairs.setdefault(key['pair_id'],[]).append((record,key))
        for pair in pairs.values():
            assert len(pair)==2
            a,b = pair
            assert a[1]['pair_kind']==b[1]['pair_kind']
            changed = a[1]['labels'] != b[1]['labels']
            assert changed == (a[1]['pair_kind']=='decision_change')
        counts[split] = len(records)
        assert len(records)==manifest['splits'][split]['records']
        assert len(families)==manifest['splits'][split]['independent_scenario_families']
    for filename, expected in manifest['sha256'].items():
        assert hashlib.sha256((root/filename).read_bytes()).hexdigest()==expected, 'checksum mismatch'
    return counts
