import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from triage_bench.dataset import ROOT
from triage_bench.encoder_regularization import fit, diagnostics


@unittest.skipUnless(importlib.util.find_spec('torch'), 'requires optional encoder environment')
class RegularizationTests(unittest.TestCase):
    def test_stationarity_detects_perturbed_head_and_regularization_shrinks_coefficients(self):
        import torch
        torch.set_num_threads(1)
        x = torch.eye(7,dtype=torch.float64).repeat(2,1)
        y = torch.arange(7).repeat(2)
        weak, bias, checked = fit(x,y,.001)
        strong, _, stronger = fit(x,y,.01)
        self.assertTrue(checked['converged'])
        self.assertTrue(stronger['converged'])
        self.assertGreater(float(weak.square().sum()),float(strong.square().sum()))
        self.assertEqual((x@weak.T+bias).argmax(dim=1).tolist(),y.tolist())
        perturbed = weak.clone(); perturbed[0,0] += .1
        self.assertFalse(diagnostics(x,y,perturbed,bias,.001)['converged'])

    def test_fit_rejects_missing_classes_and_nonfinite_inputs(self):
        import torch
        x = torch.eye(7,dtype=torch.float64); y = torch.arange(7)
        with self.assertRaises(ValueError):
            fit(x[:6],y[:6],.001)
        x[0,0] = float('nan')
        with self.assertRaises(ValueError):
            fit(x,y,.001)

    def test_verifier_rejects_corrupted_artifact_and_wrong_selection(self):
        from scripts.verify_encoder_regularization import verify_experiment
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)/'experiment'
            shutil.copytree(ROOT/'examples/encoder-regularization',target)
            head = target/'l2-0.001/head.npz'
            saved = head.read_bytes(); head.write_bytes(saved+b'corrupt')
            with self.assertRaisesRegex(ValueError,'Trial artifact'):
                verify_experiment(target)
            head.write_bytes(saved)
            path = target/'results.json'
            result = json.loads(path.read_text()); result['selected'] = result['trials'][0]
            path.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError,'Selected candidate'):
                verify_experiment(target)
