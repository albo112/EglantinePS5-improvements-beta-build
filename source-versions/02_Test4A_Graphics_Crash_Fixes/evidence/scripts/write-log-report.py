from pathlib import Path
import hashlib
import json
import re

scratch = Path(__file__).resolve().parent
coverage = json.loads((scratch/'log-coverage.json').read_text())
data = json.loads((scratch/'session-timelines.json').read_text())
evidence = json.loads((scratch/'log-file-evidence.json').read_text())
crashes, launches = data['crashes'], data['launches']
for entry in coverage['manifest']:
    assert hashlib.sha256(Path(entry['path']).read_bytes()).hexdigest() == entry['sha256']
assert len(crashes)==8 and len(launches)==9 and coverage['files']==53
assert not any(entry['utf8_error_lines'] for entry in coverage['manifest'])
for launch in launches:
    values = launch['environment']['values']
    assert len(values) == 49
    for key, expected in {'EDEN_NX2_NO_MESH':'0', 'EDEN_NX2_RADV_MESH_COMPUTE_LONE':'0',
                          'EDEN_NX2_QUERY_KEEP_PENDING':'0', 'EDEN_NX2_PIPELINE_WORKERS':'4',
                          'EDEN_PS5_ZELDA_SAFE_MEMORY':'1', 'EDEN_NX2_TENSOR_ONLY':'c00',
                          'EDEN_NX2_NATIVE_TABLES':'1', 'EDEN_NX2_PAIRED_POINTERS':'1'}.items():
        assert values[key] == expected, (launch['report'], key, values[key])
for crash in crashes:
    performance = [value['text'] for value in crash['launch_settings'] if 'Performance:' in value['text']]
    assert len(performance) == len(crash['game_launches'])
    assert all('unsafe CPU off, unsafe DMA off' in value and 'skip invalidation off' in value for value in performance)
pipeline = [c for c in crashes if c['where']=='eboot+0x229fcc3' and c['thread'].startswith('VkPipelineBuilder')]
assert len(pipeline)==6

def ref(event):
    stamp = f" at app +{event['app_seconds']:.6f}s" if event['app_seconds'] is not None else ''
    return f"`{event['file']}:{event['line']}`{stamp}"

lines = ['# Test4-A supplied-log coverage and session timelines', '',
    f"Read all **{coverage['files']} files, {coverage['bytes']:,} bytes and {coverage['lines']:,} lines** from Logs3, Logs4 and Logs5. There are eight complete crash groups and nine game launches. Three empty `result.tsv` files were read and inventoried. Every input file has a SHA-256 in `log-coverage.json`.", '',
    'All times below remain exactly as the console logged them. No timezone or UTC conversion is inferred. App ages in crash reports are rounded seconds; final-session ages therefore are approximate. Heap phase offsets use their own monotonic session-start. Untimestamped stderr/cache/memory records are referenced by line order, without invented clock times.', '',
    'The eight reports name version `01.219.020`, text size `0x2ab2bb0`. The preserved Test3 ELF independently hashes to `930886ee0b0301169b3977f830954702c7b55da7afa5dc1fbc6260b300458816` and its `.text` is exactly `0x2ab2bb0`. The user-supplied Test3 ZIP hashes to `55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7`, matching the saved Test3 package. This supports the matching-symbol choice; there is no on-console executable hash in these logs.', '',
    '## Fatal reports', '',
    '| Report | Faulting thread / location | App age | Final game age | Largest free / heap |',
    '| --- | --- | ---: | ---: | ---: |']
for c in crashes:
    memory=c['memory']
    lines.append(f"| `{c['report']}` | {c['thread'].split(' (')[0]} / `{c['where']}` | {c['app_age_seconds']} s | {c['final_game_session_age_seconds_approx']:.3f} s | {memory['largest_free_mib']} / {memory['heap_mib']} MiB |")
