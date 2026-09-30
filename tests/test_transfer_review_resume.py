import copy
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from triage_bench.dataset import ROOT,read_jsonl,write_jsonl
from triage_bench.llm_review import sha
from scripts.resume_transfer_reviews import consolidate


class ReviewContinuationTests(unittest.TestCase):
    def test_first_valid_response_is_kept_even_when_later_response_agrees_with_author(self):
        records=read_jsonl(ROOT/'data/encoder-transfer-v1/train.inputs.jsonl')[:2]
        evidence=json.loads((ROOT/'examples/teacher-training/luna-01/evidence.json').read_text())
        metadata=evidence['metadata']
        first=[{'id':records[0]['id'],'status':'error','error':'HTTP 429'},
               {'id':records[1]['id'],'status':'ok','predictions':{'initial_owner':'noc'}}]
        later=[{'id':records[0]['id'],'status':'ok','predictions':{'initial_owner':'ran'}},
               {'id':records[1]['id'],'status':'ok','predictions':{'initial_owner':'power'}}]
        with tempfile.TemporaryDirectory() as temporary, patch('scripts.resume_transfer_reviews.llm_review.verify_run'):
            root=Path(temporary);inputs=root/'all.inputs.jsonl';write_jsonl(inputs,records)
            paths=[]
            for index,rows in enumerate((first,later)):
                directory=root/str(index);directory.mkdir();path=directory/'review.jsonl'
                write_jsonl(path,rows);write_jsonl(directory/'inputs.jsonl',records)
                path.with_suffix('.meta.json').write_text(json.dumps({**metadata,'input_sha256':sha(inputs)}))
                path.with_suffix('.source.py').write_text(evidence['review_source'])
                path.with_suffix('.runner.py').write_text(evidence['runner_source'])
                paths.append(path)
            output=root/'merged/review.jsonl';result=consolidate(inputs,paths,output)
            self.assertEqual(read_jsonl(output),[later[0],first[1]])
            self.assertEqual(result['failed_records'],0)
            self.assertEqual(result['missing_records'],0)
            self.assertEqual(result['review_attempts'][0]['rows'][0]['error'],'HTTP 429')
            self.assertEqual(result['review_attempts'][0]['prediction_text'],paths[0].read_text())

    def test_continuation_rejects_changed_facts(self):
        records=read_jsonl(ROOT/'data/encoder-transfer-v1/train.inputs.jsonl')[:1]
        changed=copy.deepcopy(records);changed[0]['input']['service_impact']['status']='none'
        with tempfile.TemporaryDirectory() as temporary, patch('scripts.resume_transfer_reviews.llm_review.verify_run'):
            root=Path(temporary);inputs=root/'all.inputs.jsonl';write_jsonl(inputs,records)
            directory=root/'attempt';directory.mkdir();path=directory/'review.jsonl'
            write_jsonl(path,[]);write_jsonl(directory/'inputs.jsonl',changed)
            path.with_suffix('.meta.json').write_text('{}')
            with self.assertRaisesRegex(ValueError,'changed original'):
                consolidate(inputs,[path],root/'merged/review.jsonl')
