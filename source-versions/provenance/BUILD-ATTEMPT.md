# Build status and environment blocker

**Source reconstruction / native build not completed here.**

The latest sources are overlays against pinned upstream repositories, not the complete base checkout. A direct Git fetch was attempted in this runtime:

```
git ls-remote https://github.com/heydemoura/EglantinePS5.git HEAD
fatal: unable to access ...: Could not resolve host: github.com
```

The pinned Test4-A checkout specified in `01_Test4A_12GiB_2Workers_LATEST/SOURCE.json`:

- Frontend: `https://github.com/Vampinity/Eglantine-PS5-.git` at `25cfc07be0a3675749adece5d012fdb916c4cd48`
- Core submodule: `https://github.com/Djihads80/Eglantine` at `0ca2032bffc5f1a3fca75427f7d4a4718adda660`

The source manifest and ZIP CRC checks passed, but local network access cannot fetch these commits. Consequently, the core patches could not be applied to an actual checkout and the PS5 compiler/driver dependency build was not run here. No new `eboot.bin` was produced.

On a Linux/WSL host with GitHub access and dependencies:

```
bash scripts/build-latest-on-linux.sh ./EglantinePS5-Test4A-Full-Source
```

If using a packaged ZIP extracted into a folder, call the script from the package root. The native `tools/ci/build-release.sh` build may require further environment provisioning as documented in `BUILD.txt` and upstream build docs. PS5 execution requires real hardware testing.
