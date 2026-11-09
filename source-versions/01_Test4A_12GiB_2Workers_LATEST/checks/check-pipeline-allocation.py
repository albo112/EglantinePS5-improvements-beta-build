import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


source = Path('Eglantine/src/video_core/vulkan_common/vulkan_wrapper.cpp').read_text()
start = source.index('template <typename Func>\nvoid DriverPipelineBuild(')
opening = source.index('{', start)
depth = 1
end = opening + 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
helper = source[start:end]
code = '''#include <cassert>
#include <cstdlib>
#include <new>
#include <stdexcept>
#define LOG_CRITICAL(...) ((void)0)
constexpr int VK_ERROR_OUT_OF_HOST_MEMORY = -1;
struct Exception { int result; explicit Exception(int value) : result(value) {} };
''' + helper + '''
int main(int argc, char** argv) {
    assert(argc == 2);
    setenv("EDEN_NX2_PIPELINE_FAIL_SOFT", argv[1], 1);
    unsigned calls = 0;
    DriverPipelineBuild([&] { ++calls; });
    assert(calls == 1);
    bool caught = false;
    try {
        DriverPipelineBuild([] { throw std::bad_alloc{}; });
    } catch (const Exception& error) {
        assert(argv[1][0] == '1' && error.result == VK_ERROR_OUT_OF_HOST_MEMORY);
        caught = true;
    } catch (const std::bad_alloc&) {
        assert(argv[1][0] == '0');
        caught = true;
    }
    assert(caught);
    caught = false;
    try {
        DriverPipelineBuild([] { throw Exception(-7); });
    } catch (const Exception& error) {
        assert(error.result == -7);
        caught = true;
    }
    assert(caught);
    caught = false;
    try {
        DriverPipelineBuild([] { throw std::runtime_error("other"); });
    } catch (const std::runtime_error&) {
        caught = true;
    }
    assert(caught);
}
'''
with TemporaryDirectory() as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(code)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    str(work / 'check.cpp'), '-o', str(work / 'check')], check=True)
    for enabled in ('0', '1'):
        subprocess.run([str(work / 'check'), enabled], check=True)
print('Pipeline allocation guard PASS: success, enabled/disabled allocation failure, Vulkan errors and unrelated exceptions')
