#!/usr/bin/env python3
"""Exercise the shipped memory controls from actual source; only /tmp is built.

This checks parsing, scratch retention decisions and the early transcode retry.
It does not exercise PS5 allocations, Vulkan submission, or performance.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory


def block(text, marker, opening_after_marker=False):
    start = text.index(marker)
    opening = text.index("{", start + len(marker) if opening_after_marker else start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True,
                        help="Frontend checkout, containing the Eglantine core")
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()
    source = args.source.resolve() / "Eglantine/src"
    paths = {
        "nup": source / "core/file_sys/nup_container.cpp",
        "ring": source / "video_core/renderer_vulkan/vk_staging_buffer_pool.cpp",
        "scratch": source / "video_core/texture_cache/texture_cache.h",
        "pipeline": source / "video_core/renderer_vulkan/vk_scheduler.h",
        "transcode": source / "video_core/renderer_vulkan/vk_texture_cache.cpp",
    }
    texts = {key: path.read_text() for key, path in paths.items()}
    pieces = {
        "nup": block(texts["nup"], "std::size_t ChosenCacheCap("),
        "ring": block(texts["ring"], "size_t StreamRingSize("),
        "scratch_parser": block(texts["scratch"], "static const size_t scratch_keep = []") + "();",
        "scratch_release": block(texts["scratch"], "for (auto* const scratch : {&swizzle_data_buffer, &unswizzle_data_buffer})", True),
        "pipeline": block(texts["pipeline"], "[[nodiscard]] inline bool PipelineFailSoft()"),
        "transcode_parser": block(texts["transcode"], "static const bool wait_for_memory = []") + "();",
        "transcode_retry": block(texts["transcode"], "if (wait_for_memory && staging_buffer_pool.RefusedJustNow())"),
    }
    expected_profile = {
        "EDEN_NX2_NATIVE_TABLES": "compute", "EDEN_NX2_TABLE_POOL_MIB": "128",
        "EDEN_NX2_OOT_VISUAL_WORKAROUND": "0", "EDEN_NX2_TENSOR": "compact",
        "EDEN_NX2_TENSOR_ONLY": "c00", "EDEN_NX2_OOT_DYNAMIC_FPS": "1",
        "EDEN_NX2_NO_MESH": "1", "EDEN_NUP_CACHE_MIB": "128",
        "EDEN_STREAM_RING_MIB": "64", "EDEN_TC_SCRATCH_KEEP_MIB": "16",
        "EDEN_NX2_PIPELINE_FAIL_SOFT": "1", "EDEN_NX2_TRANSCODE_WAIT": "1",
    }
    profile = {}
    for line in args.profile.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        assert key not in profile, f"duplicate profile key: {key}"
        profile[key] = value
    assert profile == expected_profile, (profile, expected_profile)

    code = r'''
#include <algorithm>
#include <cassert>
#include <cstddef>
#include <cstdlib>
#include <string>
#define LOG_INFO(...) ((void)0)
#define LOG_WARNING(...) ((void)0)
constexpr size_t MiB = size_t{1} << 20;
constexpr size_t MAX_STREAM_BUFFER_SIZE = 128 * MiB;
constexpr size_t LargeScratchCapacity = 64 * MiB;
struct Scratch {
    size_t held{};
    size_t capacity() const { return held; }
    void release() { held = 0; }
} swizzle_data_buffer, unswizzle_data_buffer;
struct Staging { bool refused{}; bool RefusedJustNow() const { return refused; } } staging_buffer_pool;
bool upload_refused{}, decode_started{};
''' + pieces["nup"] + "\n" + pieces["ring"] + "\n" + pieces["pipeline"] + r'''
void TrimScratch() {
''' + pieces["scratch_parser"] + "\n" + pieces["scratch_release"] + r'''
}
void AttemptTranscode() {
''' + pieces["transcode_parser"] + "\n" + pieces["transcode_retry"] + r'''
    decode_started = true;
}
int main(int argc, char** argv) {
    assert(argc == 4);
    const std::string control{argv[1]}, value{argv[2]}, test{argv[3]};
    const char* key = control == "nup" ? "EDEN_NUP_CACHE_MIB"
                    : control == "ring" ? "EDEN_STREAM_RING_MIB"
                    : control == "scratch" ? "EDEN_TC_SCRATCH_KEEP_MIB"
                    : control == "pipeline" ? "EDEN_NX2_PIPELINE_FAIL_SOFT"
                    : "EDEN_NX2_TRANSCODE_WAIT";
    if (value == "unset") unsetenv(key);
    else setenv(key, value.c_str(), 1);
    if (control == "nup") {
        assert(ChosenCacheCap(512 * MiB) == std::stoull(test) * MiB);
    } else if (control == "ring") {
        const bool smaller_device = test == "smaller-device";
        const size_t expected = smaller_device ? 32 : std::stoull(test);
        assert(StreamRingSize((smaller_device ? 32 : 128) * MiB) == expected * MiB);
    } else if (control == "scratch") {
        const size_t cap = std::stoull(test) * MiB;
        swizzle_data_buffer.held = cap;
        unswizzle_data_buffer.held = cap + MiB;
        TrimScratch();
        assert(swizzle_data_buffer.held == cap); // exact boundary retained
        assert(unswizzle_data_buffer.held == 0); // over boundary released
    } else if (control == "pipeline") {
        assert(PipelineFailSoft() == (test == "on"));
    } else {
        staging_buffer_pool.refused = test != "available";
        AttemptTranscode();
        const bool should_wait = test == "wait";
        assert(upload_refused == should_wait);
        assert(decode_started == !should_wait);
    }
}
'''
    cases = [
        ("nup", "unset", "512"), ("nup", "128", "128"),
        ("nup", "0", "512"), ("nup", "8", "16"), ("nup", "16", "16"),
        ("nup", "512", "512"), ("nup", "bad", "512"),
        ("ring", "unset", "128"), ("ring", "64", "64"),
        ("ring", "16", "16"), ("ring", "128", "128"),
        ("ring", "15", "128"), ("ring", "129", "128"),
        ("ring", "0", "128"), ("ring", "bad", "128"),
        ("ring", "64", "smaller-device"),
        ("scratch", "unset", "64"), ("scratch", "16", "16"),
        ("scratch", "0", "0"), ("scratch", "64", "64"),
        ("scratch", "65", "64"), ("scratch", "bad", "64"),
        ("pipeline", "unset", "off"), ("pipeline", "0", "off"),
        ("pipeline", "1", "on"), ("pipeline", "bad", "off"),
        ("transcode", "unset", "continue"), ("transcode", "0", "continue"),
        ("transcode", "1", "wait"), ("transcode", "1", "available"),
        ("transcode", "bad", "continue"),
    ]
    # Clear all five controls in each subprocess, independent of shell environment.
    env = dict(os.environ)
    for key in expected_profile:
        env.pop(key, None)
    with TemporaryDirectory(prefix="eglantine-memory-profile-", dir="/tmp") as directory:
        temporary = Path(directory)
        cpp = temporary / "check.cpp"
        binary = temporary / "check"
        cpp.write_text(code)
        compile_command = ["clang++-18", "-std=c++20", "-Wall", "-Wextra", "-Werror",
                           str(cpp), "-o", str(binary)]
        subprocess.run(compile_command, check=True, env=env)
        for case in cases:
            subprocess.run([str(binary), *case], check=True, env=env)
    evidence = {
        "check": "actual-source memory controls and final per-title profile",
        "status": "pass", "exit_code": 0, "compiler": "clang++-18 -std=c++20 -Wall -Wextra -Werror",
        "runtime_cases_passed": len(cases), "cases": cases,
        "profile": str(args.profile.resolve()), "profile_values": profile,
        "profile_sha256": hashlib.sha256(args.profile.read_bytes()).hexdigest(),
        "source_sha256": {str(paths[key]): hashlib.sha256(path.read_bytes()).hexdigest()
                          for key, path in paths.items()},
        "extracted_blocks_sha256": {key: hashlib.sha256(value.encode()).hexdigest()
                                    for key, value in pieces.items()},
        "not_verified": ["PS5 allocation behavior", "Vulkan submission and synchronization",
                         "gameplay/crash-free duration", "measured memory or FPS improvement"],
        "mutations": "only this evidence file; compilation used an automatically removed /tmp directory",
    }
    args.evidence.write_text(json.dumps(evidence, indent=2) + "\n")
    print(json.dumps({"check": evidence["check"], "status": "pass", "exit_code": 0,
                      "runtime_cases_passed": len(cases), "profile_keys_checked": len(profile),
                      "evidence": str(args.evidence.resolve())}))


if __name__ == "__main__":
    main()
