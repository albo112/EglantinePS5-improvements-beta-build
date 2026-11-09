# Verified upstream baseline: EglantinePS5 v1.219.020

**Original project:** https://github.com/viejunerd/Eglantine-PS5-

**Canonical release:** https://github.com/viejunerd/Eglantine-PS5-/releases/tag/v1.219.020

**Upstream frontend commit:** `88054da1edf897a301cdef2b8e5d2ff8563254ec`

**Pinned emulator core (Eglantine submodule):** `0ca2032bffc5f1a3fca75427f7d4a4718adda660`

The user-supplied source file `Eglantine-PS5--1.219.020.zip` was checked for ZIP integrity (656 regular files, 52 directories); its README, Makefile and release workflow Git blob SHA-1 values match the above tag. SHA-256 of the supplied source ZIP:

```
924ff3e180dba2fd83c362f5580faddef35493978de1bfeac42543d61f73e2e3
```

That GitHub source snapshot **does not include the Eglantine submodule source**. To reproduce an upstream checkout:

```bash
git clone https://github.com/viejunerd/Eglantine-PS5-.git
cd Eglantine-PS5-
git checkout 88054da1edf897a301cdef2b8e5d2ff8563254ec
git submodule update --init --recursive
```

The project's historical source modifications are preserved separately under `source-versions/`. The Test4-A 12 GiB / 2-worker release build uses frontend `Vampinity/Eglantine-PS5-` commit `25cfc07be0a3675749adece5d012fdb916c4cd48` and the pinned core commit above. Do not confuse an upstream v1.219.020 release binary with a compiled Test4-A binary.

## Build and release status

A separate GitHub Actions workflow (`.github/workflows/build-pinned-test4a.yml`) reconstructs Test4-A with the ordered source patches and runs the PS5 native build. When it succeeds, `.github/workflows/publish-test4a-release.yml` validates the binary and publishes a GitHub prerelease with the generated ZIP and SHA256SUMS. It does not publish failed or incomplete binaries.
