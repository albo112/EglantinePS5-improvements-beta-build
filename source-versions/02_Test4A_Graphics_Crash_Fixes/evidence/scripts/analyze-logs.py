"""Inventory and classify every byte of the supplied Logs3/4/5 without executing it."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime, timedelta
import hashlib
import json
import re
import statistics

scratch = Path(__file__).resolve().parent
root = scratch / 'inputs/logs-archive'
patterns = {
    'mesh_skipped': r'Draw skipped \(EDEN_NX2_NO_MESH\)',
    'native_graphics_failed': r'Native graphics draw failed',
    'native_compute_rejected': r'Native compute shader rejected',
    'image_allocation_failed': r'(?:image.{0,80}allocat.{0,80}(?:fail|refus)|allocat.{0,80}image.{0,80}(?:fail|refus)|failed to allocate.{0,40}image)',
    'unbacked_sparse_image': r'(?:unbacked.{0,60}image|image.{0,60}unbacked)',
    'vulkan_oom': r'VK_ERROR_OUT_OF_(?:DEVICE|HOST)_MEMORY|VkResult=-[12]\b',
    'heap_failure': r'EDEN_HEAP_FAILURE',
    'bad_alloc': r'std::bad_alloc|heap exhausted',
    'allocation_failure': r'allocation_failure|allocat.{0,80}(?:failed|failure|refused)',
    'pipeline_failure': r'(?:pipeline.{0,90}(?:failed|failure|refused)|(?:failed|refused).{0,90}pipeline)',
    'shader_failure': r'(?:shader.{0,90}(?:failed|failure|rejected)|(?:failed|rejected).{0,90}shader)',
    'gpu_hang_watch': r'HANG_WATCH|hang.watch|GPU.{0,50}stalled|GPU stall|HANGWATCH',
    'timeout': r'timeout|timed out',
    'malformed_commands': r'unknown host method|invalid engine|unimplemented engine|MME.{0,80}(?:out of bounds|underflow)|FIFO underflow',
    'shader_cache_ready': r'Shader cache ready:',
    'shader_cache_progress': r'Shader cache:',
    'pipeline_builder_count': r'Pipeline builders:',
    'crash_notice': r'EDEN_CRASH\b|crash report',
    'shutdown_or_leave': r'EDEN_GAME_SESSION_END|EDEN_GAME_VISIBLE|game finished|game stopped|returning to|the app closes|then:|EDEN_EGL_CLOSED',
}
compiled = {name: re.compile(pattern, re.I) for name, pattern in patterns.items()}
clock = re.compile(r'^\[\s*(\d+\.\d+)\]')
location = re.compile(r'((?:build/)?(?:[\w.-]+/)+[\w.-]+\.(?:cpp|h|inc)):(\d+):([^:]+):')
phase_pattern = re.compile(r'EDEN_STAGE backend=(\S+) phase=(\S+) mono_ns=(\d+)')
session_pattern = re.compile(r'EDEN_GAME_SESSION_(BEGIN|END)\s+(\d+)')
frame_pattern = re.compile(r'^EDEN_VULKAN_FRAME ')
memory_pattern = re.compile(r'EDEN_MEMORY pool largest free block (\d+) MiB, short=(\d+); the guest\'s memory holds (\d+) MiB \(the kernel maps (\d+) MiB\)')

def event(relative, number, line):
    match = clock.match(line)
    return {'file': relative, 'line': number,
            'app_seconds': float(match[1]) if match else None, 'text': line[:1800]}

files = []
evidence = {}
all_categories = Counter()
for path in sorted(root.rglob('*')):
    if not path.is_file():
        continue
    relative = path.relative_to(root).as_posix()
    digest, count, bytes_read = hashlib.sha256(), 0, 0
    counters, severity, locations = Counter(), Counter(), Counter()
    examples = {name: [] for name in patterns}
    last = {}
    errors, rejects = Counter(), Counter()
    sessions, phases, memory, frames, ready, environments = [], [], [], [], [], []
    env = None
    heap_requests = Counter()
    utf8_errors = []
    first_app_seconds = last_app_seconds = None
    with path.open('rb') as stream:
        for number, raw in enumerate(stream, 1):
            digest.update(raw)
            count, bytes_read = number, bytes_read + len(raw)
            try:
                line = raw.decode('utf-8').rstrip('\r\n')
            except UnicodeDecodeError:
                utf8_errors.append(number)
                line = raw.decode('utf-8', errors='replace').rstrip('\r\n')
            timed = clock.match(line)
            if timed:
                if first_app_seconds is None:
                    first_app_seconds = float(timed[1])
                last_app_seconds = float(timed[1])
            mark = None
            for name, pattern in compiled.items():
                if pattern.search(line):
                    counters[name] += 1
                    if mark is None:
                        mark = event(relative, number, line)
                    if len(examples[name]) < 3:
                        examples[name].append(mark)
                    last[name] = mark
            level = re.search(r'<(Critical|Error|Warning)>', line)
            if level:
                severity[level[1]] += 1
                source = location.search(line)
                if source:
                    locations[source[1] + ':' + source[3]] += 1
                message = line.split(':', 4)[-1].strip()
                normalized = re.sub(r'0x[0-9a-fA-F]+|\b[0-9a-fA-F]{12,16}\b', '<hex>', message)
                normalized = re.sub(r'\b\d+\b', '<n>', normalized)
                errors[normalized[:700]] += 1
            if 'Native compute shader rejected:' in line:
                reason = line.split('Native compute shader rejected:', 1)[1].strip()
                reason = re.sub(r'0x[0-9a-fA-F]+', '<hex>', reason)
                rejects[reason] += 1
            session = session_pattern.search(line)
            if session:
                sessions.append(event(relative, number, line) | {'kind': session[1], 'session': int(session[2])})
            phase = phase_pattern.search(line)
            if phase:
                phases.append(event(relative, number, line) | {'backend': phase[1], 'phase': phase[2], 'mono_ns': int(phase[3])})
            allocation = re.search(r'EDEN_HEAP_FAILURE requested=(\d+)', line)
            if allocation:
                heap_requests[int(allocation[1])] += 1
            mem = memory_pattern.search(line)
            if mem:
                memory.append(event(relative, number, line) | dict(zip(
                    ('largest_free_mib', 'short', 'guest_mib', 'kernel_mapped_mib'), map(int, mem.groups()))))
            if frame_pattern.match(line):
                values = {key: float(value) for key, value in re.findall(r'(\w+)=([-+]?\d+(?:\.\d+)?)', line)}
                frames.append(event(relative, number, line) | {'values': values})
            if 'Shader cache ready:' in line:
                match = re.search(r'Shader cache ready: (\d+) pipelines in (\d+) ms', line)
                ready.append(event(relative, number, line) | ({'pipelines': int(match[1]), 'milliseconds': int(match[2])} if match else {}))
            if line.startswith('EDEN_ENV_TITLE '):
                key, value = line.removeprefix('EDEN_ENV_TITLE ').split('=', 1)
                if env is None or key in env['values']:
                    env = {'file': relative, 'first_line': number, 'values': {}}
                    environments.append(env)
                env['values'][key] = value
                env['last_line'] = number
            else:
                env = None
    assert bytes_read == path.stat().st_size
    entry = {'path': str(path), 'relative': relative, 'bytes': bytes_read, 'lines': count,
             'sha256': digest.hexdigest(), 'read_complete': True, 'utf8_error_lines': utf8_errors}
    files.append(entry)
    all_categories.update(counters)
    evidence[relative] = {'categories': dict(counters), 'examples': {name: value for name, value in examples.items() if value},
        'last_examples': last, 'severity': dict(severity), 'top_error_sources': locations.most_common(20),
        'top_normalized_errors': errors.most_common(20), 'compute_rejection_reasons': rejects.most_common(),
        'sessions': sessions, 'phases': phases, 'memory': memory, 'frames': frames, 'shader_cache_ready': ready,
        'environment_blocks': environments, 'heap_failure_requests': dict(heap_requests),
        'first_app_seconds': first_app_seconds, 'last_app_seconds': last_app_seconds}

crashes = []
for entry in files:
    if not re.fullmatch(r'crash-\d{8}-\d{6}\.txt', Path(entry['relative']).name):
        continue
    path = Path(entry['path'])
    text = path.read_text()
    fields = {line.split(': ', 1)[0]: line.split(': ', 1)[1] for line in text.splitlines() if ': ' in line}
    time = re.search(r'time: ([\d-]+ [\d:]+), (\d+) s after', text)
    wall, age = datetime.fromisoformat(time[1]), int(time[2])
    prefix = entry['relative'].removesuffix('.txt')
    companions = [prefix + suffix for suffix in ('-eden_log.txt', '-heap.log', '-stderr.log')]
    assert all(name in evidence for name in companions)
    eden, heap, stderr = [evidence[name] for name in companions]
    begins = [value for value in eden['sessions'] if value['kind'] == 'BEGIN']
    app_start = wall - timedelta(seconds=age)
    for value in eden['sessions']:
        if value['app_seconds'] is not None:
            value['approx_wall_time'] = (app_start + timedelta(seconds=value['app_seconds'])).isoformat(sep=' ', timespec='milliseconds')
    memory_match = re.search(r'memory: largest free block (\d+) MiB of (\d+) MiB, heap (\d+) MiB and (\d+) MiB in (\d+) large blocks', text)
    combined = Counter()
    for values in (eden, heap, stderr):
        combined.update(values['categories'])
    values = [record['values'] for record in heap['frames'] if 'fps' in record['values']]
    fps = {'samples': len(values)}
    if values:
        fps.update(min_sample_fps=min(v['fps'] for v in values), median_sample_fps=statistics.median(v['fps'] for v in values),
                   max_sample_fps=max(v['fps'] for v in values), worst_frame_ms=max(v['worst_ms'] for v in values),
                   total_sample_seconds=sum(v['seconds'] for v in values),
                   weighted_fps=sum(v['frames'] for v in values)/sum(v['seconds'] for v in values))
    crashes.append({'report': entry['relative'], 'sha256': entry['sha256'], 'version': fields['version'],
        'wall_time_as_logged': wall.isoformat(sep=' '), 'app_age_seconds': age,
        'approx_app_start_wall': app_start.isoformat(sep=' '), 'what': fields['what'], 'where': fields['where'],
        'thread': fields['thread'], 'running': fields['running'], 'memory': dict(zip(
            ('largest_free_mib', 'pool_mib', 'heap_mib', 'large_mib', 'large_blocks'), map(int, memory_match.groups()))) if memory_match else fields.get('memory'),
        'game_launches': begins, 'session_events': eden['sessions'],
        'final_game_session_age_seconds_approx': age-begins[-1]['app_seconds'] if begins else None,
        'categories': dict(combined), 'shader_cache_ready': stderr['shader_cache_ready'],
        'environment_blocks': heap['environment_blocks'], 'phases': heap['phases'],
        'memory_samples': stderr['memory'], 'heap_failure_requests': stderr['heap_failure_requests'],
        'fps_log_samples': fps, 'companion_files': companions})

coverage = {'status': 'pass', 'exit_code': 0, 'files': len(files), 'bytes': sum(f['bytes'] for f in files),
            'lines': sum(f['lines'] for f in files), 'crash_groups': len(crashes),
            'game_launches_in_crash_captures': sum(len(c['game_launches']) for c in crashes),
            'folders': {folder.name: {'files': sum(f['relative'].startswith(folder.name+'/') for f in files),
                'bytes': sum(f['bytes'] for f in files if f['relative'].startswith(folder.name+'/')),
                'lines': sum(f['lines'] for f in files if f['relative'].startswith(folder.name+'/'))}
                for folder in sorted(root.iterdir()) if folder.is_dir()},
            'category_counts_all_files': dict(all_categories), 'manifest': files,
            'notes': ['All paths are source data only; no log content executed.',
                      'Category counts count stored lines, not necessarily independent runtime events.',
                      'Wall times remain exactly as console logged; inferred startup times have rounded-second uncertainty.',
                      'stderr and heap lines without a clock cannot be assigned invented absolute timestamps.']}
(scratch / 'log-coverage.json').write_text(json.dumps(coverage, indent=2) + '\n')
(scratch / 'log-file-evidence.json').write_text(json.dumps(evidence, indent=2) + '\n')
(scratch / 'session-timelines.json').write_text(json.dumps({'status': 'pass', 'exit_code': 0, 'crashes': crashes}, indent=2) + '\n')
print(json.dumps({key: coverage[key] for key in ('status','exit_code','files','bytes','lines','crash_groups','game_launches_in_crash_captures','folders')}))
