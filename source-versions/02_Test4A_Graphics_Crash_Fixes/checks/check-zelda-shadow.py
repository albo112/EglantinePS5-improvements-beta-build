import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


SOURCE = 'src/shader_recompiler/backend/spirv/spirv_emit_context.cpp'
baseline = subprocess.check_output(['git', '-C', 'Eglantine', 'show', f'HEAD:{SOURCE}'], text=True)
patched = (Path('Eglantine') / SOURCE).read_text()


def sampled_type(source):
    return re.search(r'Id ImageType\([^\n]+\).*?const Id type\{([^}]+)\};', source, re.S)[1]


with TemporaryDirectory() as directory:
    work = Path(directory)
    test_source = work / 'sampled_type.cpp'
    test_binary = work / 'sampled_type'
    test_source.write_text(f'''#include <cassert>
using Id = unsigned;
struct Context {{ Id U32[2]{{0, 1}}; Id F32[2]{{0, 2}}; }};
struct Descriptor {{ bool is_depth; bool is_integer; }};
Id before(Context ctx, Descriptor desc) {{ return {sampled_type(baseline)}; }}
Id after(Context ctx, Descriptor desc) {{ return {sampled_type(patched)}; }}
int main() {{
    assert(before({{}}, {{true, true}}) == 1);
    assert(after({{}}, {{true, true}}) == 2);
    assert(after({{}}, {{true, false}}) == 2);
    assert(after({{}}, {{false, true}}) == 1);
    assert(after({{}}, {{false, false}}) == 2);
}}
''')
    subprocess.run(['clang++-18', '-std=c++20', '-Wall', '-Wextra', '-Werror', str(test_source), '-o', str(test_binary)], check=True)
    subprocess.run([str(test_binary)], check=True)
    assembly = '''OpCapability Shader
OpMemoryModel Logical GLSL450
OpEntryPoint Fragment %main "main" %texture
OpExecutionMode %main OriginUpperLeft
OpDecorate %texture DescriptorSet 0
OpDecorate %texture Binding 0
%void = OpTypeVoid
%function = OpTypeFunction %void
%f32 = OpTypeFloat 32
%u32 = OpTypeInt 32 0
%vec2 = OpTypeVector %f32 2
%image = OpTypeImage %SAMPLED_TYPE 2D 1 0 0 1 Unknown
%sampled = OpTypeSampledImage %image
%pointer = OpTypePointer UniformConstant %sampled
%texture = OpVariable %pointer UniformConstant
%zero = OpConstant %f32 0
%coordinate = OpConstantComposite %vec2 %zero %zero
%main = OpFunction %void None %function
%label = OpLabel
%combined = OpLoad %sampled %texture
%result = OpImageSampleDrefImplicitLod %f32 %combined %coordinate %zero
OpReturn
OpFunctionEnd
'''
    for type_id in ('u32', 'f32'):
        module = work / f'{type_id}.spvasm'
        binary = work / f'{type_id}.spv'
        module.write_text(assembly.replace('SAMPLED_TYPE', type_id))
        subprocess.run(['spirv-as', '--target-env', 'vulkan1.2', str(module), '-o', str(binary)], check=True)
        validation = subprocess.run(['spirv-val', '--target-env', 'vulkan1.2', str(binary)], text=True, capture_output=True)
        if type_id == 'u32':
            assert validation.returncode != 0 and 'Sampled Type' in validation.stderr, validation.stderr
        else:
            assert validation.returncode == 0, validation.stderr

print('Zelda shadow SPIR-V PASS: old unsigned depth image rejected, patched float depth image accepted; non-depth integer path preserved')
