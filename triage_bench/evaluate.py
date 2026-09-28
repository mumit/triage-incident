"""Failure-inclusive metrics; answer probabilities and provider confidence stay distinct."""
import hashlib
import json
import math
import random
from collections import defaultdict
from pathlib import Path

from .dataset import read_jsonl
from .policy import OPTIONS


def quantile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values)-1, math.ceil(len(values)*fraction)-1)]


def evaluate(labels_path, predictions_path, output=None):
    keys, rows = read_jsonl(labels_path), read_jsonl(predictions_path)
    by_id = {r['id']: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError('Duplicate prediction IDs')
    ids = {k['id'] for k in keys}
    if len(ids) != len(keys) or set(by_id) - ids:
        raise ValueError('Duplicate label IDs or unknown prediction IDs')
    if not keys:
        raise ValueError('Empty label file')
    metrics = {'label_sha256': hashlib.sha256(Path(labels_path).read_bytes()).hexdigest(),
               'prediction_sha256': hashlib.sha256(Path(predictions_path).read_bytes()).hexdigest(),
               'records': len(keys), 'attempted_records': len(rows),
               'missing_records': len(ids - set(by_id)),
               'failed_records': sum(r.get('status') != 'ok' for r in rows),
               'fields': {}, 'limitations': 'Synthetic policy benchmark. Repeated family realizations are not independent incidents. No production benefit is measured.'}
    matches = defaultdict(dict)
    for field, choices in OPTIONS.items():
        confusion = {c: {p: 0 for p in [*choices, 'ERROR']} for c in choices}
        correct = 0
        brier = []
        bins = [[] for _ in range(10)]
        selective = []
        family_scores = defaultdict(list)
        for key in keys:
            row = by_id.get(key['id'], {})
            pred = row.get('predictions', {}).get(field) if row.get('status') == 'ok' else None
            actual = key['labels'][field]
            accepted = key['accepted_answers'][field]
            ok = pred in accepted
            matches[key['id']][field] = ok
            correct += ok
            confusion[actual][pred if pred in choices else 'ERROR'] += 1
            family_scores[key['incident_family_id']].append(int(ok))
            dist = row.get('probabilities', {}).get(field) if row.get('status') == 'ok' else None
            if dist is not None:
                if set(dist) != set(choices) or any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or not 0 <= v <= 1 for v in dist.values()) or abs(sum(dist.values())-1)>0.001:
                    raise ValueError('Invalid prediction probability distribution')
                if pred not in choices:
                    raise ValueError('Probability distribution without a valid prediction')
                # Unique reference only; no probability target is fabricated for ambiguous labels.
                if len(accepted) == 1:
                    brier.append(sum((dist[c] - int(c == actual)) ** 2 for c in choices))
                confidence = dist[pred]
                bins[min(9, int(confidence*10))].append((confidence, int(ok)))
                selective.append((confidence, int(ok)))
        f1s = []
        for cls in choices:
            tp = confusion[cls][cls]
            fp = sum(confusion[a][cls] for a in choices if a != cls)
            fn = sum(confusion[cls][p] for p in confusion[cls] if p != cls)
            f1s.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
        reliability = [{'bin': i, 'count': len(b), 'mean_probability': sum(x[0] for x in b)/len(b),
                        'accuracy': sum(x[1] for x in b)/len(b)} for i,b in enumerate(bins) if b]
        rng = random.Random(17)
        groups = list(family_scores.values())
        boot = []
        for _ in range(1000):
            sample = [rng.choice(groups) for _ in groups]
            boot.append(sum(sum(g) for g in sample)/sum(len(g) for g in sample))
        metrics['fields'][field] = {'accuracy': correct/len(keys), 'macro_f1': sum(f1s)/len(f1s),
            'confusion_matrix': confusion, 'brier_score': sum(brier)/len(brier) if brier else None,
            'brier_records': len(brier), 'probability_records': len(selective), 'reliability_bins': reliability,
            'family_bootstrap_95_percent_interval': [quantile(boot,.025), quantile(boot,.975)],
            'families': len(groups), 'coverage_curve': [
                {'threshold': t, 'accepted': sum(c >= t for c,_ in selective),
                 'coverage': sum(c >= t for c,_ in selective)/len(keys),
                 'error_rate': (sum(1-ok for c,ok in selective if c>=t)/sum(c>=t for c,_ in selective)) if any(c>=t for c,_ in selective) else None}
                for t in [0,.5,.7,.8,.9,.95,.99]]}
    metrics['all_fields_accuracy'] = sum(all(m.values()) for m in matches.values())/len(keys)
    severe = [k for k in keys if k['labels']['priority']=='P1']
    metrics['p1_miss_rate'] = sum(not matches[k['id']]['priority'] for k in severe)/len(severe) if severe else None
    metrics['p1_records'] = len(severe)
    pairs = defaultdict(list)
    for key in keys:
        if 'pair_id' in key:
            pairs[key['pair_id']].append(key)
    metrics['paired_families'] = len(pairs)
    metrics['pair_all_fields_accuracy'] = sum(len(pair)==2 and all(all(matches[k['id']].values()) for k in pair) for pair in pairs.values())/len(pairs) if pairs else None
    latencies = [r['latency_ms'] for r in rows if r.get('status')=='ok' and 'latency_ms' in r]
    metrics['successful_latency_ms'] = {'p50': quantile(latencies,.5), 'p95': quantile(latencies,.95), 'records': len(latencies)}
    if output:
        Path(output).parent.mkdir(parents=True,exist_ok=True)
        Path(output).write_text(json.dumps(metrics,indent=2)+'\n')
    return metrics
