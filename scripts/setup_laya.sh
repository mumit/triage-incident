#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export UV_CACHE_DIR="$PWD/.cache/uv"
python3_executable=$(python3 -c 'import sys; print(sys.executable)')
if command -v uv >/dev/null 2>&1; then
  uv venv --python "$python3_executable" --allow-existing .venv-laya
  uv pip install --python .venv-laya/bin/python 'laya==0.3.21'
else
  python3 -m venv .venv-laya
  .venv-laya/bin/python -m pip install 'laya==0.3.21'
fi
printf '%s\n' 'Ready. Run scripts/start_laya.sh. The first start downloads the multilingual checkpoint.'
