"""Install focused host-only NIR tests in an expendable Mesa source copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--mesa-source', type=Path, required=True)
parser.add_argument('--build-dir', type=Path, required=True)
parser.add_argument('--configure', action='store_true')
parser.add_argument('--build', action='store_true')
args = parser.parse_args()
source = args.mesa_source.resolve()
build = args.build_dir.resolve()
bundle = Path(__file__).resolve().parent
nir = source / 'src/compiler/nir'
meson_file = nir / 'meson.build'
if not meson_file.is_file():
    parser.error('--mesa-source must contain src/compiler/nir/meson.build')
baseline = bundle / 'test4a_nir_copy_prop_baseline.c'
expected = '35cbb1a29df5676ddc5a7c6ea54896d393f22d2148fd2d147c33c8f0273730d8'
if hashlib.sha256(baseline.read_bytes()).hexdigest() != expected:
    parser.error('bundled Test3 baseline pass does not match the recorded SHA-256')
for original, destination in [(bundle / 'nir-oom-test.c', nir / 'tests/test4a_nir_oom.c'),
                              (baseline, nir / 'tests/test4a_nir_copy_prop_baseline.c')]:
    if not destination.exists() or original.read_bytes() != destination.read_bytes():
        shutil.copyfile(original, destination)
text = meson_file.read_text()
original_text = text
for name, files in [
    ('test4a_nir_oom', "'tests/test4a_nir_oom.c'"),
    ('test4a_nir_oom_baseline', "'tests/test4a_nir_oom.c', 'tests/test4a_nir_copy_prop_baseline.c'"),
]:
    target = f"executable('{name}', files({files}),\n" + """  include_directories : [inc_include, inc_src],
  dependencies : [dep_thread, idep_nir, idep_mesautil],
  link_args : ['-Wl,--wrap=ralloc_context', '-Wl,--wrap=linear_context', '-Wl,--wrap=reralloc_size'])
"""
    if f"executable('{name}'," not in text:
        text += '\n' + target
    elif text.count(target) != 1:
        parser.error(f'existing {name} target differs; use a clean host source copy')
if text != original_text:
    meson_file.write_text(text)
configure = ['meson', 'setup']
if (build / 'build.ninja').exists():
    configure.append('--reconfigure')
configure += [str(build), str(source), '-Dplatforms=[]', '-Dgallium-drivers=softpipe',
              '-Dvulkan-drivers=[]', '-Dopengl=true', '-Dgles1=disabled',
              '-Dgles2=disabled', '-Degl=disabled', '-Dgbm=disabled', '-Dglx=disabled',
              '-Dglvnd=disabled', '-Dllvm=disabled', '-Dlibunwind=disabled',
              '-Dbuild-tests=false', '-Dbuildtype=debugoptimized', '-Db_ndebug=false',
              '-Db_sanitize=address,undefined', '-Dtools=nir']
compile_command = ['ninja', '-C', str(build), 'src/compiler/nir/test4a_nir_oom',
                   'src/compiler/nir/test4a_nir_oom_baseline', '-j1']
if args.configure:
    subprocess.run(configure, check=True)
if args.build:
    subprocess.run(compile_command, check=True)
print(json.dumps({'status': 'pass', 'exit_code': 0, 'mesa_source': str(source),
                  'build_dir': str(build), 'baseline_sha256': expected,
                  'configure_command': configure, 'build_command': compile_command,
                  'scope': 'host-only test targets; do not use this source tree for native packaging'}))
