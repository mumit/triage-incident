#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  printf '%s\n' 'This setup targets Apple Silicon. Follow the upstream Kev guide for other platforms.' >&2
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  printf '%s\n' 'Install uv first; Kev requires Python >=3.12,<3.14.' >&2
  exit 1
fi
export UV_CACHE_DIR="$PWD/.cache/uv"
# Kev currently requires Python >=3.12,<3.14. Select a compatible Python 3
# interpreter rather than depending on whichever version `python3` names today.
kev_python="${KEV_PYTHON:-$(uv python find '>=3.12,<3.14')}"
kev_source_ref="${KEV_SOURCE_REF:-3e1cd3bb588a388a06827443380befece23e68c7}"
uv venv --python "$kev_python" --allow-existing .venv-kev-mac
uv pip install --python .venv-kev-mac/bin/python "kev[serve] @ git+https://github.com/jaredpalmer/kev.git@$kev_source_ref"
printf 'Kev software installed from source revision %s. Run scripts/start_kev_mac.sh to download and serve weights.\n' "$kev_source_ref"
