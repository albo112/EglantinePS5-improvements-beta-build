import argparse
import json
from pathlib import Path
import hashlib, os, subprocess

p = argparse.ArgumentParser()
p.add_argument('--stage', choices=['source', 'native'], required=True)
a = p.parse_args()
root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
out = Path('/mnt/c/Users/Doni/Documents/Codex/2026-11-06/ca/work/test4-a')
checks = ['check-heap-growth.py', 'check-performance-settings.py'] if a.stage == 'source' else [
    'check-staging-pressure.py', 'check-integer-buffer-clear.py', 'check-radv-native.py',
    'check-native-gpu-thread.py', 'check-gpu-sync-stop.py', 'check-gpu-producer-stop.py',
    'check-transient-images.py', 'check-sparse-header.py']
results = []
for name in checks:
    with (out/(name+'.log')).open('w') as log:
        command = ['python3', '-B', str(root/'tools'/name)]
        if name == 'check-sparse-header.py':
            command.append(str(Path((root/'.local/headless-cache').read_text().strip())/'native-local'))
        env = dict(os.environ, TSAN_OPTIONS='memory_limit_mb=1536')
        r = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
    results.append({'check': name, 'exit_code': r.returncode, 'log': name+'.log'})
    if a.stage == 'native':
        results[-1]['script_sha256'] = hashlib.sha256((root/'tools'/name).read_bytes()).hexdigest()
    print(json.dumps(results[-1]), flush=True)
result = {'status': 'pass' if all(r['exit_code'] == 0 for r in results) else 'fail',
          'exit_code': int(any(r['exit_code'] for r in results)), 'stage': a.stage, 'checks': results,
          'host_tsan_options': 'memory_limit_mb=1536'}
(out/f'project-checks-{a.stage}.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result), flush=True)
raise SystemExit(result['exit_code'])
