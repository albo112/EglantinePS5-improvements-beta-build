# EglantinePS5 — supplied source versions (newest to oldest)

This directory includes **all source code and patches supplied in the chat**, arranged by development version newest first. It does not pretend that a compiled PS5 program can be turned back into exact project source or that external upstream checkouts were supplied.

| Order | Folder | Included | Status |
|---|---|---|---|
| 01 (latest) | `01_Test4A_12GiB_2Workers_LATEST/` | Test4-A frontend + 264 core patches, driver series, scripts, tests, docs, with the **12 GiB / 2 pipeline workers** profile | Reconstruction kit, not full pinned upstream |
| 02 | `02_Test4A_Graphics_Crash_Fixes/` | Original Test4-A source changes | Patches, not full pinned upstream |
| 03 | `03_Test3_Graphics_Crash_Fixes/` | Test3 source changes | Partial source/patches |
| 04 | `04_Test2_Memory_Fix/` | Test2 source changes | Partial source/patches |
| 05 | `05_T34_RADV_Compiled_Release_Only/` | Source-status note | Only compiled PS5 package was supplied for this version |

## Build the latest source from pinned upstream

```bash
bash scripts/reconstruct-latest.sh ./EglantinePS5-Test4A-Full-Source
```

With appropriate Linux/WSL toolchains and dependencies installed, run the combined reconstruction + native build:

```bash
bash scripts/build-latest-on-linux.sh ./EglantinePS5-Test4A-Full-Source
```

Both require internet to fetch pinned revisions. The reconstruction runner validates hashes, initializes the Eglantine core submodule, applies the frontend patch, copies the core and driver overlays and calls the upstream patch runner. The driver series is applied by the upstream build path.

**Pins:** Frontend `Vampinity/Eglantine-PS5- @ 25cfc07be0a3675749adece5d012fdb916c4cd48`; core `Djihads80/Eglantine @ 0ca2032bffc5f1a3fca75427f7d4a4718adda660`. The latest profile sets `EDEN_NX2_MEMORY_GB=12` and `EDEN_NX2_PIPELINE_WORKERS=2`. The 12 GiB value refers to the guest-memory layout and is not a global host process RAM cap.

## Provenance and limitations

`provenance/original-upload-hashes.json` lists SHA-256 checksums of all source and compiled build archives. Compiled release ZIP files (`PPSA98515/`, `eboot.bin`) are deliberately not embedded here because the request is for source versions, but their original archives remain available in the conversation uploads. Test4-A Source-Changes.rar and the prior ZIP were byte-equal except for the game configuration profile, now included in folder 01. No new build has been compiled or hardware tested.

See `provenance/BUILD-ATTEMPT.md` for the blocking network error and exact build command.
