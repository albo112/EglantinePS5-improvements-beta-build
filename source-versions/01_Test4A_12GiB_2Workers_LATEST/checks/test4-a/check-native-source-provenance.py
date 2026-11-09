from pathlib import Path
import hashlib, json, subprocess, tempfile

root = Path('/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5')
out = Path(__file__).resolve().parent
cache = Path((root/'.local/headless-cache').read_text().strip())
names = ['video_core/renderer_vulkan/vk_rasterizer.cpp',
         'video_core/renderer_vulkan/vk_pipeline_cache.cpp',
         'video_core/renderer_vulkan/vk_texture_cache.cpp',
         'video_core/texture_cache/texture_cache.h',
         'video_core/texture_cache/texture_cache_base.h',
         'shader_recompiler/backend/spirv/spirv_emit_context.cpp',
         'video_core/memory_manager.cpp', 'video_core/memory_manager.h',
         'video_core/engines/engine_upload.cpp',
         'video_core/renderer_vulkan/vk_compute_pipeline.cpp']
hashes = {}
for name in names:
    actual = (root/'Eglantine/src'/name).read_bytes()
    assert actual == (cache/'source/src'/name).read_bytes(), ('Stale core copy', name)
    hashes[name] = hashlib.sha256(actual).hexdigest()
generated = cache/'native-local/headless'
raster = (generated/'vulkan_rasterizer.cpp').read_text()
pipeline = (generated/'vk_pipeline_cache_cost.cpp').read_text()
texture = (generated/'vk_texture_cache_cost.cpp').read_text()
def extract(text, start, end):
    return text[text.index(start):text.index(end, text.index(start))]
original = (root/'Eglantine/src/video_core/renderer_vulkan/vk_rasterizer.cpp').read_text()
predicate = extract(original, '    static const bool no_mesh_always', '    // Mario Kart World:')
assert predicate in raster
assert 'Native graphics draw was not submitted: failures={}' in raster
assert 'refusing submission completion' not in raster
original = (root/'Eglantine/src/video_core/renderer_vulkan/vk_pipeline_cache.cpp').read_text()
predicate = extract(original, 'bool DropMeshDrawsBeforeBuild()', '\n}\n') + '\n}'
assert predicate in pipeline
assert '''if (!IsUnwrittenSparse(runtime_.device, info, gpu_addr_)) {
                throw vk::Exception{VK_ERROR_OUT_OF_DEVICE_MEMORY};
            }''' in texture
commands = json.loads((cache/'native-local/compile_commands.json').read_text())
compiled = {str(Path(item['file']).resolve()) for item in commands}
required = [generated/name for name in ['vulkan_rasterizer.cpp', 'vk_pipeline_cache_cost.cpp', 'vk_texture_cache_cost.cpp']]
required += [root/'headless/main.cpp', root/'headless/crash_report.cpp']
assert all(str(path.resolve()) in compiled for path in required)
old_core = [name for name in compiled if '/ps5-eden-headless.' in name and '/source/src/' in name
            and not name.startswith(str(cache/'source/src') + '/')]
assert not old_core, old_core
slot_input = root/'Eglantine/src/common/slot_vector.h'
slot_generator = root/'headless/slot_vector_recovery.cmake'
slot_header = generated/'recovery/common/slot_vector.h'
deps = subprocess.check_output(['ninja','-C',str(cache/'native-local'),'-t','deps'], text=True)
slot_dependencies = [line.strip() for line in deps.splitlines() if line.strip().endswith('common/slot_vector.h')]
assert slot_dependencies and set(slot_dependencies) == {str(slot_header)}
with tempfile.TemporaryDirectory(prefix='test4a-slot-provenance-') as directory:
    expected_slot = Path(directory)/'slot_vector.h'
    subprocess.run(['cmake','-DSLOT_VECTOR_INPUT='+str(slot_input),'-DSLOT_VECTOR_OUTPUT='+str(expected_slot),
                    '-P',str(slot_generator)], check=True)
    assert expected_slot.read_bytes() == slot_header.read_bytes()
result = {'status':'pass','exit_code':0, 'raw_core_files':len(names),
          'raw_core_sha256':hashes, 'generated_compile_targets':[str(path) for path in required],
          'checks':['exact core copies','generated renderer mesh Boolean and bounded diagnostic',
                    'generated pipeline mesh Boolean','generated texture OOM branch',
                    'native compilation entries for new source paths',
                    'all recorded SlotVector dependencies use the exact recovery-generated header'],
          'slot_vector':{'recovery_header':str(slot_header),'compiled_dependencies':len(slot_dependencies),
                         'original_header_dependencies':0,'generated_bytes_match':True},
          'scope':'Native source provenance; no PS5 execution or visual validation'}
current = [root/'Eglantine/src'/name for name in names]
current += [cache/'source/src'/name for name in names]
current += required + [cache/'native-local/compile_commands.json', Path(__file__).resolve()]
current += [slot_input, slot_generator, slot_header]
result['current_file_sha256'] = {str(path):hashlib.sha256(path.read_bytes()).hexdigest() for path in current}
(out/'native-source-provenance.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['current_file_sha256','raw_core_sha256']}))
