"""Fit the declared transfer candidates and save local inference on identical inputs."""

import argparse
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench import teacher_encoder,teacher_finetune,transfer_encoder  # noqa: E402


def run(release,output):
    release=Path(release);output=Path(output)
    output.mkdir(parents=True,exist_ok=False)
    train_inputs=release/'train.inputs.jsonl';train_labels=release/'train.labels.jsonl'
    dev_inputs=release/'development.inputs.jsonl';dev_labels=release/'development.labels.jsonl'
    previous=output/'previous-head';previous.mkdir()
    teacher_encoder.predict(dev_inputs,previous/'development.predictions.jsonl',ROOT/'examples/encoder-regularization/l2-0.001')
    fitted=output/'frozen-heads'
    transfer_encoder.train(train_inputs,train_labels,dev_inputs,dev_labels,fitted)
    for name,directory in [('expanded-structured',fitted/'structured'),('expanded-text-only',fitted/'text-only')]:
        path=output/name;path.mkdir()
        teacher_encoder.predict(train_inputs,path/'training.predictions.jsonl',directory)
        teacher_encoder.predict(dev_inputs,path/'development.predictions.jsonl',directory)
        print(name,'inference complete',flush=True)
    for seed in (17,29):
        directory=output/f'finetuned-{seed}'
        teacher_finetune.train(train_inputs,train_labels,dev_inputs,dev_labels,directory,epochs=20,seed=seed)
        teacher_finetune.predict(train_inputs,directory/'training.predictions.jsonl',directory)
        teacher_finetune.predict(dev_inputs,directory/'development.predictions.jsonl',directory)
        print('finetuned',seed,'inference complete',flush=True)
    return output


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--release',type=Path,required=True);p.add_argument('--output-dir',type=Path,required=True)
    a=p.parse_args();run(a.release,a.output_dir)
