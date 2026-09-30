import importlib.util
import tempfile
import unittest
from pathlib import Path

from triage_bench import teacher_encoder
from triage_bench.dataset import ROOT,read_jsonl
from triage_bench.encoder import CLASSES,FIELDS

spec=importlib.util.spec_from_file_location('training_builder',ROOT/'scripts/prepare_teacher_training.py')
builder=importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class TeacherEncoderTests(unittest.TestCase):
    def test_training_pairs_cover_all_classes_and_do_not_duplicate_development_family_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'training'
            manifest=builder.build(output)
            records=read_jsonl(output/'train.inputs.jsonl')
            keys=read_jsonl(output/'reference.labels.jsonl')
            self.assertEqual(manifest['records'],60)
            self.assertEqual(manifest['families'],30)
            self.assertEqual({tuple(key['labels'][field] for field in FIELDS) for key in keys},set(CLASSES))
            development=read_jsonl(ROOT/'data/workflow-study/development-v2/reference.labels.jsonl')
            self.assertFalse({key['incident_family_id'] for key in keys}&{key['incident_family_id'] for key in development})
            self.assertEqual(len({r['id'] for r in records}),60)
            for index in range(0,60,2):
                self.assertEqual(keys[index]['pair_id'],keys[index+1]['pair_id'])
                self.assertNotEqual(records[index]['input']['observations'],records[index+1]['input']['observations'])

    def test_graph_membership_feature_distinguishes_complete_negative_evidence(self):
        records=read_jsonl(ROOT/'data/workflow-study/development-v2/development.inputs.jsonl')
        connected,disconnected=records[-2:]
        positive=teacher_encoder.graph_features(connected['input'])
        negative=teacher_encoder.graph_features(disconnected['input'])
        self.assertEqual(positive,[1,1,1,1,1,0])
        self.assertEqual(negative,[1,1,0,1,0,1])
        self.assertEqual(teacher_encoder.observation_ages(connected['input']),[0])
        text=teacher_encoder.render(connected['input'])
        self.assertIn('Edges:',text)
        self.assertIn('Change:',text)
        self.assertNotIn(connected['id'],text)

    def test_renderer_retains_unknown_change_and_conflicting_measurements(self):
        records=read_jsonl(ROOT/'data/workflow-study/development-v2/development.inputs.jsonl')
        text=teacher_encoder.render(records[6]['input'])
        self.assertIn('discrepancy has not been resolved',text)
        self.assertIn('"status": "unknown"',text)
