"""Build the offline study walkthrough from committed evidence snapshots."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / 'docs/presentation/incident-triage-study.html'
TEMPLATE = ROOT / 'docs/presentation/study-walkthrough.template.html'


def read(name):
    return json.loads((ROOT / name).read_text())


def build(output=DESTINATION):
    zero = read('examples/full-zero-shot-evaluation.evidence.json')
    original = read('examples/encoder-evaluation.evidence.json')
    transfer = read('examples/encoder-transfer/evaluation-01/combined-development.evidence.json')
    benchmark = read('examples/encoder-transfer/expanded-head-resident-benchmark.json')
    summaries = read('examples/encoder-transfer/evaluation-01/summary.json')
    records = {
        r['id']: r['input'] for r in
        (json.loads(line) for line in
         (ROOT / 'examples/encoder-transfer/release-v1/development.inputs.jsonl').read_text().splitlines())
    }
    cases = []
    for case in transfer['cases']:
        predictions = {}
        for model, run in transfer['runs'].items():
            prediction = next(p for p in run['predictions'] if p['id'] == case['id'])
            predictions[model] = prediction['predictions']
        cases.append({
            'id': case['id'], 'family': case['incident_family_id'], 'pair': case['pair_id'],
            'input': records[case['id']], 'labels': case['labels'], 'predictions': predictions,
            'max_probability': max(next(p for p in transfer['runs']['expanded-structured']['predictions']
                                        if p['id'] == case['id'])['disposition_probabilities']),
        })
    sources = [
        ('Technical report', 'docs/incident-triage-technical-report.md'),
        ('Zero-shot case evidence', 'examples/full-zero-shot-evaluation.evidence.json'),
        ('Original encoder results', 'docs/encoder-study.md'),
        ('Original encoder case evidence', 'examples/encoder-evaluation.evidence.json'),
        ('Jev decomposition results', 'docs/workflow-jev-development-results.md'),
        ('Compact Jev control', 'docs/compact-jev-results.md'),
        ('Corrected development review', 'docs/development-v2-results.md'),
        ('Teacher-trained encoder', 'docs/teacher-encoder-results.md'),
        ('Regularization experiment', 'docs/encoder-regularization-results.md'),
        ('Expanded transfer report', 'docs/encoder-transfer-results.md'),
        ('Transfer cohort summaries', 'examples/encoder-transfer/evaluation-01/summary.json'),
        ('Transfer case evidence', 'examples/encoder-transfer/evaluation-01/combined-development.evidence.json'),
        ('Accepted release and exclusions', 'examples/encoder-transfer/release-v1/manifest.json'),
        ('Paired comparison analysis', 'examples/encoder-transfer/comparison-analysis.json'),
        ('Selective coverage diagnostic', 'examples/encoder-transfer/selective-development.json'),
        ('Resident latency measurements', 'examples/encoder-transfer/expanded-head-resident-benchmark.json'),
    ]
    payload = {
        'zero': {split: {'records': s['records'], 'models': s['models']}
                 for split, s in zero['splits'].items()},
        'original': {split: {'records': s['records'], 'models': s['models']}
                     for split, s in original['splits'].items()},
        'transfer': summaries,
        'cases': cases,
        'coverage': read('examples/encoder-transfer/selective-development.json')['curves']['expanded-structured'],
        'benchmark': {'load': benchmark['model_load_ms'], 'measurements': [
            {key: value for key, value in m.items() if key != 'batches'}
            for m in benchmark['measurements']]},
        'sources': [{'title': title, 'path': path,
                     'sha256': hashlib.sha256((ROOT / path).read_bytes()).hexdigest()}
                    for title, path in sources],
    }
    # Escape the script-closing character while preserving exact JSON values.
    serialized = json.dumps(payload, separators=(',', ':'), ensure_ascii=True).replace('<', '\\u003c')
    template = TEMPLATE.read_text()
    if template.count('@@STUDY_DATA@@') != 1:
        raise ValueError('Expected one study-data marker')
    output = Path(output)
    output.write_text(template.replace('@@STUDY_DATA@@', serialized))
    return output


if __name__ == '__main__':
    print(build())
