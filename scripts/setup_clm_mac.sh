#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  printf '%s\n' 'This setup requires an Apple Silicon Mac. Use setup_clm.sh for Linux/NVIDIA.' >&2
  exit 1
fi
export UV_CACHE_DIR="$PWD/.cache/uv"
# Upstream declares vLLM as a mandatory dependency. This inference-only Mac
# environment intentionally replaces it with our MLX endpoint; no training stack.
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 --allow-existing .venv-clm-mac
  uv pip install --python .venv-clm-mac/bin/python 'mlx-lm==0.31.3' 'torch>=2.6' 'numpy>=1.24' 'requests>=2.28' 'fastapi>=0.100' 'uvicorn>=0.23' 'huggingface-hub>=0.20'
  uv pip install --python .venv-clm-mac/bin/python --no-deps 'contrastive-lm==0.1.0'
else
  python3.12 -m venv .venv-clm-mac
  .venv-clm-mac/bin/python -m pip install 'mlx-lm==0.31.3' 'torch>=2.6' 'numpy>=1.24' 'requests>=2.28' 'fastapi>=0.100' 'uvicorn>=0.23' 'huggingface-hub>=0.20'
  .venv-clm-mac/bin/python -m pip install --no-deps 'contrastive-lm==0.1.0'
fi
printf '%s\n' 'Software installed. No model weights downloaded. Run scripts/start_clm_mac.sh when ready.'
