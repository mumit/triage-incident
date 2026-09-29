import json
import unittest

from triage_bench import compact_jev, workflow
from triage_bench.dataset import ROOT, read_jsonl
from triage_bench.policy import questions
from triage_bench.runner import normalize


class CompactJevTests(unittest.TestCase):
    def test_control_changes_only_questions_relative_to_workflow_request(self):
        record = read_jsonl(ROOT / 'data/workflow-study/draft.inputs.jsonl')[0]
        compact = compact_jev.request_body(record, 'jev-1.13.0')
        decomposed = workflow.request_body(record, 'jev-1.13.0')
        self.assertEqual(compact['state'], decomposed['state'])
        self.assertEqual(compact['model'], decomposed['model'])
        self.assertEqual(compact['questions'], questions())
        self.assertEqual(len(compact['questions']), 4)
        self.assertEqual(json.loads(compact['state'])['observations'], record['input']['observations'])

    def test_control_preserves_original_answers_and_model_priority(self):
        response = {'answers': {
            'initial_owner': {'choice': 'power'},
            'priority': {'choice': 'P1'},
            'next_check': {'choice': 'inspect_power'},
            'insufficient_evidence': {'noul': .2},
        }}
        packet = {'service_impact': {'status': 'none', 'affected_sites': 0}}
        self.assertEqual(compact_jev.normalize(response, packet), normalize(response))
        self.assertEqual(compact_jev.normalize(response, packet)[0]['priority'], 'P1')


if __name__ == '__main__':
    unittest.main()
