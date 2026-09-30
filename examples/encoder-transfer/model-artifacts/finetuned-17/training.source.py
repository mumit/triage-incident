"""End-to-end MiniLM candidate, separate from the frozen encoder and head trial."""

import json
import random
import time
from pathlib import Path

from . import encoder,teacher_encoder
from .dataset import read_jsonl,write_jsonl
from .policy import priority
from .teacher_training import validate

PROTOCOL='northstar-teacher-finetuned-minilm-v1'


def train(train_inputs,train_labels,dev_inputs,dev_labels,output,epochs=20,seed=17):
    if not isinstance(epochs,int) or isinstance(epochs,bool) or epochs<1:
        raise ValueError('Epochs must be a positive integer')
    if not isinstance(seed,int) or isinstance(seed,bool) or not 0<=seed<2**32:
        raise ValueError('Seed must be an integer in the NumPy seed range')
    validate(train_inputs,train_labels,dev_inputs,dev_labels)
    import numpy as np
    import torch
    import transformers
    output=Path(output)
    if output.exists():
        raise FileExistsError(output)
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed);torch.set_num_threads(1)
    records=read_jsonl(train_inputs);development=read_jsonl(dev_inputs)
    keys=read_jsonl(train_labels);devkeys=read_jsonl(dev_labels)
    keymap={k['id']:k for k in keys};devmap={k['id']:k for k in devkeys}
    if set(keymap)!={r['id'] for r in records} or set(devmap)!={r['id'] for r in development}:
        raise ValueError('Training/development IDs differ')
    if {k['incident_family_id'] for k in keys}&{k['incident_family_id'] for k in devkeys}:
        raise ValueError('Training/development family IDs overlap')
    if any('LLM' not in k.get('review_status','') for k in keys+devkeys):
        raise ValueError('Explicit LLM review provenance required')
    targets=[encoder.class_index(keymap[r['id']]['labels']) for r in records]
    devtargets=[encoder.class_index(devmap[r['id']]['labels']) for r in development]
    if set(targets)!=set(range(7)):
        raise ValueError('All seven training dispositions required')
    tokenizer,model,device=encoder.load_encoder(local_files_only=True)
    feature_size=len(teacher_encoder.features(records[0]['input']))
    head=torch.nn.Linear(model.config.hidden_size+feature_size,7).to(device)
    def prepare(rows):
        tokens=tokenizer([teacher_encoder.render(r['input']) for r in rows],padding=True,truncation=False,return_tensors='pt')
        if tokens['input_ids'].shape[1]>teacher_encoder.MAX_TOKENS:
            raise ValueError('Input exceeds limit; no truncation')
        flags=torch.tensor([teacher_encoder.features(r['input']) for r in rows],dtype=torch.float32)
        return tokens,flags
    train_tokens,train_flags=prepare(records);dev_tokens,dev_flags=prepare(development)
    y=torch.tensor(targets);dy=torch.tensor(devtargets)
    counts=torch.bincount(y,minlength=7)
    class_weights=(len(y)/(7*counts)).to(torch.float32).to(device)
    optimizer=torch.optim.AdamW([{'params':model.parameters(),'lr':3e-5},{'params':head.parameters(),'lr':1e-3}],weight_decay=.01)
    def logits(tokens,flags,indices):
        selected={name:values[indices].to(device) for name,values in tokens.items()}
        hidden=model(**selected).last_hidden_state
        mask=selected['attention_mask'].unsqueeze(-1)
        pooled=(hidden*mask).sum(dim=1)/mask.sum(dim=1)
        pooled=torch.nn.functional.normalize(pooled,p=2,dim=1)
        return head(torch.cat((pooled,teacher_encoder.FEATURE_SCALE*flags[indices].to(device)),dim=1))
    def correct(tokens,flags,target):
        with torch.inference_mode():
            return sum(int((logits(tokens,flags,slice(start,start+16)).argmax(dim=1).cpu()==target[start:start+16]).sum()) for start in range(0,len(target),16))
    output.mkdir(parents=True,exist_ok=False)
    best=-1;selected_epoch=0;history=[];started=time.perf_counter()
    for epoch in range(1,epochs+1):
        model.train();head.train()
        order=torch.randperm(len(y));losses=[]
        for start in range(0,len(y),8):
            indices=order[start:start+8]
            optimizer.zero_grad()
            loss=torch.nn.functional.cross_entropy(logits(train_tokens,train_flags,indices),y[indices].to(device),weight=class_weights)
            loss.backward();torch.nn.utils.clip_grad_norm_(list(model.parameters())+list(head.parameters()),1)
            optimizer.step();losses.append(float(loss.detach()))
        model.eval();head.eval()
        training=correct(train_tokens,train_flags,y);dev=correct(dev_tokens,dev_flags,dy)
        history.append({'epoch':epoch,'training_correct':training,'development_correct':dev,'mean_training_loss':sum(losses)/len(losses)})
        print(f'Epoch {epoch}: training {training}/{len(y)}; development {dev}/{len(dy)}',flush=True)
        if dev>best:
            best=dev;selected_epoch=epoch
            model.save_pretrained(output/'checkpoint');tokenizer.save_pretrained(output/'checkpoint')
            torch.save({k:v.detach().cpu() for k,v in head.state_dict().items()},output/'head.pt')
    metadata={'request_protocol':PROTOCOL,'base_model_id':encoder.MODEL_ID,'base_revision':encoder.MODEL_REVISION,
              'architecture':'End-to-end MiniLM encoder plus seven-way linear head, structured features, and policy priority',
              'max_tokens':teacher_encoder.MAX_TOKENS,'feature_size':feature_size,'selected_epoch':selected_epoch,
              'history':history,'training_records':len(records),'development_records':len(development),
              'train_input_sha256':teacher_encoder.sha(train_inputs),'train_label_sha256':teacher_encoder.sha(train_labels),
              'dev_input_sha256':teacher_encoder.sha(dev_inputs),'dev_label_sha256':teacher_encoder.sha(dev_labels),
              'training_families':sorted({k['incident_family_id'] for k in keys}),
              'development_families':sorted({k['incident_family_id'] for k in devkeys}),
              'selection':'Maximum complete development agreement; earliest epoch wins ties; not holdout performance',
              'hyperparameters':{'epochs':epochs,'encoder_lr':3e-5,'head_lr':1e-3,'batch_size':8,'seed':seed,'weight_decay':.01},
              'device':device,'training_seconds':time.perf_counter()-started,
              'encoder_parameters':sum(p.numel() for p in model.parameters()),
              'renderer_sha256':teacher_encoder.sha(teacher_encoder.__file__),'training_source_sha256':teacher_encoder.sha(__file__),
              'versions':{'torch':torch.__version__,'transformers':transformers.__version__,'numpy':np.__version__},
              'artifact_sha256':{str(p.relative_to(output)):teacher_encoder.sha(p) for p in (output/'checkpoint').iterdir() if p.is_file()}}
    metadata['artifact_sha256']['head.pt']=teacher_encoder.sha(output/'head.pt')
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (output/'training.source.py').write_bytes(Path(__file__).read_bytes())
    return metadata


