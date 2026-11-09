#!/usr/bin/env python3
"""Check the pinned generated GPU FIFO, fence watermark and stop cancellation."""
from pathlib import Path
import subprocess, tempfile

root = Path(__file__).resolve().parents[1]
cache = Path((root / '.local/headless-cache').read_text().strip())
worker = (cache / 'native-local/headless/gpu_thread.cpp').read_text()
header = (cache / 'native-local/headless/include/video_core/gpu_thread.h').read_text()
start = worker.index('u64 ThreadManager::PushCommand(')
body = worker[start:worker.index('\n} // namespace', start)]
assert 'state.queue.EmplaceWait(' not in body
assert 'state.queue.TryEmplace(std::move(command_data), fence, block)' in body
assert 'return fence <= state.signaled_fence.load(std::memory_order_relaxed);' in body
assert 'state.cv.wait(lk, stop_source.get_token(),' in body
signal_start = worker.index('void SignalCommand(')
signal_body = worker[signal_start:worker.index('\n} // Anonymous namespace', signal_start)]
assert 'void SignalCommand(SynchState& state, u64 fence, bool block)' in signal_body
assert 'state.signaled_fence.store(fence);' in signal_body
assert signal_body.index('state.signaled_fence.store(fence);') < signal_body.index('std::scoped_lock lk{state.write_lock};')
assert 'state.cv.notify_all();' in signal_body
assert 'bool block{};' in header and 'HostCommandCompletion' not in header
main = (root / 'headless/main.cpp').read_text()
assert 'system.Pause();' not in main
code = r'''
#include <array>
#include <variant>
#include <atomic>
#include <cassert>
#include <chrono>
#include <condition_variable>
#include <future>
#include <mutex>
#include <stop_token>
#include <thread>
#include "common/host_command_queue.h"
using u64 = unsigned long long;
using CommandData = std::variant<int>;
struct Item { CommandData command{}; u64 fence{}; bool block{}; };
struct SynchState {
 std::mutex write_lock;
 Common::HostCommandQueue<Item> queue;
 u64 last_fence{};
 std::atomic<u64> signaled_fence{};
 std::condition_variable_any cv;
};
namespace VideoCommon {
struct GpuSplit {
 static GpuSplit& Get() { static GpuSplit split; return split; }
 void Stop() {}
};
}
struct ThreadManager {
 SynchState state;
 std::stop_source stop_source;
 u64 PushCommand(CommandData&&, bool, bool);
 void NotifyShutdown();
 void Stop() { stop_source.request_stop(); }
};
''' + signal_body + '\n' + body + r'''
Item Pop(ThreadManager& manager) {
 Item item;
 const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
 while (!manager.state.queue.TryPop(item)) {
   assert(std::chrono::steady_clock::now() < deadline);
   std::this_thread::yield();
 }
 return item;
}
int main() {
 ThreadManager manager;
 // Exceed the former bounded queue capacity without a consumer.
 constexpr int count = 16384;
 for (int i = 0; i < count; ++i)
   assert(manager.PushCommand(int{i}, false, true) == u64(i + 1));
 Item item;
 for (int i = 0; i < count; ++i) {
   assert(manager.state.queue.TryPop(item));
   assert(std::get<int>(item.command) == i && item.fence == u64(i + 1));
   assert(!item.block);
 }
 assert(!manager.state.queue.TryPop(item));
 manager.stop_source.request_stop();
 assert(manager.PushCommand(4, false, true) == 0);
 assert(!manager.state.queue.TryPop(item));

 // Synchronous mode forces block=true; cancellation must release its fence wait.
 ThreadManager synchronous;
 auto fence_wait = std::async(std::launch::async, [&] {
   return synchronous.PushCommand(5, false, false);
 });
 const Item synchronous_item = Pop(synchronous);
 assert(synchronous_item.fence == 1 && synchronous_item.block);
 assert(fence_wait.wait_for(std::chrono::milliseconds(10)) == std::future_status::timeout);
 synchronous.stop_source.request_stop();
 assert(fence_wait.wait_for(std::chrono::seconds(1)) == std::future_status::ready);
 assert(fence_wait.get() == 1);
 assert(synchronous.state.signaled_fence.load() == 0);
 assert(!synchronous.state.queue.TryPop(item));

 // The pinned worker publishes its cumulative fence before taking write_lock.
 // A nonblocking command signals without taking write_lock at all.
 ThreadManager published;
 {
   std::unique_lock held(published.state.write_lock);
   SignalCommand(published.state, 0, false);
   auto signal = std::async(std::launch::async, [&] { SignalCommand(published.state, 1, true); });
   const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(1);
   while (published.state.signaled_fence.load() != 1) {
     assert(std::chrono::steady_clock::now() < deadline);
     std::this_thread::yield();
   }
   assert(signal.wait_for(std::chrono::milliseconds(10)) == std::future_status::timeout);
   held.unlock();
   assert(signal.wait_for(std::chrono::seconds(1)) == std::future_status::ready);
   signal.get();
 }
 // A completion already published before the wait must satisfy the predicate immediately.
 assert(published.PushCommand(6, true, true) == 1);
 item = Pop(published);
 assert(item.fence == 1 && item.block && std::get<int>(item.command) == 6);

 // Completion after parking wakes the caller and returns its own fence.
 ThreadManager completed;
 auto completing = std::async(std::launch::async, [&] {
   return completed.PushCommand(6, true, true);
 });
 const Item completion_item = Pop(completed);
 assert(completion_item.fence == 1 && completion_item.block);
 assert(completing.wait_for(std::chrono::milliseconds(10)) == std::future_status::timeout);
 SignalCommand(completed.state, completion_item.fence, completion_item.block);
 assert(completing.wait_for(std::chrono::seconds(1)) == std::future_status::ready);
 assert(completing.get() == 1);

 // The current completion protocol is an ordered cumulative watermark, not a
 // per-request completion object. Each FIFO signal releases only its prefix.
 ThreadManager ordered;
 std::array<std::future<u64>, 8> waits;
 for (int i = 0; i < int(waits.size()); ++i)
   waits[i] = std::async(std::launch::async, [&, i] { return ordered.PushCommand(int{i}, true, true); });
 std::array<Item, 8> items;
 for (int i = 0; i < int(items.size()); ++i) {
   items[i] = Pop(ordered);
   assert(items[i].fence == u64(i + 1) && items[i].block);
 }
 SignalCommand(ordered.state, 0, true);
 for (auto& wait : waits)
   assert(wait.wait_for(std::chrono::milliseconds(1)) == std::future_status::timeout);
 for (int i = 0; i < int(items.size()); ++i) {
   const Item& pending = items[i];
   const int producer = std::get<int>(pending.command);
   SignalCommand(ordered.state, pending.fence, pending.block);
   assert(ordered.state.signaled_fence.load() == pending.fence);
   assert(waits[producer].wait_for(std::chrono::seconds(1)) == std::future_status::ready);
   assert(waits[producer].get() == pending.fence);
   for (int later = i + 1; later < int(items.size()); ++later)
     assert(waits[std::get<int>(items[later].command)].wait_for(std::chrono::milliseconds(1)) ==
            std::future_status::timeout);
 }
 assert(!ordered.state.queue.TryPop(item));

 // Stop requested before callback registration must also prevent publication.
 ThreadManager cancelled;
 cancelled.stop_source.request_stop();
 assert(cancelled.PushCommand(8, true, true) == 0);
 assert(!cancelled.state.queue.TryPop(item));
}
'''
with tempfile.TemporaryDirectory() as tmp:
    source = Path(tmp) / 'check.cpp'
    source.write_text(code)
    executable = Path(tmp) / 'check'
    subprocess.run(['c++', '-std=c++20', '-pthread', '-fsanitize=address,undefined',
                    '-fno-omit-frame-pointer', '-I' + str(cache / 'source/src'),
                    str(source), '-o', str(executable)], check=True)
    subprocess.run([str(executable)], check=True, timeout=10)
print('GPU producer: PASS 16384 FIFO publications, exact pinned fence/block ordering, stopped enqueue and synchronous wait, completion before/after parking, eight ordered concurrent waiters')