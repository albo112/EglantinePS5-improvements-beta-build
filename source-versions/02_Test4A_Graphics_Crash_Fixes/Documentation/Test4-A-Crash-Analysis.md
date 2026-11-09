# Test4-A crash analysis

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

## Coverage and build identity

All **53 files / 130,434,078 bytes / 910,036 lines** were read. The archive contains eight complete crash groups and nine game launches, including one normal return to the menu before a second launch in the same app. Three empty TSV files are included in the coverage manifest. `log-coverage.json` records individual hashes; `session-timelines.json` preserves stage and memory evidence.

| Input archive | Extracted files | Original SHA-256 |
| --- | ---: | --- |
| `nsw2 emu log files.rar` | 53 | `7d60ed64c5ba1ff9bc9e5ca7fa915a873d634166cd4212c33b2991e68e3c6afa` |
| `EglantinePS5-v1.219.020.zip` | 69 | `8209561dc5e9328e92cc8668a084e4f4e37b26e30df5c9d614a28a90470d4ae7` |
| `EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes.zip` | 71 | `55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7` |
| `EglantinePS5-Zelda-Test3-Source-Changes.zip` | 25 | `5a06546cec7c9314ddb7f45003988d87da0a4d7f90e4d047ca56fc8bd20ee1fb` |

All crash summaries name `01.219.020` and code size `0x2ab2bb0`. The saved Test3 ELF has that exact text size and SHA-256 `930886ee0b0301169b3977f830954702c7b55da7afa5dc1fbc6260b300458816`. The supplied Test3 package also matches the saved package hash. These support the symbol match; the logs do not contain an on-console executable hash.

## Fatal events

Times are exactly as logged by the console. No timezone conversion is inferred. Final-session ages are approximate because crash app ages are rounded; they are not uninterrupted playability measurements.

| Report / console timestamp | Thread | Instruction | Largest free block (MiB) | Final game age (s) |
| --- | --- | --- | ---: | ---: |
| `Logs3/crash-20261107-200504.txt` | VkPipelineBuilder | `eboot+0x229fcc3` | 2 | 129.996 |
| `Logs3/crash-20261107-200953.txt` | CPUCore_3 | `0x11ccd2b585, generated code` | 1 | 93.861 |
| `Logs3/crash-20261107-201432.txt` | VkPipelineBuilder | `eboot+0x229fcc3` | 0 | 216.859 |
| `Logs3/crash-20261107-201818.txt` | VkPipelineBuilder | `eboot+0x229fcc3` | 2 | 156.832 |
| `Logs3/crash-20261107-202529.txt` | not named | `0x8000a3fd5, outside eboot` | 2 | 383.802 |
| `Logs4/crash-20261107-203446.txt` | VkPipelineBuilder | `eboot+0x229fcc3` | 2 | 253.722 |
| `Logs4/crash-20261107-203836.txt` | VkPipelineBuilder | `eboot+0x229fcc3` | 0 | 147.756 |
| `Logs5/crash-20261107-205143.txt` | VkPipelineBuilder | `eboot+0x229fcc3` | 3 | 629.099 |

The six pipeline reports fault at **exactly `eboot+0x229fcc3`**, not six nearby offsets. Independent `llvm-addr2line-18` resolves that address to Mesa `copy_entry_create`, `src/compiler/nir/nir_opt_copy_prop_vars.c:419`. `llvm-objdump-18` shows `movq %rdx,0xa0(%rax,%rcx)`. In every one of those six reports, `rax=0` and `rcx+0xa0` exactly equals the recorded low fault address. This establishes a null backing-pointer write at the dynamic-array append. Allocation-failure source tracing supports the OOM mechanism; it does not establish the initial source of every byte retained in the shared memory pool or prove a use-after-free.

## Prioritized findings and corrections

