import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from triage_bench.dataset import ROOT,read_jsonl
from triage_bench.encoder import CLASSES,FIELDS

spec=importlib.util.spec_from_file_location('transfer_generator',ROOT/'scripts/prepare_encoder_transfer.py')
generator=importlib.util.module_from_spec(spec);spec.loader.exec_module(generator)


_iterdir = Path.iterdir


def reversed_directory_order(path):
    return iter(sorted(_iterdir(path), reverse=True))


class TransferDataTests(unittest.TestCase):
    def test_reproduction_pair_assignment_and_cross_split_mechanism_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'data'
            with patch.object(Path, 'iterdir', reversed_directory_order):
                manifest=generator.build(output)
            self.assertEqual(list(manifest['sha256']),sorted(manifest['sha256']))
            for name in ('train.inputs.jsonl','train.reference.labels.jsonl','development.inputs.jsonl',
                         'development.reference.labels.jsonl','families.json','manifest.json'):
                self.assertEqual((output/name).read_bytes(),(ROOT/'data/encoder-transfer-v1'/name).read_bytes())
            training=read_jsonl(output/'train.reference.labels.jsonl')
            development=read_jsonl(output/'development.reference.labels.jsonl')
            self.assertEqual((len(training),len(development)),(60,40))
            for field in ('id','pair_id','incident_family_id'):
                self.assertFalse({k[field] for k in training}&{k[field] for k in development})
            old=read_jsonl(ROOT/'examples/teacher-training/release-v1/train.labels.jsonl')+read_jsonl(ROOT/'examples/review/development-v2-reviewed-release/candidate.labels.jsonl')
            self.assertFalse({k['incident_family_id'] for k in training+development}&{k['incident_family_id'] for k in old})
            for keys in (training,development):
                self.assertEqual({tuple(k['labels'][f] for f in FIELDS) for k in keys},set(CLASSES))
                for a,b in zip(keys[::2],keys[1::2]):
                    self.assertEqual(a['pair_id'],b['pair_id'])
                    self.assertNotEqual(a['labels'],b['labels'])

    def test_active_change_records_do_not_claim_future_actual_completion(self):
        for split in ('train','development'):
            for r in read_jsonl(ROOT/'data/encoder-transfer-v1'/(split+'.inputs.jsonl')):
                change=r['input']['change_record']
                if change['status']=='in_progress':
                    self.assertNotIn('ended_at',change)

    def test_accepted_release_reproduces_reviewed_labels_and_keeps_excluded_pair_visible(self):
        from scripts.prepare_transfer_release import prepare
        root=ROOT/'examples/encoder-transfer'
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'release'
            with patch.object(Path, 'iterdir', reversed_directory_order):
                manifest=prepare(root,output)
            self.assertEqual(list(manifest['sha256']),sorted(manifest['sha256']))
            self.assertEqual(manifest['records'],{'train':118,'development':54})
            self.assertEqual(manifest['families'],{'train':59,'development':27})
            self.assertEqual(manifest['new_development']['rejected_families'],['core_signing_key_change_competition'])
            for name in ('train.inputs.jsonl','train.labels.jsonl','development.inputs.jsonl','development.labels.jsonl',
                         'new-development.inputs.jsonl','new-development.labels.jsonl','manifest.json'):
                self.assertEqual((output/name).read_bytes(),(root/'release-v1'/name).read_bytes())
            import json
            decisions=json.loads((output/'new-development/decisions.json').read_text())
            rejected=[d for d in decisions if d['incident_family_id']=='core_signing_key_change_competition']
            self.assertEqual(len(rejected),2)
            self.assertTrue(any('teacher/audit decision disagreement' in d['reasons'] for d in rejected))
