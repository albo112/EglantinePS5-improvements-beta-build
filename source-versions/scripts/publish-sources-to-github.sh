#!/usr/bin/env bash
set -euo pipefail
# Publish the complete versioned source tree without overwriting unrelated files.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE="${1:-https://github.com/albo112/EglantinePS5-Fork-improvements.-.git}"
TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
git clone "$REMOTE" "$TEMP/repository"
mkdir -p "$TEMP/repository/source-versions"
for item in \
    01_Test4A_12GiB_2Workers_LATEST \
    02_Test4A_Graphics_Crash_Fixes \
    03_Test3_Graphics_Crash_Fixes \
    04_Test2_Memory_Fix \
    05_T34_RADV_Compiled_Release_Only \
    provenance \
    scripts; do
    cp -a "$ROOT/$item" "$TEMP/repository/source-versions/"
done
cp "$ROOT/README.md" "$TEMP/repository/source-versions/README.md"
git -C "$TEMP/repository" add source-versions
if git -C "$TEMP/repository" diff --cached --quiet; then
    echo "All source files already match the repository."
    exit 0
fi
git -C "$TEMP/repository" commit -m "Import EglantinePS5 source history newest to oldest"
git -C "$TEMP/repository" push origin HEAD:main
echo "Successfully published the versioned source files."
