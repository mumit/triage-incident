"""Verify all heads, stationarity, selection and saved inference without API calls."""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench import encoder, teacher_encoder  # noqa: E402
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.encoder_regularization import PROTOCOL, GRID, SOLVER, diagnostics  # noqa: E402
from scripts.teacher_encoder_evidence import verify  # noqa: E402


def verify_experiment(directory):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    directory = Path(directory)
    plan = json.loads((directory/'plan.json').read_text())
    result = json.loads((directory/'results.json').read_text())
    if (plan['protocol'] != PROTOCOL or result['protocol'] != PROTOCOL
            or plan['l2_trials'] != list(GRID) or plan['solver'] != SOLVER
            or result['plan_sha256'] != teacher_encoder.sha(directory/'plan.json')
            or plan['source_sha256'] != teacher_encoder.sha(directory/'training.source.py')
            or plan['renderer_source_sha256'] != teacher_encoder.sha(teacher_encoder.__file__)
            or result['feature_matrix_sha256'] != teacher_encoder.sha(directory/'features.npz')):
        raise ValueError('Experiment plan or source identity differs')
    inputs = {'training':ROOT/'examples/teacher-training/release-v1/train.inputs.jsonl',
              'development':ROOT/'examples/review/development-v2-reviewed-release/candidate.inputs.jsonl'}
    labels = {'training':ROOT/'examples/teacher-training/release-v1/train.labels.jsonl',
              'development':ROOT/'examples/review/development-v2-reviewed-release/candidate.labels.jsonl'}
    targets = {}
    for cohort,prefix in (('training','train'),('development','dev')):
        for kind,path in (('input',inputs[cohort]),('label',labels[cohort])):
            if plan['identities'][f'{prefix}_{kind}_sha256'] != teacher_encoder.sha(path):
                raise ValueError('Experiment data differs')
        keymap = {k['id']:k for k in read_jsonl(labels[cohort])}
        targets[cohort] = torch.tensor([encoder.class_index(keymap[r['id']]['labels']) for r in read_jsonl(inputs[cohort])])
    evidence = {cohort:verify(inputs[cohort],labels[cohort],directory/(cohort+'.evidence.json')) for cohort in inputs}
    with np.load(directory/'features.npz',allow_pickle=False) as saved:
        matrices = {name:torch.tensor(saved[name],dtype=torch.float64) for name in inputs}
    reference_path = ROOT/'examples/teacher-training/encoder-head-v1'
    if result['reference_head_sha256'] != teacher_encoder.sha(reference_path/'head.npz'):
        raise ValueError('Previous head differs')
    with np.load(reference_path/'head.npz',allow_pickle=False) as saved:
        old_weights = torch.tensor(saved['weights'],dtype=torch.float64)
        old_bias = torch.tensor(saved['bias'],dtype=torch.float64)
    checked = diagnostics(matrices['training'],targets['training'],old_weights,old_bias,.01)
    previous = result['previous_head_diagnostics']
    if (checked['converged'] != previous['converged']
            or any(abs(checked[k]-previous[k])>1e-12 for k in ('objective','gradient_inf_norm'))):
        raise ValueError('Previous-head stationarity differs')
    if [t['l2'] for t in result['trials']] != list(GRID):
        raise ValueError('Trial grid differs')
    expected_names = {t['name'] for t in result['trials']}
    if any(set(e['runs']) != expected_names for e in evidence.values()):
        raise ValueError('Evidence must include every trial')
    for trial in result['trials']:
        name = trial['name']; path = directory/name
        meta = json.loads((path/'metadata.json').read_text())
        if (meta['head_sha256'] != teacher_encoder.sha(path/'head.npz')
                or meta['optimization_sha256'] != teacher_encoder.sha(path/'optimization.npz')
                or meta['optimization'] != trial or meta['experiment_plan_sha256'] != result['plan_sha256']):
            raise ValueError('Trial artifact differs')
        with np.load(path/'optimization.npz',allow_pickle=False) as saved:
            weights = torch.tensor(saved['weights']); bias = torch.tensor(saved['bias'])
        checked = diagnostics(matrices['training'], targets['training'], weights, bias, trial['l2'])
        if (not checked['converged'] or not trial['converged']
                or abs(checked['objective']-trial['objective']) > 1e-12
                or abs(checked['gradient_inf_norm']-trial['gradient_inf_norm']) > 1e-12):
            raise ValueError('Stationarity differs or fit did not converge')
        with np.load(path/'head.npz',allow_pickle=False) as saved:
            if not (np.array_equal(saved['weights'],weights.numpy().astype(np.float32))
                    and np.array_equal(saved['bias'],bias.numpy().astype(np.float32))):
                raise ValueError('Inference head differs from fitted head')
        for cohort,x in matrices.items():
            predicted = (x@weights.T+bias).argmax(dim=1).tolist()
            section = evidence[cohort]['runs'][name]
            rows = {r['id']:r for r in section['predictions']}
            serial = [encoder.class_index(rows[r['id']]['predictions']) for r in read_jsonl(inputs[cohort])
                      if rows.get(r['id'],{}).get('status') == 'ok']
            correct = sum(p==int(y) for p,y in zip(predicted,targets[cohort]))
            if (serial != predicted or correct != trial[cohort+'_correct']
                    or section['summary']['all_four_correct'] != correct
                    or section['metadata']['head_sha256'] != meta['head_sha256']
                    or section['metadata']['head_training'] != meta):
                raise ValueError('Serial predictions differ from fitted scores')
    selected = max((t for t in result['trials'] if t['converged']),key=lambda t:t['development_correct'])
    if selected != result['selected']:
        raise ValueError('Selected candidate differs from declared rule')
    print(f'Verified five converged fits, saved heads and serial predictions. Selected {selected["name"]}: '
          f'{selected["training_correct"]}/58 training; {selected["development_correct"]}/16 development.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    verify_experiment(parser.parse_args().directory)
