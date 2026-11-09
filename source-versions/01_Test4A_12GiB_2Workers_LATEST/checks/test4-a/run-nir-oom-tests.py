import argparse
import json
import os
from pathlib import Path
import subprocess

p = argparse.ArgumentParser()
p.add_argument('--stage', choices=['before', 'after'], required=True)
a = p.parse_args()
root = Path('/var/lib/eglantine-build/zelda-test4-a/mesa-oom-host')
out = Path('/mnt/c/Users/Doni/Documents/Codex/2026-11-06/ca/work/test4-a')
results = []
for mode in range(4):
    for nested in range(2):
        env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1')
        command = [str(root / 'build/src/compiler/nir/test4a_nir_oom'), str(mode), str(nested)]
        r = subprocess.run(command, text=True, capture_output=True, env=env, timeout=60)
        log = out / f'nir-oom-{a.stage}-{mode}-{nested}.log'
        log.write_text(r.stdout + r.stderr)
        results.append({'mode': mode, 'nested': nested, 'exit_code': r.returncode,
                        'log': log.name, 'stdout': r.stdout.strip()})
result = {'status': 'pass' if all(r['exit_code'] == 0 for r in results) else 'fail',
          'exit_code': int(any(r['exit_code'] for r in results)), 'stage': a.stage,
          'cases': results, 'sanitizers': ['address', 'undefined'],
          'checks': ['NIR validation', 'control-flow metadata', 'semantic result 2087', 'cleanup']}
(out / f'nir-oom-{a.stage}.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(result['exit_code'])
