"""Separate actual warning/error evidence from settings and API argument mentions."""
from pathlib import Path
from collections import Counter, defaultdict
import hashlib
import json
import re
import statistics

scratch = Path(__file__).resolve().parent
root = scratch / 'inputs/logs-archive'
coverage = json.loads((scratch / 'log-coverage.json').read_text())
evidence = json.loads((scratch / 'log-file-evidence.json').read_text())
timeline = json.loads((scratch / 'session-timelines.json').read_text())
rules = {
    'hang_watch_warning_lines': re.compile(r'<Warning>.*Hang watch:'),
    'timed_out_messages': re.compile(r'timed out', re.I),
    'timeout_warning_or_error_lines': re.compile(r'<(?:Warning|Error|Critical)>.*timeout', re.I),
    'sparse_image_allocation_fallback_lines': re.compile(r'CreateImage: .*does not fit; using an unbacked sparse image'),
    'over_budget_image_allocation_lines': re.compile(r'CreateImage: .*over the memory budget; allocating it anyway'),
    'uncached_storage_pointer_lines': re.compile(r'Uncached storage pointer classification'),
    'storage_binding_budget_lines': re.compile(r'All 32 storage buffer bindings taken'),
    'native_qmd_failed_lines': re.compile(r'Native QMD failed: native shader dispatch required'),
    'direct_allocation_failed_lines': re.compile(r'^Direct allocation failed:'),
    'normal_session_end_lines': re.compile(r'EDEN_GAME_SESSION_END\b'),
}
clock = re.compile(r'^\[\s*(\d+\.\d+)\]')
all_new = Counter()
duplicates = defaultdict(list)
for item in coverage['manifest']:
    path = Path(item['path'])
    raw = path.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['sha256']
    duplicates[item['sha256']].append(item['relative'])
    data = evidence[item['relative']]
    text = raw.decode('utf-8')
    data['all_log_levels'] = dict(Counter(re.findall(r'<(Trace|Debug|Info|Warning|Error|Critical)>', text)))
    for old, new in (('gpu_hang_watch', 'hang_watch_mentions'), ('timeout', 'timeout_mentions')):
        if old in data['categories']:
            data['categories'][new] = data['categories'].pop(old)
        if old in data['examples']:
            data['examples'][new] = data['examples'].pop(old)
        if old in data['last_examples']:
            data['last_examples'][new] = data['last_examples'].pop(old)
    hits = defaultdict(list)
    data['launch_settings'] = []
    data['boot_headers'] = []
    for number, line in enumerate(text.splitlines(), 1):
        match = clock.match(line)
        event = {'file': item['relative'], 'line': number,
                 'app_seconds': float(match[1]) if match else None, 'text': line[:1800]}
        for name, pattern in rules.items():
            if pattern.search(line):
                hits[name].append(event)
        if '[EglantinePS5] launch:' in line:
            data['launch_settings'].append(event)
        if 'diagnostic build ' in line:
            data['boot_headers'].append(event)
    data['precise_events'] = dict(hits)
    for name, events in hits.items():
        data['categories'][name] = len(events)
        data['examples'][name] = events[:3]
        data['last_examples'][name] = events[-1]
        all_new[name] += len(events)

