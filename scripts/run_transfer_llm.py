"""Run Luna's unchanged classification prompt independently of offline label review."""

import argparse
import os
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.app import load_env  # noqa: E402
from triage_bench.llm import chat_endpoint  # noqa: E402
from triage_bench.runner import run  # noqa: E402


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inputs',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--env-file',type=Path,required=True);p.add_argument('--model',default='gpt-6-luna')
    p.add_argument('--min-interval',type=float,default=8)
    a=p.parse_args();load_env(a.env_file)
    key=os.getenv('FUELIX_BEARER_TOKEN','');base=os.getenv('LLM_BASE_URL','')
    if not key or not base:p.error('Fuel iX token and base URL required')
    if not 0<=a.min_interval<=60:p.error('Interval must be within 60 seconds')
    def progress(index,count,row):
        print(f'{index}/{count}: {row["status"]}',flush=True)
        if index<count:time.sleep(a.min_interval)
    result=run(a.inputs,a.output,provider='llm',model=a.model,endpoint=chat_endpoint(base),
               api_key=key,context_tokens=32768,deployment='Fuel iX proxy; separate zero-shot classification reference',
               progress=progress)
    if result['failed_records']:sys.exit(2)
