#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
py="$PWD/.venv-clm-mac/bin/python"
if [[ ! -x "$py" ]]; then printf '%s\n' 'Run scripts/setup_clm_mac.sh first.' >&2; exit 1; fi
export HF_HOME="$PWD/.cache/huggingface"
export XDG_CACHE_HOME="$PWD/.cache"
export CLM_DEVICE=cpu
export CLM_ACTION_CACHE=64MB
precision="${CLM_PRECISION:-bf16}"
case "$precision" in
  bf16) encoder='czl/CLM-v0.1-8B-MLX' ;;
  8bit) encoder='czl/CLM-v0.1-8B-MLX-8bit' ;;
  *) printf '%s\n' 'Use CLM_PRECISION=bf16 or 8bit.' >&2; exit 1 ;;
esac
if ! "$py" -c 'import socket; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("127.0.0.1", 8092)); s.close()' 2>/dev/null; then
  printf '%s\n' 'Port 8092 is already in use. Stop the existing encoder before starting CLM.' >&2
  exit 1
fi
instance_id=$("$py" -c 'import uuid; print(uuid.uuid4().hex)')
mkdir -p runs/clm-mac
"$py" -m triage_bench.mlx_embeddings --model "$encoder" --max-tokens 8192 --port 8092 --instance-id "$instance_id" \
  > runs/clm-mac/encoder.log 2>&1 &
encoder_pid=$!
api_pid=''
cleanup() {
  kill "$encoder_pid" 2>/dev/null || true
  if [[ -n "$api_pid" ]]; then kill "$api_pid" 2>/dev/null || true; fi
}
trap cleanup EXIT
trap 'exit 130' INT TERM
printf '%s\n' 'Starting MLX encoder. First start downloads weights; see runs/clm-mac/encoder.log.'
ready=0
for ((i=0;i<900;i++)); do
  if ! kill -0 "$encoder_pid" 2>/dev/null; then
    printf '%s\n' 'Encoder failed; inspect runs/clm-mac/encoder.log.' >&2; exit 1
  fi
  if "$py" -c 'import json,sys,urllib.request; info=json.load(urllib.request.urlopen("http://127.0.0.1:8092/health",timeout=2)); assert info.get("instance_id")==sys.argv[1] and info.get("model")==sys.argv[2]' "$instance_id" "$encoder" >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
if [[ "$ready" != 1 ]]; then printf '%s\n' 'Encoder startup timed out after 30 minutes.' >&2; exit 1; fi
head_path=$("$py" -c 'from huggingface_hub import hf_hub_download; print(hf_hub_download("Contrastive-LM/CLM-v0.1-8B", "CLM_v0.1-8B.pt"))')
"$py" -c 'import json,urllib.request,hashlib,sys; from pathlib import Path; info=json.load(urllib.request.urlopen("http://127.0.0.1:8092/health")); info["head_sha256"]=hashlib.sha256(Path(sys.argv[1]).read_bytes()).hexdigest(); print(json.dumps(info,indent=2))' "$head_path" > runs/clm-mac/deployment.json
.venv-clm-mac/bin/clm-serve --host 127.0.0.1 --port 8700 --device cpu \
  --emb-url http://127.0.0.1:8092/v1/embeddings --emb-model qwen3-8b --max-tokens 8192 \
  --ckpt "$head_path" --model "clm-mlx-$precision=$head_path" --no-ui &
api_pid=$!
printf 'CLM alias: clm-mlx-%s. Set this model identifier in the app.\n' "$precision"
wait "$api_pid"