def predict(inputs,output,model_dir):
    import torch
    from transformers import AutoModel,AutoTokenizer
    output=Path(output);model_dir=Path(model_dir)
    if output.exists() or output.with_suffix('.meta.json').exists():
        raise FileExistsError(output)
    meta=json.loads((model_dir/'metadata.json').read_text())
    if meta['request_protocol']!=PROTOCOL or meta['renderer_sha256']!=teacher_encoder.sha(teacher_encoder.__file__):
        raise ValueError('Fine-tuned protocol/renderer differs')
    if any(teacher_encoder.sha(model_dir/name)!=checksum for name,checksum in meta['artifact_sha256'].items()):
        raise ValueError('Fine-tuned artifact hash differs')
    device='mps' if torch.backends.mps.is_available() else 'cpu';started=time.perf_counter()
    tokenizer=AutoTokenizer.from_pretrained(model_dir/'checkpoint',local_files_only=True)
    model=AutoModel.from_pretrained(model_dir/'checkpoint',local_files_only=True).eval().to(device)
    head=torch.nn.Linear(model.config.hidden_size+meta['feature_size'],7).to(device)
    head.load_state_dict(torch.load(model_dir/'head.pt',weights_only=True,map_location=device));head.eval()
    load_ms=(time.perf_counter()-started)*1000;rows=[]
    for record in read_jsonl(inputs):
        start=time.perf_counter();packet=record['input']
        try:
            tokens=tokenizer(teacher_encoder.render(packet),return_tensors='pt',truncation=False)
            if tokens['input_ids'].shape[1]>teacher_encoder.MAX_TOKENS:
                raise ValueError('Input exceeds limit; no truncation')
            tokens=tokens.to(device)
            with torch.inference_mode():
                hidden=model(**tokens).last_hidden_state;mask=tokens['attention_mask'].unsqueeze(-1)
                pooled=torch.nn.functional.normalize((hidden*mask).sum(dim=1)/mask.sum(dim=1),p=2,dim=1)
                flags=torch.tensor([teacher_encoder.features(packet)],dtype=torch.float32,device=device)
                scores=head(torch.cat((pooled,teacher_encoder.FEATURE_SCALE*flags),dim=1))
                probabilities=scores.softmax(dim=1)[0].cpu().tolist();category=int(scores.argmax())
            answers=dict(zip(encoder.FIELDS,encoder.CLASSES[category]));answers['priority']=priority(packet['service_impact'])
            row={'id':record['id'],'status':'ok','predictions':answers,'disposition_probabilities':probabilities}
        except (ValueError,KeyError,TypeError) as exc:
            row={'id':record['id'],'status':'error','error':f'{type(exc).__name__}: {exc}'}
        row['latency_ms']=(time.perf_counter()-start)*1000;rows.append(row)
    write_jsonl(output,rows)
    runmeta={'provider':'teacher_finetuned','request_protocol':PROTOCOL,'input_sha256':teacher_encoder.sha(inputs),
             'head_training':meta,'model_load_ms':load_ms,'device':device,'records':len(rows),
             'failed_records':sum(r['status']!='ok' for r in rows),'no_autoregressive_calls':True,
             'execution':'serial local inference; cached checkpoint; no warmup; per-record latency excludes model load'}
    output.with_suffix('.meta.json').write_text(json.dumps(runmeta,indent=2)+'\n')
    return rows
