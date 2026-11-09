"""Read-only classification of every newly supplied graphics/memory log."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import statistics

scratch = Path(__file__).resolve().parent
logs = scratch / 'inputs/logs-archive'
patterns = {
    'no_mesh_skip': r'Draw skipped \(EDEN_NX2_NO_MESH\)',
    'native_draw_failed': r'Native graphics draw failed',
    'compute_rejected': r'Native compute shader rejected',
    'image_over_budget': r'is over the memory budget; allocating it anyway',
    'image_unbacked': r'unbacked sparse image',
    'image_refused': r'EDEN_IMAGE_REFUSED|Image .* failed: ',
    'buffer_failure': r'CreateBuffer failed|CreateBuffer:.*(?:fail|OUT_OF)',
    'vulkan_device_oom': r'VK_ERROR_OUT_OF_DEVICE_MEMORY|VkResult=-2',
    'heap_failure': r'EDEN_HEAP_FAILURE',
    'allocation_failure': r'allocation failure:',
    'swap_reclaim': r'EDEN_SWAP reclaim for graphics:',
    'swap_reclaim_zero': r'EDEN_SWAP reclaim for graphics: 0 slots',
    'hang_or_timeout_warning': r'<Warning>.*(?:\bhang\b|\bstall\b|\btimeout\b)',
    'hang_watch_back_report': r'Hang watch: the back runs',
}
compiled = {name: re.compile(pattern, re.I) for name, pattern in patterns.items()}
result = {'status': 'pass', 'exit_code': 0, 'patterns': patterns, 'files': {}, 'raw_totals': {},
          'unique_content_totals': {}, 'warning_error_signatures': {}, 'crashes': []}
totals, unique_totals, signatures = Counter(), Counter(), Counter()
seen = set()
for path in sorted(logs.rglob('*')):
    if not path.is_file():
        continue
    data = path.read_bytes()
    text = data.decode('utf-8-sig')
    lines = text.splitlines()
    digest = hashlib.sha256(data).hexdigest()
    counts, examples, env, frames, memory, reclaims = Counter(), {}, {}, [], [], []
    for number, line in enumerate(lines, 1):
        for category, pattern in compiled.items():
            if pattern.search(line):
                counts[category] += 1
                examples.setdefault(category, [])
                if len(examples[category]) < 3:
                    examples[category].append({'line': number, 'text': line[:1600]})
        if match := re.search(r'EDEN_ENV_TITLE (\w+)=(.*)', line):
            env[match[1]] = match[2]
        if line.startswith('EDEN_VULKAN_FRAME '):
            values = dict(re.findall(r'(\w+)=([\d.]+)', line))
            frames.append({'line': number, **{key: float(value) for key, value in values.items()}})
        if match := re.search(r"EDEN_MEMORY pool largest free block (\d+) MiB, short=(\d+); the guest's memory holds (\d+) MiB \(the kernel maps (\d+) MiB\)", line):
            memory.append({'line': number, **dict(zip(('largest_mib', 'short', 'guest_mib', 'mapped_mib'), map(int, match.groups())))})
        if match := re.search(r'EDEN_SWAP reclaim for graphics: (\d+) slots, (\d+) MiB given back \(asked (\d+) MiB\)', line):
            reclaims.append({'line': number, **dict(zip(('slots', 'given_mib', 'asked_mib'), map(int, match.groups())))})
        if re.search(r'<(?:Error|Warning|Critical)>', line) and re.search(r'Render\.Vulkan|Shader|HW\.GPU', line):
            message = re.sub(r'^\[.*?\] ', '', line)
            message = re.sub(r'0x[0-9a-fA-F]+', '0x#', message)
            message = re.sub(r'\b\d+\b', '#', message)
            signatures[message[:400]] += 1
    record = {'sha256': digest, 'bytes': len(data), 'lines': len(lines), 'read_complete': True,
              'duplicate_content': digest in seen, 'counts': dict(counts), 'examples': examples,
              'title_environment': env, 'frame_samples': len(frames), 'memory_samples': memory,
              'reclaim_samples': reclaims}
    if frames:
        fps = [item['fps'] for item in frames]
        record['frame_summary'] = {'samples': len(fps), 'min': min(fps), 'median': statistics.median(fps),
                                   'max': max(fps), 'first': frames[0], 'last': frames[-1],
                                   'max_worst_ms': max(item['worst_ms'] for item in frames)}
    if re.fullmatch(r'crash-\d{8}-\d{6}\.txt', path.name):
        result['crashes'].append({'path': path.relative_to(logs).as_posix(),
            **{key: re.search(r'^' + key + r': (.*)$', text, re.M)[1]
               for key in ('version', 'time', 'what', 'where', 'thread', 'memory')}})
    result['files'][path.relative_to(logs).as_posix()] = record
    totals.update(counts)
    if digest not in seen:
        unique_totals.update(counts)
    seen.add(digest)
result['raw_totals'] = dict(totals)
result['unique_content_totals'] = dict(unique_totals)
result['warning_error_signatures'] = dict(signatures.most_common())
result['files_read'] = len(result['files'])
result['bytes_read'] = sum(item['bytes'] for item in result['files'].values())
(scratch / 'graphics-memory-audit.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps({key: result[key] for key in ('status', 'exit_code', 'files_read', 'bytes_read', 'raw_totals', 'unique_content_totals')}))
print(json.dumps({'top_signatures': dict(signatures.most_common(18))}))
