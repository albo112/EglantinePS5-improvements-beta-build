# Test4-A supplied-log coverage and session timelines

Read all **53 files, 130,434,078 bytes and 910,036 lines** from Logs3, Logs4 and Logs5. There are eight complete crash groups and nine game launches. Three empty `result.tsv` files were read and inventoried. Every input file has a SHA-256 in `log-coverage.json`.

All times below remain exactly as the console logged them. No timezone or UTC conversion is inferred. App ages in crash reports are rounded seconds; final-session ages therefore are approximate. Heap phase offsets use their own monotonic session-start. Untimestamped stderr/cache/memory records are referenced by line order, without invented clock times.

The eight reports name version `01.219.020`, text size `0x2ab2bb0`. The preserved Test3 ELF independently hashes to `930886ee0b0301169b3977f830954702c7b55da7afa5dc1fbc6260b300458816` and its `.text` is exactly `0x2ab2bb0`. The user-supplied Test3 ZIP hashes to `55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7`, matching the saved Test3 package. This supports the matching-symbol choice; there is no on-console executable hash in these logs.

## Fatal reports

| Report | Faulting thread / location | App age | Final game age | Largest free / heap |
| --- | --- | ---: | ---: | ---: |
| `Logs3/crash-20261107-200504.txt` | VkPipelineBuilder / `eboot+0x229fcc3` | 401 s | 129.996 s | 2 / 1696 MiB |
| `Logs3/crash-20261107-200953.txt` | CPUCore_3 / `0x00000011ccd2b585 (outside the app's code: a system library or generated code)` | 103 s | 93.861 s | 1 / 1408 MiB |
| `Logs3/crash-20261107-201432.txt` | VkPipelineBuilder / `eboot+0x229fcc3` | 226 s | 216.859 s | 0 / 1472 MiB |
| `Logs3/crash-20261107-201818.txt` | VkPipelineBuilder / `eboot+0x229fcc3` | 166 s | 156.832 s | 2 / 1664 MiB |
| `Logs3/crash-20261107-202529.txt` | not named / `0x00000008000a3fd5 (outside the app's code: a system library or generated code)` | 393 s | 383.802 s | 2 / 1440 MiB |
| `Logs4/crash-20261107-203446.txt` | VkPipelineBuilder / `eboot+0x229fcc3` | 266 s | 253.722 s | 2 / 1440 MiB |
| `Logs4/crash-20261107-203836.txt` | VkPipelineBuilder / `eboot+0x229fcc3` | 191 s | 147.756 s | 0 / 1152 MiB |
| `Logs5/crash-20261107-205143.txt` | VkPipelineBuilder / `eboot+0x229fcc3` | 640 s | 629.099 s | 3 / 1632 MiB |

**Six unique reports** have `SIGSEGV` on `VkPipelineBuilder` at **exactly `eboot+0x229fcc3`**: 20:05:04, 20:14:32, 20:18:18, 20:34:46, 20:38:36 and 20:51:43. They are not six different offsets. The remaining reports are a generated CPU write at 20:09:53 and an unnamed-thread/system-library write at 20:25:29. All eight report only 0–3 MiB as the largest free block. This establishes severe pool pressure, not the original cause of each fault. Scanned stack values marked `?` are not validated call frames.

## Each game launch

| Capture / launch | Eden begin (app seconds) | Cached pipeline records / preload | First frame after heap session-start | Recorded end / duration | Logged frame median |
| --- | ---: | ---: | ---: | --- | ---: |
| `crash-20261107-200504` #1 | 12.894099 | 2405 / 11.513 s | 29.503 s | normal return to menu; 51.983 s | 57.332 FPS (3 samples) |
| `crash-20261107-200504` #2 | 271.004094 | 2405 / 11.111 s | 29.939 s | fatal report; 129.996 s | 30.259 FPS (19 samples) |
| `crash-20261107-200953` #1 | 9.138919 | 2209 / 11.411 s | 30.088 s | fatal report; 93.861 s | 54.339 FPS (12 samples) |
| `crash-20261107-201432` #1 | 9.141163 | 2209 / 11.313 s | 30.252 s | fatal report; 216.859 s | 12.810 FPS (36 samples) |
| `crash-20261107-201818` #1 | 9.167876 | 1555 / 8.708 s | 28.083 s | fatal report; 156.832 s | 21.983 FPS (23 samples) |
| `crash-20261107-202529` #1 | 9.198198 | 1596 / 9.509 s | 28.853 s | fatal report; 383.802 s | 59.366 FPS (69 samples) |
| `crash-20261107-203446` #1 | 12.277626 | 1556 / 9.810 s | 42.348 s | fatal report; 253.722 s | 11.784 FPS (39 samples) |
| `crash-20261107-203836` #1 | 43.244244 | 1488 / 8.508 s | 27.082 s | fatal report; 147.756 s | 32.639 FPS (22 samples) |
| `crash-20261107-205143` #1 | 10.901371 | 1138 / 7.395 s | 48.760 s | fatal report; 629.099 s | 1.100 FPS (97 samples) |

The first app has a normal return to the menu at app +64.877283 s, followed by another launch at +271.004094 s. Its 401-second app age is **not** uninterrupted gameplay. Session identifier `1` is reused; launch ordinals above distinguish the two. All nine launches preload nonempty emulator pipeline caches (1,138–2,405 records); driver/Mesa binary-cache warmth is not established, and **none is a controlled all-caches-empty cold-start test**. The loader count does not prove every cached pipeline built successfully. FPS figures are historic Test3 log windows in unrecorded/different scenes and are not a controlled public/Test3/Test4-A benchmark.

## Ordered evidence for each launch

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

## Frequency and meaning

