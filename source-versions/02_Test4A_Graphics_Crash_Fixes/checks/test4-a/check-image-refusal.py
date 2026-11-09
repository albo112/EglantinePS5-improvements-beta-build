"""Compile actual constructor/refusal/slot logic with a deterministic allocation-failure device."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
from tempfile import TemporaryDirectory

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, default=Path.cwd())
parser.add_argument('--baseline', action='store_true')
parser.add_argument('--result', type=Path, default=Path(__file__).with_name('image-refusal-result.json'))
args = parser.parse_args()
root = args.source.resolve()
tested = Path(__file__).with_name('image-refusal-baseline') if args.baseline else root
names = ['Eglantine/src/video_core/renderer_vulkan/vk_texture_cache.cpp',
         'Eglantine/src/video_core/texture_cache/texture_cache.h']
image, cache = [(tested / name).read_text() for name in names]
header = (root / 'Eglantine/src/video_core/renderer_vulkan/vk_texture_cache.h').read_text()

def block(text, marker):
    begin = text.index(marker)
    opened = text.index('{', begin)
    depth, end = 1, opened + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[begin:end]

constructor = block(image[image.index('Image::Image(TextureCacheRuntime&'):],
                    'if (original_image.IsUnbacked())')
survives = block(header, '[[nodiscard]] bool SurvivesImageRefusal(Make&& make)')
if 'ImageId TextureCache<P>::TryMakeImage(' in cache:
    make = block(cache, 'ImageId TextureCache<P>::TryMakeImage(')
    make = make.replace('ImageId TextureCache<P>::TryMakeImage(', 'ImageId Cache::TryMakeImage(')
    begin = cache.index('            const ImageId new_shadow_id = TryMakeImage(')
else:
    join = cache[cache.index('ImageId TextureCache<P>::JoinImages('):]
    begin_make = join.index('    ImageId new_image_id{};')
    end_make = join.index('    Image& new_image = slot_images[new_image_id];', begin_make)
    make = ('ImageId Cache::TryMakeImage(const ImageInfo& info, GPUVAddr gpu_addr, DAddr cpu_addr) {\n'
            + join[begin_make:end_make].replace('new_info', 'info')
            + '    return new_image_id;\n}')
    begin = cache.index('            feedback_shadows.push_back(slot_images.insert(')
end = cache.index('            LOG_INFO(HW_GPU, "Colour target', begin)
shadow = cache[begin:end]
refresh_start = cache.index('    image.flags &= ~ImageFlagBits::CpuModified;',
                            cache.index('void TextureCache<P>::RefreshContents('))
refresh_clear = cache[refresh_start:cache.index('\n', refresh_start)]
refresh_unbacked = block(cache[refresh_start:], 'if (True(image.flags & ImageFlagBits::Unbacked))')

prefix = r'''
#include <algorithm>
#include <cassert>
#include <chrono>
#include <cstdint>
#include <cstdio>
#include <limits>
#include <stdexcept>
#include <vector>
#include <utility>
#include "common/slot_vector.h"
using u64 = std::uint64_t;
using GPUVAddr = u64;
using VAddr = u64;
using DAddr = u64;
using ImageId = Common::SlotId;
constexpr int VK_ERROR_OUT_OF_DEVICE_MEMORY = -2;
constexpr int VK_ERROR_OUT_OF_HOST_MEMORY = -1;
namespace vk {
struct Exception { int result; int GetResult() const { return result; } };
}
namespace VideoCommon {
namespace ImageFlagBits {
constexpr unsigned Unbacked = 1, UnwrittenSparse = 2, SparseLayers = 4,
                   SparseTiles = 8, CpuModified = 16, Tracked = 32;
}
struct NullImageParams {};
}
namespace ImageFlagBits = VideoCommon::ImageFlagBits;
struct ImageInfo {
    struct { unsigned width=64, height=64, depth=1; } size;
    struct { int layers=1; } resources;
    bool unwritten=false, layers=false, tiles=false, sparse_init=true;
};
struct Resource {
    static inline int live=0, destroyed=0;
    bool owns=false, unbacked=false;
    Resource() = default;
    explicit Resource(bool empty) : owns(true), unbacked(empty) { ++live; }
    Resource(Resource&& other) noexcept : owns(std::exchange(other.owns, false)), unbacked(other.unbacked) {}
    Resource& operator=(Resource&& other) noexcept {
        Release(); owns=std::exchange(other.owns, false); unbacked=other.unbacked; return *this;
    }
    Resource(const Resource&) = delete;
    void Release() { if (owns) { --live; ++destroyed; owns=false; } }
    ~Resource() { Release(); }
    bool IsUnbacked() const { return owns && unbacked; }
};
#define LOG_ERROR(...) ((void)0)
#define LOG_WARNING(...) ((void)0)
bool UsesSparseLayers(int, const ImageInfo& info, GPUVAddr) { return info.layers; }
bool UsesSparseTiles(int, const ImageInfo& info, GPUVAddr) { return info.tiles; }
bool IsUnwrittenSparse(int, const ImageInfo& info, GPUVAddr) { return info.unwritten; }
ImageInfo TrimmedHostInfo(int, const ImageInfo& info, unsigned) { return info; }
u64 CalculateGuestSizeInBytes(const ImageInfo& info) {
    return u64{info.size.width} * info.size.height * info.size.depth * unsigned(info.resources.layers) * 4;
}
struct Image;
struct Runtime {
    int device=0, creations=0, layouts=0;
    bool recovered=false, ends=false;
    bool ImageRefusalEnds() const { return ends; }
    void TransitionImageLayout(Image&) { ++layouts; }
    template<class Make>
__SURVIVES__
};
Resource MakeHostImage(Runtime& runtime, const ImageInfo&, unsigned&, GPUVAddr, bool) {
    return Resource(!runtime.recovered);
}
struct Image {
    ImageInfo info;
    unsigned host_level_offset=0, flags=ImageFlagBits::CpuModified;
    Resource original_image;
    explicit Image(VideoCommon::NullImageParams) {}
    Image(Runtime& runtime_, const ImageInfo& info_, GPUVAddr gpu_addr_, VAddr)
        : info(info_), original_image((++runtime_.creations, !runtime_.recovered || info.unwritten || info.layers || info.tiles)) {
__CONSTRUCTOR__
    }
    Image(Image&&) noexcept = default;
    Image& operator=(Image&&) noexcept = default;
    bool InitSparseLayers() { return info.sparse_init; }
    bool InitSparseTiles() { return info.sparse_init; }
};
bool True(unsigned value) { return value != 0; }
class Cache {
public:
    Runtime runtime;
    Common::SlotVector<Image> slot_images;
    std::vector<ImageId> feedback_shadows;
    std::chrono::steady_clock::time_point image_refused_until{};
    u64 image_refused_bytes=0;
    bool image_refused=false;
    int uploads=0;
    Cache() { (void)slot_images.insert(VideoCommon::NullImageParams{}); }
    ImageId TryMakeImage(const ImageInfo& info, GPUVAddr gpu_addr, DAddr cpu_addr);
    ImageId MakeShadow(const ImageInfo& info) {
        struct { ImageId id{33}; } view;
        [[maybe_unused]] constexpr ImageId NULL_IMAGE_VIEW_ID{0};
        const GPUVAddr gpu_addr=0x1000;
        const DAddr cpu_addr=0x2000;
        for (int once=0; once!=1; ++once) {
__SHADOW__
        }
        return view.id;
    }
    void Refresh(Image& image) {
__REFRESH_CLEAR__
        image.flags |= ImageFlagBits::Tracked;
__REFRESH_UNBACKED__
        ++uploads;
    }
    void Expire() { image_refused_until={}; }
};
__MAKE__
int failures=0;
void Check(bool condition, const char* message) {
    std::printf("%s: %s\n", condition ? "PASS" : "FAIL", message);
    failures += !condition;
}
int main() {
    ImageInfo ordinary;
    {
        Cache cache;
        int before=Resource::destroyed;
        auto id=cache.TryMakeImage(ordinary, 0x1000, 0x2000);
        Check(!id && cache.slot_images.size()==1 && Resource::live==0 && Resource::destroyed==before+1,
              "ordinary OOM publishes no slot and RAII destroys the empty VkImage");
        cache.runtime.recovered=true;
        auto paused=cache.TryMakeImage(ordinary, 0x1000, 0x2000);
        Check(!paused && cache.runtime.creations==1, "existing one-second backoff avoids allocation churn");
        cache.Expire();
        id=cache.TryMakeImage(ordinary, 0x1000, 0x2000);
        if(id) cache.Refresh(cache.slot_images[id]);
        Check(id && id.Value()==1 && !cache.slot_images[id].original_image.IsUnbacked() && cache.uploads==1,
              "recovery reuses the failed slot and uploads guest content without another guest write");
    }
    {
        Cache cache;
        auto view=cache.MakeShadow(ordinary);
        Check(view.Value()==0 && cache.feedback_shadows.empty() && cache.slot_images.size()==1,
              "feedback shadow OOM uses the existing null descriptor without publishing a shadow");
        cache.runtime.recovered=true;
        view=cache.MakeShadow(ordinary);
        Check(view.Value()==0 && cache.runtime.creations==1, "feedback shadows share refusal backoff");
        cache.Expire(); cache.MakeShadow(ordinary);
        Check(cache.feedback_shadows.size()==1 && cache.feedback_shadows[0].Value()==1 &&
              !cache.slot_images[cache.feedback_shadows[0]].original_image.IsUnbacked(),
              "feedback shadow is retried and backed after recovery");
    }
    for(int mode=0; mode<7; ++mode) {
        Cache cache;
        ImageInfo info;
        if(mode==0) info.unwritten=true;
        if(mode==1) info.size.width=1u<<29;
        if(mode==2 || mode==4) info.layers=true;
        if(mode==3 || mode==5) info.tiles=true;
        if(mode==4 || mode==5) info.sparse_init=false;
        if(mode==6) cache.runtime.recovered=true;
        auto id=cache.TryMakeImage(info, 0x1000, 0x2000);
        unsigned required=mode==2 ? ImageFlagBits::SparseLayers : mode==3 ? ImageFlagBits::SparseTiles :
                          (mode==0 || mode==4 || mode==5) ? ImageFlagBits::UnwrittenSparse : 0;
        Check(id && (cache.slot_images[id].flags & required)==required &&
              cache.slot_images[id].original_image.IsUnbacked()==(mode!=6),
              "intentional unwritten/huge/sparse layer/sparse tile and backed paths preserved");
    }
    {
        Cache cache;
        cache.runtime.ends=true;
        bool threw=false;
        try { (void)cache.TryMakeImage(ordinary,0x1000,0x2000); }
        catch(const vk::Exception& e) { threw=e.GetResult()==VK_ERROR_OUT_OF_DEVICE_MEMORY; }
        Check(threw && cache.slot_images.size()==1 && Resource::live==0,
              "explicit end-on-OOM policy still propagates with clean ownership");
        bool other=false;
        try { (void)cache.runtime.SurvivesImageRefusal([] { throw vk::Exception{VK_ERROR_OUT_OF_HOST_MEMORY}; }); }
        catch(const vk::Exception& e) { other=e.GetResult()==VK_ERROR_OUT_OF_HOST_MEMORY; }
        Check(other,"non-device-OOM exceptions are never swallowed");
    }
    Check(Resource::live==0,"all test-owned VkImages released");
    return failures ? 1 : 0;
}
'''
code = prefix
for name, value in {'SURVIVES': survives, 'CONSTRUCTOR': constructor, 'SHADOW': shadow,
                    'REFRESH_CLEAR': refresh_clear, 'REFRESH_UNBACKED': refresh_unbacked,
                    'MAKE': make}.items():
    code = code.replace('__' + name + '__', value)
result = {'status':'fail','exit_code':1,'baseline':args.baseline,
          'source_sha256':{name:hashlib.sha256((tested/name).read_bytes()).hexdigest() for name in names},
          'scope':'actual constructor branch, shared refusal path, feedback creation branch, refresh flags, generated SlotVector; simulated device allocation'}
with TemporaryDirectory(prefix='test4a-image-refusal-') as temporary:
    folder=Path(temporary)
    (folder/'common').mkdir()
    (folder/'common/assert.h').write_text('#pragma once\n#include <cassert>\n#define DEBUG_ASSERT(x) assert(x)\n')
    (folder/'common/common_types.h').write_text('#pragma once\n#include <cstdint>\nusing u64=std::uint64_t; using u32=std::uint32_t;\n')
    slot=folder/'slot_vector.h'
    subprocess.run(['cmake','-DSLOT_VECTOR_INPUT='+str(root/'Eglantine/src/common/slot_vector.h'),
                    '-DSLOT_VECTOR_OUTPUT='+str(slot),'-P',str(root/'headless/slot_vector_recovery.cmake')],check=True)
    (folder/'common/slot_vector.h').write_text(slot.read_text())
    (folder/'check.cpp').write_text(code)
    built=subprocess.run(['clang++-18','-std=c++20','-Wall','-Wextra','-Werror',
                          '-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(folder),
                          str(folder/'check.cpp'),'-o',str(folder/'check')],text=True,capture_output=True)
    result['compile_exit']=built.returncode
    if built.returncode:
        result['compile_stderr']=built.stderr
    else:
        checked=subprocess.run([str(folder/'check')],text=True,capture_output=True)
        result.update(exit_code=checked.returncode,status='pass' if checked.returncode==0 else 'fail',
                      stdout=checked.stdout,stderr=checked.stderr)
args.result.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
raise SystemExit(result['exit_code'])
