#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
py="$PWD/.venv-kev-mac/bin/python"
if [[ ! -x "$py" ]]; then
  printf '%s\n' 'Run scripts/setup_kev_mac.sh first.' >&2
  exit 1
fi
if ! "$py" -c 'import socket; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1); s.bind(("127.0.0.1",8009)); s.close()' 2>/dev/null; then
  printf '%s\n' 'Port 8009 is already in use. Stop the existing Kev server before starting another.' >&2
  exit 1
fi
export HF_HOME="$PWD/.cache/huggingface"
export XDG_CACHE_HOME="$PWD/.cache"
kev_run="${KEV_RUN:-jaredpalmer/kev-4b@139fdd94f1b6a6ad80cc15e08fcb99cac885a101}"
printf 'Starting Kev from %s. First start downloads the adapter and its base model.\n' "$kev_run"
exec "$py" -m kev.serve --run "$kev_run" --host 127.0.0.1 --port 8009
