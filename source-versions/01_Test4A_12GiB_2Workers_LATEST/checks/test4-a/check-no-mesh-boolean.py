"""Exercise exact renderer, pipeline, and generated-driver no-mesh predicates."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import os
import subprocess
from tempfile import TemporaryDirectory

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=Path.cwd())
parser.add_argument('--result', type=Path, default=Path(__file__).with_name('no-mesh-boolean-result.json'))
args = parser.parse_args()
root = args.source.resolve()
paths = ['Eglantine/src/video_core/renderer_vulkan/vk_rasterizer.cpp',
         'Eglantine/src/video_core/renderer_vulkan/vk_pipeline_cache.cpp', 'tools/patch-radv-wsi.py']
renderer, cache, patcher = [(root / name).read_text() for name in paths]

def block(text, marker):
    begin = text.index(marker)
    opened = text.index('{', begin)
    depth, end = 1, opened + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]

render_start = renderer.index('    static const bool no_mesh_always')
render_end = renderer.index('    // Mario Kart World:', render_start)
render_predicate = renderer[render_start:render_end]
drop_function = block(cache, 'bool DropMeshDrawsBeforeBuild()')
driver = next(node.value for node in ast.walk(ast.parse(patcher))
              if isinstance(node, ast.Constant) and isinstance(node.value, str)
              and 'const bool eden_mesh_buffers' in node.value)
begin = driver.index('   const char *const eden_no_mesh_buffers')
end = driver.index(';', driver.index('const bool eden_mesh_buffers', begin)) + 1
driver_predicate = driver[begin:end]
begin = renderer.index('if (mesh_draw && (no_mesh || no_mesh_title ||') + len('if ')
depth, end = 1, begin + 1
while depth:
    depth += (renderer[end] == '(') - (renderer[end] == ')')
    end += 1
condition = renderer[begin + 1:end - 1]
code = '''#include <cstdlib>
#include <cstdio>
#include <filesystem>
using u32 = unsigned;
''' + drop_function + '''
int main() {
''' + render_predicate + driver_predicate + '''
bool mesh_draw=true, no_mesh_title=false;
struct Device { bool ext=false; bool IsExtMeshShaderSupported() const { return ext; } } device;
struct Pipeline { bool fallback=true; bool RunsMeshAsCompute() const { return fallback; } } p;
const auto* pipeline=&p;
const bool with_fallback = ''' + condition + ''';
p.fallback=false;
const bool without_fallback = ''' + condition + ''';
device.ext=true;
const bool with_mesh_extension = ''' + condition + ''';
no_mesh_title=true;
const bool mkw_still_skipped = ''' + condition + ''';
std::printf("{\\"no_mesh\\":%d,\\"drop_before_build\\":%d,\\"driver_buffers\\":%d,"
            "\\"with_fallback\\":%d,\\"without_fallback\\":%d,\\"with_extension\\":%d,\\"mkw_skipped\\":%d}\\n",
            int(no_mesh),int(DropMeshDrawsBeforeBuild()),int(eden_mesh_buffers),
            int(with_fallback),int(without_fallback),int(with_mesh_extension),int(mkw_still_skipped));
}
'''
result = {'status': 'fail', 'exit_code': 1, 'source_sha256': {
    name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in paths}, 'cases': []}
with TemporaryDirectory(prefix='test4a-no-mesh-') as temporary:
    folder = Path(temporary)
    (folder / 'check.cpp').write_text(code)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    '-fsanitize=address,undefined', '-fno-omit-frame-pointer',
                    str(folder / 'check.cpp'), '-o', str(folder / 'check')], check=True)
    present = folder / 'mesh-disabled.txt'
    present.write_text('test toggle\n')
    missing = folder / 'not-present.txt'
    cases = [(None, None, None, None, False, False, True),
             ('0', '1', '1', None, False, False, True),
             ('1', '1', '1', None, True, True, False),
             ('', '1', '1', None, True, True, False),
             ('0', '0', '1', None, False, False, True),
             ('1', '1', '1', str(missing), False, False, True),
             ('0', '1', '1', str(present), True, False, True),
             (None, '1', '1', str(present), True, False, True)]
    for mesh, build, buffers, toggle, expected_mesh, expected_drop, expected_buffers in cases:
        env = os.environ.copy()
        for key, value in zip(('EDEN_NX2_NO_MESH', 'EDEN_NX2_NO_MESH_BUILD',
                               'EDEN_RADV_NO_MESH_BUFFERS', 'EDEN_NX2_NO_MESH_FILE'),
                              (mesh, build, buffers, toggle)):
            if value is None: env.pop(key, None)
            else: env[key] = value
        checked = subprocess.run([str(folder / 'check')], env=env, text=True, capture_output=True)
        observed = json.loads(checked.stdout) if checked.returncode == 0 else {}
        expected = {'no_mesh': int(expected_mesh), 'drop_before_build': int(expected_drop),
                    'driver_buffers': int(expected_buffers), 'with_fallback': int(expected_mesh),
                    'without_fallback': 1, 'with_extension': int(expected_mesh), 'mkw_skipped': 1}
        result['cases'].append({'no_mesh_value': mesh, 'no_mesh_build': build,
            'no_mesh_buffers': buffers, 'file_toggle': 'present' if toggle == str(present) else 'missing' if toggle else None,
            'expected': expected, 'actual': observed, 'exit_code': checked.returncode,
            'stderr': checked.stderr, 'pass': checked.returncode == 0 and observed == expected})
result['exit_code'] = 0 if all(case['pass'] for case in result['cases']) else 1
result['status'] = 'pass' if result['exit_code'] == 0 else 'fail'
args.result.write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(result['exit_code'])
