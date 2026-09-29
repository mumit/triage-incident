"""Small, encoder-only classifier for initial incident disposition.

The pretrained encoder is frozen. A seven-way linear head learns the allowed
owner/check/evidence combinations; explicit policy computes priority.
No autoregressive model or text-generation API is used.
"""

import hashlib
import json
import re
import time
from pathlib import Path

from .dataset import read_jsonl, write_jsonl
from .policy import priority


MODEL_ID = 'sentence-transformers/all-MiniLM-L6-v2'
MODEL_REVISION = '1110a243fdf4706b3f48f1d95db1a4f5529b4d41'
MAX_TOKENS = 256
FEATURE_SCALE = 0.5
CLASSIFIER_C = 0.1
FIELDS = ('initial_owner', 'next_check', 'insufficient_evidence')
CLASSES = (
    ('ran', 'inspect_radio', 'no'),
    ('transport', 'inspect_transport', 'no'),
    ('power', 'inspect_power', 'no'),
    ('core', 'inspect_core', 'no'),
    ('noc', 'gather_evidence', 'yes'),
    ('noc', 'verify_change', 'yes'),
    ('noc', 'monitor', 'no'),
)
FEATURE_PATTERNS = (
    r'change|maintenance|configuration|planned work|scope|window',
    r'recover|clear|baseline|no active fault',
    r'missing|stale|unavailable|unknown|not arrived|cannot|disagree|conflict|not independently',
)


def render_packet(packet):
    """Remove duplicated ticket prose and asset IDs; retain current evidence."""
    observation = ' '.join(item['detail'] for item in packet['observations'])
    impact = packet['service_impact']
    return (f'Observation: {observation} Impact: {impact["status"]} at '
            f'{impact["affected_sites"]} sites. Topology: {packet["topology"]["note"]}')


def structured_features(packet):
    observation = ' '.join(item['detail'] for item in packet['observations']).lower()
    status = packet['service_impact']['status']
    return [int(status == value) for value in ('none', 'unknown', 'degraded', 'outage')] + [
        int(bool(re.search(pattern, observation))) for pattern in FEATURE_PATTERNS]


def class_index(labels):
    return CLASSES.index(tuple(labels[field] for field in FIELDS))


def policy_guard(packet, category):
    """Veto a domain assignment contradicted by explicit freshness/topology facts.

    These guards are separate from the learned classifier and require positive
    evidence that the supplied graph is complete or that the sole diagnostic
    observation is stale. Other cases retain the classifier's decision.
    """
    observation = ' '.join(item['detail'] for item in packet['observations']).lower()
    if (category in range(4) and re.search(r'\b(?:\d+\s+(?:minutes?|hours?)\s+old|stale)\b', observation)
            and re.search(r'\b(?:only|sole)\b', observation)
            and (re.search(r'\bno current\b', observation)
                 or re.search(r'\bcurrent\b[^.]*\b(?:unavailable|missing)\b', observation))):
        return 4, 'sole domain evidence is stale and current telemetry is unavailable'

    topology = packet['topology']
    if category == 1 and topology.get('note', '').strip().lower().startswith('complete upstream dependencies'):
        alarm = re.search(r'\buplink\s+([a-z0-9_-]+)\b', observation)
        if alarm:
            node = alarm.group(1).lower()
            graph = {}
            for left, right in topology.get('edges', []):
                left, right = left.lower(), right.lower()
                graph.setdefault(left, set()).add(right)
                graph.setdefault(right, set()).add(left)
            sites = [item for item in graph if re.search(r'(?:^|-)s\d+$', item)]
            if sites and len(sites) == packet['service_impact']['affected_sites']:
                connected = set(sites)
                frontier = list(sites)
                while frontier:
                    for neighbor in graph.get(frontier.pop(), ()):
                        if neighbor not in connected:
                            connected.add(neighbor)
                            frontier.append(neighbor)
                if node not in connected:
                    return 4, 'no affected site depends on the alarmed uplink in the complete topology'
    return category, None


def load_encoder(device=None, local_files_only=False):
    import torch
    from transformers import AutoModel, AutoTokenizer

    device = device or ('mps' if torch.backends.mps.is_available() else 'cpu')
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, revision=MODEL_REVISION,
                                               local_files_only=local_files_only)
    model = AutoModel.from_pretrained(MODEL_ID, revision=MODEL_REVISION,
                                      local_files_only=local_files_only).eval().to(device)
    return tokenizer, model, device


