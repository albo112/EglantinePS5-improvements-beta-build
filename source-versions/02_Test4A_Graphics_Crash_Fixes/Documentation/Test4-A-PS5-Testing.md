# Test4-A PS5 testing instructions

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

## Before installation

Use a package only after the native build and package verification are certified. Requested filename: `EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes.zip`. Current state: Completed receipt reports exit **0**, with unchanged source hashes during the build. Final outer-ZIP CRC, manifests, file permissions and SHA-256 hashes are recorded in the adjacent `Zelda-Test4-A-Verification.json` after packaging. Validate that receipt before installing.

1. Fully close the emulator. Back up the current executable and title profile, and preserve saves/settings/caches.
2. Use the same homebrew installation method you currently use. Your logs select `/system_ex/app/PPSA98515`; a second `/data/homebrew/PPSA98515` exists. Do not assume copying to the second folder changes the active installation.
3. Install the final app folder/profile as documented with the certified package. Verify the next boot trace's selected folder, build marker/date and version. An optional local ZIP hash does not prove the installed binary; an executable readback/hash is stronger evidence when available.
4. Keep output 1080p/60 Hz, 1x resolution and Bilinear for the initial comparison. Record the complete title environment block. Use the unchanged 49-key Prettier profile packaged as the Test4-A default for graphics testing. All supplied crash sessions used the historical Faster profile, so they are not an equivalent-correctness baseline for default Prettier.

`Zelda-faster-profile.txt` is retained only to reproduce that historical Test3 baseline. Its `LONE=0` leaves lone-mesh fallback disabled and may omit foliage. Do not select it as a recommended performance preset or treat its FPS as equivalent to complete rendering. Preserve its bytes for comparison; it is not the default installation profile.

## Controlled warm comparison

Use the same save, route, camera, output, shader-cache state and log level for Test3 and Test4-A, with Prettier on both for graphics-correctness comparisons. Identify any separate historical Faster run as a potentially incomplete-graphics baseline. If available in the current save, include a slow pan through Kokiri Forest vegetation, the Deku Tree exterior, water/reflections and an interior/dungeon transition. Do not change several profile flags between runs.

For correctness, check whether tree canopies, grass/plants and previously missing surfaces render consistently. Compare light/dark areas and water with the same camera and output mode. Count flashes and visible glitches from a recording where available; a still screenshot does not prove flash reduction. Keep any capture contrast/HDR settings constant.

Run a short repeatable route first, then extend normal gameplay to 20–30 minutes if stable. A 60-minute target is a test target, not a promised result. Distinguish app uptime from game-session duration and note any return to the menu or reload.

Record FPS sample distribution, worst frame intervals, memory headroom and the exact scene. Do not call a faster run equivalent if it omits geometry. Correcting Test3's `NO_MESH=0` bug can increase actual GPU work. The supplied archives contain only Faster-profile sessions; any full-foliage comparison must identify that difference.

## Cold-cache comparison

Perform this only after a successful warm test and with the emulator fully closed. Locate the actual title pipeline cache and Mesa/RADV disk-cache folders first. Preserve them by copying or renaming into timestamped backups; do not delete them and do not touch saves, firmware or keys. Record which caches were quarantined.

The source-derived title cache is `/data/eglantineps5/user/cache/shader/0400486024dec000/`, containing any of `vulkan.bin`, `vulkan_mesh.bin`, `vulkan_used.bin` and `vulkan_pipelines.bin`. Back it up to the PC and rename the console folder to `0400486024dec000-Test3-backup` before a title-cache cold test. A separate fully cold driver test also backs up and renames `/data/eglantineps5/cache/radv`. Test the same scene once cold and again after a clean exit with the newly written warm cache. Preserve both cache versions if classification errors recur.

A cache is not proven cold merely because one file was removed. Verify startup cache counts and whether the separate driver cache was also reset. Repeat the same route, keep compile-worker settings unchanged initially, and report loading time, shader-compilation stalls, headroom and any first-encounter graphics failures. Restore the backed-up caches afterward if needed.

## If it crashes or stalls

Keep the crash summary and its matching `-eden_log.txt`, `-heap.log` and `-stderr.log`, plus `crash-index.txt`, both current/previous boot traces and current logs. Keep the complete folder instead of selecting only final lines. Note the scene/transition, route, profile, cache state and how long the game itself ran.

Do not repeatedly restart and overwrite evidence before copying it. Preserve the final Test4-A verification receipt and executable hash; developers need matching symbols. A hang-watch warning or stale log alone is not proof of a GPU hang.

Remote dashboard/video setup remains Test4-B work. Test4-A uses lightweight existing logs and bounded diagnostics; no console connection or remote video test has been performed for this snapshot.
