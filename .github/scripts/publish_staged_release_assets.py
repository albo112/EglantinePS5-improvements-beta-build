#!/usr/bin/env python3
"""Publish original Albo ZIP bundles from immutable, SHA-256-verified staging chunks."""
import hashlib,json,os,subprocess,sys,zipfile
from pathlib import Path

ROOT=Path("release-uploads")
GH_REPO="albo112/EglantinePS5-Fork-improvements.-"

def run(*args, check=True):
    return subprocess.run(args,check=check,text=True,capture_output=True)

def check_zip(filename):
    with zipfile.ZipFile(filename) as z:
        if z.testzip() is not None:
            raise RuntimeError(f"Archive corruption: {filename}")
        if "PS5-build/PPSA98515/eboot.bin" not in z.namelist():
            raise RuntimeError(f"Missing PS5 executable: {filename}")
        if not z.getinfo("PS5-build/PPSA98515/eboot.bin").file_size:
            raise RuntimeError("Empty PS5 executable")
        if "RELEASE-MANIFEST.json" not in z.namelist():
            raise RuntimeError("Missing source and provenance manifest")

def publish_one(directory):
    meta_path=directory/"manifest.json"
    if not meta_path.is_file():
        print("Skipping unfinished staging directory:",directory)
        return
    meta=json.loads(meta_path.read_text())
    pieces=sorted(directory.glob("part-*.bin"))
    if len(pieces)!=meta["part_count"]:
        raise RuntimeError(f"Incomplete chunk upload for {meta['tag']}: {len(pieces)} / {meta['part_count']}")
    output=Path("/tmp")/meta["filename"]
    digest=hashlib.sha256()
    size=0
    with output.open("wb") as out:
        for piece in pieces:
            with piece.open("rb") as src:
                while block:=src.read(1024*1024):
                    out.write(block)
                    digest.update(block)
                    size+=len(block)
    if digest.hexdigest()!=meta["sha256"] or size!=meta["bytes"]:
        raise RuntimeError(f"ZIP digest or length mismatch: {meta['tag']}")
    check_zip(output)
    sums=Path("/tmp")/(meta["filename"]+".sha256")
    sums.write_text(f"{meta['sha256']}  {meta['filename']}\n")
    tag=meta["tag"]
    release=run("gh","release","view",tag,"--repo",GH_REPO,check=False)
    if release.returncode==0:
        assets=run("gh","release","view",tag,"--repo",GH_REPO,"--json","assets",
                    "--jq",".assets[].name").stdout.splitlines()
        if meta["filename"] in assets:
            print("Existing release asset verified by name; skipping upload:",tag)
            return
        print("Uploading additional asset to existing release",tag)
        run("gh","release","upload",tag,str(output),str(sums),"--repo",GH_REPO)
        return
    notes=Path("/tmp")/(tag+"-notes.md")
    notes.write_text(
        f"# {meta['title']}\n\n"
        f"**Experimental PS5 release.** Original user-supplied executable paired with its available "
        f"source-change patches and reconstruction instructions. These archives have been verified "
        f"for integrity and executable presence; no claim of new console compatibility or stability.\n\n"
        f"{meta['description']}\n\n"
        f"- Maintainer: **Albo (@albo112)**.\n"
        f"- Original work: viejunerd, Djihads80, Vampinity, heydemoura, BlackBearReloaded and other upstream contributors.\n"
        f"- AI assistance: OpenAI ChatGPT and Codex (tools, not human maintainers).\n"
        f"- Source changes: https://github.com/{GH_REPO}/tree/main/source-versions\n"
        f"- License and credits: https://github.com/{GH_REPO}/blob/main/LICENSE and CREDITS.md\n"
        f"- Package SHA-256: `{meta['sha256']}`.\n"
        f"- Source package includes no games, firmware or private keys.\n\n"
        f"Keep a backup of your existing PS5 app and saves. T34 RADV does not have an independently "
        f"supplied source tree.\n"
    )
    run("gh","release","create",tag,str(output),str(sums),
        "--repo",GH_REPO,"--target","main","--prerelease",
        "--title",meta["title"]+" (experimental)","--notes-file",str(notes))
    print("PUBLISHED:",tag)

if __name__=="__main__":
    if not ROOT.is_dir():
        sys.exit("Missing release-uploads directory")
    for d in sorted(ROOT.iterdir()):
        if d.is_dir():
            publish_one(d)
