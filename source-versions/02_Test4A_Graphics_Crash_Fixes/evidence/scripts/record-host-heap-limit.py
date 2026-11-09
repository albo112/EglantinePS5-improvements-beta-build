from pathlib import Path
import hashlib, json, subprocess

out = Path('/mnt/c/Users/Doni/Documents/Codex/2026-11-06/ca/work/test4-a')
root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
heap_files = ['headless/heap_arenas.inc', 'third_party/app_heap.c']
subprocess.run(['runuser', '-u', 'eglantine-build', '--', 'git', '-C', str(root),
                'diff', '--exit-code', 'HEAD', '--', *heap_files], check=True)
first = (out/'check-heap-growth-first-attempt.log').read_text()
retry = (out/'check-heap-growth.py.log').read_text()
kernel = subprocess.check_output(['dmesg'], text=True)
oom = [line for line in kernel.splitlines() if 'Out of memory: Killed process' in line and '(heap-thread)' in line]
assert oom and 'exit -9' in first
assert 'TimeoutExpired' in retry and 'timed out after 900 seconds' in retry
for text in [first, retry]:
    assert '[checked] ' in text and 'heap by pieces:' in text and '[checked] whole heap at once:' in text
    assert 'runtime error:' not in text and 'WARNING: ThreadSanitizer:' not in text
source = json.loads((out/'project-checks-source.json').read_text())
assert source['checks'] == [
    {'check':'check-heap-growth.py','exit_code':1,'log':'check-heap-growth.py.log'},
    {'check':'check-performance-settings.py','exit_code':0,'log':'check-performance-settings.py.log'}]
result = {'status':'unavailable', 'record_exit_code':0, 'test_exit_code':1,
          'scope':'Optional full unchanged-heap ThreadSanitizer stress test; not a supplied Test3 check',
          'first_attempt':{'exit_code':1,'child_exit_code':-9,'kernel_oom':True,'kernel_records':oom},
          'retry':{'exit_code':1,'timeout_seconds':900,'exception':'TimeoutExpired',
                   'TSAN_OPTIONS':'memory_limit_mb=1536'},
          'ubsan_modes':{'pieces_exit_code':0,'whole_exit_code':0,'passed_in_both_attempts':True},
          'heap_runtime_source_changed':False,
          'heap_diff_from_pinned_exit_code':0,
          'heap_source_sha256':{name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in heap_files},
          'limitation':'Full heap ThreadSanitizer validation did not finish on this 3818MiB WSL host; no race-free claim.',
          'evidence_sha256':{name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in [
              'check-heap-growth-first-attempt.log','check-heap-growth.py.log','project-checks-source.json']}}
(out/'host-heap-test-limits.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
