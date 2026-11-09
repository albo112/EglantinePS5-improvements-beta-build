#!/usr/bin/env bash
# Requires Linux/WSL with internet and all PS5, LLVM and driver-toolchain dependencies.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$PWD/EglantinePS5-Test4A-Full-Source}"
if [[ -e "$DEST" ]]; then
    echo "Existing source tree: $DEST; refusing to overlay it. Choose a clean destination." >&2
    exit 2
fi
bash "$ROOT/scripts/reconstruct-latest.sh" "$DEST"
cd "$DEST"
# Reproduce the native build invocation recorded in Test4-A BUILD.txt.
JOBS="${JOBS:-3}" RADV_BUILD_JOBS="${RADV_BUILD_JOBS:-2}" bash tools/ci/build-release.sh
