from pathlib import Path
import hashlib
import json
import shutil
import subprocess

scratch = Path(__file__).parent
old = Path('/var/lib/eglantine-build/zelda-test3/Eglantine-PS5')
root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
sources = scratch / 'inputs/test3-sources'
pins = json.loads((sources / 'SOURCE.json').read_text())
assert not root.exists(), 'Do not overwrite an existing reconstruction'
root.parent.mkdir(exist_ok=True)
log = (scratch / 'reconstruction.log').open('w')

def run(command, cwd=None):
    subprocess.run(command, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)

run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(old), str(root)])
run(['git', 'checkout', '-b', 'codex/zelda-test4-a', pins['frontend_commit']], root)
run(['git', 'remote', 'set-url', 'origin', pins['frontend_repository']], root)
run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(old / 'Eglantine'), str(root / 'Eglantine')])
run(['git', 'checkout', '-b', 'codex/zelda-test4-a-core', pins['core_commit']], root / 'Eglantine')
run(['git', 'remote', 'set-url', 'origin', 'https://github.com/Djihads80/Eglantine'], root / 'Eglantine')

def nested(repo, prior):
    entries = subprocess.check_output(['git', '-C', str(repo), 'ls-files', '--stage', '-z']).split(b'\0')
    for entry in entries:
        if not entry.startswith(b'160000 '):
            continue
        fields, raw = entry.split(b'\t', 1)
        name = raw.decode()
        commit = fields.split()[1].decode()
        path, seed = repo / name, prior / name
        assert (seed / '.git').exists(), str(seed)
        run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(seed), str(path)])
        run(['git', 'checkout', '--detach', commit], path)
        nested(path, seed)

nested(root / 'Eglantine', old / 'Eglantine')
run(['git', 'apply', '--check', str(sources / 'local-frontend-and-check.patch')], root)
run(['git', 'apply', str(sources / 'local-frontend-and-check.patch')], root)
for name in pins['extra_core_overlays']:
    src = sources / 'tools/eglantine-patches' / name
    dst = root / 'tools/eglantine-patches' / name
    assert not dst.exists()
    shutil.copyfile(src, dst)
patches = sorted((root / 'tools/eglantine-patches').glob('*.patch'))
assert len(patches) == pins['base_core_overlays'] + len(pins['extra_core_overlays']) == 261
run(['bash', 'tools/apply-eglantine-patches.sh'], root)
run(['git', 'diff', '--check'], root)
run(['git', '-C', 'Eglantine', 'diff', '--check'], root)
baseline = json.loads(Path('/var/lib/eglantine-build/zelda-test4-baseline/test3-source-manifest.json').read_text())
missing, changed = [], []
for name, expected in baseline['files'].items():
    path = root / name
    if not path.is_file():
        missing.append(name)
    elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        changed.append(name)
result = {'status': 'pass' if not missing and not changed else 'fail',
          'exit_code': 0 if not missing and not changed else 1, 'source': str(root),
          'branch': 'codex/zelda-test4-a', 'frontend': pins['frontend_commit'], 'core': pins['core_commit'],
          'applied_core_overlays': len(patches), 'compared_test3_source_files': len(baseline['files']),
          'missing': missing, 'changed': changed, 'original_test3_package_sha256':
          '55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7'}
(scratch / 'reconstruction.json').write_text(json.dumps(result, indent=2) + '\n')
log.close()
print(json.dumps(result))
raise SystemExit(result['exit_code'])
