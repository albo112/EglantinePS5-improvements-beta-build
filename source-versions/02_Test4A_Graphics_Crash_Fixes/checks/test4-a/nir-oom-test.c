#include "compiler/nir/nir.h"
#include "compiler/nir/nir_builder.h"
#include "compiler/nir/nir_deref.h"
#include "util/ralloc.h"
#include <assert.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static bool active;
static unsigned mode, scenario, matching_grows, failures;
static size_t failed_bytes;
void *__real_ralloc_context(const void *ctx);
linear_ctx *__real_linear_context(void *ctx);
void *__real_reralloc_size(const void *ctx, void *ptr, size_t size);
void *__wrap_ralloc_context(const void *ctx);
linear_ctx *__wrap_linear_context(void *ctx);
void *__wrap_reralloc_size(const void *ctx, void *ptr, size_t size);
void *__wrap_ralloc_context(const void *ctx)
{
   if (active && mode == 2) { ++failures; return NULL; }
   return __real_ralloc_context(ctx);
}
linear_ctx *__wrap_linear_context(void *ctx)
{
   if (active && mode == 3) { ++failures; return NULL; }
   return __real_linear_context(ctx);
}
void *__wrap_reralloc_size(const void *ctx, void *ptr, size_t size)
{
   /* The recorded pass's copy entries are 168 bytes on the 64-bit host and PS5. */
   if (active && mode == 1 && size && size % 168 == 0 &&
       matching_grows++ == (scenario ? 1 : 3)) {
      ++failures;
      failed_bytes = size;
      return NULL;
   }
   return __real_reralloc_size(ctx, ptr, size);
}

