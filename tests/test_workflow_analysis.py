import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from triage_bench.dataset import ROOT
from triage_bench.study_evidence import export, verify


def script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowAnalysisTests(unittest.TestCase):
    def test_priority_derivation_preserves_other_answers_and_errors(self):
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs, labels, source, derived = (root / filename for filename in
                                               ('inputs.jsonl', 'labels.jsonl', 'source.jsonl', 'derived.jsonl'))
            packet = {'service_impact': {'status': 'degraded', 'affected_sites': 2}}
            inputs.write_text(''.join(json.dumps({'id': str(i), 'input': packet}) + '\n' for i in range(2)))
            values = dict(initial_owner='ran', next_check='inspect_radio', insufficient_evidence='no', priority='P3')
            labels.write_text(''.join(json.dumps({'id': str(i), 'incident_family_id': 'family',
                                                 'labels': values, 'accepted_answers': {k: [v] for k, v in values.items()}}) + '\n' for i in range(2)))
            rows = [{'id': '0', 'status': 'ok', 'predictions': {**values, 'priority': 'P2'},
                     'probabilities': {'priority': {'P2': 1}}, 'provider_confidence': {'priority': 1}},
                    {'id': '1', 'status': 'error', 'predictions': {}, 'error': 'HTTP 520'}]
            source.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            source.with_suffix('.meta.json').write_text(json.dumps({'input_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest()}))
            self.assertEqual(script('derive_policy_priority').derive(inputs, source, derived), 1)
            copied = [json.loads(line) for line in derived.read_text().splitlines()]
            self.assertEqual(copied[0]['predictions'], values)
            self.assertNotIn('priority', copied[0]['probabilities'])
            self.assertEqual(copied[1], rows[1])
            evidence = root / 'evidence.json'
            snapshot = export(inputs, labels, {'source': source, 'policy': derived}, evidence)
            verify(evidence, inputs, labels)
            snapshot['runs']['policy']['predictions'][0]['source_priority'] = 'P4'
            evidence.write_text(json.dumps(snapshot))
            with self.assertRaisesRegex(ValueError, 'changed more than priority'):
                verify(evidence, inputs, labels)

    def test_repeat_consistency_excludes_failed_calls(self):
        prediction = dict(initial_owner='noc', priority='P3', next_check='gather_evidence', insufficient_evidence='yes')
        cases = [{'id': str(i), 'incident_family_id': str(i), 'accepted_answers': {k: [v] for k, v in prediction.items()}} for i in range(2)]
        original = [{'id': str(i), 'status': 'ok', 'predictions': prediction} for i in range(2)]
        repeat = [original[0], {'id': '1', 'status': 'error', 'predictions': {}}]
        result = script('analyze_workflow_evidence').analyze({
            'evaluation_use': 'development only; not a holdout', 'cases': cases,
            'runs': {'candidate': {'predictions': original}, 'candidate_repeat': {'predictions': repeat}}})
        self.assertEqual(result['repeat_consistency']['candidate'],
                         {'matched_successful_records': 1, 'changed_final_decisions': 0})


if __name__ == '__main__':
    unittest.main()
