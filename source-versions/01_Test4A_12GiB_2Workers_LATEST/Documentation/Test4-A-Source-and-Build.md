# Test4-A source reconstruction and build handoff

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

## Exact base

- Frontend repository: `https://github.com/Vampinity/Eglantine-PS5-`
- Frontend revision: `25cfc07be0a3675749adece5d012fdb916c4cd48`
- Core repository: `https://github.com/Djihads80/Eglantine`
- Core revision: `0ca2032bffc5f1a3fca75427f7d4a4718adda660`
- Isolated frontend: `/var/lib/eglantine-build/zelda-test4-a/Eglantine-PS5`, branch `codex/zelda-test4-a`
- Isolated core branch: `codex/zelda-test4-a-core`

The supplied `SOURCE.json`, `BUILD.txt`, frontend diff, four extra patches, profiles, checks and research documents define Test3. Reconstruction applied the frontend diff to the pinned frontend, copied the four additional overlays and ran the complete ordered overlay helper. The 261 overlays comprise 257 base patches plus 0425/0427/0428/0429. Byte comparison against the saved Test3 source manifest found zero missing/changed files across 5,684 files before Test4-A edits. Test4-A adds core overlays 0430/0431/0432 for a total of 264.

The separate final overlay replay starts from the pinned core, applies those 264 overlays, and compares the core's Git-listed tracked/unignored files: 4,800 files match byte for byte, with no missing, extra or changed files. This narrower replay inventory excludes nested external/submodule contents included in the earlier 5,684-file Test3 snapshot. The checks establish different things: Test3 reconstruction fidelity before changes, and final Test4-A overlay reproducibility after changes. See `overlay-replay.json` for the final replay and ordered patch hashes.

The four original archives are immutable inputs. Their checksums and extracted inventories are in `input-inventory.json`. Existing released Test3 ZIPs and matching symbols remain preserved. No public-release source substitution or unreviewed upstream merge is part of Test4-A.

## Current additional overlays

- `0430-test4a-no-mesh-boolean.patch`
- `0431-test4a-bounded-draw-diagnostics.patch`
- `0432-test4a-transient-image-refusal.patch`
- `test4a-01-nir-copy-prop-oom.patch`

The final source-change bundle must include all additional overlays, the full frontend diff, exact pins, relevant licenses, title profile(s), new tests and fixtures, original supplied verification scripts, build commands and source/artifact hashes. Host-only Mesa tests must not accidentally enter the production driver export.

The native driver export applies the original ordered driver patch series plus `tools/radv-patches/test4a-01-nir-copy-prop-oom.patch`, with the series helper and WSI fingerprint covering that directory. The host Mesa copy contains test-only Meson/C harness changes; rebuilding production from that entire copy would be incorrect. Use the pinned production Mesa source and the checked patch generator.

## Native build

Use the existing pinned dependencies in `tools/deps.json`. The prepared build-input receipt identifies an independent cache and mutable driver tree; old driver build outputs must not be linked as writable Test4-A outputs. SDK/decoder reuse is permitted only when matching pins and binary hashes are checked. Keep `build/radv-isolated` independent.

```sh
JOBS=3 RADV_BUILD_JOBS=2 bash tools/ci/build-release.sh
```

The CI path skips the full legacy source-check suite. Run the seven supplied checks with their original bytes, the inherited fence check and each new focused regression separately. GPU range check invocation must include the already-applied source and the 0429 patch path as described in supplied `BUILD.txt`.

Require a fresh successful native receipt whose source hashes before/after are identical, a final current-source test receipt and native package integrity checks before distributing the ZIP. Preserve a separately named matching Test4-A ELF. An earlier Test4 prototype build is not a Test4-A build.

Current state: Completed receipt reports exit **0**, with unchanged source hashes during the build. 8 recorded final commands, all exit **0**. Final outer-ZIP CRC, manifests, file permissions and SHA-256 hashes are recorded in the adjacent `Zelda-Test4-A-Verification.json` after packaging. Validate that receipt before installing.

No upstream push or PR is part of this work. Local changes are AI-assisted. This handoff does not claim human gameplay testing or PS5 certification.
