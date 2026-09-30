"""Run the separate local teacher-trained encoder without reading labels."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.teacher_encoder import predict  # noqa: E402

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inputs','model-dir','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    rows=predict(args.inputs,args.output,args.model_dir)
    print(f'Saved {len(rows)} predictions; {sum(r["status"]!="ok" for r in rows)} failed; no autoregressive calls')
    if any(r['status']!='ok' for r in rows):
        sys.exit(2)

if __name__=='__main__':
    main()