lines += ['', '**Six unique reports** have `SIGSEGV` on `VkPipelineBuilder` at **exactly `eboot+0x229fcc3`**: 20:05:04, 20:14:32, 20:18:18, 20:34:46, 20:38:36 and 20:51:43. They are not six different offsets. The remaining reports are a generated CPU write at 20:09:53 and an unnamed-thread/system-library write at 20:25:29. All eight report only 0–3 MiB as the largest free block. This establishes severe pool pressure, not the original cause of each fault. Scanned stack values marked `?` are not validated call frames.', '',
    '## Each game launch', '',
    '| Capture / launch | Eden begin (app seconds) | Cached pipeline records / preload | First frame after heap session-start | Recorded end / duration | Logged frame median |',
    '| --- | ---: | ---: | ---: | --- | ---: |']
for l in launches:
    cache=l['shader_cache_ready']
    first=next(p['seconds_from_heap_session_start'] for p in l['phases'] if p['phase']=='first_frame_callback')
    fps=l['fps_log_samples']
    lines.append(f"| `{Path(l['report']).stem}` #{l['launch_ordinal_within_app']} | {l['eden_begin']['app_seconds']:.6f} | {cache['pipelines']} / {cache['milliseconds']/1000:.3f} s | {first:.3f} s | {l['end_kind']}; {l['duration_to_recorded_end_seconds']:.3f} s | {fps['median_sample_fps']:.3f} FPS ({fps['samples']} samples) |")
lines += ['', 'The first app has a normal return to the menu at app +64.877283 s, followed by another launch at +271.004094 s. Its 401-second app age is **not** uninterrupted gameplay. Session identifier `1` is reused; launch ordinals above distinguish the two. All nine launches preload nonempty emulator pipeline caches (1,138–2,405 records); driver/Mesa binary-cache warmth is not established, and **none is a controlled all-caches-empty cold-start test**. The loader count does not prove every cached pipeline built successfully. FPS figures are historic Test3 log windows in unrecorded/different scenes and are not a controlled public/Test3/Test4-A benchmark.', '',
    '## Ordered evidence for each launch', '']
for l in launches:
    c=next(c for c in crashes if c['report']==l['report'])
    lines += [f"### {Path(l['report']).stem}, launch {l['launch_ordinal_within_app']}", '',
        f"- Startup context: app start approximately `{c['approx_app_start_wall']}` from the crash report's rounded age; game begins at {ref(l['eden_begin'])}. This approximate wall time is only a subtraction in the console's timebase."]
    phase_text='; '.join(f"{p['phase']} +{p['seconds_from_heap_session_start']:.3f}s (heap line {p['line']})" for p in l['phases'])
    lines.append('- Core/graphics sequence relative to the heap session-start: '+phase_text+'.')
    cache=l['shader_cache_ready']
    lines.append(f"- Initial cached shader compilation: {cache['pipelines']} pipelines in {cache['milliseconds']} ms; {ref(cache)}. Live shader compilation can still continue later.")
    mem=l['memory_snapshots']
    if mem:
        first,last=mem[0],mem[-1]
        lines.append(f"- Memory samples (stderr line order): first {ref(first)}: largest {first['largest_free_mib']} MiB, guest {first['guest_mib']} MiB, short={first['short']}; last {ref(last)}: largest {last['largest_free_mib']} MiB, guest {last['guest_mib']} MiB, short={last['short']}. Minimum recorded largest block {min(m['largest_free_mib'] for m in mem)} MiB; peak recorded guest {max(m['guest_mib'] for m in mem)} MiB. No wall-clock timestamp is fabricated for these snapshots.")
    for category,title in (('native_compute_rejected','Compute translation rejection'),('mesh_skipped','Skipped mesh draw warning'),('native_graphics_failed','Native graphics failure debug line')):
        count=l['logged_event_counts'].get(category,0)
        if count:
            lines.append(f"- {title}: {count:,} stored lines; first {ref(l['first_logged_events'][category])}, last {ref(l['last_logged_events'][category])}.")
        else:
            lines.append(f"- {title}: no matching stored line in this launch; absence of Debug messages at an Info-level logger is not proof the operation never failed.")
    start,end=l['eden_line_range']
    eden_name=l['eden_begin']['file']
    for category,title in (('over_budget_image_allocation_lines','Over-budget image allocation warning'),('sparse_image_allocation_fallback_lines','Unbacked sparse-image creation fallback'),('hang_watch_warning_lines','Hang-watch warning')):
        events=[e for e in c['precise_events'][category] if e['file']==eden_name and e['line']>=start and (end is None or e['line']<end)]
        if events:
            lines.append(f"- {title}: {len(events):,} stored lines; first {ref(events[0])}, last {ref(events[-1])}.")
    if l['normal_end']:
        lines.append(f"- End: normal game-session end at {ref(l['normal_end'])}; a later launch is recorded in the same app.")
    else:
        lines.append(f"- End: `{c['report']}:3–8`, console time {c['wall_time_as_logged']}; {c['what']}; {c['where']}; largest free block {c['memory']['largest_free_mib']} MiB. The precise originating corruption is not established by chronology alone.")
    lines.append('')