launches = []
for crash in timeline['crashes']:
    eden, heap, stderr = [evidence[name] for name in crash['companion_files']]
    categories = Counter()
    for source in (eden, heap, stderr):
        categories.update(source['categories'])
    crash['categories'] = dict(categories)
    crash['all_log_levels'] = eden['all_log_levels']
    crash['launch_settings'] = stderr['launch_settings']
    crash['precise_events'] = {name: [event for source in (eden, heap, stderr) for event in source['precise_events'].get(name, [])]
                               for name in rules}
    phase_starts = [index for index, phase in enumerate(heap['phases']) if phase['phase'] == 'session_start']
    assert len(phase_starts) == len(crash['game_launches']) == len(crash['shader_cache_ready']) == len(crash['environment_blocks'])
    performance_starts = [event['line'] for event in stderr['launch_settings'] if 'Performance:' in event['text']]
    assert len(performance_starts) == len(phase_starts)
    for ordinal, index in enumerate(phase_starts):
        phases = heap['phases'][index:phase_starts[ordinal+1] if ordinal+1 < len(phase_starts) else None]
        begin = crash['game_launches'][ordinal]
        final = ordinal == len(phase_starts)-1
        end = next((event for event in crash['session_events'] if event['kind'] == 'END' and event['line'] > begin['line']), None)
        next_eden_line = crash['game_launches'][ordinal+1]['line'] if not final else 10**12
        heap_end_line = heap['phases'][phase_starts[ordinal+1]]['line'] if not final else 10**12
        stderr_end_line = performance_starts[ordinal+1] if not final else 10**12
        samples = [sample['values'] for sample in heap['frames'] if phases[0]['line'] <= sample['line'] < heap_end_line]
        memories = [event for event in stderr['memory'] if performance_starts[ordinal] <= event['line'] < stderr_end_line]
        period_events = {}
        for category in ('mesh_skipped','native_graphics_failed','native_compute_rejected'):
            # Full event counts are extracted separately below, not inferred from first/last examples.
            period_events[category] = []
        statistics_data = {'samples': len(samples)}
        if samples:
            statistics_data.update(median_sample_fps=statistics.median(s['fps'] for s in samples),
                min_sample_fps=min(s['fps'] for s in samples), max_sample_fps=max(s['fps'] for s in samples),
                worst_frame_ms=max(s['worst_ms'] for s in samples),
                weighted_fps=sum(s['frames'] for s in samples)/sum(s['seconds'] for s in samples),
                recorded_sample_seconds=sum(s['seconds'] for s in samples))
        # Eden's clock is app elapsed time. Heap phases have a separate monotonic clock;
        # report their exact offsets from the matching heap session-start only.
        launch = {'report': crash['report'], 'launch_ordinal_within_app': ordinal+1,
            'eden_begin': begin, 'normal_end': end if end and end['line'] < next_eden_line else None,
            'duration_to_recorded_end_seconds': (end['app_seconds'] - begin['app_seconds']) if end and end['line'] < next_eden_line else
                crash['app_age_seconds'] - begin['app_seconds'],
            'end_kind': 'normal return to menu' if end and end['line'] < next_eden_line else 'fatal report',
            'phases': [phase | {'seconds_from_heap_session_start': (phase['mono_ns']-phases[0]['mono_ns'])/1e9} for phase in phases],
            'shader_cache_ready': crash['shader_cache_ready'][ordinal],
            'environment': crash['environment_blocks'][ordinal], 'memory_snapshots': memories,
            'fps_log_samples': statistics_data, 'eden_line_range': [begin['line'], next_eden_line if not final else None]}
        launches.append(launch)

# Get exact launch-local event frequencies and endpoints without mixing sessions or levels.
for launch in launches:
    relative = launch['eden_begin']['file']
    begin, end = launch['eden_line_range']
    counters, first, last = Counter(), {}, {}
    regexes = {'mesh_skipped': 'Draw skipped (EDEN_NX2_NO_MESH)',
               'native_graphics_failed': 'Native graphics draw failed',
               'native_compute_rejected': 'Native compute shader rejected'}
    for number, line in enumerate((root / relative).read_text().splitlines(), 1):
        if number < begin or end is not None and number >= end:
            continue
        for key, phrase in regexes.items():
            if phrase in line:
                match = clock.match(line)
                event = {'file': relative, 'line': number, 'app_seconds': float(match[1]) if match else None, 'text': line[:1800]}
                counters[key] += 1
                first.setdefault(key, event)
                last[key] = event
    launch['logged_event_counts'] = dict(counters)
    launch['first_logged_events'] = first
    launch['last_logged_events'] = last

coverage['category_counts_all_files'] = dict(sum((Counter(value['categories']) for value in evidence.values()), Counter()))
coverage['identical_file_hash_groups'] = [names for names in duplicates.values() if len(names)>1]
coverage['notes'] += ['Hang-watch/timeout mention counts include settings and API arguments; precise warning/event counters are separate.',
    'A sparse fallback counter is only a CreateImage fallback log; unbacked mention totals also include views/targets.',
    'Log verbosity differs sharply: native draw-failure Debug counts cannot be used as cross-run operation rates.',
    'Current heap/stderr files are residual restart snapshots, not additional completed gameplay trials.']
timeline['launches'] = launches
timeline['notes'] = ['Console wall times are kept as logged; no UTC conversion or timezone assumption.',
    'Approximate wall times derived from rounded app ages have at least one-second uncertainty.',
    'Heap phase offsets use the heap monotonic session-start; stderr memory/cache events have line ordering, not fabricated times.',
    'All FPS values below are samples from historic Test3 logs, not measurements of public release or Test4-A.']
(scratch / 'log-coverage.json').write_text(json.dumps(coverage, indent=2)+'\n')
(scratch / 'log-file-evidence.json').write_text(json.dumps(evidence, indent=2)+'\n')
(scratch / 'session-timelines.json').write_text(json.dumps(timeline, indent=2)+'\n')
print(json.dumps({'status':'pass','exit_code':0,'files_verified':len(coverage['manifest']),
                  'launch_timelines':len(launches),'precise_counts':dict(all_new)}))
