"""Complete reviewed release, declared model fits and comparison after review resumes."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.export_transfer_reviews import export_all  # noqa: E402
from scripts.prepare_transfer_release import prepare  # noqa: E402
from scripts.run_encoder_transfer_candidates import run  # noqa: E402
from scripts.evaluate_encoder_transfer import evaluate  # noqa: E402
from scripts.verify_transfer_encoder import verify  # noqa: E402
from scripts.benchmark_transfer_encoder import benchmark  # noqa: E402


def complete(env_file):
    # Only wait for the current local continuation process, never schedule later work.
    last=ROOT/'runs/encoder-transfer/sol-training-audit-consolidated/review.meta.json'
    deadline=time.monotonic()+3600
    while not last.exists():
        if time.monotonic()>deadline:raise TimeoutError('Required review continuation did not finish')
        time.sleep(20)
    meta=json.loads(last.read_text())
    if meta['failed_records'] or meta['missing_records']:raise RuntimeError('Required reviews remain incomplete')
    output=ROOT/'examples/encoder-transfer'
    export_all(output)
    release=output/'release-v1';prepare(output,release)
    models=ROOT/'runs/encoder-transfer/candidates-01';run(release,models)
    luna=models/'luna-classifier';luna.mkdir()
    subprocess.run([sys.executable,str(ROOT/'scripts/run_transfer_llm.py'),
                    '--inputs',str(release/'development.inputs.jsonl'),
                    '--output',str(luna/'development.predictions.jsonl'),
                    '--env-file',str(env_file),'--min-interval','8'],check=True)
    evidence=output/'evaluation-01';evaluate(release,models,evidence)
    verify(release,models,evidence)
    benchmark(release/'development.inputs.jsonl',models/'frozen-heads/structured',
              output/'expanded-head-resident-benchmark.json',repeats=10)
    print('Transfer comparison and verification complete',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--env-file',type=Path,required=True)
    complete(p.parse_args().env_file)
