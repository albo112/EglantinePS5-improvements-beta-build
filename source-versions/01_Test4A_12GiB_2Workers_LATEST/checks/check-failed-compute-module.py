from pathlib import Path
import subprocess
import resource
from tempfile import TemporaryDirectory

source = Path('Eglantine/src/video_core/renderer_vulkan/vk_compute_pipeline.cpp').read_text()
start = source.index('        try {\n            pipeline = device.GetLogical().CreateComputePipeline(')
end = source.index('        // Log compute pipeline creation', start)
body = source[start:end]
code = r'''#include <cassert>
#include <cstdint>
#include <memory>
#include <mutex>
#include <stdexcept>
namespace vk { using Exception = std::runtime_error; }
static unsigned destroyed, logged, notified;
struct Module { ~Module() { ++destroyed; } };
static void LogFailure() { assert(destroyed == 1); ++logged; }
#define LOG_CRITICAL(...) LogFailure()
struct Notify { void MarkShaderComplete() { assert(destroyed == 1); ++notified; } };
struct Condvar { void notify_one() { assert(destroyed == 1); } };
struct Device {
    bool fail;
    Device& GetLogical() { return *this; }
    int CreateComputePipeline(int, int) {
        if (fail) throw vk::Exception("allocation failure");
        return 1;
    }
};
void Build(bool fail) {
    Device device{fail};
    int pipeline = 0, compute_ci = 0;
    auto pipeline_cache = std::make_unique<int>();
    auto spv_module = std::make_unique<Module>();
    std::mutex build_mutex;
    bool is_built = false;
    Condvar build_condvar;
    Notify notify;
    auto* shader_notify = &notify;
    auto worker = [&] {
''' + body + r'''
        assert(pipeline == 1 && !is_built && destroyed == 0);
        spv_module.reset();
        is_built = true;
    };
    worker();
    assert(is_built && !spv_module && destroyed == 1);
    assert(fail ? (logged == 1 && notified == 1 && pipeline == 0)
                : (logged == 0 && notified == 0 && pipeline == 1));
}
int main() {
    Build(true);
    destroyed = logged = notified = 0;
    Build(false);
}
'''
with TemporaryDirectory() as directory:
    work = Path(directory)
    # The test must catch the old failure path that kept the module alive while logging.
    old = code.replace('            spv_module.reset();\n', '', 1)
    assert old != code
    (work / 'before.cpp').write_text(old)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    str(work / 'before.cpp'), '-o', str(work / 'before')], check=True)
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    before = subprocess.run([str(work / 'before')], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, preexec_fn=no_core)
    assert before.returncode != 0, 'regression did not detect retained failed module'
    (work / 'check.cpp').write_text(code)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    str(work / 'check.cpp'), '-o', str(work / 'check')], check=True)
    subprocess.run([str(work / 'check')], check=True)
print('Failed compute module PASS: old path rejected; module freed before low-memory log and completion, success preserved')
