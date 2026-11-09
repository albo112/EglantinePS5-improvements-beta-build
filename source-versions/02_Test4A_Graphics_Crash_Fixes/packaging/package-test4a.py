"""Stage and validate the Test4-A ZIPs after a frozen, successful native build.

Default mode is read-only preflight. Use --package only after reviewing preflight;
--validate rechecks existing outputs. This script never installs to a console.
"""
from argparse import ArgumentParser
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
import ast
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile

SCRATCH = Path(__file__).resolve().parent
ROOT = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
OUTPUT = SCRATCH.parents[1] / 'outputs'
MAIN = 'EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes.zip'
SOURCES = 'EglantinePS5-Zelda-Test4-A-Source-Changes.zip'
RECEIPT = 'Zelda-Test4-A-Verification.json'
PROFILE = 'env-0400486024dec000.txt'
FRONTEND = '25cfc07be0a3675749adece5d012fdb916c4cd48'
CORE = '0ca2032bffc5f1a3fca75427f7d4a4718adda660'
TEST3_SYMBOL_SHA = '930886ee0b0301169b3977f830954702c7b55da7afa5dc1fbc6260b300458816'
NIR_EXPORT = ROOT.parent / 'mihawk-vulkan-review/.deps/work/radv-src/src/compiler/nir/nir_opt_copy_prop_vars.c'
NIR_HOST = ROOT.parent / 'mesa-oom-host/source/src/compiler/nir/nir_opt_copy_prop_vars.c'
NIR_DIAGNOSTIC = b'EglantinePS5 Test4-A: NIR copy propagation stopped on allocation failure; retaining valid shader IR'
REPORT_NAMES = ['Test4-A-README.md', 'Test4-A-Crash-Analysis.md', 'Test4-A-Changelog.md',
                'Test4-A-Validation.md', 'Test4-A-PS5-Testing.md',
                'Test4-A-Regression-Comparison.md', 'Test4-A-Source-and-Build.md']
