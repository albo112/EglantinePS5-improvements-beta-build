# Test4-A validation report

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

## Completed checks

- Four original archives: CRC/integrity and extraction exit 0; originals rehashed unchanged. Extracted 218 files into new directories.
- Exact Test3 reconstruction: exit 0; 261 overlays applied, 5,684 source-snapshot files compared, zero missing/changed files at baseline. This earlier snapshot includes nested external/submodule contents.
- All seven supplied verification scripts and the inherited fence contract: exit 0, with their original script bytes retained. Final post-change receipt: 8 recorded final commands, all exit **0**.
- NO_MESH regression: baseline exit 1; patched eight-case actual-source check exit 0 under ASan/UBSan.
- NIR allocation regression: baseline exit 1, two normal cases pass and six injected-OOM cases fail; patched 8-case real-NIR check exit 0 under ASan/UBSan. Validator, metadata, semantic result 2087 and cleanup pass. An additional 24-case caller-path receipt reports pass / exit 0.
- Transient image refusal: baseline exit 1; patched check exit 0, 16 host cases using actual source branches and simulated device allocation. Ownership, refusal backoff, recovered upload, both creation callers and sparse-policy preservation pass.
- Bounded draw failures: both checks exit 0. One extracted counter produces 40 warnings for 32,768 failed calls across eight threads; the two-path template check produces 80 warnings for 65,536 total failures across eight threads. Production counters are per `PrepareDraw` template instantiation (direct and indirect paths separately), not process-global. The NIR diagnostic cap is separately process-global at eight messages. The crash-report suite was rerun and passed exit 0.
- Crash-report suite: host/native-mock suite exit 0, including global heap failure context and safely probed fault instruction output.
- Independent pipeline address check: saved ELF hash matched; all six crash register equations and symbol/disassembly matches passed, exit 0.

| Supplied / inherited check | Exit |
| --- | ---: |
| `check-display-mode.py` | 0 |
| `check-failed-compute-module.py` | 0 |
| `check-gpu-memory-ranges.py` | 0 |
| `check-pipeline-allocation.py` | 0 |
| `check-upload-allocation-guard.py` | 0 |
| `check-zelda-accuracy-profile.py` | 0 |
| `check-zelda-shadow.py` | 0 |
| `check-fence-requirements.py` | 0 |

The range guard test uses the already-applied source with an explicit 0429 patch path. It reverses only scratch copies to reproduce the old invalid-address behavior; the real tree is not reverted. Other supplied checks exercise display selection, failed-module cleanup, pipeline allocation error handling, upload allocation guards, accuracy settings and depth SPIR-V validation.

## Expected failing-before evidence

The mesh test intentionally failed before the correction because value 0 still activated mesh skipping in the rasterizer, pre-build gate and driver policy. This was a behavioral regression result, not a segmentation fault hidden by the test. The patched test preserves supported fallback/extension behavior and the unrelated game exception.

The initial NIR test reproduced the null copy-entry OOM boundary without hiding it behind a segmentation-fault handler. Patched tests preserve valid earlier transformations and shader semantics under controlled allocation failure. The image regression checks failed-slot cleanup and backed retry without inventing a physical GPU allocation test. Earlier Test4 prototype results are not used as Test4-A evidence.

## Additional project checks and retained attempts

Source-stage result: `fail` / exit 1; 1/2 commands exit 0. Native-stage result: `pass` / exit 0; 8/8 commands exit 0. Fresh 264-overlay reproduction: Pass / exit 0; all 264 ordered patches replayed, and 4,800 core Git-listed tracked/unignored files match byte for byte with no missing, extra or changed files (`overlay-replay.json`). This comparison excludes nested external/submodule contents included in the earlier 5,684-file Test3 snapshot.

Native source provenance: Pass / exit 0: ten modified/retained core files match the native cache copies byte for byte. Generated renderer/pipeline mesh predicates, bounded draw diagnostics and texture OOM handling are checked; compile commands reference the three generated units and current main/crash-report sources, with other project-cache source paths excluded. The recorded 46 compiled SlotVector dependencies all use the native exception-safe recovery header, with zero original-header dependencies. Regenerating that header through the actual CMake recovery script gives an exact byte match. All 30 current input hashes, including the original SlotVector header, recovery generator and derived header, are rechecked at packaging. This establishes build-input provenance, not PS5 rendering or runtime validation.

