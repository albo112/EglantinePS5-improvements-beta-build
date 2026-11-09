# Test4-A Zelda 12 GiB / 2-worker source variant

This package combines the previously verified **Test4-A source reconstruction kit** with the user-uploaded `EglantinePS5-Zelda-Test4-A-Source-Changes.rar`. The RAR contains 456 source-bundle files. All 456 were compared byte-for-byte against the earlier Test4-A source ZIP. Exactly one differs: `profiles/env-0400486024dec000.txt`.

The new profile has:

```ini
EDEN_NX2_MEMORY_GB=12
EDEN_NX2_PIPELINE_WORKERS=2
```

The older profile specified `EDEN_NX2_PIPELINE_WORKERS=4` and did not explicitly set `EDEN_NX2_MEMORY_GB`. The core's memory-layout patch interprets 12 as the **12 GiB guest memory layout** (it is not a verified hard 12 GB cap on the entire emulator process). The pipeline-workers patch reads the worker limit and requests two builder threads. This is configuration/source inspection only; the compiled PS5 executable has not been verified against these values here.

**Reconstruction:** `reconstruct-test4a.sh` overlays this exact updated game profile when reconstructing the frontend and emulator core pinned to commits listed in `README-START-HERE.md`. Upstream source trees and build dependencies are not bundled, and reconstruction or a PS5 build was not run in this environment.

**Other profiles:** `profiles/zelda-faster-profile.txt` remains the unchanged *older* 4-worker profile, intentionally preserved as supplied. Use the game-specific `profiles/env-0400486024dec000.txt` for this 12 GiB / 2-worker configuration.

**Manifest:** The original `SOURCE-MANIFEST.json` has been preserved under `SOURCE-MANIFEST-ORIGINAL-TEST4A.json`. The current `SOURCE-MANIFEST.json` updates the single changed profile hash and independently verifies all 455 manifest-tracked files. Additional provenance and exact difference are in `TEST4A-12GB-2WORKERS-AUDIT.json` and `TEST4A-12GB-2WORKERS-PROFILE.diff`.
