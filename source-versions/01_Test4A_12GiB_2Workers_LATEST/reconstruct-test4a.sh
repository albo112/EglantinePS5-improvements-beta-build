#!/usr/bin/env bash
# Reconstruct the pinned Test4-A source on Linux/WSL with Git and network access.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${1:-$PWD/EglantinePS5-Test4A-Full-Source}"
if [ -e "$DEST" ]; then echo "Refusing to overwrite existing: $DEST" >&2; exit 2; fi
command -v git >/dev/null
command -v python3 >/dev/null
mkdir -p "$(dirname "$DEST")"
git clone https://github.com/Vampinity/Eglantine-PS5-.git "$DEST"
git -C "$DEST" checkout --detach 25cfc07be0a3675749adece5d012fdb916c4cd48
git -C "$DEST" submodule update --init --recursive
# Ensure the core is exactly the pinned Test4-A base, not the parent checkout's tip.
if [ ! -d "$DEST/Eglantine/.git" ] && [ ! -f "$DEST/Eglantine/.git" ]; then
  echo 'Missing expected Eglantine git submodule. Verify frontend checkout.' >&2; exit 3
fi
git -C "$DEST/Eglantine" remote add source-pin https://github.com/Djihads80/Eglantine.git 2>/dev/null || true
git -C "$DEST/Eglantine" fetch source-pin 0ca2032bffc5f1a3fca75427f7d4a4718adda660
git -C "$DEST/Eglantine" checkout --detach 0ca2032bffc5f1a3fca75427f7d4a4718adda660
git -C "$DEST/Eglantine" submodule update --init --recursive
# Apply frontend source changes before modifying the source-overlay tools.
git -C "$DEST" apply --check "$HERE/frontend-pinned-to-test4a.patch"
git -C "$DEST" apply "$HERE/frontend-pinned-to-test4a.patch"
# Overlay the supplied source-only modifications (not build products or evidence).
for sub in tools checks Documentation audit profiles; do
  if [ -d "$HERE/$sub" ]; then cp -a "$HERE/$sub/." "$DEST/$sub/"; fi
done
# Some supplied tools may be new; existing upstream tools retain all other files.
# The frontend checkout contains the overlay runner; it applies ordered core patches.
if [ ! -f "$DEST/tools/apply-eglantine-patches.sh" ]; then
  echo 'Missing frontend overlay runner: tools/apply-eglantine-patches.sh' >&2; exit 4
fi
(cd "$DEST" && bash tools/apply-eglantine-patches.sh)
(cd "$DEST" && git diff --check && git -C Eglantine diff --check)
echo "Reconstructed Test4-A frontend + pinned core source at: $DEST"
echo "Review BUILD.txt and Documentation/Test4-A-Source-and-Build.md before compiling."
echo "Do not apply the 264 core patches a second time."
