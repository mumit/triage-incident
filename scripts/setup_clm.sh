#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Linux ]] || ! command -v nvidia-smi >/dev/null 2>&1; then
  printf '%s\n' 'Run this setup on a Linux NVIDIA GPU host. See docs/app.md for the SSH connection.' >&2
  exit 1
fi
export UV_CACHE_DIR="$PWD/.cache/uv"
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 --allow-existing .venv-clm
  uv pip install --python .venv-clm/bin/python 'contrastive-lm==0.1.0'
else
  python3.12 -m venv .venv-clm
  .venv-clm/bin/python -m pip install 'contrastive-lm==0.1.0'
fi
printf '%s\n' 'Ready. Run scripts/start_clm.sh. This downloads Qwen3-8B and CLM weights on first start.'
