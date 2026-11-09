"""Run every verification script supplied in the exact Test3 source archive."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--stage', choices=('baseline', 'final'), required=True)
args = parser.parse_args()
scratch = Path(__file__).parent
supplied = scratch / 'inputs/test3-sources/checks'
checks = scratch / 'checks/supplied'
for path in supplied.rglob('*'):
    if path.is_file():
        target = checks / path.relative_to(supplied)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
root = Path.cwd()
commands = []
for path in sorted(checks.glob('check-*.py')):
    assert path.read_bytes() == (supplied / path.name).read_bytes()
    command = ['python3', '-B', str(path)]
    if path.name == 'check-gpu-memory-ranges.py':
        command += ['--source', 'Eglantine', '--applied', '--patch',
                    str(root / 'tools/eglantine-patches/0429-gpu-memory-range-guards.patch'),
                    '--work-dir', str(scratch / ('gpu-ranges-' + args.stage)),
                    '--evidence', str(scratch / ('gpu-ranges-' + args.stage + '.json'))]
    commands.append(command)
assert len(commands) == 7
commands.append(['python3', '-B', 'tools/check-fence-requirements.py'])
results = []
for command in commands:
    process = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    item = {'command': command, 'exit_code': process.returncode, 'output': process.stdout.strip(),
            'script_sha256': hashlib.sha256(Path(command[2]).read_bytes()).hexdigest()}
    results.append(item)
    print(json.dumps({'check': Path(command[2]).name, 'exit_code': process.returncode,
                      'output': item['output'][-700:]}), flush=True)
target = scratch / ('supplied-checks-' + args.stage + '.json')
target.write_text(json.dumps(results, indent=2) + '\n')
passed = all(item['exit_code'] == 0 for item in results)
print(json.dumps({'status': 'pass' if passed else 'fail', 'exit_code': 0 if passed else 1,
                  'supplied_scripts': 7, 'additional_fence_check': 1, 'stage': args.stage}))
raise SystemExit(0 if passed else 1)
