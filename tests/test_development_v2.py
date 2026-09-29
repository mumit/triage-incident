import importlib.util
import tempfile
import unittest
from pathlib import Path

from triage_bench.dataset import ROOT, read_jsonl

spec = importlib.util.spec_from_file_location('development_v2', ROOT / 'scripts/prepare_reviewed_development_v2.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class DevelopmentV2Tests(unittest.TestCase):
    def test_corrections_preserve_pairs_impact_and_domain_interventions(self):
        original = read_jsonl(ROOT / 'data/workflow-study/draft.inputs.jsonl')
        original_labels = read_jsonl(ROOT / 'data/workflow-study/draft.labels.jsonl')
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'release'
            builder.build(output)
            current = read_jsonl(output / 'development.inputs.jsonl')
            current_labels = read_jsonl(output / 'reference.labels.jsonl')
            for before, after, old_key, new_key in zip(original, current, original_labels, current_labels):
                self.assertEqual(after['id'], before['id'] + '-v2')
                self.assertEqual(old_key['labels'], new_key['labels'])
                self.assertEqual(old_key['pair_id'], new_key['pair_id'])
                self.assertEqual(old_key['incident_family_id'], new_key['incident_family_id'])
                self.assertEqual(before['input']['service_impact'], after['input']['service_impact'])
                self.assertEqual(before['input']['topology'], after['input']['topology'])
                self.assertNotIn('Use the supplied observation', str(after['input']['change_record']))
                if old_key['incident_family_id'] not in {'mixed_dc_voltage', 'core_certificate'} or before['id'].endswith('-a') and old_key['incident_family_id']=='core_certificate':
                    self.assertEqual(before['input']['observations'], after['input']['observations'])
            text = (output / 'development.inputs.jsonl').read_text()
            self.assertIn('the discrepancy has not been resolved', text)
            self.assertIn('show no packet discard', text)
            self.assertIn('partial service availability', text)
            with self.assertRaises(FileExistsError):
                builder.build(output)
