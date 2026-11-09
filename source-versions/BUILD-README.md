# Pinned source build notes

After the source archive has been extracted into this folder, reconstruct the newest source on a Linux/WSL machine with GitHub network access and the required PS5/LLVM/RADV toolchains.

```bash
bash scripts/reconstruct-latest.sh ./EglantinePS5-Test4A-Full-Source
# To reconstruct and then invoke the recorded native build:
bash scripts/build-latest-on-linux.sh ./EglantinePS5-Test4A-Full-Source
```

The native invocation from Test4-A's evidence was:
```bash
JOBS=3 RADV_BUILD_JOBS=2 bash tools/ci/build-release.sh
```

Do not apply any of the 264 core patches twice. Do not apply older Test2/Test3 patches on top of Test4-A. Run the Test4-A source and GPU/driver checks, then test the resulting PS5 release on actual hardware. A 12 GiB guest layout is not a hard cap on host process memory.
