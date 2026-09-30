"""Measure resident encoder inference separately from loading and warmup."""

import argparse
import json
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench import encoder,teacher_encoder  # noqa: E402
from triage_bench.dataset import read_jsonl  # noqa: E402
from triage_bench.evaluate import quantile  # noqa: E402


def benchmark(inputs,model_dir,output,repeats=10):
    if repeats<1:raise ValueError('Positive repeat count required')
    import numpy as np
    import torch
    output=Path(output);model_dir=Path(model_dir)
    if output.exists():raise FileExistsError(output)
    meta=json.loads((model_dir/'metadata.json').read_text())
    if meta['renderer_source_sha256']!=teacher_encoder.sha(teacher_encoder.__file__) or meta['head_sha256']!=teacher_encoder.sha(model_dir/'head.npz'):
        raise ValueError('Model or renderer differs')
    with np.load(model_dir/'head.npz',allow_pickle=False) as saved:weights,bias=saved['weights'],saved['bias']
    torch.set_num_threads(1)
    start=time.perf_counter();tokenizer,model,device=encoder.load_encoder(local_files_only=True)
    load_ms=(time.perf_counter()-start)*1000
    packets=[r['input'] for r in read_jsonl(inputs)]
    def infer(batch):
        x=teacher_encoder.matrix(batch,teacher_encoder.encode(batch,tokenizer,model,device,batch_size=len(batch)))
        return (x@weights.T+bias).argmax(axis=1).tolist()
    # Warm every packet before measurements and save repeat consistency.
    expected=[infer([p])[0] for p in packets]
    measurements=[]
    for batch_size in (1,8,16):
        latencies=[];decisions=[];started=time.perf_counter()
        for repetition in range(repeats):
            observed=[]
            for index in range(0,len(packets),batch_size):
                batch=packets[index:index+batch_size];before=time.perf_counter();answers=infer(batch)
                elapsed=(time.perf_counter()-before)*1000;observed.extend(answers)
                latencies.append({'batch_records':len(batch),'latency_ms':elapsed,'per_record_ms':elapsed/len(batch)})
            decisions.append(observed)
        elapsed=time.perf_counter()-started;values=[r['latency_ms'] for r in latencies]
        measurements.append({'batch_size':batch_size,'repeats':repeats,'measured_records':len(packets)*repeats,
                             'decisions_match_serial':all(d==expected for d in decisions),
                             'batch_p50_ms':quantile(values,.5),'batch_p95_ms':quantile(values,.95),
                             'records_per_second':len(packets)*repeats/elapsed,'wall_seconds':elapsed,'batches':latencies})
    result={'protocol':'northstar-resident-encoder-benchmark-v1','device':device,'model_load_ms':load_ms,
            'head_sha256':meta['head_sha256'],'input_sha256':teacher_encoder.sha(inputs),
            'execution':'Single resident process; one serial pass of explicit warmup; no concurrency; per-batch times include tokenizer, features, encode and head; no API calls',
            'limitations':'Local small synthetic sample; no deployment capacity or production latency claim',
            'measurements':measurements}
    output.parent.mkdir(parents=True,exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='measurements'},indent=2))
    for m in measurements:print(m['batch_size'],'batch p95 ms',m['batch_p95_ms'],'records/s',m['records_per_second'],'consistent',m['decisions_match_serial'])
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','model-dir','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--repeats',type=int,default=10)
    a=p.parse_args();benchmark(a.inputs,a.model_dir,a.output,a.repeats)
