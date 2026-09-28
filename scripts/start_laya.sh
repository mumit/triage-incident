#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export HF_HOME="$PWD/.cache/huggingface"
export USE_TF=0
if [[ ! -x .venv-laya/bin/python ]]; then
  printf '%s\n' 'Run scripts/setup_laya.sh first.' >&2
  exit 1
fi
exec .venv-laya/bin/python -m triage_bench.laya_server "$@"
