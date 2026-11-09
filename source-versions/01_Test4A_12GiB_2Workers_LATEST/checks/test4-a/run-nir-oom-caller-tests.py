"""Exercise all three copy-entry consumers with the actual NIR implementation."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--stage', choices=['before', 'after'], required=True)
parser.add_argument('--build-dir', type=Path, default=Path('build-nir-oom'))
parser.add_argument('--output-dir', type=Path, default=Path('nir-oom-results'))
args = parser.parse_args()
build_dir = args.build_dir.resolve()
out = args.output_dir.resolve()
out.mkdir(parents=True, exist_ok=True)
target = 'test4a_nir_oom_baseline' if args.stage == 'before' else 'test4a_nir_oom'
results = []
for scenario in ['store', 'load', 'copy']:
    for mode in range(4):
        for nested in range(2):
            env = dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',
                       UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1')
            command = [str(build_dir / 'src/compiler/nir' / target),
                       str(mode), str(nested), scenario]
            completed = subprocess.run(command, text=True, capture_output=True,
                                       env=env, timeout=60)
            log = out / f'nir-oom-callers-{args.stage}-{scenario}-{mode}-{nested}.log'
            log.write_text(completed.stdout + completed.stderr)
            expected_failure = args.stage == 'before' and mode != 0
            matched = (completed.returncode != 0) == expected_failure
            results.append({'scenario': scenario, 'mode': mode, 'nested': nested,
                            'exit_code': completed.returncode,
                            'expected_failure': expected_failure,
                            'expected_result_observed': matched,
                            'log': log.name, 'stdout': completed.stdout.strip()})
passed = all(case['expected_result_observed'] for case in results)
result = {'status': 'pass' if passed else 'fail', 'exit_code': 0 if passed else 1,
          'stage': args.stage, 'target': target, 'cases': results,
          'sanitizers': ['address', 'undefined'],
          'checks': ['NIR validation', 'control-flow metadata', 'semantic result 2087',
                     'all three copy-entry consumers', 'partial progress',
                     'initial state allocation failure leaves IR unchanged', 'cleanup']}
(out / f'nir-oom-callers-{args.stage}.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(result['exit_code'])
