"""Portable development evidence; preserve errors, latency, and intermediates."""

import hashlib
import json
import tempfile
from collections import defaultdict
from pathlib import Path

from .dataset import read_jsonl
from .evaluate import evaluate


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def summarize(labels_path, prediction_path):
    metrics = evaluate(labels_path, prediction_path)
    keys = read_jsonl(labels_path)
    rows = {row['id']: row for row in read_jsonl(prediction_path)}
    pairs = defaultdict(list)
    field_correct = {}
    for field, score in metrics['fields'].items():
        field_correct[field] = round(score['accuracy'] * metrics['records'])
    uncertainty = {'true_positive': 0, 'false_positive': 0, 'false_negative': 0}
    false_domain = false_monitor = 0
    for key in keys:
        row = rows.get(key['id'], {})
        predictions = row.get('predictions', {}) if row.get('status') == 'ok' else {}
        correct = all(predictions.get(field) in choices for field, choices in key['accepted_answers'].items())
        if key.get('pair_id'):
            pairs[key['pair_id']].append(correct)
        actual_yes = key['labels']['insufficient_evidence'] == 'yes'
        predicted_yes = predictions.get('insufficient_evidence') == 'yes'
        uncertainty['true_positive'] += actual_yes and predicted_yes
        uncertainty['false_positive'] += not actual_yes and predicted_yes
        uncertainty['false_negative'] += actual_yes and not predicted_yes
        false_domain += key['labels']['initial_owner'] == 'noc' and predictions.get('initial_owner') in ('ran', 'transport', 'power', 'core')
        false_monitor += key['labels']['next_check'] != 'monitor' and predictions.get('next_check') == 'monitor'
    tp, fp, fn = (uncertainty[key] for key in ('true_positive', 'false_positive', 'false_negative'))
    uncertainty.update(precision=tp / (tp + fp) if tp + fp else None,
                       recall=tp / (tp + fn) if tp + fn else None)
    return {
        'records': metrics['records'], 'all_four_correct': round(metrics['all_fields_accuracy'] * metrics['records']),
        'field_correct': field_correct, 'failed_records': metrics['failed_records'], 'missing_records': metrics['missing_records'],
        'pairs': len(pairs), 'complete_pairs': sum(len(values) == 2 and all(values) for values in pairs.values()),
        'insufficient_evidence': uncertainty, 'false_domain_assignments': false_domain, 'false_monitor_dispositions': false_monitor,
        'p1_records': metrics['p1_records'],
        'p1_missed': round(metrics['p1_miss_rate'] * metrics['p1_records']) if metrics['p1_records'] else 0,
        'latency_ms': metrics['successful_latency_ms'],
    }


def export(inputs_path, labels_path, runs, output_path):
    """runs maps descriptive, distinct configuration names to prediction paths."""
    inputs, labels, output = Path(inputs_path), Path(labels_path), Path(output_path)
    if output.exists():
        raise FileExistsError(output)
    input_ids = {row['id'] for row in read_jsonl(inputs)}
    label_ids = {row['id'] for row in read_jsonl(labels)}
    if input_ids != label_ids:
        raise ValueError('Input and label IDs differ')
    snapshot = {
        'study': 'Northstar workflow development', 'evaluation_use': 'development only; not a holdout',
        'labels_reviewed': False, 'input_sha256': sha(inputs), 'label_sha256': sha(labels),
        'cases': read_jsonl(labels), 'runs': {},
    }
    for name, path in runs.items():
        path = Path(path)
        meta = json.loads(path.with_suffix('.meta.json').read_text())
        if meta['input_sha256'] != snapshot['input_sha256']:
            raise ValueError(f'{name} uses different inputs')
        rows = []
        for original in read_jsonl(path):
            row = {key: value for key, value in original.items() if key != 'raw_response'}
            # Allowlist only primitive answers from provider response. No arbitrary
            # provider text or credentials enter this portable evidence export.
            if 'raw_response' in original:
                row['intermediate_answers'] = {
                    question: {key: value for key, value in answer.items()
                               if key in ('choice', 'noul', 'score', 'probabilities', 'confidence')}
                    for question, answer in original['raw_response'].get('answers', {}).items()}
            rows.append(row)
        snapshot['runs'][name] = {'prediction_sha256': sha(path), 'metadata': meta,
                                  'summary': summarize(labels, path), 'predictions': rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x') as stream:
        json.dump(snapshot, stream, indent=2, allow_nan=False)
        stream.write('\n')
    return snapshot


def verify(snapshot_path, inputs_path, labels_path):
    snapshot = json.loads(Path(snapshot_path).read_text())
    if snapshot['input_sha256'] != sha(inputs_path) or snapshot['label_sha256'] != sha(labels_path):
        raise ValueError('Dataset differs from the development evidence')
    if snapshot['cases'] != read_jsonl(labels_path):
        raise ValueError('Snapshot labels differ from the draft answer keys')
    if snapshot['evaluation_use'] != 'development only; not a holdout' or snapshot['labels_reviewed'] is not False:
        raise ValueError('Development evidence has an incorrect review or evaluation claim')
    with tempfile.TemporaryDirectory() as directory:
        for name, section in snapshot['runs'].items():
            if section['metadata']['input_sha256'] != snapshot['input_sha256']:
                raise ValueError(f'{name} metadata has different inputs')
            prediction_path = Path(directory) / 'predictions.jsonl'
            prediction_path.write_text(''.join(json.dumps(row) + '\n' for row in section['predictions']))
            if summarize(labels_path, prediction_path) != section['summary']:
                raise ValueError(f'{name} recorded summary differs from saved predictions')
    return snapshot
