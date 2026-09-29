import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from triage_bench.dataset import ROOT

spec = importlib.util.spec_from_file_location('prepare_specialist_review', ROOT / 'scripts/prepare_specialist_review.py')
review_tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(review_tool)


class SpecialistReviewTests(unittest.TestCase):
    def setup_pack(self, root):
        inputs = root / 'inputs.jsonl'
        inputs.write_text(json.dumps({
            'id': 'case', 'label_rationale': 'DRAFT_LABEL_SENTINEL',
            'predictions': 'MODEL_SENTINEL',
            'input': {'decision_timestamp': '2026-01-01T00:00:00Z',
                      'observations': [{'detail': 'Independent current diagnostics are unavailable.'}],
                      'service_impact': {'status': 'unknown', 'affected_sites': None}},
        }) + '\n')
        output = root / 'pack'
        review_tool.create(inputs, output)
        responses = json.loads((output / 'responses.json').read_text())
        responses['reviewer'] = {'name': 'test reviewer', 'network_operations_experience': 'test fixture'}
        return inputs, output, responses

    def test_blind_pack_excludes_labels_and_predictions_and_keeps_pending(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, output, responses = self.setup_pack(Path(directory))
            self.assertNotIn('DRAFT_LABEL_SENTINEL', (output / 'review.md').read_text())
            self.assertNotIn('MODEL_SENTINEL', (output / 'review.md').read_text())
            path = output / 'responses.json'
            path.write_text(json.dumps(responses))
            result = review_tool.validate(inputs, path)
            self.assertFalse(result['complete'])
            self.assertEqual(result['review_counts']['pending'], 1)

    def test_approval_requires_policy_consistent_answers_and_reviewer(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, output, responses = self.setup_pack(Path(directory))
            case = responses['cases'][0]
            case.update(decision='approve', rationale='No current domain evidence.')
            case['accepted_answers'] = {'initial_owner': ['noc'], 'priority': ['P3'],
                                        'next_check': ['gather_evidence'], 'insufficient_evidence': ['yes']}
            path = output / 'responses.json'
            path.write_text(json.dumps(responses))
            self.assertTrue(review_tool.validate(inputs, path)['complete'])
            case['accepted_answers']['priority'] = ['P4']
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'Priority conflicts'):
                review_tool.validate(inputs, path)
            case['accepted_answers']['priority'] = ['P3']
            responses['reviewer']['name'] = ''
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'Reviewer name'):
                review_tool.validate(inputs, path)

    def test_revisions_need_actual_input_corrections(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, output, responses = self.setup_pack(Path(directory))
            responses['cases'][0].update(decision='revise', rationale='Impact needs clarification.')
            path = output / 'responses.json'
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'Input correction'):
                review_tool.validate(inputs, path)

    def test_approval_cannot_include_input_corrections_or_untyped_answers(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, output, responses = self.setup_pack(Path(directory))
            case = responses['cases'][0]
            case.update(decision='approve', rationale='No current domain evidence.', input_corrections='Change impact.')
            case['accepted_answers'] = {'initial_owner': ['noc'], 'priority': ['P3'],
                                        'next_check': ['gather_evidence'], 'insufficient_evidence': ['yes']}
            path = output / 'responses.json'
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'unchanged inputs'):
                review_tool.validate(inputs, path)
            case['input_corrections'] = ''
            case['accepted_answers']['initial_owner'] = [{}]
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'Invalid accepted'):
                review_tool.validate(inputs, path)

    def test_nontext_reviewer_and_rationale_do_not_count_as_completed(self):
        with tempfile.TemporaryDirectory() as directory:
            inputs, output, responses = self.setup_pack(Path(directory))
            path = output / 'responses.json'
            responses['reviewer']['name'] = None
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'Reviewer name'):
                review_tool.validate(inputs, path)
            responses['reviewer']['name'] = 'test reviewer'
            responses['cases'][0].update(decision='reject', rationale=None)
            path.write_text(json.dumps(responses))
            with self.assertRaisesRegex(ValueError, 'Review rationale'):
                review_tool.validate(inputs, path)


if __name__ == '__main__':
    unittest.main()
