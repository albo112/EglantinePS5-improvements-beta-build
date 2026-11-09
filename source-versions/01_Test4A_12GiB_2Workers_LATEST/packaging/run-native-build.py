from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, os, subprocess, time

root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
out = Path('/mnt/c/Users/Doni/Documents/Codex/2026-11-06/ca/work/test4-a')
receipt = out/'native-build.json'
result = {'status': 'waiting-for-driver', 'started_utc': datetime.now(timezone.utc).isoformat()}
def save():
    temp = receipt.with_suffix('.tmp')
    temp.write_text(json.dumps(result, indent=2)+'\n')
    temp.replace(receipt)
save()
while True:
    driver = json.loads((out/'driver-build.json').read_text())
    if driver['status'] != 'running':
        assert driver['exit_code'] == 0, driver
        break
    time.sleep(5)
def hashes():
    files = []
    for folder in ['headless', 'src', 'Eglantine/src', 'tools/eglantine-patches',
                   'tools/patch-radv-series', 'tools/radv-patches']:
        files.extend(p for p in (root/folder).rglob('*') if p.is_file())
    files.extend(root/'tools'/n for n in ['patch-radv-series.py','patch-radv-wsi.py','patch-radv-memory-report.py'])
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
for command in [['git','diff','--check'], ['git','-C','Eglantine','diff','--check']]:
    subprocess.run(command, cwd=root, check=True)
result.update(status='building', source_before=hashes(), command=['bash','tools/ci/build-release.sh'])
save()
env = dict(os.environ, JOBS='3', RADV_BUILD_JOBS='2', CCACHE_MAXSIZE='4G')
env.pop('EDEN_DEV_CHECKOUT', None)
with (out/'native-build.log').open('w') as log:
    r = subprocess.run(result['command'], cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
result['source_after'] = hashes()
result['source_unchanged_during_build'] = result['source_before'] == result['source_after']
result['exit_code'] = r.returncode or int(not result['source_unchanged_during_build'])
result['status'] = 'pass' if result['exit_code'] == 0 else 'fail'
result['finished_utc'] = datetime.now(timezone.utc).isoformat()
save()
raise SystemExit(result['exit_code'])