| Stage | Check | Exit | Log |
| --- | --- | ---: | --- |
| Source | `check-heap-growth.py` | 1 | `check-heap-growth.py.log` |
| Source | `check-performance-settings.py` | 0 | `check-performance-settings.py.log` |
| Native | `check-staging-pressure.py` | 0 | `check-staging-pressure.py.log` |
| Native | `check-integer-buffer-clear.py` | 0 | `check-integer-buffer-clear.py.log` |
| Native | `check-radv-native.py` | 0 | `check-radv-native.py.log` |
| Native | `check-native-gpu-thread.py` | 0 | `check-native-gpu-thread.py.log` |
| Native | `check-gpu-sync-stop.py` | 0 | `check-gpu-sync-stop.py.log` |
| Native | `check-gpu-producer-stop.py` | 0 | `check-gpu-producer-stop.py.log` |
| Native | `check-transient-images.py` | 0 | `check-transient-images.py.log` |
| Native | `check-sparse-header.py` | 0 | `check-sparse-header.py.log` |

The optional full heap ThreadSanitizer stress test **did not complete** on this host. The first attempt completed both checked UBSan heap modes, then its ThreadSanitizer subprocess was killed with exit -9. The host kernel identified memory exhaustion during that test (about 3.5 GiB consumed). The retry used `TSAN_OPTIONS=memory_limit_mb=1536`; both checked UBSan modes passed again, but the ThreadSanitizer subprocess raised `TimeoutExpired` after **900 seconds**. The final heap check remains **exit 1**, and `project-checks-source.json` remains **status fail / exit 1**; the performance-settings check is exit 0. These outcomes are retained rather than converted into passes.

`host-heap-test-limits.json` records why the optional full TSan stress is unavailable. Packaging may acknowledge only this specific host limitation while retaining the failed receipts/logs; all fix-specific tests, supplied checks and eight native project checks must still pass. This does not establish heap race freedom or reproduce a PS5 heap crash. The heap implementation and allocation limits were not changed for Test4-A; the new crash-report snapshot reader is covered by the passing crash-report suite.

The first sparse-header invocation lacked its required native build-directory argument and failed with `IndexError`. The runner was corrected to pass the independent cache's `native-local` build and that check moved to the native stage. An invocation error is not a passed regression check. Both original first-attempt logs and receipt are retained; the current row above gives the actual corrected outcome.

The first native check batch had six passes and two host harness compilation failures. The sync harness lacked the current scalar/logging/back-thread stand-ins; the producer harness required a completion header/API absent from the pinned source. Both harnesses now exercise the actual generated implementation. Original failure logs and `project-checks-native-first-attempt.json` are retained, and the final native table records their fresh rerun results. No runtime source or native binary was changed for these test corrections.

## Final release gates

| Gate | Current state |
| --- | --- |
| Native PS5 release build | Completed receipt reports exit **0**, with unchanged source hashes during the build. |
| Final post-change command set | 8 recorded final commands, all exit **0**. |
| Optional full heap TSan stress | Incomplete: first host OOM, retry timed out after 900 s; heap check remains exit 1. Checked UBSan heap modes passed. |
| Executable/package inventory, CRC, permissions, metadata and hashes | Final outer-ZIP CRC, manifests, file permissions and SHA-256 hashes are recorded in the adjacent `Zelda-Test4-A-Verification.json` after packaging. Validate that receipt before installing. |
| Matching Test4-A symbols retained | The matching ELF path/hash is recorded in the adjacent final verification receipt. |
| Actual PS5 run | Not performed |
| Controlled Test3/Test4-A FPS/visual comparison | Not performed |
| All-cache-empty cold launch | Not performed |
| Long crash-free gameplay duration | Not performed |

The upstream CI route uses `EDEN_SKIP_SOURCE_CHECKS=1`. Running the supplied and relevant focused checks separately does not equal running every legacy upstream source check. A native compile also cannot validate physical PS5 allocation, GPU scheduling, HDR/SDR output or gameplay correctness.

No Test4-A FPS result or elimination of all crashes is claimed. Keep original logs, original packages and matching Test3 symbols. Final checks must be rerun after the last code or documentation mutation.
