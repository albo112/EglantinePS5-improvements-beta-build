from datetime import datetime, timezone
from pathlib import Path
import json, os, subprocess

root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
out = Path('/mnt/c/Users/Doni/Documents/Codex/2026-11-06/ca/work/test4-a')
command = ['bash', 'tools/build-radv-dependencies.sh']
result = {'command': command, 'started_utc': datetime.now(timezone.utc).isoformat(), 'status': 'running'}
receipt = out/'driver-build.json'
receipt.write_text(json.dumps(result, indent=2))
env = dict(os.environ, RADV_BUILD_JOBS='2', JOBS='2', CCACHE_MAXSIZE='4G')
with (out/'driver-build.log').open('w') as log:
    r = subprocess.run(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
result.update(status='pass' if r.returncode == 0 else 'fail', exit_code=r.returncode,
              finished_utc=datetime.now(timezone.utc).isoformat())
receipt.write_text(json.dumps(result, indent=2)+'\n')
raise SystemExit(r.returncode)
