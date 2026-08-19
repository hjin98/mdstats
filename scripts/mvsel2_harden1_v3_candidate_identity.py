#!/usr/bin/env python3
"""Compute the Protocol-v3 candidate content identity for MVSEL2 hardening.

The identity includes every tracked file by default and excludes only declared
coordination/evidence classes that cannot affect build, runtime, scientific,
package, specification, release, or qualification behavior.  Benchmark source
is included; generated benchmark JSON evidence is excluded.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Iterable


POLICY_ID = "mdstats.mvsel2-harden1-v3.candidate-identity.v1"


def _excluded(path: str) -> bool:
    if path.startswith("workplans/"):
        return True
    if path.startswith("qualification/"):
        return True
    if path.startswith("verification/"):
        return True
    if path.startswith("audits/") and path.endswith((".log", ".json")):
        return True
    if path.startswith("benchmarks/") and path.endswith(".json"):
        return True
    return False


def _run(*args: str) -> bytes:
    return subprocess.run(
        args,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def _tracked_entries() -> Iterable[tuple[str, str, str]]:
    payload = _run("git", "ls-files", "--stage", "-z")
    for row in payload.split(b"\0"):
        if not row:
            continue
        metadata, raw_path = row.split(b"\t", 1)
        mode, blob_sha, stage = metadata.decode("ascii").split()
        if stage != "0":
            raise RuntimeError(f"unmerged tracked path: {raw_path!r}")
        yield raw_path.decode("utf-8", "surrogateescape"), mode, blob_sha


def _blob_bytes(blob_sha: str) -> bytes:
    return _run("git", "cat-file", "blob", blob_sha)


def _tracked_dirty_paths() -> tuple[str, ...]:
    rows = _run("git", "status", "--porcelain=v1", "-z").split(b"\0")
    dirty: list[str] = []
    for row in rows:
        if not row:
            continue
        text = row.decode("utf-8", "surrogateescape")
        status = text[:2]
        path = text[3:]
        if status == "??":
            continue
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if not _excluded(path):
            dirty.append(path)
    return tuple(sorted(set(dirty)))


def build_manifest() -> dict[str, object]:
    dirty = _tracked_dirty_paths()
    if dirty:
        raise RuntimeError(
            "candidate tracked surfaces are dirty: " + ", ".join(dirty)
        )

    included: list[dict[str, str]] = []
    excluded: list[str] = []
    digest = hashlib.sha256()
    digest.update((POLICY_ID + "\n").encode("utf-8"))
    for path, mode, blob_sha in sorted(_tracked_entries()):
        if _excluded(path):
            excluded.append(path)
            continue
        payload = _blob_bytes(blob_sha)
        content_sha256 = hashlib.sha256(payload).hexdigest()
        row = {
            "path": path,
            "mode": mode,
            "sha256": content_sha256,
        }
        included.append(row)
        encoded = json.dumps(
            row, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8", "surrogateescape")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)

    head = _run("git", "rev-parse", "HEAD").decode("ascii").strip()
    return {
        "schema": "mdstats.protocol-v3-candidate-content-identity.v1",
        "policy_id": POLICY_ID,
        "candidate_commit": head,
        "candidate_content_identity": digest.hexdigest(),
        "included": included,
        "excluded": excluded,
        "exclusion_rule": (
            "exclude workplans/, qualification/, verification/, audits/*.log|json, "
            "and generated benchmarks/*.json; include benchmark source and all other tracked files"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--digest-only", action="store_true")
    args = parser.parse_args()

    manifest = build_manifest()
    if args.digest_only:
        print(manifest["candidate_content_identity"])
    else:
        text = json.dumps(manifest, indent=2, sort_keys=True) + "\n"
        if args.manifest is None:
            print(text, end="")
        else:
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            args.manifest.write_text(text, encoding="utf-8")
            print(manifest["candidate_content_identity"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
