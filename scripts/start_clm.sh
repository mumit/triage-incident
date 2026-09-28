#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv-clm/bin/vllm ]]; then
  printf '%s\n' 'Run scripts/setup_clm.sh on the GPU host first.' >&2
  exit 1
fi
export HF_HOME="$PWD/.cache/huggingface"
export XDG_CACHE_HOME="$PWD/.cache"
mkdir -p runs/clm-server
.venv-clm/bin/vllm serve Qwen/Qwen3-8B \
  --host 127.0.0.1 --served-model-name qwen3-8b --runner pooling \
  --max-model-len 8192 --gpu-memory-utilization 0.85 --port 8090 \
  > runs/clm-server/encoder.log 2>&1 &
encoder_pid=$!
api_pid=''
cleanup() {
  kill "$encoder_pid" 2>/dev/null || true
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM
printf '%s\n' 'Starting embedding server. Progress: runs/clm-server/encoder.log'
ready=0
for ((i=0;i<600;i++)); do
  if ! kill -0 "$encoder_pid" 2>/dev/null; then
    printf '%s\n' 'Embedding server failed. Inspect runs/clm-server/encoder.log.' >&2
    exit 1
  fi
  if .venv-clm/bin/python -c 'import urllib.request; urllib.request.urlopen("http://127.0.0.1:8090/health",timeout=2)' >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then
  printf '%s\n' 'Embedding server did not become ready within 20 minutes.' >&2
  exit 1
fi
.venv-clm/bin/clm-serve --host 127.0.0.1 --port 8700 \
  --emb-url http://127.0.0.1:8090/v1/embeddings --emb-model qwen3-8b \
  --max-tokens 8192 --no-ui &
api_pid=$!
wait "$api_pid"
