#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$PWD/EglantinePS5-Test4A-Full-Source}"
exec bash "$ROOT/01_Test4A_12GiB_2Workers_LATEST/reconstruct-test4a.sh" "$DEST"
