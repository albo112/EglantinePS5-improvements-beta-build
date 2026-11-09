"""Write evidence-based Test4-A handoff reports; does not build or package anything."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess

scratch = Path(__file__).resolve().parent
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--evidence-only', action='store_true',
                    help='Use the prior source-file inventory; do not contact WSL or certify current source hashes.')
parser.add_argument('--for-package', action='store_true',
                    help='Require the native build to pass and point final ZIP integrity to the adjacent receipt.')
args = parser.parse_args()
reports = scratch / 'reports'
reports.mkdir(exist_ok=True)
root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
output = scratch.parents[1] / 'outputs'

def read_json(path, default=None):
    return json.loads(path.read_text(encoding='utf-8-sig')) if path.exists() else default

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()

def windows_path(name):
    name = name.replace('\\', '/')
    return Path('/mnt/c' + name[2:]) if os.name != 'nt' and name.lower().startswith('c:/') else Path(name)

inventory = read_json(scratch / 'input-inventory.json')
audit = read_json(scratch / 'log-audit-summary.json')
reconstruction = read_json(scratch / 'reconstruction.json')
before_mesh = read_json(scratch / 'no-mesh-boolean-before.json')
after_mesh = read_json(scratch / 'no-mesh-boolean-result.json')
supplied = read_json(scratch / 'supplied-checks-baseline.json')
before_nir = read_json(scratch / 'nir-oom-before.json')
after_nir = read_json(scratch / 'nir-oom-after.json')
caller_nir = read_json(scratch / 'nir-oom-callers-after.json')
before_image = read_json(scratch / 'image-refusal-before.json')
after_image = read_json(scratch / 'image-refusal-result.json')
diagnostics = read_json(scratch / 'diagnostics-checks.json')
build = read_json(scratch / 'native-build.json')
driver = read_json(scratch / 'driver-build.json')
final_checks = read_json(scratch / 'supplied-checks-final.json')
project_source = read_json(scratch / 'project-checks-source.json')
project_native = read_json(scratch / 'project-checks-native.json')
heap_limits = read_json(scratch / 'host-heap-test-limits.json')
native_provenance = read_json(scratch / 'native-source-provenance.json')
overlay_replay = read_json(scratch / 'overlay-replay.json')
certificate = read_json(output / 'Zelda-Test4-A-Verification.json')
assert len(inventory) == 4 and audit['files_read'] == 53 and audit['complete_crash_groups'] == 8
assert reconstruction['exit_code'] == 0 and reconstruction['compared_test3_source_files'] == 5684
assert before_mesh['exit_code'] == 1 and after_mesh['exit_code'] == 0
assert len(supplied) == 8 and all(item['exit_code'] == 0 for item in supplied)
assert before_nir['exit_code'] != 0 and after_nir['exit_code'] == 0
assert before_image['exit_code'] != 0 and after_image['exit_code'] == 0
assert diagnostics['exit_code'] == 0
for item in inventory:
    assert digest(windows_path(item['source'])) == item['archive_sha256'], item['source']

if args.evidence_only:
    previous = read_json(reports / 'report-status.json')
    changed = previous['changed_source_snapshot']
    new_core = ['0430-test4a-no-mesh-boolean.patch', '0431-test4a-bounded-draw-diagnostics.patch',
                '0432-test4a-transient-image-refusal.patch']
    new_driver = ['test4a-01-nir-copy-prop-oom.patch']
else:
    baseline = read_json(Path('/var/lib/eglantine-build/zelda-test4-baseline/test3-source-manifest.json'))
    changed = [name for name, expected in baseline['files'].items()
               if not (root / name).is_file() or digest(root / name) != expected]
    new_core = sorted(path.name for path in (root / 'tools/eglantine-patches').glob('043*.patch'))
    new_driver = sorted(path.name for path in (root / 'tools/radv-patches').glob('*.patch'))
actual_files = '\n'.join('- `' + name + '`' for name in sorted(changed)) or '- None.'
patch_list = '\n'.join('- `' + name + '`' for name in new_core + new_driver) or '- No additional overlays present.'
build_text = ('Completed receipt reports exit **0**, with unchanged source hashes during the build.'
              if build and build.get('exit_code') == 0 and build.get('source_unchanged_during_build') else
              f"Pending: native build state is `{build.get('status', 'unavailable') if build else 'unavailable'}`; "
              f"driver build state is `{driver.get('status', 'unavailable') if driver else 'unavailable'}`. "
              'No successful final native-build receipt was available for this report snapshot.')
checks_text = (f"{len(final_checks)} recorded final commands, all exit **0**."
               if final_checks and all(item['exit_code'] == 0 for item in final_checks) else
               'Pending: the final post-change command set has not been certified in this report snapshot.')
package_text = ('Package verification receipt reports **pass / exit 0**.'
                if certificate and certificate.get('status') == 'pass' else
                'Pending: no Test4-A package integrity receipt was available for this report snapshot.')
if args.for_package:
    assert not args.evidence_only
    assert build and build.get('status') == 'pass' and build.get('exit_code') == 0
    assert build.get('source_unchanged_during_build') is True
    package_text = ('Final outer-ZIP CRC, manifests, file permissions and SHA-256 hashes are recorded in '
                    'the adjacent `Zelda-Test4-A-Verification.json` after packaging. Validate that receipt before installing.')
symbol_text = ('The matching ELF path/hash is recorded in the adjacent final verification receipt.'
               if args.for_package else 'Pending final native artifact')
artifact_hash_text = ('See adjacent verification receipt' if args.for_package else 'Pending final package')
artifact_inventory_text = ('See adjacent verification receipt' if args.for_package else 'Pending final inventory')
native_cert_text = ('Native build passed; console validation remains unperformed.'
                    if build and build.get('exit_code') == 0 else 'Native/runtime certification pending.')
banner = ('> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging '
          'are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.\n\n')
nir_cases = len(after_nir['cases'])
image_cases = after_image['stdout'].count('PASS:')
nir_callers_text = (f"An additional {len(caller_nir['cases'])}-case caller-path receipt reports pass / exit 0."
                    if caller_nir and caller_nir.get('exit_code') == 0 else
                    'Additional caller-path coverage is pending its separate receipt.')
def project_summary(receipt):
    if not receipt:
        return 'Pending receipt.'
    return (f"`{receipt['status']}` / exit {receipt['exit_code']}; "
            f"{sum(item['exit_code'] == 0 for item in receipt['checks'])}/{len(receipt['checks'])} commands exit 0.")

project_rows = '\n'.join(f"| {stage} | `{item['check']}` | {item['exit_code']} | `{item['log']}` |"
                          for stage, receipt in [('Source', project_source), ('Native', project_native)]
                          if receipt for item in receipt['checks'])
replay_text = ('Pass / exit 0; all 264 ordered patches replayed, and 4,800 core Git-listed '
               'tracked/unignored files match byte for byte with no missing, extra or changed files '
               '(`overlay-replay.json`). This comparison excludes nested external/submodule contents '
               'included in the earlier 5,684-file Test3 snapshot.'
               if overlay_replay and overlay_replay.get('exit_code') == 0 else 'Pending fresh overlay replay receipt.')
provenance_text = ('Pass / exit 0: ten modified/retained core files match the native cache copies byte for byte. '
                   'Generated renderer/pipeline mesh predicates, bounded draw diagnostics and texture OOM handling '
                   'are checked; compile commands reference the three generated units and current main/crash-report '
                   'sources, with other project-cache source paths excluded. '
                   f"The recorded {native_provenance['slot_vector']['compiled_dependencies']} compiled SlotVector dependencies "
                   'all use the native exception-safe recovery header, with zero original-header dependencies. '
                   'Regenerating that header through the actual CMake recovery script gives an exact byte match. '
                   'All 30 current input hashes, including the original SlotVector header, recovery generator and derived '
                   'header, are rechecked at packaging.'
                   if native_provenance and native_provenance.get('exit_code') == 0 else
                   'Pending native source provenance receipt.')

archive_rows = '\n'.join(f"| `{Path(item['source']).name}` | {len(item['files'])} | `{item['archive_sha256']}` |"
                         for item in inventory)
crashes = [
    ('Logs3', '200504', 'VkPipelineBuilder', 'eboot+0x229fcc3', '2', '129.996'),
    ('Logs3', '200953', 'CPUCore_3', '0x11ccd2b585, generated code', '1', '93.861'),
    ('Logs3', '201432', 'VkPipelineBuilder', 'eboot+0x229fcc3', '0', '216.859'),
    ('Logs3', '201818', 'VkPipelineBuilder', 'eboot+0x229fcc3', '2', '156.832'),
    ('Logs3', '202529', 'not named', '0x8000a3fd5, outside eboot', '2', '383.802'),
    ('Logs4', '203446', 'VkPipelineBuilder', 'eboot+0x229fcc3', '2', '253.722'),
    ('Logs4', '203836', 'VkPipelineBuilder', 'eboot+0x229fcc3', '0', '147.756'),
    ('Logs5', '205143', 'VkPipelineBuilder', 'eboot+0x229fcc3', '3', '629.099'),
]
crash_rows = '\n'.join(f'| `{folder}/crash-20261107-{time}.txt` | {thread} | `{where}` | {free} | {age} |'
                       for folder, time, thread, where, free, age in crashes)
timeline = (scratch / 'session-timelines.md').read_text()
ordered = timeline.split('## Ordered evidence for each launch\n', 1)[1].split('## Frequency and meaning\n', 1)[0]

documents = {}
documents['Test4-A-README.md'] = f'''# EglantinePS5 Zelda Test4-A

{banner}Test4-A addresses crashes and rendering correctness from the supplied Logs3, Logs4 and Logs5. The remote dashboard and video work are reserved for Test4-B and are not part of this release scope.

The highest-confidence findings are six identical NIR compiler null writes under severe memory pressure and a configuration-value bug that makes `EDEN_NX2_NO_MESH=0` skip geometry. Correcting skipped rendering can increase real GPU work, so the earlier FPS figures cannot be promised with complete graphics.

Implemented source corrections check NIR allocation failures, honor the mesh toggle, and keep refused image allocations out of the cache until a backed retry succeeds. Bounded draw-failure counters, a global heap-failure snapshot and safely probed fault-instruction bytes improve future crash evidence. These changes have focused host checks; visual quality, crash-free duration and performance still need PS5 testing.

The unchanged 49-key Prettier profile is the Test4-A default. `Zelda-faster-profile.txt` is retained only as the historical Test3 comparison baseline: its `LONE=0` leaves lone-mesh fallback disabled and may omit foliage. It is not an equivalent-correctness performance recommendation.

- [Crash analysis and session timelines](Test4-A-Crash-Analysis.md)
- [Detailed changelog](Test4-A-Changelog.md)
- [Validation results and limits](Test4-A-Validation.md)
- [PS5 testing instructions](Test4-A-PS5-Testing.md)
- [Regression comparison](Test4-A-Regression-Comparison.md)
- [Source reconstruction and build instructions](Test4-A-Source-and-Build.md)

Requested final emulator filename: `EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes.zip`.

Current receipt state: {build_text} {checks_text} {package_text}

Preserved inputs: all four original archives remain byte-identical. The public and Test3 packages are comparison inputs, not replacements for the reconstructed Test3 source.
'''

documents['Test4-A-Crash-Analysis.md'] = f'''# Test4-A crash analysis

{banner}## Coverage and build identity

All **53 files / 130,434,078 bytes / 910,036 lines** were read. The archive contains eight complete crash groups and nine game launches, including one normal return to the menu before a second launch in the same app. Three empty TSV files are included in the coverage manifest. `log-coverage.json` records individual hashes; `session-timelines.json` preserves stage and memory evidence.

| Input archive | Extracted files | Original SHA-256 |
| --- | ---: | --- |
{archive_rows}

All crash summaries name `01.219.020` and code size `0x2ab2bb0`. The saved Test3 ELF has that exact text size and SHA-256 `930886ee0b0301169b3977f830954702c7b55da7afa5dc1fbc6260b300458816`. The supplied Test3 package also matches the saved package hash. These support the symbol match; the logs do not contain an on-console executable hash.

## Fatal events

Times are exactly as logged by the console. No timezone conversion is inferred. Final-session ages are approximate because crash app ages are rounded; they are not uninterrupted playability measurements.

| Report / console timestamp | Thread | Instruction | Largest free block (MiB) | Final game age (s) |
| --- | --- | --- | ---: | ---: |
{crash_rows}

The six pipeline reports fault at **exactly `eboot+0x229fcc3`**, not six nearby offsets. Independent `llvm-addr2line-18` resolves that address to Mesa `copy_entry_create`, `src/compiler/nir/nir_opt_copy_prop_vars.c:419`. `llvm-objdump-18` shows `movq %rdx,0xa0(%rax,%rcx)`. In every one of those six reports, `rax=0` and `rcx+0xa0` exactly equals the recorded low fault address. This establishes a null backing-pointer write at the dynamic-array append. Allocation-failure source tracing supports the OOM mechanism; it does not establish the initial source of every byte retained in the shared memory pool or prove a use-after-free.

## Prioritized findings and corrections

| Priority / finding | Exact evidence and frequency | Source / function | Status and correction | Regression risk / validation |
| --- | --- | --- | --- | --- |
| P0: NIR append after failed allocation | Six reports above; all six null-base instruction/register matches. All eight crashes show only 0–3 MiB largest free block. | Mesa `nir_opt_copy_prop_vars.c:copy_entry_create`; `util_dynarray` grow/append | Implemented checked allocation and safe early end of optional copy propagation, including initial state/context guards. {nir_cases} real-NIR ASan/UBSan cases pass; no exception/longjmp across driver code or blanket draw suppression. | Already-valid IR, metadata and semantic result are checked. Native driver build and PS5 low-memory behavior remain separate gates; other compiler OOM paths may still fail. |
| P1: `NO_MESH=0` still skips geometry | 244 stored bounded skip warnings. Example `Logs5/crash-20261107-205143-eden_log.txt:162599` at app +162.815784 s. All nine loaded profiles say `NO_MESH=0`. | `RasterizerVulkan::PrepareDraw`, `DropMeshDrawsBeforeBuild`, RADV mesh-buffer policy | Implemented in overlay 0430 plus WSI patch generator: literal 0 is off; explicit on/legacy/file paths retain compatibility. Eight actual-source sanitizer cases pass. | Restored geometry costs real work and may expose further resource pressure. The existing supported mesh-as-compute fallback is retained; compare the same visual route on PS5. |
| P1: failed image allocation becomes an unbacked resource | 192 `CreateImage` sparse fallbacks; 208 over-budget allocation warnings. Example `Logs4/crash-20261107-203836-eden_log.txt:3055–3533`, app +184.437987 to +190.768982 s. | `vulkan_memory_allocator.cpp:CreateImage`; texture `Image` construction / `TryMakeImage` / `JoinImages` and feedback-shadow creation | Overlay 0432 rejects ordinary failed backing before publishing a cache slot. Both constructor callers share the existing one-second refusal backoff and can retry after recovery, preserving intentionally sparse images. | {image_cases} actual-source host cases pass with simulated allocation, RAII ownership and retry checks. Physical allocation behavior and texture recovery still need PS5 evidence. |
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

{ordered}
'''

documents['Test4-A-Changelog.md'] = f'''# Test4-A detailed changelog

{banner}## Preserved Test3 foundation

The frontend remains pinned to `25cfc07be0a3675749adece5d012fdb916c4cd48`; the core remains `0ca2032bffc5f1a3fca75427f7d4a4718adda660`. Reconstruction applied 257 baseline overlays and the four supplied Test3 overlays 0425, 0427, 0428 and 0429. All 5,684 source files matched the saved Test3 manifest before Test4-A edits. Existing Test3 builds and sources remain preserved.

The separate Test4-A replay applies all 264 overlays and checks 4,800 core Git-listed tracked/unignored files. That narrower file set excludes nested external/submodule contents present in the earlier Test3 snapshot; the two counts describe different comparison scopes.

Retained protections include depth-image sampled-type correctness, failed compute-module cleanup, upload-size/allocation checks, GPU virtual-range checks, the display fallback correction, and title-scoped CPU/DMA/cache-invalidation settings. Their supplied checks pass in the reconstructed tree.

## Implemented and host-checked in this snapshot

`0430-test4a-no-mesh-boolean.patch` changes the rasterizer and pre-build mesh gate to honor a literal 0 value. `tools/patch-radv-wsi.py` applies compatible semantics to the driver buffer policy. The existing supported mesh-as-compute fallback and extension requirements remain enforced.

Before: `EDEN_NX2_NO_MESH=0` still turns skipping on. After: unset/literal 0 do not request skipping; explicit/legacy on and file-toggle behavior remain covered. Eight actual-source cases pass under AddressSanitizer and UndefinedBehaviorSanitizer after the baseline check failed with exit 1.

Expected effect: valid mesh work is allowed to reach the existing supported path. Visual restoration and changed memory/FPS cost remain unverified on PS5. FPS earned by omitted rendering is not a valid correctness improvement.

The unchanged 49-key Prettier profile remains the Test4-A default. The archived Faster file is retained for historical Test3 comparison only: its `LONE=0` leaves lone-mesh fallback disabled and may omit foliage. Fixing the separate no-mesh toggle does not make that profile an equivalent-correctness recommendation.

`tools/radv-patches/test4a-01-nir-copy-prop-oom.patch` checks dynamic copy-entry allocation and initial pass state/context allocation in Mesa's optional NIR variable copy-propagation pass. Failure ends the optimization safely while preserving valid work already completed. The pass retains metadata/cleanup semantics; it does not reject the entire shader or draw. The production driver patch-series helper and fingerprint include the new patch. Its NIR diagnostic counter is process-global and prints at most eight messages to stderr.

Before: two normal real-NIR cases pass and six injected OOM cases fail. After: all {nir_cases} cases pass under ASan/UBSan, including NIR validation, control-flow metadata, preserved stores and semantic result 2087. {nir_callers_text} This covers the demonstrated crash boundary; it does not eliminate general memory exhaustion or all possible compiler OOM faults.

`0432-test4a-transient-image-refusal.patch` prevents ordinary unbacked images from being retained as clean texture-cache resources. Constructor failure cleans up owned image handles. Both image creation callers use a shared refusal boundary: normal joins and feedback shadows retain the existing one-second backoff and retry after memory recovery. A feedback failure uses the existing null descriptor temporarily and leaves no published shadow. Intentionally unwritten/sparse paths and the explicit end-on-OOM policy remain intact. All {image_cases} host cases pass with simulated device allocation; actual PS5 texture recovery is unverified.

`0431-test4a-bounded-draw-diagnostics.patch` replaces the misleading native-failure completion message with cumulative warnings for the first eight failures and every 1,024th afterward, per draw-path template instantiation. The templated `PrepareDraw` has separate direct and indirect call paths, each with its own static counter; these are not one process-global draw counter. The original harness tests one extracted counter: 32,768 failed calls across eight threads produce exactly 40 warnings, exit 0. The additional two-path template test covers 65,536 total failures across eight threads and produces exactly 80 warnings, exit 0. Existing flags and preceding detailed errors remain available. No extra skipped draws or queue waits are introduced.

Frontend crash reports now include the global last heap allocation failure (count, requested bytes and reason) and safely probed 32 bytes at the faulting instruction pointer. An unreadable address is reported without dereferencing it. The heap snapshot is global context and must not be mistaken for a causal thread-specific allocation. The existing host/native-mock crash-report suite covers the new reader/output. The allocator implementation and heap limits are unchanged. A boot marker identifies the local Test4-A build. These additions help investigate the two unresolved non-pipeline faults; they do not fix their originating instructions.

Two inherited host test harnesses were corrected after the native build: `tools/check-gpu-sync-stop.py` supplies the missing scalar/logging/back-thread stand-ins, and `tools/check-gpu-producer-stop.py` tests the pinned fence-watermark implementation instead of requiring a newer, absent per-request completion API. Actual production methods remain extracted into the tests. These are test-only compatibility corrections; the compiled runtime did not change.

## Native and console certification

Final inclusion requires the native build receipt, matching symbols and package validation. Complete geometry, texture recovery, brightness, flashes, sustained FPS and crash-free gameplay need controlled PS5 tests. No memory limits, descriptor budgets or reserve safety policies are raised by these corrections.

Current additional overlay files present:

{patch_list}

Current source files whose bytes differ from reconstructed Test3:

{actual_files}

## Risks that remain

Correct rendering can cost FPS and memory. The overall resource-exhaustion cause, CPU/system-library faults, brightness, dark glitches, white flashes, long-session stability and cold-cache behavior still require measured console testing. Native build state: {build_text}
'''

supplied_rows = '\n'.join(f"| `{Path(item['command'][2]).name}` | {item['exit_code']} |"
                           for item in supplied)
documents['Test4-A-Validation.md'] = f'''# Test4-A validation report

{banner}## Completed checks

- Four original archives: CRC/integrity and extraction exit 0; originals rehashed unchanged. Extracted 218 files into new directories.
- Exact Test3 reconstruction: exit 0; 261 overlays applied, 5,684 source-snapshot files compared, zero missing/changed files at baseline. This earlier snapshot includes nested external/submodule contents.
- All seven supplied verification scripts and the inherited fence contract: exit 0, with their original script bytes retained. Final post-change receipt: {checks_text}
- NO_MESH regression: baseline exit 1; patched eight-case actual-source check exit 0 under ASan/UBSan.
- NIR allocation regression: baseline exit 1, two normal cases pass and six injected-OOM cases fail; patched {nir_cases}-case real-NIR check exit 0 under ASan/UBSan. Validator, metadata, semantic result 2087 and cleanup pass. {nir_callers_text}
- Transient image refusal: baseline exit 1; patched check exit 0, {image_cases} host cases using actual source branches and simulated device allocation. Ownership, refusal backoff, recovered upload, both creation callers and sparse-policy preservation pass.
- Bounded draw failures: both checks exit 0. One extracted counter produces 40 warnings for 32,768 failed calls across eight threads; the two-path template check produces 80 warnings for 65,536 total failures across eight threads. Production counters are per `PrepareDraw` template instantiation (direct and indirect paths separately), not process-global. The NIR diagnostic cap is separately process-global at eight messages. The crash-report suite was rerun and passed exit 0.
- Crash-report suite: host/native-mock suite exit 0, including global heap failure context and safely probed fault instruction output.
- Independent pipeline address check: saved ELF hash matched; all six crash register equations and symbol/disassembly matches passed, exit 0.

| Supplied / inherited check | Exit |
| --- | ---: |
{supplied_rows}

The range guard test uses the already-applied source with an explicit 0429 patch path. It reverses only scratch copies to reproduce the old invalid-address behavior; the real tree is not reverted. Other supplied checks exercise display selection, failed-module cleanup, pipeline allocation error handling, upload allocation guards, accuracy settings and depth SPIR-V validation.

## Expected failing-before evidence

The mesh test intentionally failed before the correction because value 0 still activated mesh skipping in the rasterizer, pre-build gate and driver policy. This was a behavioral regression result, not a segmentation fault hidden by the test. The patched test preserves supported fallback/extension behavior and the unrelated game exception.

The initial NIR test reproduced the null copy-entry OOM boundary without hiding it behind a segmentation-fault handler. Patched tests preserve valid earlier transformations and shader semantics under controlled allocation failure. The image regression checks failed-slot cleanup and backed retry without inventing a physical GPU allocation test. Earlier Test4 prototype results are not used as Test4-A evidence.

## Additional project checks and retained attempts

Source-stage result: {project_summary(project_source)} Native-stage result: {project_summary(project_native)} Fresh 264-overlay reproduction: {replay_text}

Native source provenance: {provenance_text} This establishes build-input provenance, not PS5 rendering or runtime validation.

| Stage | Check | Exit | Log |
| --- | --- | ---: | --- |
{project_rows}

The optional full heap ThreadSanitizer stress test **did not complete** on this host. The first attempt completed both checked UBSan heap modes, then its ThreadSanitizer subprocess was killed with exit -9. The host kernel identified memory exhaustion during that test (about 3.5 GiB consumed). The retry used `TSAN_OPTIONS=memory_limit_mb=1536`; both checked UBSan modes passed again, but the ThreadSanitizer subprocess raised `TimeoutExpired` after **900 seconds**. The final heap check remains **exit 1**, and `project-checks-source.json` remains **status fail / exit 1**; the performance-settings check is exit 0. These outcomes are retained rather than converted into passes.

`host-heap-test-limits.json` records why the optional full TSan stress is unavailable. Packaging may acknowledge only this specific host limitation while retaining the failed receipts/logs; all fix-specific tests, supplied checks and eight native project checks must still pass. This does not establish heap race freedom or reproduce a PS5 heap crash. The heap implementation and allocation limits were not changed for Test4-A; the new crash-report snapshot reader is covered by the passing crash-report suite.

The first sparse-header invocation lacked its required native build-directory argument and failed with `IndexError`. The runner was corrected to pass the independent cache's `native-local` build and that check moved to the native stage. An invocation error is not a passed regression check. Both original first-attempt logs and receipt are retained; the current row above gives the actual corrected outcome.

The first native check batch had six passes and two host harness compilation failures. The sync harness lacked the current scalar/logging/back-thread stand-ins; the producer harness required a completion header/API absent from the pinned source. Both harnesses now exercise the actual generated implementation. Original failure logs and `project-checks-native-first-attempt.json` are retained, and the final native table records their fresh rerun results. No runtime source or native binary was changed for these test corrections.

## Final release gates

| Gate | Current state |
| --- | --- |
| Native PS5 release build | {build_text} |
| Final post-change command set | {checks_text} |
| Optional full heap TSan stress | Incomplete: first host OOM, retry timed out after 900 s; heap check remains exit 1. Checked UBSan heap modes passed. |
| Executable/package inventory, CRC, permissions, metadata and hashes | {package_text} |
| Matching Test4-A symbols retained | {symbol_text} |
| Actual PS5 run | Not performed |
| Controlled Test3/Test4-A FPS/visual comparison | Not performed |
| All-cache-empty cold launch | Not performed |
| Long crash-free gameplay duration | Not performed |

The upstream CI route uses `EDEN_SKIP_SOURCE_CHECKS=1`. Running the supplied and relevant focused checks separately does not equal running every legacy upstream source check. A native compile also cannot validate physical PS5 allocation, GPU scheduling, HDR/SDR output or gameplay correctness.

No Test4-A FPS result or elimination of all crashes is claimed. Keep original logs, original packages and matching Test3 symbols. Final checks must be rerun after the last code or documentation mutation.
'''

documents['Test4-A-PS5-Testing.md'] = f'''# Test4-A PS5 testing instructions

{banner}## Before installation

Use a package only after the native build and package verification are certified. Requested filename: `EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes.zip`. Current state: {build_text} {package_text}

1. Fully close the emulator. Back up the current executable and title profile, and preserve saves/settings/caches.
2. Use the same homebrew installation method you currently use. Your logs select `/system_ex/app/PPSA98515`; a second `/data/homebrew/PPSA98515` exists. Do not assume copying to the second folder changes the active installation.
3. Install the final app folder/profile as documented with the certified package. Verify the next boot trace's selected folder, build marker/date and version. An optional local ZIP hash does not prove the installed binary; an executable readback/hash is stronger evidence when available.
4. Keep output 1080p/60 Hz, 1x resolution and Bilinear for the initial comparison. Record the complete title environment block. Use the unchanged 49-key Prettier profile packaged as the Test4-A default for graphics testing. All supplied crash sessions used the historical Faster profile, so they are not an equivalent-correctness baseline for default Prettier.

`Zelda-faster-profile.txt` is retained only to reproduce that historical Test3 baseline. Its `LONE=0` leaves lone-mesh fallback disabled and may omit foliage. Do not select it as a recommended performance preset or treat its FPS as equivalent to complete rendering. Preserve its bytes for comparison; it is not the default installation profile.

## Controlled warm comparison

Use the same save, route, camera, output, shader-cache state and log level for Test3 and Test4-A, with Prettier on both for graphics-correctness comparisons. Identify any separate historical Faster run as a potentially incomplete-graphics baseline. If available in the current save, include a slow pan through Kokiri Forest vegetation, the Deku Tree exterior, water/reflections and an interior/dungeon transition. Do not change several profile flags between runs.

For correctness, check whether tree canopies, grass/plants and previously missing surfaces render consistently. Compare light/dark areas and water with the same camera and output mode. Count flashes and visible glitches from a recording where available; a still screenshot does not prove flash reduction. Keep any capture contrast/HDR settings constant.

Run a short repeatable route first, then extend normal gameplay to 20–30 minutes if stable. A 60-minute target is a test target, not a promised result. Distinguish app uptime from game-session duration and note any return to the menu or reload.

Record FPS sample distribution, worst frame intervals, memory headroom and the exact scene. Do not call a faster run equivalent if it omits geometry. Correcting Test3's `NO_MESH=0` bug can increase actual GPU work. The supplied archives contain only Faster-profile sessions; any full-foliage comparison must identify that difference.

## Cold-cache comparison

Perform this only after a successful warm test and with the emulator fully closed. Locate the actual title pipeline cache and Mesa/RADV disk-cache folders first. Preserve them by copying or renaming into timestamped backups; do not delete them and do not touch saves, firmware or keys. Record which caches were quarantined.

The source-derived title cache is `/data/eglantineps5/user/cache/shader/0400486024dec000/`, containing any of `vulkan.bin`, `vulkan_mesh.bin`, `vulkan_used.bin` and `vulkan_pipelines.bin`. Back it up to the PC and rename the console folder to `0400486024dec000-Test3-backup` before a title-cache cold test. A separate fully cold driver test also backs up and renames `/data/eglantineps5/cache/radv`. Test the same scene once cold and again after a clean exit with the newly written warm cache. Preserve both cache versions if classification errors recur.

A cache is not proven cold merely because one file was removed. Verify startup cache counts and whether the separate driver cache was also reset. Repeat the same route, keep compile-worker settings unchanged initially, and report loading time, shader-compilation stalls, headroom and any first-encounter graphics failures. Restore the backed-up caches afterward if needed.

## If it crashes or stalls

Keep the crash summary and its matching `-eden_log.txt`, `-heap.log` and `-stderr.log`, plus `crash-index.txt`, both current/previous boot traces and current logs. Keep the complete folder instead of selecting only final lines. Note the scene/transition, route, profile, cache state and how long the game itself ran.

Do not repeatedly restart and overwrite evidence before copying it. Preserve the final Test4-A verification receipt and executable hash; developers need matching symbols. A hang-watch warning or stale log alone is not proof of a GPU hang.

Remote dashboard/video setup remains Test4-B work. Test4-A uses lightweight existing logs and bounded diagnostics; no console connection or remote video test has been performed for this snapshot.
'''

documents['Test4-A-Regression-Comparison.md'] = f'''# Public release, Test3 and Test4-A comparison

{banner}| Property | Public v1.219.020 | Supplied Zelda Test3 | Test4-A snapshot |
| --- | --- | --- | --- |
| Original package SHA-256 | `8209561dc5e9328e92cc8668a084e4f4e37b26e30df5c9d614a28a90470d4ae7` | `55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7` | {artifact_hash_text} |
| Extracted files | 69 | 71 | {artifact_inventory_text} |
| User-observed FPS | 15–19, supplied by user | 30–58, supplied by user | Not measured |
| Controlled matched benchmark | None provided | None provided | Not performed |
| New supplied crash logs | No verified public-release trial in Logs3–5 | Eight crashes / nine launches; symbols support Test3 | No PS5 trial |
| Mesh configuration | Not inferred from binary alone | All observed profiles say 0 but presence-based source still skips mesh work | Literal 0 parsing corrected and host-tested; visual result pending |
| Profile comparison | No matched trial | Supplied crash sessions use Faster; `LONE=0` may omit foliage | Unchanged 49-key Prettier is default. Faster is retained only as the historical incomplete-graphics baseline. |
| Compiler OOM crash boundary | Not inferred without matching symbols/source | Six identical null dynamic-array writes | Checked optimization abort implemented; {nir_cases} initial real-NIR host cases plus 24 caller cases pass. {native_cert_text} |
| Cached textures after allocation refusal | No matched runtime evidence | Sparse-image fallback warnings under pressure | Scoped cleanup/backoff/retry implemented; {image_cases} simulated-allocation host cases pass; hardware result pending |
| Test3 upload/range/shader/display guards | Not inferred | Reconstructed and retained | Supplied checks pass; final receipt shown in validation report |
| Targeted diagnostics | Not inferred | Verbose draw-failure Debug output | Bounded cumulative warnings, heap-failure snapshot, fault instruction bytes and boot marker; host checked |
| Remote dashboard | Not assessed | Not required | Excluded; reserved for Test4-B |

The user-observed FPS ranges are useful motivation, not a measured regression guarantee. Logged Test3 medians vary from 1.1 to 59.366 FPS by session; scenes, duration, Debug logging and memory pressure differ. The fastest short sample is not representative of longer demanding gameplay, and the longest observed final session ends in a crash after approximately 629 s.

Test3's omitted mesh work is a concrete confounder. Restoring valid rendering can reduce numeric FPS while improving correctness. The goal is to retain legitimate Test3 optimizations, not reproduce a high counter by dropping essential geometry. No Test4-A change is certified solely because its logs become quieter.

Acceptance requires the same route/save/cache/output/profile comparison, correct vegetation/textures, no new pipeline/image errors, better sustained headroom and measured duration/FPS. If a change fails those checks, revise or revert that isolated change rather than adding unrelated tuning.
'''

documents['Test4-A-Source-and-Build.md'] = f'''# Test4-A source reconstruction and build handoff

{banner}## Exact base

- Frontend repository: `https://github.com/Vampinity/Eglantine-PS5-`
- Frontend revision: `25cfc07be0a3675749adece5d012fdb916c4cd48`
- Core repository: `https://github.com/Djihads80/Eglantine`
- Core revision: `0ca2032bffc5f1a3fca75427f7d4a4718adda660`
- Isolated frontend: `/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5`, branch `codex/zelda-test4-a`
- Isolated core branch: `codex/zelda-test4-a-core`

The supplied `SOURCE.json`, `BUILD.txt`, frontend diff, four extra patches, profiles, checks and research documents define Test3. Reconstruction applied the frontend diff to the pinned frontend, copied the four additional overlays and ran the complete ordered overlay helper. The 261 overlays comprise 257 base patches plus 0425/0427/0428/0429. Byte comparison against the saved Test3 source manifest found zero missing/changed files across 5,684 files before Test4-A edits. Test4-A adds core overlays 0430/0431/0432 for a total of 264.

The separate final overlay replay starts from the pinned core, applies those 264 overlays, and compares the core's Git-listed tracked/unignored files: 4,800 files match byte for byte, with no missing, extra or changed files. This narrower replay inventory excludes nested external/submodule contents included in the earlier 5,684-file Test3 snapshot. The checks establish different things: Test3 reconstruction fidelity before changes, and final Test4-A overlay reproducibility after changes. See `overlay-replay.json` for the final replay and ordered patch hashes.

The four original archives are immutable inputs. Their checksums and extracted inventories are in `input-inventory.json`. Existing released Test3 ZIPs and matching symbols remain preserved. No public-release source substitution or unreviewed upstream merge is part of Test4-A.

## Current additional overlays

{patch_list}

The final source-change bundle must include all additional overlays, the full frontend diff, exact pins, relevant licenses, title profile(s), new tests and fixtures, original supplied verification scripts, build commands and source/artifact hashes. Host-only Mesa tests must not accidentally enter the production driver export.

The native driver export applies the original ordered driver patch series plus `tools/radv-patches/test4a-01-nir-copy-prop-oom.patch`, with the series helper and WSI fingerprint covering that directory. The host Mesa copy contains test-only Meson/C harness changes; rebuilding production from that entire copy would be incorrect. Use the pinned production Mesa source and the checked patch generator.

## Native build

Use the existing pinned dependencies in `tools/deps.json`. The prepared build-input receipt identifies an independent cache and mutable driver tree; old driver build outputs must not be linked as writable Test4-A outputs. SDK/decoder reuse is permitted only when matching pins and binary hashes are checked. Keep `build/radv-isolated` independent.

```sh
JOBS=3 RADV_BUILD_JOBS=2 bash tools/ci/build-release.sh
```

The CI path skips the full legacy source-check suite. Run the seven supplied checks with their original bytes, the inherited fence check and each new focused regression separately. GPU range check invocation must include the already-applied source and the 0429 patch path as described in supplied `BUILD.txt`.

Require a fresh successful native receipt whose source hashes before/after are identical, a final current-source test receipt and native package integrity checks before distributing the ZIP. Preserve a separately named matching Test4-A ELF. An earlier Test4 prototype build is not a Test4-A build.

Current state: {build_text} {checks_text} {package_text}

No upstream push or PR is part of this work. Local changes are AI-assisted. This handoff does not claim human gameplay testing or PS5 certification.
'''

assert len(documents) == 7
for name, text in documents.items():
    text = text.rstrip() + '\n'
    assert not any(line.rstrip() != line for line in text.splitlines()), name
    assert text.count('```') % 2 == 0, name
    (reports / name).write_text(text)
for name, text in documents.items():
    for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', text):
        if not target.startswith(('http:', 'https:', '#')):
            assert (reports / target).is_file(), (name, target)
status = {'status': 'pass', 'exit_code': 0, 'report_count': len(documents),
          'files': {name: digest(reports / name) for name in sorted(documents)},
          'original_archives_unchanged': True, 'native_build_receipt': build_text,
          'final_checks_receipt': checks_text, 'package_receipt': package_text,
          'no_ps5_runtime_claim': True, 'source_inventory_live': not args.evidence_only,
          'for_package': args.for_package,
          'changed_source_snapshot': sorted(changed)}
(reports / 'report-status.json').write_text(json.dumps(status, indent=2) + '\n')
print(json.dumps({'status': 'pass', 'exit_code': 0, 'report_count': len(documents),
                  'directory': str(reports), 'native_build': build_text, 'package': package_text}))
