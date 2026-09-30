"""Verify transfer head stationarity, ablation and fitted versus serial decisions."""

import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench import encoder,teacher_encoder  # noqa: E402
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.encoder_regularization import diagnostics  # noqa: E402
from triage_bench.teacher_training import validate  # noqa: E402
from scripts.teacher_encoder_evidence import verify as verify_evidence  # noqa: E402


def verify(release,models,evidence):
    import numpy as np
    import torch
    torch.set_num_threads(1)
    release=Path(release);models=Path(models);evidence=Path(evidence)
    validate(release/'train.inputs.jsonl',release/'train.labels.jsonl',release/'development.inputs.jsonl',release/'development.labels.jsonl')
    sections={}
    for cohort,stem in [('training','train'),('combined-development','development')]:
        sections[cohort]=verify_evidence(release/(stem+'.inputs.jsonl'),release/(stem+'.labels.jsonl'),evidence/(cohort+'.evidence.json'))
    frozen=models/'frozen-heads'
    with np.load(frozen/'features.npz',allow_pickle=False) as saved:
        matrices={k:torch.tensor(saved[k],dtype=torch.float64) for k in ('training','development')}
    targets={}
    for cohort,stem in [('training','train'),('development','development')]:
        keys={k['id']:k for k in read_jsonl(release/(stem+'.labels.jsonl'))}
        targets[cohort]=torch.tensor([encoder.class_index(keys[r['id']]['labels']) for r in read_jsonl(release/(stem+'.inputs.jsonl'))])
    for name in ('structured','text-only'):
        directory=frozen/name;meta=json.loads((directory/'metadata.json').read_text())
        if meta['head_sha256']!=teacher_encoder.sha(directory/'head.npz') or meta['optimization_sha256']!=teacher_encoder.sha(directory/'optimization.npz'):
            raise ValueError('Frozen artifact differs')
        if meta['feature_matrix_sha256']!=teacher_encoder.sha(frozen/'features.npz'):
            raise ValueError('Feature matrix differs')
        with np.load(directory/'optimization.npz',allow_pickle=False) as saved:
            weights=torch.tensor(saved['weights']);bias=torch.tensor(saved['bias'])
        dimension=weights.shape[1]
        checked=diagnostics(matrices['training'][:,:dimension],targets['training'],weights,bias,.001)
        if not checked['converged'] or abs(checked['objective']-meta['optimization']['objective'])>1e-12:
            raise ValueError('Fit is not stationary')
        with np.load(directory/'head.npz',allow_pickle=False) as saved:
            if (not np.array_equal(saved['weights'][:,:dimension],weights.numpy().astype(np.float32))
                    or not np.array_equal(saved['bias'],bias.numpy().astype(np.float32))
                    or (name=='text-only' and np.count_nonzero(saved['weights'][:,dimension:]))):
                raise ValueError('Inference head or text ablation differs')
        for cohort,stem,section in [('training','train','training'),('development','development','combined-development')]:
            predicted=(matrices[cohort][:,:dimension]@weights.T+bias).argmax(dim=1).tolist()
            run=sections[section]['runs']['expanded-'+name]
            rows={r['id']:r for r in run['predictions']}
            serial=[encoder.class_index(rows[r['id']]['predictions']) for r in read_jsonl(release/(stem+'.inputs.jsonl'))]
            if serial!=predicted:raise ValueError('Saved serial decisions differ from fitted scores')
    for seed in (17,29):
        directory=models/f'finetuned-{seed}';meta=json.loads((directory/'metadata.json').read_text())
        for path,checksum in meta['artifact_sha256'].items():
            if teacher_encoder.sha(directory/path)!=checksum:raise ValueError('Fine-tuned artifact differs')
        if teacher_encoder.sha(directory/'training.source.py')!=meta['training_source_sha256']:
            raise ValueError('Archived fine-tuning source differs')
        best=max(meta['history'],key=lambda h:h['development_correct'])
        if best['epoch']!=meta['selected_epoch']:raise ValueError('Epoch selection differs')
        for cohort,field in [('training','training_correct'),('combined-development','development_correct')]:
            if sections[cohort]['runs'][f'finetuned-{seed}']['summary']['all_four_correct']!=best[field]:
                raise ValueError('Fine-tuned serial score differs from selected epoch')
    print('Verified release separation, stationary heads, text ablation, serial decisions, fine-tuned artifacts and epoch selection')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('release','model-root','evidence-root'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();verify(a.release,a.model_root,a.evidence_root)
