#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_PATH="$ROOT_DIR/scripts/vm_io_diagnose.py"

if [[ ! -f "$SCRIPT_PATH" ]]; then
  echo "Error: script not found at $SCRIPT_PATH" >&2
  exit 1
fi

python3 "$SCRIPT_PATH" "$@"
