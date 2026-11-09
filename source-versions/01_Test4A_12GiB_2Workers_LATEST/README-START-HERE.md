# Latest variant: 12 GiB / 2 workers

Read `README-12GB-2WORKERS.md` first. This is the user-provided **Test4-A 12 GiB / 2-worker** profile variant; it preserves the original Test4-A code patches. It is a **reconstruction kit**, not a complete upstream checkout or verified rebuilt PS5 binary.

---

# EglantinePS5 – Zelda Test4-A source reconstruction kit

This is **the complete set of source changes present in the eight user-uploaded ZIPs**, not a self-contained checkout of all upstream C/C++ files. The latest Test4-A source-change archive is the canonical patch set. This kit contains 264 ordered Eglantine core patches, the frontend patch, driver patches, test fixtures, evidence, pinned revisions and build instructions.

## How to reconstruct the full source tree

With an internet-connected Linux/WSL machine, Git, Python and ordinary build prerequisites, run:

```bash
bash reconstruct-test4a.sh /path/to/EglantinePS5-Test4A-Full-Source
```

The script checks out:
- Frontend: https://github.com/Vampinity/Eglantine-PS5- at `25cfc07be0a3675749adece5d012fdb916c4cd48`
- Core: https://github.com/Djihads80/Eglantine at `0ca2032bffc5f1a3fca75427f7d4a4718adda660`

It applies the frontend changes, copies bundled tools and source tests, then runs the upstream patch-application helper to apply the 264 core overlays once. The exact external dependencies and build requirements are in `SOURCE.json`, `BUILD.txt`, `tools/deps.json` and `Documentation/Test4-A-Source-and-Build.md`.

The source kit does not include those baseline Git repositories, all external build dependencies, game content, keys, firmware or proprietary SDK components. It has not been rebuilt or gameplay-tested in this environment, and the reconstruction script has not been executed here because outbound Git hosting is unreachable in this container. Git/network/toolchain failures may require manual adjustments.

## Earlier versions

The earlier Test2 and Test3 source-patch archives were also supplied and inspected. They are preserved separately under `historical-source-archives/` for reference. They are **not** applied after Test4-A; doing so could regress or duplicate newer changes. The 37 MB ZIPs are compiled PS5 release packages, not source trees.

## Verification

All 8 supplied archives passed their ZIP CRC tests. The included `SOURCE-MANIFEST.json` hashes of original Test4-A bundled files were independently checked before packaging. `PACKAGE-AUDIT.json` records SHA-256 hashes of the original ZIPs and the manifest verification count.