def encode_packets(packets, tokenizer, model, device, batch_size=32):
    """Mean-pool and L2-normalize MiniLM encoder states."""
    import numpy as np
    import torch

    vectors = []
    with torch.inference_mode():
        for start in range(0, len(packets), batch_size):
            texts = [render_packet(packet) for packet in packets[start:start + batch_size]]
            tokens = tokenizer(texts, padding=True, truncation=False, return_tensors='pt')
            lengths = tokens['attention_mask'].sum(dim=1)
            if any(length > MAX_TOKENS for length in lengths):
                raise ValueError(f'Compact incident exceeds the {MAX_TOKENS}-token encoder limit')
            tokens = tokens.to(device)
            hidden = model(**tokens).last_hidden_state
            mask = tokens['attention_mask'].unsqueeze(-1)
            pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1)
            vectors.append(torch.nn.functional.normalize(pooled, p=2, dim=1).cpu().numpy())
    return np.concatenate(vectors) if vectors else np.empty((0, model.config.hidden_size))


def feature_matrix(packets, embeddings):
    import numpy as np

    flags = np.asarray([structured_features(packet) for packet in packets], dtype=np.float32)
    return np.hstack((embeddings, FEATURE_SCALE * flags))


def fit_head(train_inputs, train_labels, validation_inputs, validation_labels, output_dir):
    """Fit on training families; use validation only to report the frozen choice."""
    import numpy as np
    import sklearn
    import torch
    import transformers
    from sklearn.linear_model import LogisticRegression

    output_dir = Path(output_dir)
    if output_dir.exists():
        raise FileExistsError(output_dir)
    training = read_jsonl(train_inputs)
    validation = read_jsonl(validation_inputs)
    train_keys = {item['id']: item for item in read_jsonl(train_labels)}
    validation_keys = {item['id']: item for item in read_jsonl(validation_labels)}
    if set(train_keys) != {item['id'] for item in training}:
        raise ValueError('Training inputs and labels have different incident IDs')
    if set(validation_keys) != {item['id'] for item in validation}:
        raise ValueError('Validation inputs and labels have different incident IDs')
    if not {item['incident_family_id'] for item in train_keys.values()}.isdisjoint(
            {item['incident_family_id'] for item in validation_keys.values()}):
        raise ValueError('Training and validation families must be disjoint')
    tokenizer, model, device = load_encoder()
    train_packets = [item['input'] for item in training]
    val_packets = [item['input'] for item in validation]
    train_matrix = feature_matrix(train_packets, encode_packets(train_packets, tokenizer, model, device))
    val_matrix = feature_matrix(val_packets, encode_packets(val_packets, tokenizer, model, device))
    targets = np.asarray([class_index(train_keys[item['id']]['labels']) for item in training])
    val_targets = np.asarray([class_index(validation_keys[item['id']]['labels']) for item in validation])
    head = LogisticRegression(C=CLASSIFIER_C, class_weight='balanced', max_iter=2000,
                              random_state=17).fit(train_matrix, targets)
    if tuple(head.classes_) != tuple(range(len(CLASSES))):
        raise ValueError('Training data does not cover all seven decision classes')
    val_predictions = head.predict(val_matrix)
    output_dir.mkdir(parents=True, exist_ok=False)
    np.savez_compressed(output_dir / 'head.npz', weights=head.coef_.astype(np.float32),
                        bias=head.intercept_.astype(np.float32))
    metadata = {
        'model_id': MODEL_ID, 'model_revision': MODEL_REVISION,
        'architecture': 'frozen MiniLM encoder plus seven-way logistic head; deterministic priority',
        'encoder_parameters': sum(parameter.numel() for parameter in model.parameters()),
        'classes': CLASSES, 'fields': FIELDS, 'max_tokens': MAX_TOKENS,
        'feature_scale': FEATURE_SCALE, 'feature_patterns': FEATURE_PATTERNS,
        'classifier_C': CLASSIFIER_C, 'class_weight': 'balanced',
        'train_rows': len(training), 'train_families': len({key['incident_family_id'] for key in train_keys.values()}),
        'validation_rows': len(validation), 'validation_families': len({key['incident_family_id'] for key in validation_keys.values()}),
        'validation_correct': int((val_predictions == val_targets).sum()),
        'train_input_sha256': hashlib.sha256(Path(train_inputs).read_bytes()).hexdigest(),
        'train_label_sha256': hashlib.sha256(Path(train_labels).read_bytes()).hexdigest(),
        'validation_input_sha256': hashlib.sha256(Path(validation_inputs).read_bytes()).hexdigest(),
        'validation_label_sha256': hashlib.sha256(Path(validation_labels).read_bytes()).hexdigest(),
        'versions': {'torch': torch.__version__, 'transformers': transformers.__version__,
                     'sklearn': sklearn.__version__, 'numpy': np.__version__},
    }
    (output_dir / 'metadata.json').write_text(json.dumps(metadata, indent=2) + '\n')
    return metadata


