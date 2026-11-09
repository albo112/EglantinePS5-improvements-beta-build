import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


root = Path.cwd()
source = (root / 'headless/vulkan_surface.cpp').read_text()
start = source.index('    const bool fast = Eden::Display::requested_hz.load() >= 120;')
end = source.index('    std::fprintf(stderr, "[EglantinePS5] Vulkan display: framebuffers', start)
selection = source[start:end]
code = '''#include <cassert>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "display_refresh.h"
struct Mode {
    struct Parameters {
        struct Extent { unsigned width, height; } visibleRegion;
        unsigned refreshRate;
    } parameters;
};
Mode Select(std::vector<Mode> modes, int hz, int width, int height, bool full = false) {
    Eden::Display::requested_hz = hz;
    Eden::Display::output_width = width;
    Eden::Display::output_height = height;
    if (full) setenv("EDEN_VULKAN_FULL_FRAMEBUFFERS", "1", 1);
    else unsetenv("EDEN_VULKAN_FULL_FRAMEBUFFERS");
''' + selection + '''
    return mode;
}
void Require(Mode actual, unsigned width, unsigned height, unsigned rate, const char* test) {
    if (actual.parameters.visibleRegion.width != width ||
        actual.parameters.visibleRegion.height != height || actual.parameters.refreshRate != rate) {
        std::fprintf(stderr, "%s: got %ux%u at %u, expected %ux%u at %u\\n", test,
            actual.parameters.visibleRegion.width, actual.parameters.visibleRegion.height,
            actual.parameters.refreshRate, width, height, rate);
        std::exit(1);
    }
}
int main() {
    const std::vector<Mode> slow{{{ {3840,2160},59940}},{{{2560,1440},59940}},{{{1920,1080},59940}}};
    const std::vector<Mode> both{{{{3840,2160},119880}},{{{2560,1440},119880}},
        {{{1920,1080},119880}},{{{3840,2160},59940}},{{{1920,1080},59940}}};
    Require(Select(slow, 60, 1920, 1080), 1920, 1080, 59940, "normal 1080p");
    Require(Select(slow, 120, 1920, 1080), 1920, 1080, 59940, "unsupported 120Hz");
    Require(Select(slow, 120, 2560, 1440), 2560, 1440, 59940, "unsupported 120Hz at 1440p");
    Require(Select(both, 120, 1920, 1080), 1920, 1080, 119880, "supported 120Hz");
    Require(Select(both, 60, 1920, 1080), 1920, 1080, 59940, "60Hz on a fast display");
    Require(Select(slow, 120, 1920, 1080, true), 3840, 2160, 59940, "explicit full framebuffers");
    Require(Select(both, 120, 1920, 1080, true), 3840, 2160, 119880, "explicit full framebuffers at 120Hz");
    Require(Select(slow, 120, 1280, 720), 3840, 2160, 59940, "unavailable dimensions");
    std::puts("Display mode selection PASS: unsupported and supported refresh, requested dimensions, explicit full size");
}
'''
with TemporaryDirectory() as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(code)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror',
                    '-I', str(root / 'headless'), str(work / 'check.cpp'), '-o', str(work / 'check')], check=True)
    subprocess.run([str(work / 'check')], check=True)
