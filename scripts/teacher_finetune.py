"""Train or run the separate end-to-end teacher encoder candidate."""
import argparse
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from triage_bench.teacher_finetune import train,predict  # noqa: E402

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('train','predict'))
    for name in ('train-inputs','train-labels','dev-inputs','dev-labels','output-dir','inputs','model-dir','output'):
        parser.add_argument('--'+name,type=Path)
    parser.add_argument('--epochs',type=int,default=20)
    parser.add_argument('--seed',type=int,default=17)
    args=parser.parse_args()
    if args.mode=='train':
        if not all((args.train_inputs,args.train_labels,args.dev_inputs,args.dev_labels,args.output_dir)):
            parser.error('Training requires training/development inputs and labels plus output-dir')
        train(args.train_inputs,args.train_labels,args.dev_inputs,args.dev_labels,args.output_dir,args.epochs,args.seed)
    else:
        if not all((args.inputs,args.model_dir,args.output)):
            parser.error('Prediction requires inputs, model-dir, and output')
        rows=predict(args.inputs,args.output,args.model_dir)
        failed=sum(r['status']!='ok' for r in rows)
        print(f'Saved {len(rows)} local predictions; {failed} failed; no autoregressive calls')
        if failed:
            sys.exit(2)

if __name__=='__main__':
    main()