| Priority / finding | Exact evidence and frequency | Source / function | Status and correction | Regression risk / validation |
| --- | --- | --- | --- | --- |
| P0: NIR append after failed allocation | Six reports above; all six null-base instruction/register matches. All eight crashes show only 0–3 MiB largest free block. | Mesa `nir_opt_copy_prop_vars.c:copy_entry_create`; `util_dynarray` grow/append | Implemented checked allocation and safe early end of optional copy propagation, including initial state/context guards. 8 real-NIR ASan/UBSan cases pass; no exception/longjmp across driver code or blanket draw suppression. | Already-valid IR, metadata and semantic result are checked. Native driver build and PS5 low-memory behavior remain separate gates; other compiler OOM paths may still fail. |
| P1: `NO_MESH=0` still skips geometry | 244 stored bounded skip warnings. Example `Logs5/crash-20261107-205143-eden_log.txt:162599` at app +162.815784 s. All nine loaded profiles say `NO_MESH=0`. | `RasterizerVulkan::PrepareDraw`, `DropMeshDrawsBeforeBuild`, RADV mesh-buffer policy | Implemented in overlay 0430 plus WSI patch generator: literal 0 is off; explicit on/legacy/file paths retain compatibility. Eight actual-source sanitizer cases pass. | Restored geometry costs real work and may expose further resource pressure. The existing supported mesh-as-compute fallback is retained; compare the same visual route on PS5. |
| P1: failed image allocation becomes an unbacked resource | 192 `CreateImage` sparse fallbacks; 208 over-budget allocation warnings. Example `Logs4/crash-20261107-203836-eden_log.txt:3055–3533`, app +184.437987 to +190.768982 s. | `vulkan_memory_allocator.cpp:CreateImage`; texture `Image` construction / `TryMakeImage` / `JoinImages` and feedback-shadow creation | Overlay 0432 rejects ordinary failed backing before publishing a cache slot. Both constructor callers share the existing one-second refusal backoff and can retry after recovery, preserving intentionally sparse images. | 16 actual-source host cases pass with simulated allocation, RAII ownership and retry checks. Physical allocation behavior and texture recovery still need PS5 evidence. |
| P1: shared-pool pressure and ineffective reclamation | Every fatal report largest free 0–3 MiB; 212 reclaim lines, 200 reporting 0 slots. | Guest memory service, texture-cache GC, direct-memory and heap allocators | Severe pressure verified; a single leak or universal fragmentation cause is not proven. Caps and safety guards remain. A global heap last-failure snapshot adds request size/reason to crash reports. | The snapshot is context, not proof that the last heap failure caused a particular crash. Compare committed/live/held memory and allocation success with equivalent scenes. |
| P2: native draw failures and misleading completion wording | 27,262 Debug lines in two Debug-heavy captures. Logs4 line 145335 follows mesh skip; Logs5 lines 162599–162600 show the same sequence. | Templated `RasterizerVulkan::PrepareDraw` scope-exit / `native_execution_failed` | Overlay 0431 records cumulative failures per draw-path template instantiation: direct and indirect calls have separate counters, each logging the first eight warnings and every 1,024th thereafter. It replaces misleading completion wording; no reader established that the old flag withheld queue completion. | One extracted counter gives 40 warnings for 32,768 failures on eight threads. The two-path template test gives 80 warnings for 65,536 total failures, exit 0. These are per-path counters, not a process-global 40-line bound. Actual draw outcomes and preceding detailed errors remain visible; no additional skip or wait is introduced. |
| P2: rejected compute and storage binding limits | 90 matrix-translation rejection lines, 144 native-QMD-failed lines; 111 uncached-pointer and 63 binding-budget warnings. Example Logs5 compute lines 51335–51598 at app +81.587133–81.708425 s. | `KeplerCompute::DispatchNativeCompute` / `ProcessNativeMethod`; global-memory storage-buffer classification | All logged matrix rejections name native matrix multiplication excluded by `TENSOR_ONLY`. A completed supported translation/fallback is not established by these logs. | Keep unsupported operations visible. Do not invent output, globally reject shaders, or raise the 32-binding limit without device/IR evidence. |
| P2: waits/stalls | 146 actual hang-watch warning lines; zero precise timed-out warning/error matches. Example Logs3/201818 lines 3567–3651 at +158.773189–163.787622 s. | `gpu_split.cpp:ReportBack`, `vulkan_scheduler.cpp:ReportFreeze` | Back/worker snapshots show waits for GPU ticks or pipeline builds. They do not alone prove a missing Vulkan barrier or physical GPU hang. | Correlate progress, compiler and allocation events. Avoid global idle waits or barrier changes without a reproducible ordering defect. |
| Residual: CPU and system-library faults | Two reports at 20:09:53 and 20:25:29, both under pressure. | Generated CPU code / an outside-eboot instruction | Exact originating instruction/resource cause remains unresolved. Crash reports now safely probe 32 bytes at RIP through the existing kernel-pipe copy helper and handle unreadable addresses. | Matching crash-report host/native-mock checks verify instruction output. This is evidence collection, not a correction of the two faults or proof of malformed-command origin. |

