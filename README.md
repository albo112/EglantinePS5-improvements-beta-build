# EglantinePS5 — Fork Improvements

Experimental Nintendo Switch / Switch 2 emulation project for a jailbroken PS5.

## Project maintainer and credits

Maintained by **[Albo (@albo112)](https://github.com/albo112)**. This is an experimental derivative of the work by **[@viejunerd](https://github.com/viejunerd/Eglantine-PS5-)**, **[@Djihads80](https://github.com/Djihads80/Eglantine)**, **[@Vampinity](https://github.com/Vampinity/Eglantine-PS5-)**, **[@heydemoura](https://github.com/heydemoura/EglantinePS5)** and other upstream contributors.

Development support: **OpenAI ChatGPT and Codex (AI-assisted work)**. See **[CREDITS.md](CREDITS.md)** for proper attribution and source lineage. Upstream authors are credited, not represented as maintainers of this fork.

## Source code versions — newest first

**[Browse the complete versioned source collection](source-versions/)**

1. **[Test4-A — 12 GiB / 2 workers (latest)](source-versions/01_Test4A_12GiB_2Workers_LATEST/)**: 264 ordered emulator-core patches, frontend, driver patches, graphics/crash fixes, tests, and the game-specific configuration profile.
2. **[Test4-A — original graphics/crash fixes](source-versions/02_Test4A_Graphics_Crash_Fixes/)**.
3. **[Test3 — graphics/crash fixes](source-versions/03_Test3_Graphics_Crash_Fixes/)**.
4. **[Test2 — memory fixes](source-versions/04_Test2_Memory_Fix/)**.
5. **[T34 RADV source status](source-versions/05_T34_RADV_Compiled_Release_Only/)**: compiled release provided, no independent source tree.

Also included: [source provenance, checksums](source-versions/provenance/), [reconstruction and publication scripts](source-versions/scripts/), and a [verified archive transfer](source-versions/archive/).

## Latest configuration

```ini
EDEN_NX2_MEMORY_GB=12
EDEN_NX2_PIPELINE_WORKERS=2
```

The 12 GiB setting selects a **guest memory layout**, not a total host-process memory cap.

## Pinned upstream inputs

- Frontend: [Vampinity/Eglantine-PS5-](https://github.com/Vampinity/Eglantine-PS5-/tree/25cfc07be0a3675749adece5d012fdb916c4cd48) at `25cfc07be0a3675749adece5d012fdb916c4cd48`.
- Emulator core: [Djihads80/Eglantine](https://github.com/Djihads80/Eglantine) at `0ca2032bffc5f1a3fca75427f7d4a4718adda660`.

These folders are the **full set of user-supplied source modifications**, not a vendored checkout of every upstream source and binary dependency. The reconstruction script fetches the exact upstream commits and applies each ordered patch once. Build instructions are in [the source-versions README](source-versions/README.md).

## Experimental release archive

See **[RELEASES.md](RELEASES.md)** for the five supplied PS5 binaries, checksum verification, testing caveats and the release-upload instructions. GitHub-built test releases are published separately after CI validation.

## Build and validation

GitHub Actions includes a [native PS5 build workflow](.github/workflows/build-pinned-test4a.yml) for reconstructing the pinned source and attempting a release build. **An Actions run is not proof of build success**: verify the job result, produced `eboot.bin`, release ZIP integrity, and real console testing before describing a build as validated.

Do not mix older Test2/Test3 patches on top of the latest Test4-A series. GUI redesign is deferred until after graphics fixes, performance, gameplay stability, and validated builds.

No proprietary game dumps, console keys, firmware or SDK components are included.
