# Test4-A detailed changelog

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

## Preserved Test3 foundation

The frontend remains pinned to `25cfc07be0a3675749adece5d012fdb916c4cd48`; the core remains `0ca2032bffc5f1a3fca75427f7d4a4718adda660`. Reconstruction applied 257 baseline overlays and the four supplied Test3 overlays 0425, 0427, 0428 and 0429. All 5,684 source files matched the saved Test3 manifest before Test4-A edits. Existing Test3 builds and sources remain preserved.

The separate Test4-A replay applies all 264 overlays and checks 4,800 core Git-listed tracked/unignored files. That narrower file set excludes nested external/submodule contents present in the earlier Test3 snapshot; the two counts describe different comparison scopes.

Retained protections include depth-image sampled-type correctness, failed compute-module cleanup, upload-size/allocation checks, GPU virtual-range checks, the display fallback correction, and title-scoped CPU/DMA/cache-invalidation settings. Their supplied checks pass in the reconstructed tree.

## Implemented and host-checked in this snapshot

`0430-test4a-no-mesh-boolean.patch` changes the rasterizer and pre-build mesh gate to honor a literal 0 value. `tools/patch-radv-wsi.py` applies compatible semantics to the driver buffer policy. The existing supported mesh-as-compute fallback and extension requirements remain enforced.

Before: `EDEN_NX2_NO_MESH=0` still turns skipping on. After: unset/literal 0 do not request skipping; explicit/legacy on and file-toggle behavior remain covered. Eight actual-source cases pass under AddressSanitizer and UndefinedBehaviorSanitizer after the baseline check failed with exit 1.

Expected effect: valid mesh work is allowed to reach the existing supported path. Visual restoration and changed memory/FPS cost remain unverified on PS5. FPS earned by omitted rendering is not a valid correctness improvement.

The unchanged 49-key Prettier profile remains the Test4-A default. The archived Faster file is retained for historical Test3 comparison only: its `LONE=0` leaves lone-mesh fallback disabled and may omit foliage. Fixing the separate no-mesh toggle does not make that profile an equivalent-correctness recommendation.

`tools/radv-patches/test4a-01-nir-copy-prop-oom.patch` checks dynamic copy-entry allocation and initial pass state/context allocation in Mesa's optional NIR variable copy-propagation pass. Failure ends the optimization safely while preserving valid work already completed. The pass retains metadata/cleanup semantics; it does not reject the entire shader or draw. The production driver patch-series helper and fingerprint include the new patch. Its NIR diagnostic counter is process-global and prints at most eight messages to stderr.

Before: two normal real-NIR cases pass and six injected OOM cases fail. After: all 8 cases pass under ASan/UBSan, including NIR validation, control-flow metadata, preserved stores and semantic result 2087. An additional 24-case caller-path receipt reports pass / exit 0. This covers the demonstrated crash boundary; it does not eliminate general memory exhaustion or all possible compiler OOM faults.

`0432-test4a-transient-image-refusal.patch` prevents ordinary unbacked images from being retained as clean texture-cache resources. Constructor failure cleans up owned image handles. Both image creation callers use a shared refusal boundary: normal joins and feedback shadows retain the existing one-second backoff and retry after memory recovery. A feedback failure uses the existing null descriptor temporarily and leaves no published shadow. Intentionally unwritten/sparse paths and the explicit end-on-OOM policy remain intact. All 16 host cases pass with simulated device allocation; actual PS5 texture recovery is unverified.

`0431-test4a-bounded-draw-diagnostics.patch` replaces the misleading native-failure completion message with cumulative warnings for the first eight failures and every 1,024th afterward, per draw-path template instantiation. The templated `PrepareDraw` has separate direct and indirect call paths, each with its own static counter; these are not one process-global draw counter. The original harness tests one extracted counter: 32,768 failed calls across eight threads produce exactly 40 warnings, exit 0. The additional two-path template test covers 65,536 total failures across eight threads and produces exactly 80 warnings, exit 0. Existing flags and preceding detailed errors remain available. No extra skipped draws or queue waits are introduced.

Frontend crash reports now include the global last heap allocation failure (count, requested bytes and reason) and safely probed 32 bytes at the faulting instruction pointer. An unreadable address is reported without dereferencing it. The heap snapshot is global context and must not be mistaken for a causal thread-specific allocation. The existing host/native-mock crash-report suite covers the new reader/output. The allocator implementation and heap limits are unchanged. A boot marker identifies the local Test4-A build. These additions help investigate the two unresolved non-pipeline faults; they do not fix their originating instructions.

Two inherited host test harnesses were corrected after the native build: `tools/check-gpu-sync-stop.py` supplies the missing scalar/logging/back-thread stand-ins, and `tools/check-gpu-producer-stop.py` tests the pinned fence-watermark implementation instead of requiring a newer, absent per-request completion API. Actual production methods remain extracted into the tests. These are test-only compatibility corrections; the compiled runtime did not change.

## Native and console certification

Final inclusion requires the native build receipt, matching symbols and package validation. Complete geometry, texture recovery, brightness, flashes, sustained FPS and crash-free gameplay need controlled PS5 tests. No memory limits, descriptor budgets or reserve safety policies are raised by these corrections.

Current additional overlay files present:

- `0430-test4a-no-mesh-boolean.patch`
- `0431-test4a-bounded-draw-diagnostics.patch`
- `0432-test4a-transient-image-refusal.patch`
- `test4a-01-nir-copy-prop-oom.patch`

Current source files whose bytes differ from reconstructed Test3:

- `Eglantine/src/video_core/renderer_vulkan/vk_pipeline_cache.cpp`
- `Eglantine/src/video_core/renderer_vulkan/vk_rasterizer.cpp`
- `Eglantine/src/video_core/renderer_vulkan/vk_texture_cache.cpp`
- `Eglantine/src/video_core/texture_cache/texture_cache.h`
- `Eglantine/src/video_core/texture_cache/texture_cache_base.h`
- `headless/crash_report.cpp`
- `headless/main.cpp`
- `tools/check-crash-report.py`
- `tools/check-gpu-producer-stop.py`
- `tools/check-gpu-sync-stop.py`
- `tools/patch-radv-series.py`
- `tools/patch-radv-wsi.py`

## Risks that remain

Correct rendering can cost FPS and memory. The overall resource-exhaustion cause, CPU/system-library faults, brightness, dark glitches, white flashes, long-session stability and cold-cache behavior still require measured console testing. Native build state: Completed receipt reports exit **0**, with unchanged source hashes during the build.