Counts above are stored lines, not unique allocations, shader programs, physical hangs, or all failed draws. Skip warnings are rate limited; Debug-level failures are absent from Info-only captures. Broad `timeout` matches include `ChannelSetTimeout` and `Poll(timeout=0)` arguments and must not be counted as failures.

## Configuration and performance constraints

Every observed launch uses the 49-key Faster profile: `LONE=0`, `QUERY_KEEP_PENDING=0`, all-stage tables/paired pointers on, four pipeline builders and the safe-memory override. CPU Auto, Default DMA and normal cache invalidation are logged; unsafe-setting advice does not explain these new sessions. Logs4/20:34:46 and Logs5/20:51:43 contain 319,118 and 531,699 Debug-tagged lines respectively, so logging load is also a comparison confounder.

The historical Faster profile also leaves lone-mesh fallback disabled through `LONE=0`, so it may continue omitting foliage even after correcting the separate `NO_MESH=0` parsing bug. Test4-A therefore defaults to the unchanged 49-key Prettier profile. Faster's bytes are preserved only for reproducing the historical incomplete-graphics baseline, not as an equivalent-correctness preset.

All nine launches preload nonempty emulator caches (1,138–2,405 records in 7.395–11.513 s). That does not prove every record builds, or that the separate driver cache is warm. No controlled all-cache-empty test is present. The longest final session lasts about 629 s and includes a median logged 1.1 FPS and a worst recorded interval about 24.969 s; it is not evidence of stable gameplay.

The selected resource/app folder in the logs is `/system_ex/app/PPSA98515`, while `/data/homebrew/PPSA98515` also exists. Verify the active installation/profile path when testing. App-folder selection alone is not a cryptographic proof of which executable is mapped.

## Session timelines

The following preserves each recorded launch's startup, shader preload, graphics readiness, pressure/error windows and final event. Untimestamped stderr samples retain line order rather than invented wall-clock times.


### crash-20261107-200504, launch 1

- Startup context: app start approximately `2026-11-07 19:58:23` from the crash report's rounded age; game begins at `Logs3/crash-20261107-200504-eden_log.txt:3` at app +12.894099s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 127); core_constructed +0.554s (heap line 133); core_initialized +0.566s (heap line 135); game_loaded +2.337s (heap line 151); cpu_manager_ready +2.339s (heap line 154); first_frame_callback +29.503s (heap line 158); shortcut_return_to_menu +47.659s (heap line 227); core_shutdown +52.549s (heap line 229); core_destroyed +52.554s (heap line 231).
- Initial cached shader compilation: 2405 pipelines in 11513 ms; `Logs3/crash-20261107-200504-stderr.log:135`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs3/crash-20261107-200504-stderr.log:95`: largest 11356 MiB, guest 172 MiB, short=0; last `Logs3/crash-20261107-200504-stderr.log:143`: largest 8435 MiB, guest 1719 MiB, short=0. Minimum recorded largest block 8435 MiB; peak recorded guest 1719 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs3/crash-20261107-200504-eden_log.txt:1361` at app +51.569357s, last `Logs3/crash-20261107-200504-eden_log.txt:1405` at app +51.608882s.
- Skipped mesh draw warning: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- End: normal game-session end at `Logs3/crash-20261107-200504-eden_log.txt:2308` at app +64.877283s; a later launch is recorded in the same app.

### crash-20261107-200504, launch 2

