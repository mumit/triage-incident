"""Export portable case-level evidence from completed local encoder runs."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.evaluate import evaluate  # noqa: E402


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    model_dir = ROOT / 'runs/encoder/minilm-v1'
    head = model_dir / 'head.npz'
    trained = json.loads((model_dir / 'metadata.json').read_text())
    snapshot = {
        'study': 'Northstar frozen MiniLM encoder classifier',
        'encoder_model': trained['model_id'],
        'encoder_revision': trained['model_revision'],
        'encoder_parameters': trained['encoder_parameters'],
        'head_sha256': sha(head),
        'head_training': trained,
        'protocol': {
            'raw': 'frozen encoder, seven-class trained head, deterministic priority',
            'guarded': 'raw classifier plus explicit stale-evidence and complete-topology vetoes',
            'selection': 'head and seven feature mix selected on validation; test labels had been examined in earlier work',
            'guard_selection': 'policy guards implemented after inspecting paired challenge misses; guarded challenge score is post-hoc',
            'no_autoregressive_calls': True,
        },
        'splits': {},
    }
    for split in ('validation', 'test', 'challenge'):
        labels = ROOT / f'data/{split}.labels.jsonl'
        inputs = ROOT / f'data/{split}.inputs.jsonl'
        section = {'records': len(read_jsonl(inputs)), 'input_sha256': sha(inputs),
                   'label_sha256': sha(labels), 'models': {}, 'cases': []}
        by_variant = {}
        for variant, filename in (('raw', f'{split}.predictions.jsonl'),
                                  ('guarded', f'{split}.guarded.predictions.jsonl')):
            predictions = model_dir / filename
            rows = read_jsonl(predictions)
            by_variant[variant] = {row['id']: row for row in rows}
            metrics = evaluate(labels, predictions)
            meta = json.loads(predictions.with_suffix('.meta.json').read_text())
            if metrics['failed_records'] or metrics['missing_records'] or len(by_variant[variant]) != len(rows):
                raise ValueError(f'Incomplete {split} {variant} run')
            if meta['head_sha256'] != snapshot['head_sha256'] or meta['model_revision'] != snapshot['encoder_revision']:
                raise ValueError(f'Model changed for {split} {variant}')
            section['models'][variant] = {
                'predictions_sha256': sha(predictions),
                'all_four_correct': round(metrics['all_fields_accuracy'] * metrics['records']),
                'field_correct': {field: round(value['accuracy'] * metrics['records'])
                                  for field, value in metrics['fields'].items()},
                'p1_missed': round(metrics['p1_miss_rate'] * metrics['p1_records']),
                'p1_records': metrics['p1_records'],
                'complete_pairs': round(metrics['pair_all_fields_accuracy'] * metrics['paired_families'])
                                  if metrics['paired_families'] else None,
                'guarded_records': meta.get('guarded_records', 0),
                'latency_ms': metrics['successful_latency_ms'],
            }
        keys = {item['id']: item for item in read_jsonl(labels)}
        for item in read_jsonl(inputs):
            incident_id = item['id']
            entry = {'id': incident_id, 'incident_family_id': keys[incident_id]['incident_family_id'],
                     'predictions': {variant: by_variant[variant][incident_id]['predictions']
                                     for variant in ('raw', 'guarded')}}
            if split == 'challenge':
                entry['pair_id'] = keys[incident_id]['pair_id']
            if 'guard_reason' in by_variant['guarded'][incident_id]:
                entry['guard_reason'] = by_variant['guarded'][incident_id]['guard_reason']
            section['cases'].append(entry)
        snapshot['splits'][split] = section
    output = ROOT / 'examples/encoder-evaluation.evidence.json'
    output.write_text(json.dumps(snapshot, indent=2) + '\n')
    print(output)


if __name__ == '__main__':
    main()
