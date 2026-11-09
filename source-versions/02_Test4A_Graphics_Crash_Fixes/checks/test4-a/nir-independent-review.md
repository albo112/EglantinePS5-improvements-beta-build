# Test4-A NIR allocation-failure review

The reviewed production patch is `tools/radv-patches/test4a-01-nir-copy-prop-oom.patch` (SHA-256 `c46f5edadf5b6296ae99849ca5c7b270e97b947472b09668e0c5bbfc93b88a89`). No production implementation was changed by this independent review.

## Crash evidence

Six of the eight new crash summaries name `VkPipelineBuilder` and fault at `eboot+0x229fcc3`: Logs3 20:05:04, 20:14:32 and 20:18:18; Logs4 20:34:46 and 20:38:36; Logs5 20:51:43. The retained Test3 ELF SHA-256 is `930886ee0b0301169b3977f830954702c7b55da7afa5dc1fbc6260b300458816`; its text size `0x2ab2bb0` matches all eight summaries. An installed-console executable hash is unavailable, so this is a size/revision match rather than cryptographic proof of the installed image.

The ELF `.text` VMA is zero: symbolication uses `0x229fcc3`, without adding the runtime load base. The exact instruction is `movq %rdx,0xa0(%rax,%rcx)`, in `copy_entry_create`, `nir_opt_copy_prop_vars.c:419`. All six register dumps have RAX=0; RCX+0xa0 matches each reported fault address. The original `util_dynarray_append` expands to an unchecked copy into the result of a fallible grow. This establishes the immediate null-allocation failure boundary. It does not prove which earlier consumers exhausted or fragmented memory, or rule out earlier corruption elsewhere.

## Implementation review

- Checked growth returns NULL without copying. Both direct load creation and the store/copy callers of `get_entry_and_kill_aliases` stop before dereferencing a failed entry.
- `out_of_memory` is zero initialized. Control-flow traversal stops on that flag; then/else branches clear temporary state before returning. Existing root/loop cleanup remains available. Completed prior rewrites are retained and metadata follows the existing `state.progress` result.
- Initial ralloc-context failure returns before mutation. Initial linear-context failure frees the ralloc parent and returns before mutation. Later cleanup frees the pass parent even after partial progress.
- The diagnostic uses atomic increments and emits at most eight lines per process. This bound was reviewed in code; repeated/concurrent eight-line saturation was not separately runtime tested.
- No exception, signal interception, or longjmp crosses driver frames. Shader IR and actual draws remain enabled.
- The narrow mesh-flag patch consistently treats `EDEN_NX2_NO_MESH=0` as false in rasterizer, pipeline prebuild, and generated RADV device predicates. The file-based opt-out remains. This restores intended configuration semantics; actual mesh rendering cost and correctness still need hardware testing.

No blocking correctness defect was found in the reviewed diff. Remaining allocation sites in this pass (copy structures/arrays, dereference paths, hash growth and cloning) are outside this bounded patch. Other Mesa passes and shader transformations can also allocate. This patch is not a general guarantee that compilation succeeds under exhaustion.

## Host regression evidence

The fixture uses the real Mesa NIR builder, validator, pass, lowering, constant folding and cleanup, compiled with AddressSanitizer and UndefinedBehaviorSanitizer. It covers store, direct load, and copy_deref entry creation; flat and nested-if control flow; normal allocation, copy-array growth failure, initial ralloc-context failure, and initial linear-context failure.

`ninja -C build src/compiler/nir/test4a_nir_oom src/compiler/nir/test4a_nir_oom_baseline -j1` completed with exit 0. The baseline target compiles the immutable original Test3 driver pass (source SHA-256 `35cbb1a29df5676ddc5a7c6ea54896d393f22d2148fd2d147c33c8f0273730d8`) ahead of the patched NIR archive. It does not replace the active host or native implementation.

- Patched: **24/24 cases exit 0**. NIR validates before/after injection and after reduction; metadata is valid; output remains 2087; output stores remain one for flat/two for nested. All six growth failures report genuine prior optimization progress. All twelve initial-context failures leave printed IR unchanged. Sanitizers report no violation or leak.
- Baseline: **6/6 normal cases exit 0; 18/18 injected cases fail as expected**. Six growth failures stop at the original unchecked NULL memcpy on line 419. Stack traces identify direct-load caller line 1221, store/helper line 1316/648, and copy/helper line 1398/648. Initial-context failures produce assertion or sanitizer failures, not uniformly SIGSEGVs.
- Both caller runners return structured status `pass`, exit 0, because the baseline runner explicitly expects negative-control failures. See `nir-oom-callers-before.json`, `nir-oom-callers-after.json` and their referenced logs. Original eight-case receipts remain preserved.

The host fixtures and their Meson additions are test-only. Do not copy the whole host Mesa tree into a native driver export. Native integration uses the old eleven driver patches followed by the new production overlay.

## Limits

These results confirm allocation-failure handling and shader semantics for the focused host cases. PS5 execution, crash-free duration, all Zelda shaders, loop-specific fault injection, restored geometry/textures/brightness, cold shader-cache behavior, stalls, flashes, and FPS remain unverified by this test. The user must test the resulting native package before those outcomes can be claimed.
