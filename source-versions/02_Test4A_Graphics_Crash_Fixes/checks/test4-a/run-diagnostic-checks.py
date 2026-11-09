import json
from pathlib import Path
import re, subprocess, tempfile

root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
out = Path('/mnt/c/Users/Doni/Documents/Codex/2026-11-06/ca/work/test4-a')
source = (root/'Eglantine/src/video_core/renderer_vulkan/vk_rasterizer.cpp').read_text()
m = re.search(r'            static std::atomic<u64> failures\{\};.*?\n            }', source, re.S)
assert m
program = '''#include <atomic>
#include <cstdint>
#include <cassert>
#include <thread>
#include <vector>
using u64 = uint64_t;
static std::atomic<unsigned> lines{};
#define LOG_WARNING(...) (++lines)
void record() {
''' + m.group() + '''
}
int main() {
 std::vector<std::thread> threads;
 for (int t=0;t<8;++t) threads.emplace_back([] {for(int n=0;n<4096;++n) record();});
 for(auto &t:threads)t.join();
 assert(lines==40); // first 8, then each 1024th among 32768 failures
}
'''
with tempfile.TemporaryDirectory() as d:
    p = Path(d)
    (p/'test.cpp').write_text(program)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror', '-pthread',
                    '-fsanitize=address,undefined', str(p/'test.cpp'), '-o', str(p/'test')], check=True)
    subprocess.run([str(p/'test')], check=True)
    paths_program = program.replace('void record()', 'template<int Path> void record()')
    paths_program = paths_program.replace('record();', '{ record<0>(); record<1>(); }')
    paths_program = paths_program.replace('assert(lines==40)', 'assert(lines==80)')
    (p/'paths.cpp').write_text(paths_program)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror', '-pthread',
                    '-fsanitize=address,undefined', str(p/'paths.cpp'), '-o', str(p/'paths')], check=True)
    subprocess.run([str(p/'paths')], check=True)
check = root/'tools/check-crash-report.py'
s = check.read_text()
needle = "    assert ('memory: largest free block 1234 MiB"
start = s.index(needle)
end = s.index('\n', s.index(' in report)', start))
# The existing assertion spans its conditional continuation; add a separate native-only check.
anchor = "    assert ('memory: largest free block 1234 MiB of 12288 MiB, heap 256 MiB and 96 MiB in 3 large blocks\\n' in report)"
assert anchor in s
if 'assert (\'heap allocation failures (global snapshot)' not in s:
    # Keep the original conditional assertion as-is and inject after its full line.
    lines = s.splitlines(True)
    index = next(i for i,line in enumerate(lines) if line.startswith(anchor))
    while lines[index].rstrip().endswith('\\'):
        index += 1
    lines.insert(index + 1, "    assert ('heap allocation failures (global snapshot): count 5, last request bytes 123456, reason 2 ' in report) == console\n")
    check.write_text(''.join(lines))
log = out/'crash-diagnostics-check.log'
with log.open('w') as stream:
    r = subprocess.run(['python3', '-B', str(check)], cwd=root, stdout=stream, stderr=subprocess.STDOUT)
result = {'status': 'pass' if r.returncode == 0 else 'fail', 'exit_code': r.returncode,
          'bounded_draw_log': {'threads': 8, 'failures': 32768, 'lines': 40, 'exit_code': 0},
          'bounded_draw_paths': {'threads': 8, 'paths': 2, 'total_failures': 65536, 'lines': 80, 'exit_code': 0},
          'draw_counter_scope': 'Per PrepareDraw callable instantiation; separate direct/indirect paths',
          'crash_report': {'exit_code': r.returncode, 'log': log.name}}
(out/'diagnostics-checks.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(r.returncode)
