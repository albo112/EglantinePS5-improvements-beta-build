#!/usr/bin/env bash
# Publish Albo's five original experimental ZIPs without modifying their contents.
# Prerequisites: gh CLI (authenticated as an authorized publisher), Python 3.
# Run: bash scripts/publish-uploaded-releases.sh "/path/to/five/zips"
set -euo pipefail
repo="albo112/EglantinePS5-Fork-improvements.-"
command -v gh >/dev/null
command -v python3 >/dev/null
gh auth status >/dev/null
gh repo view "$repo" >/dev/null
if [ "$#" -gt 0 ]; then cd "$1"; fi

while IFS='|' read -r tag title filename expected description; do
  [ -n "$tag" ] || continue
  if [ ! -f "$filename" ]; then echo "Missing ZIP: $filename" >&2; continue; fi
  python3 - "$filename" "$expected" <<'PY'
import hashlib,sys,zipfile
path,expected = sys.argv[1:]
with open(path,'rb') as f: actual=hashlib.file_digest(f,'sha256').hexdigest()
if actual != expected: sys.exit("Incorrect SHA-256 for " + path + ": " + actual)
with zipfile.ZipFile(path) as z:
    if z.testzip() is not None: sys.exit("Corrupt ZIP: " + path)
    if "PPSA98515/eboot.bin" not in z.namelist(): sys.exit("Missing PS5 executable in " + path)
    if z.getinfo("PPSA98515/eboot.bin").file_size == 0: sys.exit("Empty PS5 executable")
print("Verified:", path, actual)
PY
  if gh release view "$tag" --repo "$repo" >/dev/null 2>&1; then
    echo "Release already exists; skipping to avoid overwriting: $tag"
    continue
  fi
  notes="$(mktemp)"
  {
    printf '%s\n\n' "## $title" "$description"
    printf '%s\n' 'Experimental, user-supplied PS5 build; ZIP and executable presence verified, but not independently tested for stable gameplay.'
    printf '%s\n' "Original ZIP: $filename" "SHA-256: $expected"
    printf '%s\n' 'Maintainer: Albo (@albo112).'
    printf '%s\n' 'Upstream credit: viejunerd, Djihads80, Vampinity, heydemoura and earlier Eglantine/Eden/PS5 frontend contributors.'
    printf '%s\n' 'AI assistance: OpenAI ChatGPT and Codex.'
    printf '%s\n' "Corresponding source patches: https://github.com/$repo/tree/main/source-versions"
    printf '%s\n' "Attribution and license: https://github.com/$repo/blob/main/CREDITS.md and LICENSE"
    printf '%s\n' 'No games, firmware or keys included.'
  } > "$notes"
  gh release create "$tag" "$filename" --repo "$repo" --target main \
    --title "$title (experimental)" --prerelease --notes-file "$notes"
  rm -f "$notes"
  echo "Published: $tag"
done <<'BUILDS'
zelda-test4a-12gib-2workers|Test4-A 12 GiB / 2 workers|EglantinePS5-Zelda-Test4-A-12GB Latest Build(1).zip|a0410ea88a56e2520b59f5a58138bfeb305b26bbb1d1412b465b93e8c5972f97|Latest Test4-A profile: 12 GiB guest-memory layout and two pipeline workers.
zelda-test4a-original|Test4-A original graphics and crash fixes|EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes(3).zip|3cd62c1beeebeed14351c55fe81bb82597ed5c7b98ba37103954c55a31c4592b|Original Test4-A profile with four pipeline workers.
zelda-test3-graphics-crash-fixes|Test3 graphics and crash fixes|EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes(2).zip|55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7|Earlier Test3 build for graphics/crash testing.
zelda-test2-memory-fix|Test2 memory fix|EglantinePS5-Zelda-Memory-Fix-Test2(2).zip|1d18cae9fc27a8948b128c72c44e45b9a2b535d1043ca4bce491dbe3eb64d46f|Earlier memory-fix test package.
zelda-t34-radv-fix|T34 RADV fix|EglantinePS5-Zelda-T34-RADV-fix(2).zip|f8354bb8a1b722c8a3755679ee2deab89b7377cb43c383e17a85b25e4e84d26e|Earlier experimental RADV driver fix.
BUILDS