def load_head(model_dir):
    import numpy as np

    model_dir = Path(model_dir)
    metadata = json.loads((model_dir / 'metadata.json').read_text())
    if metadata['model_id'] != MODEL_ID or metadata['model_revision'] != MODEL_REVISION:
        raise ValueError('Encoder checkpoint differs from the trained head')
    if [tuple(item) for item in metadata['classes']] != list(CLASSES):
        raise ValueError('Decision classes differ from the trained head')
    if tuple(metadata['fields']) != FIELDS:
        raise ValueError('Decision fields differ from the trained head')
    if (metadata['feature_scale'] != FEATURE_SCALE or
            tuple(metadata['feature_patterns']) != FEATURE_PATTERNS or
            metadata['max_tokens'] != MAX_TOKENS):
        raise ValueError('Encoder feature protocol differs from the trained head')
    with np.load(model_dir / 'head.npz', allow_pickle=False) as saved:
        weights, bias = saved['weights'], saved['bias']
    if (weights.ndim != 2 or weights.shape[0] != len(CLASSES) or
            bias.shape != (len(CLASSES),) or not np.isfinite(weights).all() or
            not np.isfinite(bias).all()):
        raise ValueError('Invalid encoder classifier head')
    return weights, bias, metadata


def predict_file(inputs_path, output_path, model_dir, guards='none', progress=None, stop_event=None):
    """Run serial single-incident inference; never open a label file."""
    import numpy as np

    if guards not in ('none', 'policy-v1'):
        raise ValueError('Unknown policy guard variant')
    inputs_path, output_path = Path(inputs_path), Path(output_path)
    if output_path.exists() or output_path.with_suffix('.meta.json').exists():
        raise FileExistsError(output_path)
    weights, bias, metadata = load_head(model_dir)
    tokenizer, model, device = load_encoder(local_files_only=True)
    if weights.shape[1] != model.config.hidden_size + 4 + len(FEATURE_PATTERNS):
        raise ValueError('Encoder hidden size differs from the trained head')
    records = read_jsonl(inputs_path)
    rows = []
    for record in records:
        if stop_event is not None and stop_event.is_set():
            break
        started = time.perf_counter()
        packet = record['input']
        vector = feature_matrix([packet], encode_packets([packet], tokenizer, model, device))
        category = int(np.argmax(vector @ weights.T + bias))
        guard_reason = None
        if guards == 'policy-v1':
            category, guard_reason = policy_guard(packet, category)
        predictions = dict(zip(FIELDS, CLASSES[category]))
        predictions['priority'] = priority(packet['service_impact'])
        row = {'id': record['id'], 'status': 'ok', 'predictions': predictions,
               'latency_ms': (time.perf_counter() - started) * 1000}
        if guard_reason:
            row['guard_reason'] = guard_reason
        rows.append(row)
        if progress:
            progress(len(rows), len(records), row)
    write_jsonl(output_path, rows)
    run_meta = {
        'provider': 'encoder', 'model_id': MODEL_ID, 'model_revision': MODEL_REVISION,
        'head_sha256': hashlib.sha256((Path(model_dir) / 'head.npz').read_bytes()).hexdigest(),
        'head_training': metadata, 'device': device, 'records': len(records),
        'policy_guards': guards, 'guarded_records': sum('guard_reason' in row for row in rows),
        'attempted_records': len(rows), 'cancelled': len(rows) < len(records),
        'input_sha256': hashlib.sha256(inputs_path.read_bytes()).hexdigest(),
        'execution': 'serial; model loaded once; per-incident latency excludes model loading',
        'no_autoregressive_calls': True,
    }
    output_path.with_suffix('.meta.json').write_text(json.dumps(run_meta, indent=2) + '\n')
    return rows
