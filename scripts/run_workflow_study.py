"""Run frozen development candidates, then score saved outputs.

Uses new immutable run directories. Live Jev calls require a local credential;
predictions never read labels. Draft scores are development diagnostics only.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from triage_bench import compact_jev, workflow  # noqa: E402
from triage_bench.app import load_env  # noqa: E402
from triage_bench.encoder import predict_file  # noqa: E402
from triage_bench.evaluate import evaluate  # noqa: E402
from triage_bench.runner import run  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cohort', choices=('draft', 'validation'), default='draft')
    parser.add_argument('--providers', nargs='+', choices=('encoder', 'jev_workflow', 'jev_original', 'jev_compact'),
                        default=['encoder', 'jev_workflow', 'jev_original'])
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--model-dir', type=Path, default=ROOT / 'runs/encoder/minilm-v1')
    parser.add_argument('--env-file', type=Path)
    args = parser.parse_args()
    if len(set(args.providers)) != len(args.providers):
        parser.error('Each provider may be selected only once')
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('--env-file does not exist')
        load_env(args.env_file)
    import os
    if any(provider.startswith('jev') for provider in args.providers) and not os.getenv('TYPESAFE_API_KEY'):
        parser.error('Set TYPESAFE_API_KEY in the environment or the selected local .env file')
    if 'encoder' in args.providers:
        expected = json.loads((ROOT / 'examples/encoder-evaluation.evidence.json').read_text())['head_sha256']
        if hashlib.sha256((args.model_dir / 'head.npz').read_bytes()).hexdigest() != expected:
            raise ValueError('Head differs from the frozen encoder reference')
    data = ROOT / ('data/workflow-study' if args.cohort == 'draft' else 'data')
    inputs, labels = data / f'{args.cohort}.inputs.jsonl', data / f'{args.cohort}.labels.jsonl'
    args.output_dir.mkdir(parents=True, exist_ok=False)
    manifest = {'cohort': args.cohort, 'label_review': 'unreviewed AI-authored labels',
                'evaluation_use': 'development only; not a holdout', 'providers': args.providers,
                'input_sha256': hashlib.sha256(inputs.read_bytes()).hexdigest(),
                'label_sha256': hashlib.sha256(labels.read_bytes()).hexdigest(), 'results': {}}
    failed = False
    for provider in args.providers:
        predictions = args.output_dir / f'{provider}.jsonl'
        print(f'Running {provider} on {args.cohort}', flush=True)
        if provider == 'encoder':
            predict_file(inputs, predictions, args.model_dir)
        else:
            run(inputs, predictions, provider='jev', model='jev-1.13.0',
                endpoint='https://api.typesafe.ai/v1/systemone', key_env='TYPESAFE_API_KEY',
                context_tokens=8192, deployment=f'Hosted Jev; development {provider}',
                decision_workflow=({'jev_workflow': workflow, 'jev_compact': compact_jev}.get(provider)))
        # Predictions are completed and saved before the scorer opens labels.
        metrics = evaluate(labels, predictions, predictions.with_suffix('.metrics.json'))
        manifest['results'][provider] = metrics
        (args.output_dir / 'study.json').write_text(json.dumps(manifest, indent=2) + '\n')
        failed |= bool(metrics['failed_records'] or metrics['missing_records'])
        print(f'{provider}: {metrics["all_fields_accuracy"]:.1%} all four; '
              f'{metrics["failed_records"]} failed; {metrics["missing_records"]} missing', flush=True)
    if failed:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
