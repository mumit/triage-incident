"""Frozen-head transfer and text-only ablation on reviewed new families."""

import json
from pathlib import Path

from . import encoder, teacher_encoder
from .dataset import read_jsonl
from .encoder_regularization import fit
from .teacher_training import validate

PROTOCOL = 'northstar-encoder-transfer-v1'


def train(train_inputs, train_labels, dev_inputs, dev_labels, output):
    validate(train_inputs,train_labels,dev_inputs,dev_labels)
    output = Path(output)
    if output.exists():
        raise FileExistsError(output)
    import numpy as np
    import torch
    import transformers
    torch.set_num_threads(1)
    records,development = read_jsonl(train_inputs),read_jsonl(dev_inputs)
    keys,devkeys = read_jsonl(train_labels),read_jsonl(dev_labels)
    keymap={k['id']:k for k in keys};devmap={k['id']:k for k in devkeys}
    tokenizer,model,device=encoder.load_encoder(local_files_only=True)
    packets=[r['input'] for r in records]; devpackets=[r['input'] for r in development]
    embedding=teacher_encoder.encode(packets,tokenizer,model,device)
    devembedding=teacher_encoder.encode(devpackets,tokenizer,model,device)
    x=torch.tensor(teacher_encoder.matrix(packets,embedding),dtype=torch.float64)
    dx=torch.tensor(teacher_encoder.matrix(devpackets,devembedding),dtype=torch.float64)
    y=torch.tensor([encoder.class_index(keymap[r['id']]['labels']) for r in records])
    dy=torch.tensor([encoder.class_index(devmap[r['id']]['labels']) for r in development])
    output.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(output/'features.npz',training=x.numpy(),development=dx.numpy())
    results=[]
    for name,dimension in (('structured',x.shape[1]),('text-only',embedding.shape[1])):
        weights,bias,diagnostic=fit(x[:,:dimension],y,.001)
        if not diagnostic['converged']:
            raise ValueError('Transfer fit did not converge')
        inference_weights=np.zeros((7,x.shape[1]),dtype=np.float32)
        inference_weights[:,:dimension]=weights.numpy().astype(np.float32)
        directory=output/name;directory.mkdir()
        np.savez_compressed(directory/'head.npz',weights=inference_weights,bias=bias.numpy().astype(np.float32))
        np.savez_compressed(directory/'optimization.npz',weights=weights.numpy(),bias=bias.numpy())
        result={'candidate':name,'fitted_dimensions':dimension,'l2':.001,**diagnostic,
                'training_correct':int(((x[:,:dimension]@weights.T+bias).argmax(dim=1)==y).sum()),
                'development_correct':int(((dx[:,:dimension]@weights.T+bias).argmax(dim=1)==dy).sum())}
        metadata={'protocol':teacher_encoder.PROTOCOL,'experiment_protocol':PROTOCOL,
                  'architecture':'Frozen MiniLM seven-way linear head; '+name+'; deterministic policy priority',
                  'ablation':'Structured feature coefficients are exactly zero' if name=='text-only' else None,
                  'model_id':encoder.MODEL_ID,'model_revision':encoder.MODEL_REVISION,'classes':encoder.CLASSES,
                  'max_tokens':teacher_encoder.MAX_TOKENS,'feature_scale':teacher_encoder.FEATURE_SCALE,
                  'renderer_source_sha256':teacher_encoder.sha(teacher_encoder.__file__),
                  'training_source_sha256':teacher_encoder.sha(__file__),
                  'training_records':len(y),'development_records':len(dy),
                  'training_families':sorted({k['incident_family_id'] for k in keys}),
                  'development_families':sorted({k['incident_family_id'] for k in devkeys}),
                  'train_input_sha256':teacher_encoder.sha(train_inputs),'train_label_sha256':teacher_encoder.sha(train_labels),
                  'dev_input_sha256':teacher_encoder.sha(dev_inputs),'dev_label_sha256':teacher_encoder.sha(dev_labels),
                  'selected_l2':.001,'selection':'Fixed L2 from previous experiment; compared on inspected combined development',
                  'optimization':result,'optimization_sha256':teacher_encoder.sha(directory/'optimization.npz'),
                  'feature_matrix_sha256':teacher_encoder.sha(output/'features.npz'),
                  'head_sha256':teacher_encoder.sha(directory/'head.npz'),
                  'device':device,'encoder_parameters':sum(p.numel() for p in model.parameters()),
                  'versions':{'torch':torch.__version__,'numpy':np.__version__,'transformers':transformers.__version__}}
        (directory/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
        results.append(result)
        print(name,result['training_correct'], '/',len(y),'train;',result['development_correct'],'/',len(dy),'development',flush=True)
    (output/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    (output/'training.source.py').write_bytes(Path(__file__).read_bytes())
    return results
