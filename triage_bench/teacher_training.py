"""Preflight boundaries shared by the two teacher-training commands."""

from .dataset import read_jsonl
from .encoder import class_index


def validate(train_inputs, train_labels, dev_inputs, dev_labels):
    records, development = read_jsonl(train_inputs), read_jsonl(dev_inputs)
    keys, devkeys = read_jsonl(train_labels), read_jsonl(dev_labels)
    for inputs, labels in ((records, keys), (development, devkeys)):
        input_ids = {r['id'] for r in inputs}
        label_ids = {k['id'] for k in labels}
        if (not inputs or len(input_ids) != len(inputs)
                or len(label_ids) != len(labels) or input_ids != label_ids):
            raise ValueError('Inputs and labels must have matching, nonempty, unique IDs')
        if any(not k.get('incident_family_id') or not k.get('pair_id') for k in labels):
            raise ValueError('Training/development labels require family and pair IDs')
        if any('LLM' not in k.get('review_status', '') for k in labels):
            raise ValueError('Explicit LLM review provenance required')
        for key in labels:
            class_index(key['labels'])
    for field in ('id', 'incident_family_id', 'pair_id'):
        if {k[field] for k in keys} & {k[field] for k in devkeys}:
            raise ValueError(f'Training/development {field} overlap')
    if {class_index(k['labels']) for k in keys} != set(range(7)):
        raise ValueError('All seven training dispositions required')