- Startup context: app start approximately `2026-11-07 19:58:23` from the crash report's rounded age; game begins at `Logs3/crash-20261107-200504-eden_log.txt:2312` at app +271.004094s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 344); core_constructed +0.496s (heap line 350); core_initialized +0.502s (heap line 352); game_loaded +2.677s (heap line 367); cpu_manager_ready +2.679s (heap line 370); first_frame_callback +29.939s (heap line 374).
- Initial cached shader compilation: 2405 pipelines in 11111 ms; `Logs3/crash-20261107-200504-stderr.log:397`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs3/crash-20261107-200504-stderr.log:359`: largest 10586 MiB, guest 170 MiB, short=0; last `Logs3/crash-20261107-200504-stderr.log:840`: largest 72 MiB, guest 6217 MiB, short=1. Minimum recorded largest block 72 MiB; peak recorded guest 6217 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs3/crash-20261107-200504-eden_log.txt:3273` at app +310.812781s, last `Logs3/crash-20261107-200504-eden_log.txt:3315` at app +310.858166s.
- Skipped mesh draw warning: 34 stored lines; first `Logs3/crash-20261107-200504-eden_log.txt:4313` at app +340.604757s, last `Logs3/crash-20261107-200504-eden_log.txt:5071` at app +400.750707s.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- Over-budget image allocation warning: 32 stored lines; first `Logs3/crash-20261107-200504-eden_log.txt:4681` at app +361.518480s, last `Logs3/crash-20261107-200504-eden_log.txt:5051` at app +400.393014s.
- End: `Logs3/crash-20261107-200504.txt:3–8`, console time 2026-11-07 20:05:04; SIGSEGV (invalid memory access), code 1, address 0x00000000000237a0; eboot+0x229fcc3; largest free block 2 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-200953, launch 1

