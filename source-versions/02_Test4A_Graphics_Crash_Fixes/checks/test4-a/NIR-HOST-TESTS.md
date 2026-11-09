# Focused NIR allocation-failure regression

Use Linux x86-64 with Python 3, Meson, Ninja, GCC/G++, standard Mesa host build prerequisites (including Mako, PyYAML, Bison/Flex, zlib/Expat and SPIR-V/glslang tools), and ASan/UBSan support. The recorded run used GCC 15.2 and Meson 1.10.1. No PS5 or Vulkan device is used.

Start from an expendable copy of the exact pinned Test3 Mesa driver export, including its eleven existing driver patches, and apply `tools/radv-patches/test4a-01-nir-copy-prop-oom.patch` from the Test4-A source changes. Keep this host copy separate from the native driver source: the installer adds test-only Meson targets.

Keep these four files together:

- `setup-nir-oom-host-tests.py`
- `nir-oom-test.c`
- `test4a_nir_copy_prop_baseline.c`
- `run-nir-oom-caller-tests.py`

Run, substituting your directories:

```sh
python3 setup-nir-oom-host-tests.py --mesa-source /path/to/host-mesa-copy --build-dir /path/to/host-nir-build --configure --build
python3 run-nir-oom-caller-tests.py --build-dir /path/to/host-nir-build --output-dir /path/to/results --stage before
python3 run-nir-oom-caller-tests.py --build-dir /path/to/host-nir-build --output-dir /path/to/results --stage after
```

The setup script verifies the bundled original pass SHA-256, installs the fixture and two host-only targets, configures assertions and ASan/UBSan, and builds only those targets using one job. It also prints the exact Meson/Ninja commands. On an existing host source/build, it accepts an identical target definition and reconfigures when requested. Use a clean expendable source copy if target definitions differ.

The baseline target links the supplied original pass object ahead of the patched static NIR archive; the patched target uses the patched pass from that archive. Both exercise the same real NIR infrastructure. The baseline source is retained under its existing Mesa MIT copyright header; its SHA-256 is `35cbb1a29df5676ddc5a7c6ea54896d393f22d2148fd2d147c33c8f0273730d8`.

Each stage records 24 cases: store, direct load, and copy_deref consumers; flat/nested-if control flow; normal allocation, copy-array growth failure, initial ralloc-context failure, and initial linear-context failure. Expected results are six baseline normal passes, eighteen baseline negative-control failures, and twenty-four patched passes. The baseline runner returns zero when the intended failures reproduce; each individual exit code and sanitizer message remains in the JSON/log evidence. Tests check NIR validity, metadata, partial progress, unchanged IR on initial allocation failure, semantic output 2087 and leak-free cleanup.

Recorded receipts are `nir-oom-callers-before.json` and `nir-oom-callers-after.json`. These host tests do not establish PS5 crash duration, image correctness, or FPS. See `nir-independent-review.md` for the independent review and remaining allocation sites outside this fix.
