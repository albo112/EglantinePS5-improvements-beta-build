"""Seed an independent pinned build; never share mutable driver work/output trees."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess

scratch = Path(__file__).parent
root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
prior = Path('/var/lib/eglantine-build/zelda-test3/Eglantine-PS5')
pins = json.loads((root / 'tools/deps.json').read_text())['items']
log = (scratch / 'build-inputs.log').open('a')
def run(args, cwd=None):
    subprocess.run(args, cwd=cwd, stdout=log, stderr=subprocess.STDOUT, check=True)
def copy_tree(source, target):
    if target.exists():
        return
    target.mkdir(parents=True)
    run(['cp', '-a', '--reflink=auto', str(source.resolve()) + '/.', str(target)])
def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()

repositories = {}
for name in ('boilerplate', 'ps5-vulkan-tools', 'ps5-mesa', 'ps5-payload-sdk-fork'):
    pin = next(item for item in pins if item['name'] == name)
    folder = Path(pin['path']).name
    assert folder in ('ps5-native-app-boilerplate', 'mihawk-vulkan-review', 'mihawk-mesa-review', 'mihawk-sdk-review')
    source, target = prior.parent / folder, root.parent / folder
    if not target.exists():
        run(['git', 'clone', '--no-hardlinks', '--no-checkout', str(source), str(target)])
        run(['git', 'checkout', '--detach', pin['commit']], target)
        run(['git', 'remote', 'set-url', 'origin', pin['url']], target)
    actual = subprocess.check_output(['git', '-C', str(target), 'rev-parse', 'HEAD'], text=True).strip()
    assert actual == pin['commit'], (folder, actual)
    repositories[folder] = actual

old_cache = Path((prior / '.local/headless-cache').read_text().strip())
cache = Path.home() / '.cache' / ('ps5-eden-headless.' + hashlib.sha256(str(root).encode()).hexdigest()[:12])
cache.mkdir(exist_ok=True)
owner = cache / 'owner'
assert not owner.exists() or owner.read_text().strip() == str(root)
owner.write_text(str(root) + '\n')
(root / '.local').mkdir(exist_ok=True)
(root / '.local/headless-cache').write_text(str(cache) + '\n')
for name in ('sdk', 'cdeps', 'ffmpeg-native'):
    copy_tree(old_cache / name, cache / name)
copy_tree(old_cache / 'source/.cache/cpm', cache / 'source/.cache/cpm')
copy_tree(prior / '.deps', root / '.deps')
boilerplate = root.parent / 'ps5-native-app-boilerplate'
copy_tree(prior.parent / 'ps5-native-app-boilerplate/.deps', boilerplate / '.deps')
runtime = boilerplate / 'runtime/libc.prx'
old_runtime = prior.parent / 'ps5-native-app-boilerplate/runtime/libc.prx'
if not runtime.exists():
    runtime.parent.mkdir(exist_ok=True)
    shutil.copyfile(old_runtime, runtime)
assert digest(runtime) == digest(old_runtime)
driver = root.parent / 'mihawk-vulkan-review'
old_driver = prior.parent / 'mihawk-vulkan-review'
for name in ('ps5-payload-sdk', 'zlib'):
    copy_tree(old_driver / '.deps/native' / name, driver / '.deps/native' / name)
assert not (driver / '.deps/work').exists()
assert not (driver / '.deps/native/radv-release').exists()
(root / 'build/radv-isolated').mkdir(parents=True, exist_ok=True)
assert not (root / 'build/radv-isolated').is_symlink()
checks = {}
for relative in ('ffmpeg-native/install/lib/libavcodec.a', 'cdeps/lib/libcrypto.a', 'sdk/.complete'):
    assert (cache / relative).is_file(), relative
    assert digest(cache / relative) == digest(old_cache / relative), relative
    checks[relative] = digest(cache / relative)
assert 'CONFIG_LIBDAV1D_DECODER 1' in (cache / 'ffmpeg-native/config_components.h').read_text()
result = {'status': 'pass', 'exit_code': 0, 'source': str(root), 'cache': str(cache),
          'pinned_repositories': repositories, 'copied_input_hashes': checks,
          'old_runtime_sha256': digest(old_runtime), 'independent_mutable_driver_tree': True,
          'independent_radv_isolated_directory': True}
(scratch / 'build-inputs.json').write_text(json.dumps(result, indent=2) + '\n')
log.close()
print(json.dumps(result))
