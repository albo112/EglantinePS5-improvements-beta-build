# EglantinePS5 — user-provided experimental PS5 builds

**Maintainer:** [Albo (@albo112)](https://github.com/albo112).

All five uploaded binary ZIPs passed integrity checks and include `PPSA98515/eboot.bin`. They were supplied by Albo; this review does **not** establish stability or game compatibility. Version labels here are experimental development identifiers, not official upstream releases.

| Newest to oldest | Expected release tag | Original upload | PS5 content version | SHA-256 |
| --- | --- | --- | --- | --- |
| Test4-A 12 GiB, 2 workers | `zelda-test4a-12gib-2workers` | `EglantinePS5-Zelda-Test4-A-12GB Latest Build(1).zip` | 01.219.020 | `a0410ea88a56e2520b59f5a58138bfeb305b26bbb1d1412b465b93e8c5972f97` |
| Test4-A original | `zelda-test4a-original` | `EglantinePS5-Zelda-Test4-A-Graphics-and-Crash-Fixes(3).zip` | 01.219.020 | `3cd62c1beeebeed14351c55fe81bb82597ed5c7b98ba37103954c55a31c4592b` |
| Test3 graphics/crash | `zelda-test3-graphics-crash-fixes` | `EglantinePS5-Zelda-Test3-Graphics-and-Crash-Fixes(2).zip` | 01.219.020 | `55ec27a975ded934698ca04185f622459ed45ff032741502ce383ed49e9cfef7` |
| Test2 memory fix | `zelda-test2-memory-fix` | `EglantinePS5-Zelda-Memory-Fix-Test2(2).zip` | 01.219.007 | `1d18cae9fc27a8948b128c72c44e45b9a2b535d1043ca4bce491dbe3eb64d46f` |
| T34 RADV fix | `zelda-t34-radv-fix` | `EglantinePS5-Zelda-T34-RADV-fix(2).zip` | 01.219.007 | `f8354bb8a1b722c8a3755679ee2deab89b7377cb43c383e17a85b25e4e84d26e` |

The latest Test4-A ZIP sets `EDEN_NX2_MEMORY_GB=12` (guest-memory layout) and `EDEN_NX2_PIPELINE_WORKERS=2`. Its executable SHA-256 is `89b1550630d3c624b6114da483f1a0db708046f2c883d0e250a8697bd1310536`, **identical to the original Test4-A ZIP's executable**. These two ZIPs have different configuration and package contents.

## Source and license

- [Versioned source changes and reconstruction instructions](source-versions/)
- [Verified upstream v1.219.020 baseline](source-versions/UPSTREAM-v1.219.020.md)
- [GPLv3 license](LICENSE)
- [Credits and attribution](CREDITS.md)

Contributors: original upstream projects by [viejunerd](https://github.com/viejunerd/Eglantine-PS5-), [Djihads80](https://github.com/Djihads80/Eglantine), [Vampinity](https://github.com/Vampinity/Eglantine-PS5-), [heydemoura](https://github.com/heydemoura/EglantinePS5), and earlier contributors. OpenAI ChatGPT and Codex assisted with analysis, development discussion and documentation as AI tools.

The connected GitHub file integration cannot directly attach these conversation-uploaded ZIPs to GitHub Releases. The source ZIPs are **not** release assets yet. A separate, already configured GitHub Actions workflow can publish a **new successful CI-built Test4-A ZIP** after validating its binary and checksum. All source and license obligations must be met for binaries distributed under the GPLv3 and other applicable licenses.

The five original experimental ZIPs can be attached using GitHub CLI on a computer with internet access, with integrity verification and release notes; use `scripts/publish-uploaded-releases.sh` in this repository when the ZIPs are accessible locally.
