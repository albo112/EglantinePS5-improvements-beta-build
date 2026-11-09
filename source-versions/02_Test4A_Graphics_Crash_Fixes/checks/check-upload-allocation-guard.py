from pathlib import Path
import json
import re
import subprocess
from tempfile import TemporaryDirectory

root = Path.cwd()
scratch = Path(__file__).parent
prelude = (scratch / 'upload-mock-prelude.txt').read_text()
prelude = re.sub(r'void Log\([^\n]+\n#define LOG_ERROR[^\n]+', '#define LOG_ERROR(...) ((void)0)', prelude)
prelude = '#include <cstdlib>\n' + prelude
def clean(text):
    return re.sub(r'^#(?:include|pragma).*\n', '', text, flags=re.M)
header = (root / 'Eglantine/src/video_core/engines/engine_upload.h').read_text()
actual = (root / 'Eglantine/src/video_core/engines/engine_upload.cpp').read_text()
baseline = (scratch / 'before-crash-guards/src/video_core/engines/engine_upload.cpp').read_text()
tests = r'''
using namespace Tegra::Engines::Upload;
struct Fixture {
    Tegra::MemoryManager memory; Registers regs{}; VideoCore::RasterizerInterface raster; State state{memory, regs};
    Fixture() { state.BindRasterizer(&raster); regs.dest.address_low=0x1000; regs.dest.width=4; regs.dest.height=1; regs.dest.depth=1; }
    void Start(u32 bytes, u32 lines=1, bool linear=true) { regs.line_length_in=bytes; regs.line_count=lines; regs.dest.pitch=bytes; state.ProcessExec(linear); }
};
int main(int argc, char** argv) {
    const bool uncapped = argc > 1 && std::string(argv[1]) == "uncapped";
    setenv("EDEN_NX2_UPLOAD_CAP_MIB", uncapped ? "0" : "256", 1);
#ifndef PATCHED
    Fixture f; fail_input=true;
    try { f.Start(64); }
    catch (const std::bad_alloc&) { std::cout << "baseline input allocation exception reproduced\n"; return 0; }
    return 1;
#else
    unsigned cases=0;
    if (uncapped) {
        Fixture f; const auto before=input_requests;
        f.Start(0x80000000U, 2); assert(f.state.GetUploadSize()==0 && input_requests==before); ++cases;
        f.Start(0xffffffffU, 2); assert(f.state.GetUploadSize()==0 && input_requests==before); ++cases;
    } else {
        for (u32 bytes : {1848251136U, 2113929216U, 2588623024U}) {
            Fixture f; const auto before=input_requests; f.Start(bytes);
            u32 word=1; f.state.ProcessData(word, true); f.state.ProcessData(&word, 1);
            assert(f.state.GetUploadSize()==0 && input_requests==before && f.raster.calls.empty()); ++cases;
        }
        Fixture f; fail_input=true; f.Start(64); fail_input=false;
        u32 word=0x12345678; f.state.ProcessData(word, true); f.state.ProcessData(&word, 1);
        assert(f.state.GetUploadSize()==0 && f.raster.calls.empty()); ++cases;
        f.Start(4); f.state.ProcessData(&word, 1);
        assert(f.state.GetUploadSize()==4 && f.raster.calls.size()==1 && f.raster.calls[0].bytes[0]==0x78); ++cases;
        Fixture empty; empty.Start(0); empty.state.ProcessData(word, true); empty.state.ProcessData(&word, 1);
        assert(empty.raster.calls.empty()); ++cases;
        Fixture complete; u32 data[3]={1,2,3}; complete.Start(sizeof(data)); complete.state.ProcessData(data, 3);
        assert(complete.raster.calls.size()==1 && complete.raster.calls[0].input==reinterpret_cast<u8*>(data)); ++cases;
        Fixture tiled; tiled.Start(4, 1, false); fail_tiled=true; bool propagated=false;
        try { tiled.state.ProcessData(&word, 1); } catch (const std::bad_alloc&) { propagated=true; }
        fail_tiled=false; assert(propagated); ++cases;
    }
    std::cout << "{\"cases\":" << cases << ",\"status\":\"pass\"}\n";
#endif
}
'''
results = []
with TemporaryDirectory(prefix='zelda-upload-guard-') as directory:
    work = Path(directory)
    for name, source in (('baseline', baseline), ('patched', actual)):
        cpp = work / (name + '.cpp')
        cpp.write_text(prelude + clean(header) + clean(source) + tests)
        command = ['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror', '-O1', '-g',
                   '-fsanitize=address,undefined', '-fno-omit-frame-pointer', str(cpp), '-o', str(work / name)]
        if name == 'patched': command.insert(1, '-DPATCHED')
        subprocess.run(command, check=True)
        for arguments in ([[]] if name == 'baseline' else [[], ['uncapped']]):
            result = subprocess.run([str(work / name), *arguments], text=True, capture_output=True, check=True)
            results.append({'variant': name, 'arguments': arguments, 'exit_code': result.returncode,
                            'output': result.stdout.strip(), 'stderr': result.stderr})
print(json.dumps({'status': 'pass', 'exit_code': 0, 'results': results}))
(scratch / 'upload-allocation-guard-results.json').write_text(json.dumps(results, indent=2) + '\n')