- Startup context: app start approximately `2026-11-07 20:08:10` from the crash report's rounded age; game begins at `Logs3/crash-20261107-200953-eden_log.txt:3` at app +9.138919s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 132); core_constructed +0.562s (heap line 138); core_initialized +0.574s (heap line 140); game_loaded +2.562s (heap line 156); cpu_manager_ready +2.564s (heap line 159); first_frame_callback +30.088s (heap line 163).
- Initial cached shader compilation: 2209 pipelines in 11411 ms; `Logs3/crash-20261107-200953-stderr.log:135`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs3/crash-20261107-200953-stderr.log:95`: largest 11356 MiB, guest 170 MiB, short=0; last `Logs3/crash-20261107-200953-stderr.log:450`: largest 2 MiB, guest 5817 MiB, short=1. Minimum recorded largest block 2 MiB; peak recorded guest 5817 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs3/crash-20261107-200953-eden_log.txt:1400` at app +49.249300s, last `Logs3/crash-20261107-200953-eden_log.txt:1444` at app +49.296680s.
- Skipped mesh draw warning: 29 stored lines; first `Logs3/crash-20261107-200953-eden_log.txt:2923` at app +76.162751s, last `Logs3/crash-20261107-200953-eden_log.txt:3160` at app +95.229397s.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- End: `Logs3/crash-20261107-200953.txt:3–8`, console time 2026-11-07 20:09:53; SIGSEGV (invalid memory access), code 2, address 0x0000008256a00000; 0x00000011ccd2b585 (outside the app's code: a system library or generated code); largest free block 1 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-201432, launch 1

- Startup context: app start approximately `2026-11-07 20:10:46` from the crash report's rounded age; game begins at `Logs3/crash-20261107-201432-eden_log.txt:3` at app +9.141163s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 133); core_constructed +0.565s (heap line 139); core_initialized +0.577s (heap line 141); game_loaded +2.578s (heap line 157); cpu_manager_ready +2.580s (heap line 160); first_frame_callback +30.252s (heap line 164).
- Initial cached shader compilation: 2209 pipelines in 11313 ms; `Logs3/crash-20261107-201432-stderr.log:135`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs3/crash-20261107-201432-stderr.log:95`: largest 11356 MiB, guest 170 MiB, short=0; last `Logs3/crash-20261107-201432-stderr.log:1665`: largest 146 MiB, guest 6304 MiB, short=1. Minimum recorded largest block 144 MiB; peak recorded guest 6304 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs3/crash-20261107-201432-eden_log.txt:1404` at app +49.394765s, last `Logs3/crash-20261107-201432-eden_log.txt:1448` at app +49.439714s.
- Skipped mesh draw warning: 34 stored lines; first `Logs3/crash-20261107-201432-eden_log.txt:2918` at app +75.092079s, last `Logs3/crash-20261107-201432-eden_log.txt:4496` at app +222.114215s.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- Over-budget image allocation warning: 27 stored lines; first `Logs3/crash-20261107-201432-eden_log.txt:4488` at app +221.828623s, last `Logs3/crash-20261107-201432-eden_log.txt:4544` at app +226.013789s.
- Unbacked sparse-image creation fallback: 13 stored lines; first `Logs3/crash-20261107-201432-eden_log.txt:4503` at app +223.572589s, last `Logs3/crash-20261107-201432-eden_log.txt:4543` at app +226.012358s.
- End: `Logs3/crash-20261107-201432.txt:3–8`, console time 2026-11-07 20:14:32; SIGSEGV (invalid memory access), code 1, address 0x000000000002b6f0; eboot+0x229fcc3; largest free block 0 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-201818, launch 1

- Startup context: app start approximately `2026-11-07 20:15:32` from the crash report's rounded age; game begins at `Logs3/crash-20261107-201818-eden_log.txt:3` at app +9.167876s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 131); core_constructed +0.600s (heap line 137); core_initialized +0.612s (heap line 139); game_loaded +2.618s (heap line 155); cpu_manager_ready +2.621s (heap line 158); first_frame_callback +28.083s (heap line 162).
- Initial cached shader compilation: 1555 pipelines in 8708 ms; `Logs3/crash-20261107-201818-stderr.log:133`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs3/crash-20261107-201818-stderr.log:95`: largest 11354 MiB, guest 172 MiB, short=0; last `Logs3/crash-20261107-201818-stderr.log:637`: largest 2 MiB, guest 6110 MiB, short=1. Minimum recorded largest block 2 MiB; peak recorded guest 6186 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs3/crash-20261107-201818-eden_log.txt:1368` at app +47.148240s, last `Logs3/crash-20261107-201818-eden_log.txt:1412` at app +47.197287s.
- Skipped mesh draw warning: 31 stored lines; first `Logs3/crash-20261107-201818-eden_log.txt:2481` at app +72.667443s, last `Logs3/crash-20261107-201818-eden_log.txt:3400` at app +153.835131s.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- Over-budget image allocation warning: 32 stored lines; first `Logs3/crash-20261107-201818-eden_log.txt:3409` at app +154.540081s, last `Logs3/crash-20261107-201818-eden_log.txt:3446` at app +155.195495s.
- Hang-watch warning: 40 stored lines; first `Logs3/crash-20261107-201818-eden_log.txt:3567` at app +158.773189s, last `Logs3/crash-20261107-201818-eden_log.txt:3651` at app +163.787622s.
- End: `Logs3/crash-20261107-201818.txt:3–8`, console time 2026-11-07 20:18:18; SIGSEGV (invalid memory access), code 1, address 0x0000000000028270; eboot+0x229fcc3; largest free block 2 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-202529, launch 1

- Startup context: app start approximately `2026-11-07 20:18:56` from the crash report's rounded age; game begins at `Logs3/crash-20261107-202529-eden_log.txt:3` at app +9.198198s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 128); core_constructed +0.600s (heap line 134); core_initialized +0.612s (heap line 136); game_loaded +2.619s (heap line 152); cpu_manager_ready +2.621s (heap line 155); first_frame_callback +28.853s (heap line 159).
- Initial cached shader compilation: 1596 pipelines in 9509 ms; `Logs3/crash-20261107-202529-stderr.log:133`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs3/crash-20261107-202529-stderr.log:95`: largest 11356 MiB, guest 170 MiB, short=0; last `Logs3/crash-20261107-202529-stderr.log:1548`: largest 142 MiB, guest 6553 MiB, short=1. Minimum recorded largest block 66 MiB; peak recorded guest 6553 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs3/crash-20261107-202529-eden_log.txt:1351` at app +47.920619s, last `Logs3/crash-20261107-202529-eden_log.txt:1395` at app +47.972818s.
- Skipped mesh draw warning: 32 stored lines; first `Logs3/crash-20261107-202529-eden_log.txt:3817` at app +240.335571s, last `Logs3/crash-20261107-202529-eden_log.txt:5385` at app +388.049136s.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- Over-budget image allocation warning: 32 stored lines; first `Logs3/crash-20261107-202529-eden_log.txt:5109` at app +361.238271s, last `Logs3/crash-20261107-202529-eden_log.txt:5407` at app +392.279387s.
- Unbacked sparse-image creation fallback: 9 stored lines; first `Logs3/crash-20261107-202529-eden_log.txt:5388` at app +391.373288s, last `Logs3/crash-20261107-202529-eden_log.txt:5433` at app +393.067900s.
- Hang-watch warning: 20 stored lines; first `Logs3/crash-20261107-202529-eden_log.txt:5413` at app +393.029823s, last `Logs3/crash-20261107-202529-eden_log.txt:5432` at app +393.043280s.
- End: `Logs3/crash-20261107-202529.txt:3–8`, console time 2026-11-07 20:25:29; SIGSEGV (invalid memory access), code 2, address 0x000000105ca00000; 0x00000008000a3fd5 (outside the app's code: a system library or generated code); largest free block 2 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-203446, launch 1

- Startup context: app start approximately `2026-11-07 20:30:20` from the crash report's rounded age; game begins at `Logs4/crash-20261107-203446-eden_log.txt:11` at app +12.277626s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 128); core_constructed +0.608s (heap line 134); core_initialized +0.620s (heap line 136); game_loaded +3.228s (heap line 152); cpu_manager_ready +3.230s (heap line 155); first_frame_callback +42.348s (heap line 159).
- Initial cached shader compilation: 1556 pipelines in 9810 ms; `Logs4/crash-20261107-203446-stderr.log:134`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs4/crash-20261107-203446-stderr.log:95`: largest 11356 MiB, guest 170 MiB, short=0; last `Logs4/crash-20261107-203446-stderr.log:697`: largest 1605 MiB, guest 5180 MiB, short=0. Minimum recorded largest block 1605 MiB; peak recorded guest 5252 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs4/crash-20261107-203446-eden_log.txt:52233` at app +75.130682s, last `Logs4/crash-20261107-203446-eden_log.txt:52485` at app +75.251211s.
- Skipped mesh draw warning: 28 stored lines; first `Logs4/crash-20261107-203446-eden_log.txt:145331` at app +135.758690s, last `Logs4/crash-20261107-203446-eden_log.txt:321624` at app +263.721523s.
- Native graphics failure debug line: 6,907 stored lines; first `Logs4/crash-20261107-203446-eden_log.txt:145335` at app +135.760078s, last `Logs4/crash-20261107-203446-eden_log.txt:322745` at app +264.869911s.
- Over-budget image allocation warning: 21 stored lines; first `Logs4/crash-20261107-203446-eden_log.txt:322834` at app +265.226503s, last `Logs4/crash-20261107-203446-eden_log.txt:322862` at app +265.308280s.
- End: `Logs4/crash-20261107-203446.txt:3–8`, console time 2026-11-07 20:34:46; SIGSEGV (invalid memory access), code 1, address 0x000000000002c560; eboot+0x229fcc3; largest free block 2 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-203836, launch 1

- Startup context: app start approximately `2026-11-07 20:35:25` from the crash report's rounded age; game begins at `Logs4/crash-20261107-203836-eden_log.txt:3` at app +43.244244s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 127); core_constructed +0.628s (heap line 133); core_initialized +0.640s (heap line 135); game_loaded +2.624s (heap line 151); cpu_manager_ready +2.626s (heap line 154); first_frame_callback +27.082s (heap line 158).
- Initial cached shader compilation: 1488 pipelines in 8508 ms; `Logs4/crash-20261107-203836-stderr.log:133`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs4/crash-20261107-203836-stderr.log:95`: largest 11356 MiB, guest 170 MiB, short=0; last `Logs4/crash-20261107-203836-stderr.log:434`: largest 659 MiB, guest 5429 MiB, short=1. Minimum recorded largest block 659 MiB; peak recorded guest 5694 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs4/crash-20261107-203836-eden_log.txt:1352` at app +80.124390s, last `Logs4/crash-20261107-203836-eden_log.txt:1396` at app +80.169732s.
- Skipped mesh draw warning: 28 stored lines; first `Logs4/crash-20261107-203836-eden_log.txt:2388` at app +109.620573s, last `Logs4/crash-20261107-203836-eden_log.txt:3042` at app +182.946150s.
- Native graphics failure debug line: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.
- Over-budget image allocation warning: 32 stored lines; first `Logs4/crash-20261107-203836-eden_log.txt:3029` at app +181.687313s, last `Logs4/crash-20261107-203836-eden_log.txt:3079` at app +184.822721s.
- Unbacked sparse-image creation fallback: 164 stored lines; first `Logs4/crash-20261107-203836-eden_log.txt:3055` at app +184.437987s, last `Logs4/crash-20261107-203836-eden_log.txt:3533` at app +190.768982s.
- Hang-watch warning: 20 stored lines; first `Logs4/crash-20261107-203836-eden_log.txt:3125` at app +187.331783s, last `Logs4/crash-20261107-203836-eden_log.txt:3144` at app +187.345263s.
- End: `Logs4/crash-20261107-203836.txt:3–8`, console time 2026-11-07 20:38:36; SIGSEGV (invalid memory access), code 1, address 0x0000000000022930; eboot+0x229fcc3; largest free block 0 MiB. The precise originating corruption is not established by chronology alone.

### crash-20261107-205143, launch 1

- Startup context: app start approximately `2026-11-07 20:41:03` from the crash report's rounded age; game begins at `Logs5/crash-20261107-205143-eden_log.txt:11` at app +10.901371s. This approximate wall time is only a subtraction in the console's timebase.
- Core/graphics sequence relative to the heap session-start: session_start +0.000s (heap line 129); core_constructed +1.283s (heap line 135); core_initialized +1.525s (heap line 137); game_loaded +9.031s (heap line 153); cpu_manager_ready +9.076s (heap line 156); first_frame_callback +48.760s (heap line 160).
- Initial cached shader compilation: 1138 pipelines in 7395 ms; `Logs5/crash-20261107-205143-stderr.log:135`. Live shader compilation can still continue later.
- Memory samples (stderr line order): first `Logs5/crash-20261107-205143-stderr.log:95`: largest 11358 MiB, guest 172 MiB, short=0; last `Logs5/crash-20261107-205143-stderr.log:3396`: largest 412 MiB, guest 5295 MiB, short=1. Minimum recorded largest block 0 MiB; peak recorded guest 5360 MiB. No wall-clock timestamp is fabricated for these snapshots.
- Compute translation rejection: 10 stored lines; first `Logs5/crash-20261107-205143-eden_log.txt:51335` at app +81.587133s, last `Logs5/crash-20261107-205143-eden_log.txt:51598` at app +81.708425s.
- Skipped mesh draw warning: 28 stored lines; first `Logs5/crash-20261107-205143-eden_log.txt:162599` at app +162.815784s, last `Logs5/crash-20261107-205143-eden_log.txt:537316` at app +632.637575s.
- Native graphics failure debug line: 20,355 stored lines; first `Logs5/crash-20261107-205143-eden_log.txt:162600` at app +162.816471s, last `Logs5/crash-20261107-205143-eden_log.txt:538107` at app +639.651717s.
- Over-budget image allocation warning: 32 stored lines; first `Logs5/crash-20261107-205143-eden_log.txt:340099` at app +326.936361s, last `Logs5/crash-20261107-205143-eden_log.txt:363920` at app +395.972888s.
- Unbacked sparse-image creation fallback: 6 stored lines; first `Logs5/crash-20261107-205143-eden_log.txt:349400` at app +342.898386s, last `Logs5/crash-20261107-205143-eden_log.txt:354157` at app +376.372090s.
- Hang-watch warning: 66 stored lines; first `Logs5/crash-20261107-205143-eden_log.txt:350286` at app +352.801252s, last `Logs5/crash-20261107-205143-eden_log.txt:538091` at app +639.443748s.
- End: `Logs5/crash-20261107-205143.txt:3–8`, console time 2026-11-07 20:51:43; SIGSEGV (invalid memory access), code 1, address 0x0000000000031f48; eboot+0x229fcc3; largest free block 3 MiB. The precise originating corruption is not established by chronology alone.
