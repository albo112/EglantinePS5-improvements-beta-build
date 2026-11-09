#!/usr/bin/env python3
"""Exercise actual T49 fence commit/signal paths, including pending query reports."""
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

root = Path.cwd()
source = (root / 'Eglantine/src/video_core/fence_manager.h').read_text()
def body(signature):
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]

code = r'''
#include <cassert>
#include <condition_variable>
#include <functional>
#include <memory>
#include <mutex>
#include <queue>
#include <utility>
#include <vector>
using u8=unsigned char;
namespace Settings {
inline bool delayed{};
bool IsGPUFenceBehaviorDefault(){return false;} bool IsGPULevelHigh(){return false;}
bool IsGPUFenceBehaviorBalanced(){return delayed;} bool IsGPUFenceBehaviorAccurate(){return false;}
}
namespace VideoCore {inline thread_local bool g_signaling_query_report_fence=false;}
namespace VideoCommon {
namespace Nx2Profile {enum class Zone{Fence,FenceSkipped};struct Scope{explicit Scope(Zone){}};}
struct Cache {
 std::mutex mutex;bool pending{},side_work{};unsigned checks{},commits{};
 bool HasUncommittedFlushes(){++checks;return pending;}
 bool HasAsyncFlushWork(){return pending||side_work;}
 void CommitAsyncFlushes(){++commits;pending=false;}
};
struct Raster {unsigned invalidates{},flushes{};void InvalidateGPUCache(){++invalidates;}void FlushCommands(){++flushes;}};
struct TestFence {bool stubbed;};
struct Manager {
 using TFence=std::shared_ptr<TestFence>;
 static constexpr bool can_async_check=false;
 static constexpr u8 TextureFlushes=1,BufferFlushes=2;
 Cache texture_cache,buffer_cache,query_cache;Raster rasterizer;
 std::mutex guard,uncommitted_guard;std::condition_variable cv;
 unsigned skipped_fences{},queued{};bool skip{};
 std::vector<std::function<void()>> uncommitted_operations;
 std::vector<std::vector<std::function<void()>>> pending_operations;
 std::vector<u8> pending_flushes;std::queue<TFence> fences;
 template<bool>void TryReleasePendingFences(){}
 bool SkipEmptyFence(){return skip;}
 TFence CreateFence(bool stubbed){return std::make_shared<TestFence>(TestFence{stubbed});}
 void QueueFence(const TFence&){++queued;}
 struct CacheFlushes{bool should_flush;u8 committed;};
''' + body('CacheFlushes CommitCacheFlushes()') + '\n' + body('void SignalFence(std::function<void()>&& func)') + r'''
};
}
int main(){
 using namespace VideoCommon;
 for(bool query:{false,true})for(bool delayed:{false,true})for(unsigned mask=0;mask<8;++mask){
  Settings::delayed=delayed;VideoCore::g_signaling_query_report_fence=query;Manager m;m.skip=query;
  m.texture_cache.pending=mask&1;m.buffer_cache.pending=mask&2;m.query_cache.pending=mask&4;
  unsigned callbacks{};m.SignalFence([&]{++callbacks;});
  assert(m.queued==1&&m.fences.size()==1&&m.fences.front()->stubbed==(mask==0));
  assert(m.texture_cache.checks==1&&m.buffer_cache.checks==1&&m.query_cache.checks==1);
  assert(m.texture_cache.commits==bool(mask&1)&&m.buffer_cache.commits==bool(mask&2)&&m.query_cache.commits==1);
  assert(m.pending_flushes.back()==(mask&3)&&m.rasterizer.flushes==bool(mask));
  assert(callbacks==!(query||delayed)&&m.rasterizer.invalidates==1);
  if(query||delayed){assert(m.pending_operations.back().size()==1);m.pending_operations.back()[0]();assert(callbacks==1);}
 }
 VideoCore::g_signaling_query_report_fence=false;Settings::delayed=false;
 {Manager m;m.skip=true;unsigned calls{};m.SignalFence([&]{++calls;});
  assert(calls==1&&!m.queued&&!m.query_cache.checks&&!m.query_cache.commits);}
 {Manager m;m.texture_cache.side_work=true;m.SignalFence([]{});
  assert(m.queued==1&&m.fences.front()->stubbed&&m.texture_cache.commits==1);
  assert(m.pending_flushes.back()==1&&!m.rasterizer.flushes);}
}
'''
with TemporaryDirectory(prefix='zelda-query-fences-') as directory:
    work = Path(directory)
    (work / 'check.cpp').write_text(code)
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror', '-O1', '-g', '-pthread',
                    '-fsanitize=address,undefined', str(work / 'check.cpp'), '-o', str(work / 'check')], check=True)
    subprocess.run([str(work / 'check')], check=True)
print('Fence requirements PASS: 32 query/accuracy/cache combinations, empty skip, side-work and callback ordering')
