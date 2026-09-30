import copy
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from triage_bench.dataset import ROOT, read_jsonl, write_jsonl
from triage_bench.llm_review import verify_evidence
from triage_bench.teacher_training import validate

spec = importlib.util.spec_from_file_location('teacher_export', ROOT / 'scripts/export_teacher_training.py')
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)
evidence_spec = importlib.util.spec_from_file_location('teacher_evidence', ROOT / 'scripts/teacher_encoder_evidence.py')
evidence = importlib.util.module_from_spec(evidence_spec)
evidence_spec.loader.exec_module(evidence)

RELEASE = ROOT / 'examples/teacher-training/release-v1'
DEVELOPMENT = ROOT / 'examples/review/development-v2-reviewed-release'
SOURCE = ROOT / 'data/teacher-training-v1'
PRIMARY = ROOT / 'examples/teacher-training/luna-01/evidence.json'
AUDIT = ROOT / 'examples/teacher-training/sol-audit-01/evidence.json'
AUDIT_INPUT = ROOT / 'examples/teacher-training/audit-inputs/inputs.jsonl'
AUDIT_LABEL = ROOT / 'examples/teacher-training/audit-inputs/reference.labels.jsonl'


class TeacherTrainingTests(unittest.TestCase):
    def test_release_reproduces_verified_teacher_evidence_and_excludes_entire_flagged_family(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'release'
            manifest = exporter.build(SOURCE/'train.inputs.jsonl', SOURCE/'reference.labels.jsonl',
                                      PRIMARY, AUDIT, AUDIT_INPUT, AUDIT_LABEL, output)
            self.assertEqual(manifest['accepted_records'], 58)
            self.assertEqual(manifest['rejected_families'], ['change_edge_acl_scope'])
            for name in ('train.inputs.jsonl', 'train.labels.jsonl', 'decisions.json', 'manifest.json'):
                self.assertEqual((output/name).read_bytes(), (RELEASE/name).read_bytes())

    def test_audit_disagreement_on_one_variant_excludes_both(self):
        primary = verify_evidence(PRIMARY, SOURCE/'train.inputs.jsonl', SOURCE/'reference.labels.jsonl')
        audit = copy.deepcopy(verify_evidence(AUDIT, AUDIT_INPUT, AUDIT_LABEL))
        audit['reviews'][0]['predictions'] = {
            'initial_owner': 'noc', 'next_check': 'gather_evidence',
            'insufficient_evidence': 'yes', 'priority': 'P3'}
        affected = audit['reviews'][0]['id']
        family = next(k['incident_family_id'] for k in read_jsonl(SOURCE/'reference.labels.jsonl') if k['id']==affected)
        with tempfile.TemporaryDirectory() as directory, patch.object(exporter, 'verify_evidence', side_effect=[primary, audit]):
            output = Path(directory)/'release'
            manifest = exporter.build(SOURCE/'train.inputs.jsonl', SOURCE/'reference.labels.jsonl',
                                      PRIMARY, AUDIT, AUDIT_INPUT, AUDIT_LABEL, output)
            self.assertIn(family, manifest['rejected_families'])
            self.assertEqual(manifest['accepted_records'], 56)
            self.assertFalse(any(k['incident_family_id']==family for k in read_jsonl(output/'train.labels.jsonl')))

    def test_preflight_rejects_duplicate_incidents_and_id_family_or_pair_leakage(self):
        records = read_jsonl(RELEASE/'train.inputs.jsonl')
        keys = read_jsonl(RELEASE/'train.labels.jsonl')
        devrecords = read_jsonl(DEVELOPMENT/'candidate.inputs.jsonl')
        devkeys = read_jsonl(DEVELOPMENT/'candidate.labels.jsonl')
        validate(RELEASE/'train.inputs.jsonl', RELEASE/'train.labels.jsonl',
                 DEVELOPMENT/'candidate.inputs.jsonl', DEVELOPMENT/'candidate.labels.jsonl')
        for field in ('duplicate', 'id', 'incident_family_id', 'pair_id'):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                changed_records, changed_keys = copy.deepcopy(devrecords), copy.deepcopy(devkeys)
                if field == 'duplicate':
                    changed_records.append(changed_records[0])
                elif field == 'id':
                    changed_records[0]['id'] = records[0]['id']
                    changed_keys[0]['id'] = keys[0]['id']
                else:
                    changed_keys[0][field] = keys[0][field]
                inputs, labels = Path(directory)/'inputs', Path(directory)/'labels'
                write_jsonl(inputs, changed_records); write_jsonl(labels, changed_keys)
                with self.assertRaises(ValueError):
                    validate(RELEASE/'train.inputs.jsonl', RELEASE/'train.labels.jsonl', inputs, labels)

    def test_preflight_rejects_author_labels_and_zero_epochs_before_loading_model(self):
        with self.assertRaisesRegex(ValueError, 'LLM'):
            validate(SOURCE/'train.inputs.jsonl', SOURCE/'reference.labels.jsonl',
                     DEVELOPMENT/'candidate.inputs.jsonl', DEVELOPMENT/'candidate.labels.jsonl')
        from triage_bench.teacher_finetune import train
        with self.assertRaisesRegex(ValueError, 'Epochs'):
            train(None, None, None, None, None, epochs=0)

    def test_evidence_counts_failures_and_missing_predictions_and_rejects_tampering(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            path = directory/'predictions.jsonl'
            keys = read_jsonl(DEVELOPMENT/'candidate.labels.jsonl')
            rows = [{'id':k['id'], 'status':'ok', 'predictions':k['labels']} for k in keys[1:]]
            rows[0] = {'id':rows[0]['id'], 'status':'error', 'error':'input exceeds limit'}
            write_jsonl(path, rows)
            path.with_suffix('.meta.json').write_text(json.dumps({'input_sha256':evidence.sha(DEVELOPMENT/'candidate.inputs.jsonl')}))
            target = directory/'evidence.json'
            snapshot = evidence.export(DEVELOPMENT/'candidate.inputs.jsonl', DEVELOPMENT/'candidate.labels.jsonl',
                                       {'candidate':path}, target, 'development selection; not holdout')
            summary = snapshot['runs']['candidate']['summary']
            self.assertEqual(summary['all_four_correct'],14)
            self.assertEqual(summary['missing_records'],1)
            self.assertEqual(summary['failed_records'],1)
            evidence.verify(DEVELOPMENT/'candidate.inputs.jsonl', DEVELOPMENT/'candidate.labels.jsonl', target)
            snapshot['runs']['candidate']['predictions'][1]['predictions']['initial_owner'] = 'noc'
            target.write_text(json.dumps(snapshot))
            with self.assertRaisesRegex(ValueError,'Prediction identity'):
                evidence.verify(DEVELOPMENT/'candidate.inputs.jsonl', DEVELOPMENT/'candidate.labels.jsonl', target)
