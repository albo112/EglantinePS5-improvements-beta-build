from pathlib import Path
import resource
import subprocess
from tempfile import TemporaryDirectory

source = Path('headless/main.cpp').read_text()
start = source.index('            if (const char* safe_memory = std::getenv("EDEN_PS5_ZELDA_SAFE_MEMORY");')
opening = source.index('{', start)
end, depth = opening + 1, 1
while depth:
    depth += (source[end] == '{') - (source[end] == '}')
    end += 1
body = source[start:end]
prefix = r'''#include <cassert>
#include <cstdint>
#include <cstdlib>
namespace Settings {
enum class CpuAccuracy { Auto, Unsafe };
enum class DmaAccuracy { Default, Unsafe };
template <typename T> struct Field { T value; void SetValue(T v) { value = v; } };
struct Values { CpuAccuracy cpu_accuracy; Field<DmaAccuracy> dma_accuracy; Field<bool> skip_cpu_inner_invalidation; } values;
}
unsigned reports;
namespace Eden { void Report(const char*, const char*) { ++reports; } }
void Apply(uint64_t game_title) {
'''
suffix = r'''
}
void Case(uint64_t title, const char* setting, bool expected_override) {
    if (setting) setenv("EDEN_PS5_ZELDA_SAFE_MEMORY", setting, 1);
    else unsetenv("EDEN_PS5_ZELDA_SAFE_MEMORY");
    Settings::values = {Settings::CpuAccuracy::Unsafe, {Settings::DmaAccuracy::Unsafe}, {true}};
    reports = 0;
    Apply(title);
    assert(Settings::values.cpu_accuracy == (expected_override ? Settings::CpuAccuracy::Auto : Settings::CpuAccuracy::Unsafe));
    assert(Settings::values.dma_accuracy.value == (expected_override ? Settings::DmaAccuracy::Default : Settings::DmaAccuracy::Unsafe));
    assert(Settings::values.skip_cpu_inner_invalidation.value == !expected_override);
    assert(reports == unsigned(expected_override));
}
int main() {
    Case(0x0400486024DEC000ULL, "1", true);
    Case(0x0400486024DEC000ULL, "0", false);
    Case(0x0400486024DEC000ULL, nullptr, false);
    Case(0x0400486024DEC000ULL, "", false);
    Case(0x0400C3F00006E000ULL, "1", false);
    Case(0, "1", false);
}
'''
with TemporaryDirectory() as directory:
    work = Path(directory)
    def build(name, code):
        path = work / (name + '.cpp')
        path.write_text(code)
        subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                        str(path), '-o', str(work / name)], check=True)
        return work / name
    # A no-op stands for the original path, which always kept the saved unsafe settings.
    before = build('before', prefix + '    (void)game_title;\n' + suffix)
    def no_core():
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    result = subprocess.run([str(before)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=no_core)
    assert result.returncode != 0
    after = build('after', prefix + body + suffix)
    subprocess.run([str(after)], check=True)
print('PASS: old unsafe-setting path rejected; 6 title-scoped accuracy cases passed')