OLD_OUTPUTS = {
    'EglantinePS5-Zelda-T34-RADV-fix.zip': 'f8354bb8a1b722c8a3755679ee2deab89b7377cb43c383e17a85b25e4e84d26e',
    'EglantinePS5-Zelda-Memory-Fix-Test2.zip': '1d18cae9fc27a8948b128c72c44e45b9a2b535d1043ca4bce491dbe3eb64d46f',
    'EglantinePS5-Zelda-Memory-Fix-Test2-sources.zip': '820dce248d2ca7e2e7d3a5dc08eb7dc0c3b36b2fb070d07366de5a3dc1eed87d',
    'EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes.zip': '55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7',
    'EglantinePS5-Zelda-Test3-Source-Changes.zip': '5a06546cec7c9314ddb7f45003988d87da0a4d7f90e4d047ca56fc8bd20ee1fb',
}
LIMITS = [
    'No Test4-A PS5 run, crash-free duration or sustained FPS has been measured.',
    'Cold/warm cache behavior, geometry, textures, brightness, flashes and GPU scheduling require console tests.',
    'Two generated-CPU/outside-eboot fault origins remain unresolved; fault-byte logging is diagnostic only.',
    'The NIR correction covers demonstrated allocation boundaries, not every compiler allocation site.',
    'Image refusal tests simulate device allocation; no physical PS5 recovery guarantee is claimed.',
    'Underlying shared-pool pressure and ineffective reclamation are not fully explained or eliminated.',
    'Native matrix translation, storage-pointer classification and binding-budget warnings remain unresolved.',
    'Optional full unchanged-heap TSan stress is incomplete: first host OOM, then a 900-second timeout. '
    'The heap check remains exit 1; both checked UBSan modes passed, and no heap race-free claim is made.',
    'The upstream CI route skips its full legacy source-check suite; separate supplied/focused checks are recorded.',
    'No remote dashboard, remote video or console connection is included; those remain Test4-B.',
]


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def file_sha(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def encode(data):
    return (json.dumps(data, indent=2) + '\n').encode()


def host_path(path):
    text = str(path).replace('\\', '/')
    return Path('/mnt/c' + text[2:]) if os.name != 'nt' and text.lower().startswith('c:/') else Path(text)


def run(command, **kwargs):
    return subprocess.check_output(command, cwd=ROOT, **kwargs)


def safe_name(name):
    path = PurePosixPath(name)
    assert not path.is_absolute() and '..' not in path.parts and '\\' not in name, name
    assert not name.lower().endswith(('.nup', '.nsp', '.xci', '.rar', 'prod.keys', 'title.keys')), name
    assert not any(part in {'PC-Live-Logs', 'sdk', 'firmware', 'keys', '__pycache__'} for part in path.parts), name


def originals():
    inventory = read(SCRATCH / 'input-inventory.json')
    assert len(inventory) == 4
    for item in inventory:
        assert file_sha(host_path(item['source'])) == item['archive_sha256'], item['source']
    for name, expected in OLD_OUTPUTS.items():
        assert file_sha(OUTPUT / name) == expected, name
    test3 = read(OUTPUT / 'Zelda-Test3-Verification.json')
    symbols = Path(test3['symbol_file'])
    assert file_sha(symbols) == TEST3_SYMBOL_SHA, symbols
    return inventory, test3, {str(symbols): TEST3_SYMBOL_SHA}


def optional_heap_limit(source_result):
    """Accept one documented host limitation without changing its failed test status."""
    assert source_result['status'] == 'fail' and source_result['exit_code'] == 1
    assert source_result['host_tsan_options'] == 'memory_limit_mb=1536'
    assert source_result['checks'] == [
        {'check': 'check-heap-growth.py', 'exit_code': 1, 'log': 'check-heap-growth.py.log'},
        {'check': 'check-performance-settings.py', 'exit_code': 0, 'log': 'check-performance-settings.py.log'},
    ]
    proof = read(SCRATCH / 'host-heap-test-limits.json')
    assert proof['status'] == 'unavailable' and proof['record_exit_code'] == 0 and proof['test_exit_code'] == 1
    first, retry, ubsan = proof['first_attempt'], proof['retry'], proof['ubsan_modes']
    assert first['exit_code'] == 1 and first['child_exit_code'] == -9 and first['kernel_oom'] is True
    assert first['kernel_records'] and all('Out of memory: Killed process' in line and '(heap-thread)' in line
                                         for line in first['kernel_records'])
    assert retry == {'exit_code': 1, 'timeout_seconds': 900, 'exception': 'TimeoutExpired',
                     'TSAN_OPTIONS': 'memory_limit_mb=1536'}
    assert ubsan == {'pieces_exit_code': 0, 'whole_exit_code': 0, 'passed_in_both_attempts': True}
    assert proof['heap_runtime_source_changed'] is False
    assert proof['heap_diff_from_pinned_exit_code'] == 0
    assert set(proof['heap_source_sha256']) == {'headless/heap_arenas.inc', 'third_party/app_heap.c'}
    for name, expected in proof['heap_source_sha256'].items():
        assert file_sha(ROOT / name) == expected
        assert sha(run(['git', 'show', 'HEAD:' + name])) == expected, ('Heap source differs from pinned HEAD', name)
    expected_logs = {'check-heap-growth-first-attempt.log', 'check-heap-growth.py.log', 'project-checks-source.json'}
    assert set(proof['evidence_sha256']) == expected_logs
    for name, expected in proof['evidence_sha256'].items():
        assert file_sha(SCRATCH / name) == expected, ('Changed heap limitation evidence', name)
    initial_log = (SCRATCH / 'check-heap-growth-first-attempt.log').read_text()
    retry_log = (SCRATCH / 'check-heap-growth.py.log').read_text()
    assert 'exit -9' in initial_log
    assert 'TimeoutExpired' in retry_log and 'timed out after 900 seconds' in retry_log
    for text in [initial_log, retry_log]:
        assert '[checked] ' in text and 'heap by pieces:' in text and '[checked] whole heap at once:' in text
        assert 'runtime error:' not in text and 'WARNING: ThreadSanitizer:' not in text
    return proof


def gates():
    inventory, test3, preserved_symbols = originals()
    assert run(['git', 'rev-parse', 'HEAD'], text=True).strip() == FRONTEND
    assert run(['git', '-C', 'Eglantine', 'rev-parse', 'HEAD'], text=True).strip() == CORE
    for command in (['git', 'diff', '--check'], ['git', '-C', 'Eglantine', 'diff', '--check']):
        run(command)
    build = read(SCRATCH / 'native-build.json')
    driver = read(SCRATCH / 'driver-build.json')
    assert build['status'] == 'pass' and build['exit_code'] == 0, 'Native build has not passed'
    assert driver['status'] == 'pass' and driver['exit_code'] == 0, 'Driver build has not passed'
    assert build['source_unchanged_during_build'] is True
    assert build['source_before'] == build['source_after']
    for name, expected in build['source_after'].items():
        assert file_sha(ROOT / name) == expected, ('Source changed after build', name)
    supplied = read(SCRATCH / 'supplied-checks-final.json')
    assert len(supplied) == 8 and all(item['exit_code'] == 0 for item in supplied)
    for item in supplied:
        assert file_sha(host_path(item['command'][2])) == item['script_sha256']
    focused = {}
    for name in ['no-mesh-boolean-result.json', 'nir-oom-after.json', 'nir-oom-callers-after.json',
                 'image-refusal-result.json', 'diagnostics-checks.json', 'native-source-provenance.json']:
        result = read(SCRATCH / name)
        assert result['status'] == 'pass' and result['exit_code'] == 0, name
        for path, expected in result.get('source_sha256', {}).items():
            assert file_sha(ROOT / path) == expected, ('Stale focused check', name, path)
        focused[name] = result
    assert len(focused['no-mesh-boolean-result.json']['cases']) == 8
    callers = focused['nir-oom-callers-after.json']['cases']
    assert len(callers) == 24 and all(case['exit_code'] == 0 for case in callers)
    assert focused['image-refusal-result.json']['stdout'].count('PASS:') == 16
    assert focused['diagnostics-checks.json']['bounded_draw_log'] == {
        'threads': 8, 'failures': 32768, 'lines': 40, 'exit_code': 0}
    assert focused['diagnostics-checks.json']['bounded_draw_paths'] == {
        'threads': 8, 'paths': 2, 'total_failures': 65536, 'lines': 80, 'exit_code': 0}
    assert focused['diagnostics-checks.json']['crash_report']['exit_code'] == 0
    provenance = focused['native-source-provenance.json']
    assert provenance['raw_core_files'] == len(provenance['raw_core_sha256']) == 10
    cache = Path((ROOT / '.local/headless-cache').read_text().strip())
    expected_files = set()
    for name, expected in provenance['raw_core_sha256'].items():
        for path in [ROOT / 'Eglantine/src' / name, cache / 'source/src' / name]:
            assert file_sha(path) == expected, ('Stale native source provenance', path)
            expected_files.add(str(path))
    native_targets = {str(cache / 'native-local/headless' / name) for name in
                      ['vulkan_rasterizer.cpp', 'vk_pipeline_cache_cost.cpp', 'vk_texture_cache_cost.cpp']}
    native_targets |= {str(ROOT / 'headless' / name) for name in ['main.cpp', 'crash_report.cpp']}
    assert set(provenance['generated_compile_targets']) == native_targets
    expected_files |= native_targets | {str(cache / 'native-local/compile_commands.json'),
                                        str(SCRATCH / 'check-native-source-provenance.py')}
    slot = provenance['slot_vector']
    recovery_header = cache / 'native-local/headless/recovery/common/slot_vector.h'
    assert slot['recovery_header'] == str(recovery_header)
    assert slot['compiled_dependencies'] > 0 and slot['original_header_dependencies'] == 0
    assert slot['generated_bytes_match'] is True
    expected_files |= {str(ROOT / 'Eglantine/src/common/slot_vector.h'),
                       str(ROOT / 'headless/slot_vector_recovery.cmake'), str(recovery_header)}
    assert len(expected_files) == len(provenance['current_file_sha256']) == 30
    assert expected_files == provenance['current_file_sha256'].keys()
    for name, expected in provenance['current_file_sha256'].items():
        assert file_sha(Path(name)) == expected, ('Changed native provenance input', name)
    project_sets = {
        'source': {'check-heap-growth.py', 'check-performance-settings.py'},
        'native': {'check-staging-pressure.py', 'check-integer-buffer-clear.py', 'check-radv-native.py',
                   'check-native-gpu-thread.py', 'check-gpu-sync-stop.py', 'check-gpu-producer-stop.py',
                   'check-transient-images.py', 'check-sparse-header.py'},
    }
    for stage, expected in project_sets.items():
        name = f'project-checks-{stage}.json'
        result = read(SCRATCH / name)
        assert {check['check'] for check in result['checks']} == expected
        assert len(result['checks']) == len(expected)
        if stage == 'source' and result['exit_code'] != 0:
            focused['host-heap-test-limits.json'] = optional_heap_limit(result)
        else:
            assert result['status'] == 'pass' and result['exit_code'] == 0, name
            assert all(check['exit_code'] == 0 for check in result['checks'])
        if stage == 'native':
            for check in result['checks']:
                assert file_sha(ROOT / 'tools' / check['check']) == check['script_sha256']
        focused[name] = result
    replay = read(SCRATCH / 'overlay-replay.json')
    assert replay['status'] == 'pass' and replay['exit_code'] == 0, 'Fresh overlay replay has not passed'
    focused['overlay-replay.json'] = replay
    export_sha, host_sha = file_sha(NIR_EXPORT), file_sha(NIR_HOST)
    assert export_sha == host_sha, 'Native export differs from the host-tested NIR implementation'
    elf = ROOT / 'build/headless-native/llvm-pie.elf'
    assert NIR_DIAGNOSTIC in elf.read_bytes(), 'Native ELF lacks the new bounded NIR diagnostic'
    focused['native-nir-implementation.json'] = {
        'status': 'pass', 'exit_code': 0, 'native_export': str(NIR_EXPORT),
        'host_tested_source': str(NIR_HOST), 'native_sha256': export_sha,
        'host_sha256': host_sha, 'bounded_diagnostic_present_in_native_elf': True,
    }
    report = read(SCRATCH / 'reports/report-status.json')
    assert report['status'] == 'pass' and report['report_count'] == 7
    assert report.get('for_package') is True and report.get('source_inventory_live') is True, \
        'Regenerate current reports with write-release-reports.py --for-package before packaging'
    for name in REPORT_NAMES:
        assert file_sha(SCRATCH / 'reports' / name) == report['files'][name]
    assert 'local build: Zelda Test4-A' in (ROOT / 'headless/main.cpp').read_text()
    return inventory, test3, preserved_symbols, build, driver, supplied, focused


def profiles(test3_path):
    source_archive = host_path(next(item['source'] for item in read(SCRATCH / 'input-inventory.json')
                                    if Path(item['source']).name.endswith('Test3-Source-Changes.zip')))
    with zipfile.ZipFile(test3_path) as old, zipfile.ZipFile(source_archive) as source:
        prettier = old.read('PPSA98515/' + PROFILE)
        faster = old.read('Zelda-faster-profile.txt')
        assert prettier == source.read('profiles/' + PROFILE)
        assert faster == source.read('profiles/zelda-faster-profile.txt')
    values = []
    for data in (prettier, faster):
        lines = data.decode().splitlines()
        profile = dict(line.split('=', 1) for line in lines)
        assert len(lines) == len(profile) == 49 and b'\r' not in data and data.endswith(b'\n')
        assert profile['EDEN_NX2_NO_MESH'] == '0'
        assert profile['EDEN_PS5_ZELDA_SAFE_MEMORY'] == '1'
        assert profile['EDEN_NX2_NATIVE_TABLES'] == profile['EDEN_NX2_PAIRED_POINTERS'] == '1'
        values.append(profile)
    assert {key for key in values[0] if values[0][key] != values[1][key]} == {
        'EDEN_NX2_RADV_MESH_COMPUTE_LONE', 'EDEN_NX2_QUERY_KEEP_PENDING'}
    return prettier, faster


def zip_manifest(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None, path
        entries = archive.infolist()
        assert len(entries) == len(set(archive.namelist()))
        result = {}
        for info in entries:
            safe_name(info.filename)
            assert not info.is_dir(), info.filename
            result[info.filename] = {'bytes': info.file_size, 'sha256': sha(archive.read(info)),
                                     'mode': info.external_attr >> 16}
        return result


def add(archive, name, data, mode=0o100644):
    safe_name(name)
    info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
    info.create_system = 3
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = mode << 16
    archive.writestr(info, data)


def source_files(inventory, test3, supplied, focused):
    old_path = host_path(next(item['source'] for item in inventory
                             if Path(item['source']).name.endswith('Test3-Source-Changes.zip')))
    with zipfile.ZipFile(old_path) as old:
        assert old.testzip() is None
        files = {name: old.read(name) for name in old.namelist()}
    core_patches = sorted((ROOT / 'tools/eglantine-patches').glob('*.patch'))
    assert len(core_patches) == 264, len(core_patches)
    for path in core_patches:
        files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for folder in ['tools/patch-radv-series', 'tools/radv-patches']:
        for path in sorted((ROOT / folder).rglob('*')):
            if path.is_file():
                files[path.relative_to(ROOT).as_posix()] = path.read_bytes()
    for name in ['patch-radv-series.py', 'patch-radv-wsi.py', 'patch-radv-memory-report.py',
                 'check-crash-report.py', 'check-fence-requirements.py', 'check-gpu-sync-stop.py',
                 'check-gpu-producer-stop.py', 'deps.json']:
        files['tools/' + name] = (ROOT / 'tools' / name).read_bytes()
    diff = run(['git', 'diff', '--binary', '--ignore-submodules=all', 'HEAD', '--', '.'])
    files['local-frontend-and-check.patch'] = diff
    files['frontend-pinned-to-test4a.patch'] = diff
    # Only Test4-A fixtures and runners, never the unreleased Test4 dashboard/prototype.
    for name in ['check-no-mesh-boolean.py', 'check-image-refusal.py', 'run-diagnostic-checks.py',
                 'run-supplied-checks.py', 'run-nir-oom-tests.py', 'run-nir-oom-caller-tests.py',
                 'setup-nir-oom-host-tests.py', 'nir-oom-test.c', 'test4a_nir_copy_prop_baseline.c',
                 'NIR-HOST-TESTS.md', 'nir-independent-review.md', 'check-native-source-provenance.py']:
        files['checks/test4-a/' + name] = (SCRATCH / name).read_bytes()
    for folder in ['image-refusal-baseline', 'no-mesh-baseline']:
        for path in (SCRATCH / folder).rglob('*'):
            if path.is_file():
                files['checks/test4-a/' + path.relative_to(SCRATCH).as_posix()] = path.read_bytes()
    for name in ['input-inventory.json', 'log-coverage.json', 'log-audit-summary.json',
                 'log-file-evidence.json', 'session-timelines.json', 'session-timelines.md',
                 'graphics-memory-audit.json', 'graphics-memory-findings.md', 'reconstruction.json',
                 'build-inputs.json', 'native-build.json', 'driver-build.json',
                 'project-checks-source-first-attempt.json', 'project-checks-source.json',
                 'project-checks-native-first-attempt.json', 'project-checks-native.json',
                 'host-heap-test-limits.json', 'overlay-replay.json',
                 'supplied-checks-baseline.json', 'supplied-checks-final.json',
                 'no-mesh-boolean-before.json', 'no-mesh-boolean-result.json',
                 'nir-oom-before.json', 'nir-oom-after.json', 'nir-oom-callers-before.json',
                 'nir-oom-callers-after.json', 'nir-independent-review-check.json', 'image-refusal-before.json',
                 'image-refusal-result.json', 'diagnostics-checks.json', 'native-source-provenance.json']:
        files['evidence/test4-a/' + name] = (SCRATCH / name).read_bytes()
    files['evidence/test4-a/native-nir-implementation.json'] = encode(focused['native-nir-implementation.json'])
    for path in sorted(SCRATCH.glob('nir-oom-*.log')):
        files['evidence/test4-a/' + path.name] = path.read_bytes()
    for path in sorted(SCRATCH.glob('check-*-first-attempt.log')):
        files['evidence/test4-a/' + path.name] = path.read_bytes()
    for path in sorted(SCRATCH.glob('check-*.py.log')):
        files['evidence/test4-a/' + path.name] = path.read_bytes()
    files['evidence/test4-a/crash-diagnostics-check.log'] = (SCRATCH / 'crash-diagnostics-check.log').read_bytes()
    for name in REPORT_NAMES:
        files['Documentation/' + name] = (SCRATCH / 'reports' / name).read_bytes()
    files['Documentation/report-status.json'] = (SCRATCH / 'reports/report-status.json').read_bytes()
    for name in ['package-test4a.py', 'write-release-reports.py', 'run-native-build.py',
                 'run-driver-build.py', 'prepare-build-inputs.py', 'run-project-checks.py']:
        files['packaging/' + name] = (SCRATCH / name).read_bytes()
    for name in ['analyze-logs.py', 'graphics-memory-audit.py', 'refine-timelines.py',
                 'write-log-report.py', 'reconstruct-test3.py', 'record-host-heap-limit.py']:
        files['evidence/scripts/' + name] = (SCRATCH / name).read_bytes()
    pins = dict(test3['source'])
    pins.update(candidate='Zelda Test4-A', frontend_commit=FRONTEND, core_commit=CORE,
                core_repository='https://github.com/Djihads80/Eglantine',
                total_core_overlays=len(core_patches),
                core_overlay_order=[p.name for p in core_patches],
                core_overlay_sha256={p.name: file_sha(p) for p in core_patches},
                extra_core_overlays=[p.name for p in core_patches if p.name.startswith(('0425-', '0427-', '0428-', '0429-', '0430-', '0431-', '0432-'))],
                driver_patches={'tools/radv-patches/test4a-01-nir-copy-prop-oom.patch':
                                file_sha(ROOT / 'tools/radv-patches/test4a-01-nir-copy-prop-oom.patch')},
                dependency_pins=read(ROOT / 'tools/deps.json'),
                local_changes_ai_assisted=True, published_to_upstream=False,
                original_test3_archive_sha256=OLD_OUTPUTS['EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes.zip'])
    files['SOURCE.json'] = encode(pins)
    files['BUILD.txt'] = (
        'TEST4-A REPRODUCTION\n'
        'Clone the pinned frontend and initialize its exact recursive dependencies from SOURCE.json.\n'
        'Apply frontend-pinned-to-test4a.patch to that clean frontend before any source overlay helper.\n'
        'Copy the bundled tools/ directory over the frontend tools/ directory; it includes all 264 ordered core overlays.\n'
        'Do not apply core overlays twice. Use the frontend overlay helper exactly once on pinned core.\n'
        'The native build uses the eleven original driver series plus the new NIR patch through patch-radv-series.py.\n'
        'Build: JOBS=3 RADV_BUILD_JOBS=2 bash tools/ci/build-release.sh\n'
        'Run seven original supplied checks plus inherited fence check separately; final commands are in evidence/test4-a/supplied-checks-final.json.\n'
        'Replace workstation absolute script paths with the bundled checks paths; run from the frontend root.\n'
        'GPU range check: --source Eglantine --applied --patch tools/eglantine-patches/0429-gpu-memory-range-guards.patch\n'
        'Mesh/image checks: python3 checks/test4-a/check-no-mesh-boolean.py --source .; '
        'python3 checks/test4-a/check-image-refusal.py --source .\n'
        'The original mesh failure is reproducible with --source checks/test4-a/no-mesh-baseline (expected exit 1).\n'
        'The image baseline uses --source . --baseline (expected exit 1); both baseline fixture directories are included.\n'
        'The historical eight-case NIR runner and workstation orchestration runners retain original absolute paths.\n'
        'For portable 24-case NIR reproduction, use checks/test4-a/NIR-HOST-TESTS.md and its setup/caller scripts.\n'
        'Keep host-only Mesa tests separate from the production native driver export.\n'
        'After native check_package.py --check passes, add the archived 49-key Prettier profile to PPSA98515.\n'
        'The unchanged Faster profile is historical comparison only: LONE=0 disables lone-mesh fallback and may omit foliage.\n'
        'Do not recommend Faster as equivalent-correctness performance tuning; keep Prettier as the Test4-A default.\n'
        'Packaging scripts preserve this workstation workflow; adjust source/work/output locations when rebuilding elsewhere.\n'
        'No games, keys, firmware, SDK binaries, remote dashboard or Test4 prototype source are bundled.\n'
        'No upstream push or PR was made. PS5 runtime behavior remains unverified.\n').encode()
    files['SOURCE-MANIFEST.json'] = encode({name: sha(data) for name, data in sorted(files.items())})
    for name in files:
        safe_name(name)
    return files, pins


def validate(receipt_path):
    data = read(receipt_path)
    assert data['status'] == 'pass' and data['exit_code'] == 0
    heap_limit = data['host_heap_test_limits']
    if heap_limit:
        assert heap_limit == optional_heap_limit(data['focused_checks']['project-checks-source.json'])
    assert data['unverified'] == LIMITS + ([{'optional_heap_tsan': heap_limit}] if heap_limit else [])
    originals()
    for field, name in [('main_manifest', data['archive']), ('source_manifest', data['source_bundle'])]:
        path = OUTPUT / name
        assert file_sha(path) == data['archive_sha256' if field == 'main_manifest' else 'source_bundle_sha256']
        assert zip_manifest(path) == data[field]
    for name, expected in data['build']['source_after'].items():
        assert file_sha(ROOT / name) == expected, name
    for name, expected in data['focused_checks']['native-source-provenance.json']['current_file_sha256'].items():
        assert file_sha(Path(name)) == expected, ('Changed native provenance input', name)
    slot = data['focused_checks']['native-source-provenance.json']['slot_vector']
    assert slot['compiled_dependencies'] > 0 and slot['original_header_dependencies'] == 0
    assert slot['generated_bytes_match'] is True
    assert len(data['focused_checks']['native-source-provenance.json']['current_file_sha256']) == 30
    assert file_sha(Path(data['symbol_file'])) == data['symbol_sha256']
    with zipfile.ZipFile(OUTPUT / data['archive']) as archive:
        assert sha(archive.read('PPSA98515/eboot.bin')) == data['eboot_sha256']
        assert archive.read('PPSA98515/' + PROFILE) == profiles(OUTPUT / 'EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes.zip')[0]
        assert archive.read('Zelda-faster-profile.txt') == profiles(OUTPUT / 'EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes.zip')[1]
    with zipfile.ZipFile(OUTPUT / data['source_bundle']) as archive:
        assert json.loads(archive.read('SOURCE.json')) == data['source']
        manifest = json.loads(archive.read('SOURCE-MANIFEST.json'))
        assert set(manifest) == set(archive.namelist()) - {'SOURCE-MANIFEST.json'}
        for name, expected in manifest.items():
            assert sha(archive.read(name)) == expected, name
    sums = {}
    for line in (OUTPUT / 'SHA256SUMS').read_text().splitlines():
        expected, name = line.split(None, 1)
        assert name.strip() not in sums
        sums[name.strip()] = expected
    for name, expected in OLD_OUTPUTS.items():
        assert sums[name] == expected
    assert sums[data['archive']] == data['archive_sha256']
    assert sums[data['source_bundle']] == data['source_bundle_sha256']
    print(json.dumps({'status': 'pass', 'exit_code': 0, 'mode': 'validate',
                      'main_entries': len(data['main_manifest']),
                      'source_entries': len(data['source_manifest']),
                      'preserved_outputs': len(OLD_OUTPUTS), 'unverified': data['unverified']}))


def package():
    inventory, test3, old_symbols, build, driver, supplied, focused = gates()
    targets = [OUTPUT / MAIN, OUTPUT / SOURCES, OUTPUT / RECEIPT]
    assert not any(path.exists() for path in targets), 'Refusing to overwrite existing Test4-A outputs'
    symbol = ROOT / 'build/symbols/zelda-test4-a-graphics-crash.elf'
    assert not symbol.exists(), 'Refusing to overwrite saved Test4-A symbols'
    sums_path = OUTPUT / 'SHA256SUMS'
    original_sums = sums_path.read_bytes()
    assert MAIN.encode() not in original_sums and SOURCES.encode() not in original_sums
    app = ROOT / 'build/release/PPSA98515'
    native_check = subprocess.run([sys.executable, '-B', 'headless/check_package.py', '--check'],
                                  cwd=ROOT, env=os.environ | {'EDEN_PACKAGE_DIR': str(app)},
                                  text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert native_check.returncode == 0, native_check.stdout
    native_archives = list((ROOT / 'dist').glob('*.zip'))
    assert len(native_archives) == 1, native_archives
    native_manifest = zip_manifest(native_archives[0])
    app_names = {path.relative_to(app).as_posix() for path in app.rglob('*') if path.is_file()}
    assert app_names == {name.removeprefix('PPSA98515/') for name in native_manifest if name.startswith('PPSA98515/')}
    for name in app_names:
        assert file_sha(app / name) == native_manifest['PPSA98515/' + name]['sha256']
    prettier, faster = profiles(OUTPUT / 'EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes.zip')
    files, pins = source_files(inventory, test3, supplied, focused)
    with zipfile.ZipFile(native_archives[0]) as stock:
        native = {name: stock.read(name) for name in stock.namelist()}
    assert native['PPSA98515/eboot.bin'][:4] == bytes.fromhex('4f153d1d')
    eboot_sha = sha(native['PPSA98515/eboot.bin'])
    assert eboot_sha != test3['eboot_sha256']
    metadata = json.loads(native['PPSA98515/sce_sys/param.json'])
    assert metadata['titleId'] == 'PPSA98515'
    assert 'PPSA98515/' + PROFILE not in native
    # Same Test3 package root structure: native app, root notices/README and optional profile.
    additions = {'PPSA98515/' + PROFILE: prettier, 'Zelda-faster-profile.txt': faster}
    additions['README.md'] = (
        '# EglantinePS5 Zelda Test4-A\n\n'
        'Native build and the supplied/fix-specific checks passed. This candidate has not run on your PS5.\n\n'
        'Close the emulator and back up the active app/profile before installing PPSA98515 using your existing method. '
        'Your logs selected /system_ex/app/PPSA98515; verify the active folder and Test4-A boot marker.\n\n'
        'The unchanged 49-key Test3 Prettier profile is the Test4-A default. Zelda-faster-profile.txt is retained only as '
        'the historical Test3 incomplete-graphics comparison baseline: its LONE=0 leaves lone-mesh fallback disabled and may omit foliage. '
        'It is not a recommended or equivalent-correctness performance preset. All supplied crashes used Faster. '
        'Keep Prettier for graphics testing; record any separate historical Faster comparison explicitly.\n\n'
        'Read Documentation/Test4-A-PS5-Testing.md and the detailed crash/validation reports. '
        'The adjacent Zelda-Test4-A-Verification.json records ZIP/executable/source hashes and remaining limits. '
        'Texture/geometry restoration, brightness, flashes, FPS, cold-cache behavior and crash-free duration require controlled console tests.\n\n'
        'The optional full heap TSan stress did not complete on this host (OOM, then a 900-second timeout); '
        'its failed attempts and passing checked UBSan modes are documented in the validation report and verification receipt.\n\n'
        'No remote dashboard or video tool is included. No game, keys or firmware is included.\n').encode()
    for name in REPORT_NAMES:
        additions['Documentation/' + name] = (SCRATCH / 'reports' / name).read_bytes()
    stage_main, stage_source = [path.with_suffix('.staging.zip') for path in targets[:2]]
    assert not stage_main.exists() and not stage_source.exists()
    with zipfile.ZipFile(stage_main, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(native.items()):
            if name != 'README.md':
                add(archive, name, data, native_manifest[name]['mode'])
        for name, data in sorted(additions.items()):
            add(archive, name, data, 0o100777 if name.startswith('PPSA98515/') else 0o100644)
    with zipfile.ZipFile(stage_source, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            add(archive, name, data, 0o100755 if name.endswith('.py') else 0o100644)
    main_manifest, source_manifest = zip_manifest(stage_main), zip_manifest(stage_source)
    expected_main = (native.keys() - {'README.md'}) | additions.keys()
    assert set(main_manifest) == expected_main and set(source_manifest) == files.keys()
    for name, data in native.items():
        if name != 'README.md':
            assert main_manifest[name] == native_manifest[name], name
    for name, data in additions.items():
        assert main_manifest[name]['sha256'] == sha(data)
    for name, data in files.items():
        assert source_manifest[name]['sha256'] == sha(data)
    elf = ROOT / 'build/headless-native/llvm-pie.elf'
    assert elf.read_bytes()[:4] == b'\x7fELF'
    shutil.copyfile(elf, symbol)
    assert file_sha(elf) == file_sha(symbol)
    originals()
    result = {'status': 'pass', 'exit_code': 0, 'generated_utc': datetime.now(timezone.utc).isoformat(),
              'archive': MAIN, 'archive_sha256': file_sha(stage_main),
              'source_bundle': SOURCES, 'source_bundle_sha256': file_sha(stage_source),
              'eboot_sha256': eboot_sha, 'version': metadata['contentVersion'],
              'main_manifest': main_manifest, 'source_manifest': source_manifest,
              'native_archive_sha256': file_sha(native_archives[0]), 'native_manifest': native_manifest,
              'stock_native_check': {'exit_code': 0, 'output': native_check.stdout.strip()},
              'source': pins, 'build': build, 'driver_build': driver,
              'supplied_checks': supplied, 'focused_checks': focused,
              'original_input_sha256': {item['source']: item['archive_sha256'] for item in inventory},
              'preserved_artifact_sha256': OLD_OUTPUTS, 'preserved_symbol_sha256': old_symbols,
              'symbol_file': str(symbol), 'symbol_sha256': file_sha(symbol),
              'profile_sha256': sha(prettier), 'faster_profile_sha256': sha(faster),
              'profiles_unchanged_from_test3': True, 'profile_keys_each': 49, 'unverified': LIMITS}
    result['host_heap_test_limits'] = focused.get('host-heap-test-limits.json')
    if result['host_heap_test_limits']:
        result['unverified'] = LIMITS + [{'optional_heap_tsan': result['host_heap_test_limits']}]
    stage_main.replace(targets[0])
    stage_source.replace(targets[1])
    assert sums_path.read_bytes() == original_sums
    sums_path.write_bytes(original_sums.rstrip(b'\r\n') + b'\n' +
                          f"{result['archive_sha256']}  {MAIN}\n{result['source_bundle_sha256']}  {SOURCES}\n".encode())
    targets[2].write_bytes(encode(result))
    validate(targets[2])


def main():
    parser = ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument('--package', action='store_true')
    modes.add_argument('--validate', action='store_true')
    modes.add_argument('--check-script', action='store_true', help='Validate Python syntax and constant path safety only')
    args = parser.parse_args()
    if args.check_script:
        ast.parse(Path(__file__).read_text())
        for name in [MAIN, SOURCES, RECEIPT] + REPORT_NAMES:
            safe_name(name)
        assert len(OLD_OUTPUTS) == 5 and len(REPORT_NAMES) == 7
        print(json.dumps({'status': 'pass', 'exit_code': 0, 'mode': 'check-script',
                          'native_build_or_zip_not_executed': True}))
    elif args.validate:
        validate(OUTPUT / RECEIPT)
    elif args.package:
        package()
    else:
        gates()
        print(json.dumps({'status': 'pass', 'exit_code': 0, 'mode': 'read-only-preflight',
                          'next': '--package only after code freeze and script review'}))


if __name__ == '__main__':
    main()
