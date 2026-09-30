"""Separate teacher-trained encoder configuration; no autoregressive inference."""

import hashlib
import json
import re
import time
from datetime import datetime
from pathlib import Path

from . import encoder
from .dataset import read_jsonl, write_jsonl
from .policy import priority

PROTOCOL = 'northstar-teacher-encoder-v1'
MAX_TOKENS = 512
FEATURE_SCALE = .5
REGULARIZATION = (0.01, 0.1, 1.0, 10.0)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def observation_ages(packet):
    decision = datetime.fromisoformat(packet['decision_timestamp'].replace('Z','+00:00'))
    ages = []
    for observation in packet['observations']:
        if observation.get('observed_at'):
            observed = datetime.fromisoformat(observation['observed_at'].replace('Z','+00:00'))
            ages.append((decision-observed).total_seconds()/60)
    return ages


def graph_features(packet):
    text = ' '.join(item['detail'] for item in packet['observations'])
    # Mechanical graph feature only. The head learns how this relates to triage;
    # no output veto, domain prediction, or inferred missing edge is applied.
    alarm = re.search(r'\buplink\s+([A-Za-z0-9_-]+)\b',text,re.I)
    graph = {}
    for left,right in packet['topology'].get('edges',[]):
        graph.setdefault(left.lower(),set()).add(right.lower())
        graph.setdefault(right.lower(),set()).add(left.lower())
    sites = [node for node in graph if re.search(r'(?:^|-)s\d+$',node)]
    connected = []
    if alarm:
        for site in sites:
            visited={site};frontier=[site]
            while frontier:
                for neighbor in graph.get(frontier.pop(),()):
                    if neighbor not in visited:
                        visited.add(neighbor);frontier.append(neighbor)
            connected.append(alarm.group(1).lower() in visited)
    complete = packet['topology'].get('note','').lower().startswith('complete upstream dependencies')
    return [int(complete),int(bool(alarm)),sum(connected)/len(connected) if connected else 0,
            int(bool(sites)),int(bool(connected) and all(connected)),int(bool(connected) and not any(connected))]


def features(packet):
    ages=observation_ages(packet)
    change=packet.get('change_record',{})
    return encoder.structured_features(packet)+[
        min(max(ages,default=0),120)/120, min(max(min(ages,default=0),0),120)/120,
        int(any(age>15 for age in ages)), int(any(age<0 for age in ages)),
        int(change.get('status')=='unknown'),int(change.get('status')=='completed'),
        int(change.get('status')=='in_progress'),int(bool(change.get('scope'))),
    ]+graph_features(packet)


def render(packet):
    ages=observation_ages(packet)
    observation=' '.join(item['detail'] for item in packet['observations'])
    impact=packet['service_impact']
    change=packet.get('change_record',{})
    topology=packet['topology']
    return (f'Observation: {observation} Impact: {impact["status"]} at {impact["affected_sites"]} sites. '
            f'Observation age minutes: {ages}. Topology: {topology.get("note","")} '
            f'Edges: {json.dumps(topology.get("edges",[]),separators=(",",":"))}. '
            f'Change: {json.dumps(change,ensure_ascii=False,sort_keys=True)}')


def encode(packets,tokenizer,model,device,batch_size=16):
    import numpy as np
    import torch
    vectors=[]
    with torch.inference_mode():
        for start in range(0,len(packets),batch_size):
            tokens=tokenizer([render(packet) for packet in packets[start:start+batch_size]],padding=True,truncation=False,return_tensors='pt')
            if any(length>MAX_TOKENS for length in tokens['attention_mask'].sum(dim=1)):
                raise ValueError('Teacher encoder input exceeds 512 tokens; no truncation applied')
            tokens=tokens.to(device)
            hidden=model(**tokens).last_hidden_state
            mask=tokens['attention_mask'].unsqueeze(-1)
            pooled=(hidden*mask).sum(dim=1)/mask.sum(dim=1)
            vectors.append(torch.nn.functional.normalize(pooled,p=2,dim=1).cpu().numpy())
    return np.concatenate(vectors)


def matrix(packets,embeddings):
    import numpy as np
    return np.hstack((embeddings,FEATURE_SCALE*np.asarray([features(packet) for packet in packets],dtype=np.float32)))


