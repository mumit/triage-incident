"""Bounded head experiment using the unchanged teacher encoder inputs."""

import json
import time
from pathlib import Path

from . import encoder, teacher_encoder
from .dataset import read_jsonl
from .teacher_training import validate

PROTOCOL = 'northstar-encoder-regularization-v1'
GRID = (0.01, 0.003, 0.001, 0.0003, 0.0001)
SOLVER = {'max_iter': 1000, 'tolerance_grad': 1e-8, 'tolerance_change': 1e-15,
          'line_search_fn': 'strong_wolfe', 'required_gradient_inf_norm': 1e-7}


def objective(x, y, weights, bias, l2):
    import torch
    counts = torch.bincount(y, minlength=7)
    class_weights = (len(y)/(7*counts)).to(torch.float64)
    loss = torch.nn.functional.cross_entropy(x@weights.T+bias, y, weight=class_weights)
    return loss+l2*weights.square().sum()/2


def diagnostics(x, y, weights, bias, l2):
    import torch
    weights = weights.detach().clone().requires_grad_(True)
    bias = bias.detach().clone().requires_grad_(True)
    loss = objective(x, y, weights, bias, l2)
    gradients = torch.autograd.grad(loss, (weights, bias))
    norm = max(float(g.abs().max()) for g in gradients)
    return {'objective': float(loss.detach()), 'gradient_inf_norm': norm,
            'converged': norm <= SOLVER['required_gradient_inf_norm']}


def fit(x, y, l2):
    import torch
    if (x.dtype != torch.float64 or not torch.isfinite(x).all()
            or set(y.tolist()) != set(range(7)) or len(x) != len(y) or l2 <= 0):
        raise ValueError('Fit requires finite float64 inputs, all seven classes, and positive L2')
    weights = torch.zeros((7, x.shape[1]), dtype=torch.float64, requires_grad=True)
    bias = torch.zeros(7, dtype=torch.float64, requires_grad=True)
    optimizer = torch.optim.LBFGS([weights, bias], **{k:v for k,v in SOLVER.items()
                                                   if k != 'required_gradient_inf_norm'})
    def closure():
        optimizer.zero_grad()
        loss = objective(x, y, weights, bias, l2)
        loss.backward()
        return loss
    optimizer.step(closure)
    state = optimizer.state[weights]
    result = diagnostics(x, y, weights, bias, l2)
    result.update(iterations=state['n_iter'], function_evaluations=state['func_evals'])
    return weights.detach(), bias.detach(), result


