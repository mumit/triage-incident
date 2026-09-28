#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="$PWD/.cache/uv"
if command -v uv >/dev/null 2>&1; then
  uv venv --python 3.12 --allow-existing .venv-laya
  uv pip install --python .venv-laya/bin/python 'laya==0.3.21'
else
  python3.12 -m venv .venv-laya
  .venv-laya/bin/python -m pip install 'laya==0.3.21'
fi
printf '%s\n' 'Ready. Run scripts/start_laya.sh. The first start downloads the multilingual checkpoint.'
