"""Verify frozen study files and recompute both portable result snapshots."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'examples/comparison-study.closed.json').read_text())
    if manifest['status'] != 'closed':
        raise ValueError('Study is not closed')
    for filename, expected in manifest['sha256'].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f'Frozen study file changed: {filename}')
    for script in ('verify_full_evaluation.py', 'verify_encoder_evidence.py'):
        subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], cwd=ROOT, check=True)
    print(f'Closed study verified: {len(manifest["sha256"])} frozen files')


if __name__ == '__main__':
    main()