def train(train_inputs, train_labels, dev_inputs, dev_labels, output):
    validate(train_inputs, train_labels, dev_inputs, dev_labels)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    import numpy as np
    import torch
    import transformers
    torch.set_num_threads(1)
    records, development = read_jsonl(train_inputs), read_jsonl(dev_inputs)
    keys, devkeys = read_jsonl(train_labels), read_jsonl(dev_labels)
    keymap = {k['id']:k for k in keys}; devmap = {k['id']:k for k in devkeys}
    identities = {name:teacher_encoder.sha(path) for name,path in
                  (('train_input_sha256',train_inputs), ('train_label_sha256',train_labels),
                   ('dev_input_sha256',dev_inputs), ('dev_label_sha256',dev_labels))}
    reference_path = Path(__file__).resolve().parents[1]/'examples/teacher-training/encoder-head-v1'
    reference = json.loads((reference_path/'metadata.json').read_text())
    for name, checksum in identities.items():
        if reference[name] != checksum:
            raise ValueError('Bounded experiment must use the previous datasets unchanged')
    if (reference['renderer_source_sha256'] != teacher_encoder.sha(teacher_encoder.__file__)
            or reference['head_sha256'] != teacher_encoder.sha(reference_path/'head.npz')):
        raise ValueError('Reference renderer/head identity differs')
    plan = {'protocol':PROTOCOL, 'l2_trials':GRID, 'identities':identities,
            'renderer_source_sha256':teacher_encoder.sha(teacher_encoder.__file__),
            'model_id':encoder.MODEL_ID, 'model_revision':encoder.MODEL_REVISION,
            'feature_scale':teacher_encoder.FEATURE_SCALE, 'max_tokens':teacher_encoder.MAX_TOKENS,
            'solver':SOLVER, 'selection':'Maximum development complete agreement among converged fits; grid order breaks ties',
            'evaluation_use':'Previously inspected development only; not holdout',
            'source_sha256':teacher_encoder.sha(__file__)}
    output.mkdir(parents=True, exist_ok=False)
    (output/'plan.json').write_text(json.dumps(plan, indent=2)+'\n')
    (output/'training.source.py').write_bytes(Path(__file__).read_bytes())
    tokenizer, model, device = encoder.load_encoder(local_files_only=True)
    packets = [r['input'] for r in records]; devpackets = [r['input'] for r in development]
    x = torch.tensor(teacher_encoder.matrix(packets, teacher_encoder.encode(packets, tokenizer, model, device)), dtype=torch.float64)
    dx = torch.tensor(teacher_encoder.matrix(devpackets, teacher_encoder.encode(devpackets, tokenizer, model, device)), dtype=torch.float64)
    y = torch.tensor([encoder.class_index(keymap[r['id']]['labels']) for r in records])
    dy = torch.tensor([encoder.class_index(devmap[r['id']]['labels']) for r in development])
    np.savez_compressed(output/'features.npz', training=x.numpy(), development=dx.numpy())
    with np.load(reference_path/'head.npz', allow_pickle=False) as old:
        old_weights = torch.tensor(old['weights'], dtype=torch.float64)
        old_bias = torch.tensor(old['bias'], dtype=torch.float64)
    old_diagnostics = diagnostics(x, y, old_weights, old_bias, .01)
    trials = []; selected = None
    for l2 in GRID:
        started = time.perf_counter()
        weights, bias, result = fit(x, y, l2)
        name = 'l2-'+format(l2, '.4g')
        directory = output/name; directory.mkdir()
        np.savez_compressed(directory/'head.npz', weights=weights.numpy().astype(np.float32), bias=bias.numpy().astype(np.float32))
        np.savez_compressed(directory/'optimization.npz', weights=weights.numpy(), bias=bias.numpy())
        result.update(l2=l2, name=name, training_seconds=time.perf_counter()-started,
                      training_correct=int(((x@weights.T+bias).argmax(dim=1)==y).sum()),
                      development_correct=int(((dx@weights.T+bias).argmax(dim=1)==dy).sum()))
        metadata = {**reference, **identities, 'selected_l2':l2, 'trials':[result],
                    'selection':'One predefined L2 trial; experiment selects separately',
                    'head_sha256':teacher_encoder.sha(directory/'head.npz'),
                    'experiment_protocol':PROTOCOL, 'experiment_plan_sha256':teacher_encoder.sha(output/'plan.json'),
                    'training_source_sha256':teacher_encoder.sha(__file__), 'optimization':result,
                    'optimization_sha256':teacher_encoder.sha(directory/'optimization.npz'),
                    'feature_matrix_sha256':teacher_encoder.sha(output/'features.npz'),
                    'device':device, 'versions':{'torch':torch.__version__, 'numpy':np.__version__, 'transformers':transformers.__version__}}
        (directory/'metadata.json').write_text(json.dumps(metadata, indent=2)+'\n')
        trials.append(result)
        if result['converged'] and (selected is None or result['development_correct'] > selected['development_correct']):
            selected = result
        print(f'L2 {l2}: training {result["training_correct"]}/{len(y)}; development {result["development_correct"]}/{len(dy)}; '
              f'gradient {result["gradient_inf_norm"]:.3g}; converged {result["converged"]}', flush=True)
    summary = {'protocol':PROTOCOL, 'plan_sha256':teacher_encoder.sha(output/'plan.json'),
               'feature_matrix_sha256':teacher_encoder.sha(output/'features.npz'),
               'previous_head_diagnostics':old_diagnostics, 'trials':trials, 'selected':selected,
               'reference_head_sha256':reference['head_sha256'], 'training_records':len(y), 'development_records':len(dy)}
    (output/'results.json').write_text(json.dumps(summary, indent=2)+'\n')
    return summary
