#!/usr/bin/env bash
# Package the Skytronsystem source code (excluding secrets and runtime data)
# into a tar.gz archive and generate its SHA-256 hash.
#
# Usage: ./generareCodeahsh.sh [output_dir]   (default: /home/azureuser)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="${1:-/home/azureuser}"
TS="$(date +%Y%m%d_%H%M)"
ARCHIVE="$OUT_DIR/Skytronsystem_code_$TS.tar.gz"

cd "$SCRIPT_DIR"

# Step 1: Create the archive
tar --sort=name \
  --exclude='Skytronsystem/keys' \
  --exclude='Skytronsystem/mqttKeys' \
  --exclude='Skytronsystem/fileuploads' \
  --exclude='Skytronsystem/gps_data_archives' \
  --exclude='Skytronsystem/logs' \
  -czf "$ARCHIVE" Skytronsystem

# Step 2: Generate the SHA-256 hash
(cd "$OUT_DIR" && sha256sum "$(basename "$ARCHIVE")" > "$(basename "$ARCHIVE").sha256")

echo "Archive : $ARCHIVE"
echo "SHA-256 : $(cut -d' ' -f1 "$ARCHIVE.sha256")"
echo "Verify  : cd $OUT_DIR && sha256sum -c $(basename "$ARCHIVE").sha256"