counts=coverage['category_counts_all_files']
lines += ['## Frequency and meaning', '',
    'These are **stored log-line counts**, not counts of distinct GPU objects, shader programs, physical hangs, or every failed draw. Some source warnings are rate limited, and current heap/stderr files are residual startup snapshots rather than additional gameplay trials.', '',
    '| Verified logged condition | Stored lines | Source named in the logs | Interpretation / limit |',
    '| --- | ---: | --- | --- |',
    f"| `Draw skipped (EDEN_NX2_NO_MESH)` | {counts['mesh_skipped']} | `vulkan_rasterizer.cpp`, draw failure callback | The profile says `NO_MESH=0`, yet the source tests environment-variable presence. See configuration finding below. Warning deduplication makes this smaller than total skipped draws. |",
    f"| `Native graphics draw failed; refusing submission completion` | {counts['native_graphics_failed']:,} | `vulkan_rasterizer.cpp`, native draw completion guard | Debug messages occur in only two Debug-heavy captures; cannot compare raw rates with other captures. Refusal is an explicit effect of an unsuccessful native draw, not by itself a Vulkan fence timeout. |",
    f"| `Native compute shader rejected` | {counts['native_compute_rejected']} | `kepler_compute.cpp:DispatchNativeCompute` | All observed rejections name native matrix multiplication excluded by `EDEN_NX2_TENSOR_ONLY`; 10 messages per launch. Correctness/fallback requires source translation analysis. |",
    f"| `Native QMD failed: native shader dispatch required` | {counts['native_qmd_failed_lines']} | `kepler_compute.cpp:ProcessNativeMethod` | 16 stored messages per launch; not every one has a separately logged new shader rejection. |",
    f"| `Uncached storage pointer classification` | {counts['uncached_storage_pointer_lines']} | `vk_pipeline_cache_cost.cpp:CreateGraphicsPipeline/CreateComputePipeline` | Occurs while rebuilding cached resources; this alone does not establish failure of every later live pipeline. |",
    f"| `All 32 storage buffer bindings taken` | {counts['storage_binding_budget_lines']} | `global_memory_to_storage_buffer_pass.cpp:GlobalMemoryToStorageBufferPass` | Seven warnings per launch; raising a binding constant is not a proven supported fix. |",
    f"| Over-budget image allocation proceeds | {counts['over_budget_image_allocation_lines']} | `vulkan_memory_allocator.cpp:CreateImage`, log line 374 | Observed allocation-policy warning, not an exact unique-image count; many captures hit 32 such warnings. |",
    f"| `using an unbacked sparse image` from `CreateImage` | {counts['sparse_image_allocation_fallback_lines']} | `vulkan_memory_allocator.cpp:CreateImage`, log line 422 | Distinct from {counts['unbacked_sparse_image']} total unbacked-image mentions, which also include render-target/view use. Relevant to missing resources under pressure. |",
    f"| `Direct allocation failed` | {counts['direct_allocation_failed_lines']} | Untimestamped stderr, native direct-memory allocator | Recorded request sizes/return codes are in the original line; these are not all allocation failures. |",
    f"| Hang-watch warnings | {counts['hang_watch_warning_lines']} | `gpu_split.cpp:ReportBack`, `vulkan_scheduler.cpp:ReportFreeze` | Shows blocked back/worker state, including waiting for a GPU tick or pipeline build. A warning snapshot is not proof of a missing barrier or physical GPU hang. |",
    f"| Actual `timed out` messages / timeout warning-error lines | {counts.get('timed_out_messages',0)} / {counts.get('timeout_warning_or_error_lines',0)} | None matched these precise conditions | The {counts['timeout_mentions']} broad timeout mentions are API/configuration arguments such as `ChannelSetTimeout` and socket `Poll(timeout=0)`, not failures. |", '',
    '## Configuration and collection findings', '',
    '- All nine title environment blocks use the **Faster** profile: `EDEN_NX2_RADV_MESH_COMPUTE_LONE=0`, `EDEN_NX2_QUERY_KEEP_PENDING=0`, `EDEN_NX2_NO_MESH=0`, all-stage native tables and paired pointers enabled, pipeline workers 4, safe-memory override 1, `TENSOR_ONLY=c00`. No Prettier-profile gameplay run is present in this archive.',
    '- Independent read-only source inspection found `static const bool no_mesh_always{std::getenv("EDEN_NX2_NO_MESH") != nullptr};` in `Eglantine/src/video_core/renderer_vulkan/vk_rasterizer.cpp`. A value of `0` still activates that flag. The later mesh gate logs this exact skip reason. The warning callback deduplicates `(vs, ps, reason)` pairs (maximum 64), so logged skip warnings are not total skip counts. Correcting value parsing is a concrete source target; this audit did not edit it or prove visual restoration.',
    '- The native draw scope-exit sets `native_execution_failed` when `!submitted` and logs submission-completion refusal. This directly connects skipped/failed native draws with those debug refusals; it does not establish all downstream graphics causes.',
    '- All logged launch settings select CPU Auto, Default DMA, cache invalidation enabled, unsafe CPU/DMA off, async shaders off, fast GPU on, reactive flushing off. Earlier unsafe-setting advice does not diagnose these new sessions.',
    '- Logs4/20:34:46 contains **319,118 Debug lines** and Logs5/20:51:43 **531,699 Debug lines**. The other Eden crash captures contain no Debug-tagged lines. Log volume and different scenes/settings make FPS comparisons uncontrolled; logging overhead must be measured rather than assumed negligible.',
    '- The recorded app folder is **`/system_ex/app/PPSA98515`**, even though `/data/homebrew/PPSA98515` also exists. Example: `Logs5/boot-trace.txt:8–11` and every captured stderr filesystem-access line. Installing only into the other folder can leave a different selected binary/profile active. Verify the actual selected app path after installation.',
    '- Only the three empty TSV files are byte-identical whole-file duplicates. Other current/previous traces overlap in event history or are restart remnants; they are not additional independent gameplay trials.', '',
    '## What remains unverified by this log audit', '',
    'The faulting allocator/compiler function and original corruption cause require exact symbolication and source tracing. Missing trees/textures, brightness and flashes have no synchronized image/video reference here. No new build, fixed FPS, crash-free run, cold-cache behavior, public-release benchmark or PS5 Test4-A outcome is claimed. `session-timelines.json` preserves every observed stage and memory snapshot; `log-file-evidence.json` preserves exact examples, source frequencies, log levels and category counts.']
report='\n'.join(lines)+'\n'
assert not any(line.rstrip()!=line for line in report.splitlines())
assert report.count('```')%2==0
(scratch/'session-timelines.md').write_text(report)
summary = {'status':'pass','exit_code':0,'files_read':53,'bytes_read':130434078,'lines_read':910036,
           'complete_crash_groups':8,'game_launches':9,'pipeline_crashes_exact_offset':6,
           'profile_modes':{'Faster':9,'Prettier':0},
           'precise_stored_log_lines':{key:counts.get(key,0) for key in (
               'mesh_skipped','native_graphics_failed','native_compute_rejected','native_qmd_failed_lines',
               'uncached_storage_pointer_lines','storage_binding_budget_lines','over_budget_image_allocation_lines',
               'sparse_image_allocation_fallback_lines','hang_watch_warning_lines','timed_out_messages','timeout_warning_or_error_lines')},
           'report':'session-timelines.md','input_hashes_reverified':True,'source_edited':False}
(scratch/'log-audit-summary.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary))
