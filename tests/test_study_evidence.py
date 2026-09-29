import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from triage_bench.study_evidence import export, verify
from triage_bench.dataset import ROOT


class StudyEvidenceTests(unittest.TestCase):
    def test_missing_credential_rejected_before_creating_a_run(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'run'
            environment = {key: value for key, value in os.environ.items() if key != 'TYPESAFE_API_KEY'}
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/run_workflow_study.py'),
                                     '--providers', 'jev_workflow', '--output-dir', str(output)],
                                    env=environment, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn('Set TYPESAFE_API_KEY', result.stderr)
            self.assertFalse(output.exists())

    def test_partial_run_preserves_failures_missing_records_and_checks_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            inputs, labels, predictions, evidence = (root / name for name in
                                                     ('inputs.jsonl', 'labels.jsonl', 'predictions.jsonl', 'evidence.json'))
            values = dict(initial_owner='noc', priority='P3', next_check='gather_evidence', insufficient_evidence='yes')
            keys = [{'id': str(i), 'incident_family_id': 'family', 'pair_id': 'pair' if i < 2 else 'other',
                     'labels': values, 'accepted_answers': {key: [value] for key, value in values.items()}} for i in range(3)]
            inputs.write_text(''.join(json.dumps({'id': str(i)}) + '\n' for i in range(3)))
            labels.write_text(''.join(json.dumps(key) + '\n' for key in keys))
            rows = [{'id': '0', 'status': 'ok', 'predictions': values, 'latency_ms': 10,
                     'raw_response': {'answers': {'supports_power': {'noul': .1}}, 'unrelated': 'DO_NOT_EXPORT'}},
                    {'id': '1', 'status': 'error', 'predictions': {}, 'error': 'HTTP 503'}]
            predictions.write_text(''.join(json.dumps(row) + '\n' for row in rows))
            predictions.with_suffix('.meta.json').write_text(json.dumps({
                'input_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest()}))
            snapshot = export(inputs, labels, {'candidate': predictions}, evidence)
            summary = snapshot['runs']['candidate']['summary']
            self.assertEqual((summary['all_four_correct'], summary['failed_records'], summary['missing_records']), (1, 1, 1))
            self.assertEqual(summary['complete_pairs'], 0)
            self.assertNotIn('DO_NOT_EXPORT', evidence.read_text())
            self.assertEqual(snapshot['runs']['candidate']['predictions'][0]['intermediate_answers'], {'supports_power': {'noul': .1}})
            verify(evidence, inputs, labels)
            snapshot['runs']['candidate']['summary']['all_four_correct'] = 3
            evidence.write_text(json.dumps(snapshot))
            with self.assertRaisesRegex(ValueError, 'summary differs'):
                verify(evidence, inputs, labels)


if __name__ == '__main__':
    unittest.main()
