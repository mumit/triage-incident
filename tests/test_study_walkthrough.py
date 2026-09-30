import json
import re
import tempfile
import unittest
from pathlib import Path

from scripts.build_study_walkthrough import DESTINATION, build


class StudyWalkthroughTests(unittest.TestCase):
    def test_presentation_reproduces_committed_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = build(Path(temporary) / 'walkthrough.html')
            self.assertEqual(output.read_bytes(), DESTINATION.read_bytes())

    def test_embedded_coverage_matches_actual_accepted_cases(self):
        html = DESTINATION.read_text()
        payload = re.search(r'<script id="study-data" type="application/json">(.*?)</script>', html)
        data = json.loads(payload.group(1))
        for row in data['coverage']:
            accepted = [case for case in data['cases']
                        if case['max_probability'] >= row['threshold']]
            errors = sum(case['predictions']['expanded-structured'] != case['labels']
                         for case in accepted)
            self.assertEqual(len(accepted), row['accepted'])
            self.assertEqual(errors, row['errors'])