int main(int argc, char **argv)
{
   assert(argc == 3 || argc == 4);
   mode = strtoul(argv[1], NULL, 10);
   const bool nested = strtoul(argv[2], NULL, 10) != 0;
   scenario = argc == 4 && strcmp(argv[3], "load") == 0 ? 1 :
              argc == 4 && strcmp(argv[3], "copy") == 0 ? 2 : 0;
   glsl_type_singleton_init_or_ref();
   static const nir_shader_compiler_options options = {0};
   nir_builder b = nir_builder_init_simple_shader(MESA_SHADER_VERTEX, &options, "test4a-copy-prop-oom");
   nir_variable *out = nir_variable_create(b.shader, nir_var_shader_out, glsl_int_type(), "result");
   out->data.location = VARYING_SLOT_VAR0;
   nir_variable *x = scenario ? nir_variable_create(b.shader, nir_var_mem_global, glsl_int_type(), "early") :
                               nir_local_variable_create(b.impl, glsl_int_type(), "early");
   if (!scenario) nir_store_var(&b, x, nir_imm_int(&b, 7), 1);
   nir_def *sum = nir_load_var(&b, x);
   if (scenario) {
      nir_def *again = nir_load_var(&b, x);
      sum = nir_isub(&b, nir_iadd(&b, sum, again), sum);
   }
   nir_variable *array = nir_local_variable_create(b.impl, glsl_array_type(glsl_int_type(), 64, 0), "array");
   nir_variable *input = scenario ? nir_variable_create(b.shader, nir_var_mem_global,
                                   glsl_array_type(glsl_int_type(), 64, 0), "input_array") : NULL;
   nir_if *branch = nested ? nir_push_if(&b, nir_imm_bool(&b, true)) : NULL;
   for (unsigned i = 0; i < 64; ++i) {
      if (scenario == 1) continue;
      nir_deref_instr *d = nir_build_deref_array(&b, nir_build_deref_var(&b, array), nir_imm_int(&b, i));
      if (scenario == 2) {
         nir_deref_instr *src = nir_build_deref_array(&b, nir_build_deref_var(&b, input), nir_imm_int(&b, i));
         nir_copy_deref(&b, d, src);
      } else {
         nir_store_deref(&b, d, nir_imm_int(&b, i + 1), 1);
      }
   }
   for (unsigned i = 0; i < 64; ++i) {
      nir_deref_instr *d = nir_build_deref_array(&b, nir_build_deref_var(&b, scenario == 1 ? input : array), nir_imm_int(&b, i));
      sum = nir_iadd(&b, sum, nir_load_deref(&b, d));
   }
   nir_store_var(&b, out, sum, 1);
   if (nested) {
      nir_push_else(&b, branch);
      nir_store_var(&b, out, nir_imm_int(&b, 2087), 1);
      nir_pop_if(&b, branch);
   }
   nir_validate_shader(b.shader, "before injection");
   nir_metadata_require(b.impl, nir_metadata_control_flow);
   char *before = nir_shader_as_str(b.shader, b.shader);
   active = true;
   const bool progress = nir_opt_copy_prop_vars(b.shader);
   active = false;
   assert(failures == (mode ? 1 : 0));
   if (mode == 1) assert(progress);  /* Exercise a real partial optimization. */
   if (mode == 2 || mode == 3) {
      assert(!progress);
      char *after = nir_shader_as_str(b.shader, b.shader);
      assert(strcmp(before, after) == 0);
   }
   nir_validate_shader(b.shader, "after injection");
   assert((b.impl->valid_metadata & nir_metadata_control_flow) == nir_metadata_control_flow);
   if (scenario) {
      /* Interpret the externally initialized global inputs, after checking the pass's IR. */
      nir_lower_var_copies(b.shader);
      nir_foreach_block(block, b.impl) {
         nir_foreach_instr_safe(instr, block) {
            if (instr->type != nir_instr_type_intrinsic) continue;
            nir_intrinsic_instr *intrin = nir_instr_as_intrinsic(instr);
            if (intrin->intrinsic != nir_intrinsic_load_deref) continue;
            nir_deref_instr *deref = nir_src_as_deref(intrin->src[0]);
            nir_variable *var = nir_deref_instr_get_variable(deref);
            if (var != x && var != input) continue;
            unsigned value = 7;
            if (var == input) {
               assert(deref->deref_type == nir_deref_type_array && nir_src_is_const(deref->arr.index));
               value = nir_src_as_uint(deref->arr.index) + 1;
            }
            b.cursor = nir_before_instr(instr);
            nir_def_rewrite_uses(&intrin->def, nir_imm_int(&b, value));
            nir_instr_remove(instr);
         }
      }
      nir_progress(true, b.impl, nir_metadata_control_flow);
   }
   nir_lower_vars_to_ssa(b.shader);
   bool more;
   do {
      more = nir_opt_copy_prop(b.shader);
      more |= nir_opt_constant_folding(b.shader);
      more |= nir_opt_dce(b.shader);
   } while (more);
   nir_validate_shader(b.shader, "after semantic reduction");
   unsigned stores = 0;
   nir_foreach_block(block, b.impl) {
      nir_foreach_instr(instr, block) {
         if (instr->type != nir_instr_type_intrinsic) continue;
         nir_intrinsic_instr *intrin = nir_instr_as_intrinsic(instr);
         if (intrin->intrinsic != nir_intrinsic_store_deref) continue;
         nir_variable *var = nir_deref_instr_get_variable(nir_src_as_deref(intrin->src[0]));
         if (var != out) continue;
         assert(nir_src_is_const(intrin->src[1]));
         assert(nir_src_as_int(intrin->src[1]) == 2087);
         ++stores;
      }
   }
   assert(stores == (nested ? 2 : 1));
   printf("{\"status\":\"pass\",\"mode\":%u,\"nested\":%d,\"scenario\":%u,\"failures\":%u,\"failed_bytes\":%zu,\"partial_progress\":%d,\"result\":2087,\"stores\":%u}\n",
          mode, nested, scenario, failures, failed_bytes, progress, stores);
   ralloc_free(b.shader);
   glsl_type_singleton_decref();
   return 0;
}