These are **stored log-line counts**, not counts of distinct GPU objects, shader programs, physical hangs, or every failed draw. Some source warnings are rate limited, and current heap/stderr files are residual startup snapshots rather than additional gameplay trials.

| Verified logged condition | Stored lines | Source named in the logs | Interpretation / limit |
| --- | ---: | --- | --- |
| `Draw skipped (EDEN_NX2_NO_MESH)` | 244 | `vulkan_rasterizer.cpp`, draw failure callback | The profile says `NO_MESH=0`, yet the source tests environment-variable presence. See configuration finding below. Warning deduplication makes this smaller than total skipped draws. |
| `Native graphics draw failed; refusing submission completion` | 27,262 | `vulkan_rasterizer.cpp`, native draw completion guard | Debug messages occur in only two Debug-heavy captures; cannot compare raw rates with other captures. Refusal is an explicit effect of an unsuccessful native draw, not by itself a Vulkan fence timeout. |
| `Native compute shader rejected` | 90 | `kepler_compute.cpp:DispatchNativeCompute` | All observed rejections name native matrix multiplication excluded by `EDEN_NX2_TENSOR_ONLY`; 10 messages per launch. Correctness/fallback requires source translation analysis. |
| `Native QMD failed: native shader dispatch required` | 144 | `kepler_compute.cpp:ProcessNativeMethod` | 16 stored messages per launch; not every one has a separately logged new shader rejection. |
| `Uncached storage pointer classification` | 111 | `vk_pipeline_cache_cost.cpp:CreateGraphicsPipeline/CreateComputePipeline` | Occurs while rebuilding cached resources; this alone does not establish failure of every later live pipeline. |
| `All 32 storage buffer bindings taken` | 63 | `global_memory_to_storage_buffer_pass.cpp:GlobalMemoryToStorageBufferPass` | Seven warnings per launch; raising a binding constant is not a proven supported fix. |
| Over-budget image allocation proceeds | 208 | `vulkan_memory_allocator.cpp:CreateImage`, log line 374 | Observed allocation-policy warning, not an exact unique-image count; many captures hit 32 such warnings. |
| `using an unbacked sparse image` from `CreateImage` | 192 | `vulkan_memory_allocator.cpp:CreateImage`, log line 422 | Distinct from 308 total unbacked-image mentions, which also include render-target/view use. Relevant to missing resources under pressure. |
| `Direct allocation failed` | 5 | Untimestamped stderr, native direct-memory allocator | Recorded request sizes/return codes are in the original line; these are not all allocation failures. |
| Hang-watch warnings | 146 | `gpu_split.cpp:ReportBack`, `vulkan_scheduler.cpp:ReportFreeze` | Shows blocked back/worker state, including waiting for a GPU tick or pipeline build. A warning snapshot is not proof of a missing barrier or physical GPU hang. |
| Actual `timed out` messages / timeout warning-error lines | 0 / 0 | None matched these precise conditions | The 223 broad timeout mentions are API/configuration arguments such as `ChannelSetTimeout` and socket `Poll(timeout=0)`, not failures. |

## Configuration and collection findings

- All nine title environment blocks use the **Faster** profile: `EDEN_NX2_RADV_MESH_COMPUTE_LONE=0`, `EDEN_NX2_QUERY_KEEP_PENDING=0`, `EDEN_NX2_NO_MESH=0`, all-stage native tables and paired pointers enabled, pipeline workers 4, safe-memory override 1, `TENSOR_ONLY=c00`. No Prettier-profile gameplay run is present in this archive.
- Independent read-only source inspection found `static const bool no_mesh_always{std::getenv("EDEN_NX2_NO_MESH") != nullptr};` in `Eglantine/src/video_core/renderer_vulkan/vk_rasterizer.cpp`. A value of `0` still activates that flag. The later mesh gate logs this exact skip reason. The warning callback deduplicates `(vs, ps, reason)` pairs (maximum 64), so logged skip warnings are not total skip counts. Correcting value parsing is a concrete source target; this audit did not edit it or prove visual restoration.
- The native draw scope-exit sets `native_execution_failed` when `!submitted` and logs submission-completion refusal. This directly connects skipped/failed native draws with those debug refusals; it does not establish all downstream graphics causes.
- All logged launch settings select CPU Auto, Default DMA, cache invalidation enabled, unsafe CPU/DMA off, async shaders off, fast GPU on, reactive flushing off. Earlier unsafe-setting advice does not diagnose these new sessions.
- Logs4/20:34:46 contains **319,118 Debug lines** and Logs5/20:51:43 **531,699 Debug lines**. The other Eden crash captures contain no Debug-tagged lines. Log volume and different scenes/settings make FPS comparisons uncontrolled; logging overhead must be measured rather than assumed negligible.
- The recorded app folder is **`/system_ex/app/PPSA98515`**, even though `/data/homebrew/PPSA98515` also exists. Example: `Logs5/boot-trace.txt:8–11` and every captured stderr filesystem-access line. Installing only into the other folder can leave a different selected binary/profile active. Verify the actual selected app path after installation.
- Only the three empty TSV files are byte-identical whole-file duplicates. Other current/previous traces overlap in event history or are restart remnants; they are not additional independent gameplay trials.

## What remains unverified by this log audit

The faulting allocator/compiler function and original corruption cause require exact symbolication and source tracing. Missing trees/textures, brightness and flashes have no synchronized image/video reference here. No new build, fixed FPS, crash-free run, cold-cache behavior, public-release benchmark or PS5 Test4-A outcome is claimed. `session-timelines.json` preserves every observed stage and memory snapshot; `log-file-evidence.json` preserves exact examples, source frequencies, log levels and category counts.
