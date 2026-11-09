# EglantinePS5 source history — newest to oldest

The source uploads have been organized into a local downloadable source archive. This repository is being prepared to receive them. **Do not assume this branch yet contains the complete C/C++ source.**

| Order | Version | Contents available from user's uploads |
|---|---|---|
| 01 | Zelda Test4-A — 12 GiB guest memory, 2 Vulkan pipeline workers | 264 core patches; frontend patch; RADV driver series; tooling, tests, profiles |
| 02 | Zelda Test4-A — original graphics and crash fixes | 264 core patches; frontend patch; driver patches; tests |
| 03 | Zelda Test3 — graphics and crash fixes | 25 supplied source files |
| 04 | Zelda Test2 — memory fixes | 11 supplied source files |
| 05 | T34 RADV | Compiled release only; no independently supplied source snapshot |

## Pinned upstream revisions (Test4-A)
- Frontend: https://github.com/Vampinity/Eglantine-PS5- at commit `25cfc07be0a3675749adece5d012fdb916c4cd48`
- Core: https://github.com/Djihads80/Eglantine at commit `0ca2032bffc5f1a3fca75427f7d4a4718adda660`

The 12 GiB / 2-worker variant sets:
```ini
EDEN_NX2_MEMORY_GB=12
EDEN_NX2_PIPELINE_WORKERS=2
```

## Reconstruction status
The supplied source is an overlay-based reconstruction kit, *not a self-contained checkout*. A full reconstruction requires downloading the pinned source trees and applying all ordered patches once. The existing container could not resolve github.com, so neither that checkout nor a new PS5 binary build was completed there. No game or firmware files are included.

**Note:** This index documents the versions and is not a substitute for uploading the actual source contents. The consolidated source ZIP is available in the chat that requested this repository update.