def train(train_inputs,train_labels,dev_inputs,dev_labels,output):
    import numpy as np
    import torch
    import transformers
    torch.set_num_threads(1)
    output=Path(output)
    if output.exists():
        raise FileExistsError(output)
    records=read_jsonl(train_inputs);development=read_jsonl(dev_inputs)
    keys=read_jsonl(train_labels);devkeys=read_jsonl(dev_labels)
    keymap={key['id']:key for key in keys};devmap={key['id']:key for key in devkeys}
    if (len(keymap)!=len(keys) or len(devmap)!=len(devkeys)
            or set(keymap)!={r['id'] for r in records} or set(devmap)!={r['id'] for r in development}):
        raise ValueError('Training/development input and label IDs differ or duplicate')
    train_families={key['incident_family_id'] for key in keys}
    dev_families={key['incident_family_id'] for key in devkeys}
    if not train_families.isdisjoint(dev_families):
        raise ValueError('Training and development family IDs overlap')
    if {key.get('pair_id') for key in keys if key.get('pair_id')} & {key.get('pair_id') for key in devkeys if key.get('pair_id')}:
        raise ValueError('Training and development pair IDs overlap')
    targets=[encoder.class_index(keymap[r['id']]['labels']) for r in records]
    devtargets=[encoder.class_index(devmap[r['id']]['labels']) for r in development]
    if set(targets)!=set(range(7)):
        raise ValueError('Reviewed training data must cover all seven dispositions')
    if any('LLM' not in key.get('review_status','') for key in keys+devkeys):
        raise ValueError('This experiment requires explicit LLM-review label provenance')
    tokenizer,model,device=encoder.load_encoder(local_files_only=True)
    packets=[r['input'] for r in records];devpackets=[r['input'] for r in development]
    x=torch.tensor(matrix(packets,encode(packets,tokenizer,model,device)),dtype=torch.float64)
    dx=torch.tensor(matrix(devpackets,encode(devpackets,tokenizer,model,device)),dtype=torch.float64)
    y=torch.tensor(targets);dy=torch.tensor(devtargets)
    counts=torch.bincount(y,minlength=7)
    class_weights=(len(targets)/(7*counts)).to(torch.float64)
    trials=[];selected=None
    for regularization in REGULARIZATION:
        weights=torch.zeros((7,x.shape[1]),dtype=torch.float64,requires_grad=True)
        bias=torch.zeros(7,dtype=torch.float64,requires_grad=True)
        optimizer=torch.optim.LBFGS([weights,bias],max_iter=200,line_search_fn='strong_wolfe',tolerance_grad=1e-8)
        def closure():
            optimizer.zero_grad()
            loss=torch.nn.functional.cross_entropy(x@weights.T+bias,y,weight=class_weights)
            loss=loss+regularization*weights.square().sum()/2
            loss.backward();return loss
        optimizer.step(closure)
        with torch.no_grad():
            correct=int(((dx@weights.T+bias).argmax(dim=1)==dy).sum())
            traincorrect=int(((x@weights.T+bias).argmax(dim=1)==y).sum())
        trials.append({'l2':regularization,'training_correct':traincorrect,'development_correct':correct})
        print(f'L2 {regularization}: training {traincorrect}/{len(records)}; development {correct}/{len(development)}',flush=True)
        if selected is None or correct>selected[0]:
            selected=(correct,regularization,weights.detach().numpy().astype(np.float32),bias.detach().numpy().astype(np.float32))
    output.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(output/'head.npz',weights=selected[2],bias=selected[3])
    metadata={'protocol':PROTOCOL,'architecture':'frozen pinned MiniLM plus learned seven-class linear head and structured features; policy priority',
              'model_id':encoder.MODEL_ID,'model_revision':encoder.MODEL_REVISION,'classes':encoder.CLASSES,
              'max_tokens':MAX_TOKENS,'feature_scale':FEATURE_SCALE,'renderer_source_sha256':sha(__file__),
              'training_records':len(records),'training_families':sorted(train_families),
              'development_records':len(development),'development_families':sorted(dev_families),
              'train_input_sha256':sha(train_inputs),'train_label_sha256':sha(train_labels),
              'dev_input_sha256':sha(dev_inputs),'dev_label_sha256':sha(dev_labels),
              'selection':'Best complete development disposition accuracy; first trial wins ties; development only',
              'selected_l2':selected[1],'trials':trials,'head_sha256':sha(output/'head.npz'),
              'encoder_parameters':sum(p.numel() for p in model.parameters()),'device':device,
              'versions':{'torch':torch.__version__,'numpy':np.__version__,'transformers':transformers.__version__}}
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (output/'source.py').write_bytes(Path(__file__).read_bytes())
    return metadata


def predict(inputs,output,model_dir):
    import numpy as np
    output=Path(output);model_dir=Path(model_dir)
    if output.exists() or output.with_suffix('.meta.json').exists():
        raise FileExistsError(output)
    meta=json.loads((model_dir/'metadata.json').read_text())
    if (meta['protocol']!=PROTOCOL or meta['renderer_source_sha256']!=sha(__file__)
            or meta['head_sha256']!=sha(model_dir/'head.npz')
            or meta['model_revision']!=encoder.MODEL_REVISION):
        raise ValueError('Teacher encoder artifact identity differs')
    with np.load(model_dir/'head.npz',allow_pickle=False) as saved:
        weights,bias=saved['weights'],saved['bias']
    if (weights.shape!=(7,384+len(features(read_jsonl(inputs)[0]['input']))) or bias.shape!=(7,)
            or not np.isfinite(weights).all() or not np.isfinite(bias).all()):
        raise ValueError('Invalid head')
    started=time.perf_counter()
    tokenizer,model,device=encoder.load_encoder(local_files_only=True)
    load_ms=(time.perf_counter()-started)*1000
    rows=[]
    for record in read_jsonl(inputs):
        start=time.perf_counter();packet=record['input']
        try:
            x=matrix([packet],encode([packet],tokenizer,model,device))
            logits=(x@weights.T+bias)[0]
            category=int(logits.argmax())
            exp=np.exp(logits-logits.max());probabilities=exp/exp.sum()
            answers=dict(zip(encoder.FIELDS,encoder.CLASSES[category]));answers['priority']=priority(packet['service_impact'])
            row={'id':record['id'],'status':'ok','predictions':answers,
                 'disposition_probabilities':probabilities.tolist()}
        except (ValueError,KeyError,TypeError) as exc:
            row={'id':record['id'],'status':'error','error':f'{type(exc).__name__}: {exc}'}
        row['latency_ms']=(time.perf_counter()-start)*1000;rows.append(row)
    write_jsonl(output,rows)
    runmeta={'provider':'teacher_encoder','request_protocol':PROTOCOL,'input_sha256':sha(inputs),
             'head_sha256':meta['head_sha256'],'head_training':meta,'device':device,'model_load_ms':load_ms,
             'records':len(rows),'failed_records':sum(r['status']!='ok' for r in rows),
             'execution':'serial; no warmup; per-record time excludes model load; local cached weights only',
             'no_autoregressive_calls':True}
    output.with_suffix('.meta.json').write_text(json.dumps(runmeta,indent=2)+'\n')
    return rows
