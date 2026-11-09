# EglantinePS5 Zelda Test4-A

> **Handoff snapshot:** source and host evidence below are real. Native build, final checks and packaging are explicitly labelled by their available receipts. No Test4-A PS5 run is claimed.

Test4-A addresses crashes and rendering correctness from the supplied Logs3, Logs4 and Logs5. The remote dashboard and video work are reserved for Test4-B and are not part of this release scope.

The highest-confidence findings are six identical NIR compiler null writes under severe memory pressure and a configuration-value bug that makes `EDEN_NX2_NO_MESH=0` skip geometry. Correcting skipped rendering can increase real GPU work, so the earlier FPS figures cannot be promised with complete graphics.

Implemented source corrections check NIR allocation failures, honor the mesh toggle, and keep refused image allocations out of the cache until a backed retry succeeds. Bounded draw-failure counters, a global heap-failure snapshot and safely probed fault-instruction bytes improve future crash evidence. These changes have focused host checks; visual quality, crash-free duration and performance still need PS5 testing.

The unchanged 49-key Prettier profile is the Test4-A default. `Zelda-faster-profile.txt` is retained only as the historical Test3 comparison baseline: its `LONE=0` leaves lone-mesh fallback disabled and may omit foliage. It is not an equivalent-correctness performance recommendation.

- [Crash analysis and session timelines](Test4-A-Crash-Analysis.md)
- [Detailed changelog](Test4-A-Changelog.md)
- [Validation results and limits](Test4-A-Validation.md)
- [PS5 testing instructions](Test4-A-PS5-Testing.md)
- [Regression comparison](Test4-A-Regression-Comparison.md)
- [Source reconstruction and build instructions](Test4-A-Source-and-Build.md)

Requested final emulator filename: `EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes.zip`.

Current receipt state: Completed receipt reports exit **0**, with unchanged source hashes during the build. 8 recorded final commands, all exit **0**. Final outer-ZIP CRC, manifests, file permissions and SHA-256 hashes are recorded in the adjacent `Zelda-Test4-A-Verification.json` after packaging. Validate that receipt before installing.

Preserved inputs: all four original archives remain byte-identical. The public and Test3 packages are comparison inputs, not replacements for the reconstructed Test3 source.
