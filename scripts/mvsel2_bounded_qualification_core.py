#!/usr/bin/env python3
"""REV8 qualification wrapper with material G5 evidence reuse.

The previous authority-cache/orphan-discovery implementation is preserved in
``mvsel2_bounded_qualification_adapted.py``.  This outer wrapper adds only a
Protocol-3.1 evidence-reuse rule: a prior G5 PASS may be reused when the current
tracked worktree is clean on the G5 material surface and that surface is
byte-identical between the prior and current Git commits.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
from typing import Any

import mvsel2_bounded_qualification_adapted as adapted

engine = adapted.recovery.engine
_ORIGINAL_RUN_PREFLIGHT = engine.run_preflight

_G5_MATERIAL_PATHS = (
    "mdstats",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "MANIFEST.in",
    "scripts/mvsel2_qualification_preflight.py",
    "tests/test_mlff_repair2.py",
    "tests/test_mlff_mvstate2.py",
    "tests/test_mlff_mvsel2_forward.py",
    "tests/test_mlff_mvmigrate2.py",
    "tests/test_mlff_mvsel2_hardening.py",
    "tests/test_mlff_mvsel2_oracle.py",
    "tests/test_mlff_mvsel2_rev8_qualification.py",
    "tests/test_mlff_target_data2c_repair1.py",
)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )


def _current_head(repo: Path) -> str | None:
    result = _git(repo, "rev-parse", "HEAD")
    return result.stdout.strip() if result.returncode == 0 else None


def _material_surface_clean(repo: Path) -> bool:
    result = _git(repo, "status", "--porcelain", "--", *_G5_MATERIAL_PATHS)
    return result.returncode == 0 and not result.stdout.strip()


def _material_surface_unchanged(repo: Path, old: str, new: str) -> bool:
    if not old or not new:
        return False
    exists = _git(repo, "cat-file", "-e", f"{old}^{{commit}}")
    if exists.returncode != 0:
        return False
    diff = _git(repo, "diff", "--quiet", old, new, "--", *_G5_MATERIAL_PATHS)
    return diff.returncode == 0


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return value if isinstance(value, dict) else None


def _reusable_g5(repo: Path, evidence: Path) -> dict[str, Any] | None:
    current = _current_head(repo)
    if current is None or not _material_surface_clean(repo):
        return None
    parent = evidence.parent
    if not parent.is_dir():
        return None
    candidates: list[tuple[int, Path]] = []
    for run in parent.iterdir():
        if not run.is_dir() or run.resolve() == evidence.resolve():
            continue
        worker = run / "worker.json"
        if not worker.is_file():
            continue
        try:
            candidates.append((worker.stat().st_mtime_ns, run))
        except OSError:
            continue
    candidates.sort(reverse=True)
    for _mtime, run in candidates:
        payload = _load_json(run / "worker.json")
        if payload is None:
            continue
        stages = payload.get("stages")
        if not isinstance(stages, dict):
            continue
        g5 = stages.get("G5")
        if not isinstance(g5, dict) or str(g5.get("status")) != "PASS":
            continue
        prior = str(g5.get("candidate_git_head", ""))
        if not _material_surface_unchanged(repo, prior, current):
            continue
        reused = dict(g5)
        reused.update(
            {
                "status": "PASS",
                "candidate_git_head": current,
                "reused": True,
                "reused_from_candidate_git_head": prior,
                "reused_from_evidence": str(run.resolve()),
                "reuse_basis": "G5 material surface unchanged",
                "material_surface_paths": _G5_MATERIAL_PATHS,
            }
        )
        print(
            "[REV8 G5] reusing prior PASS; material surface unchanged; "
            f"source={run.name}",
            flush=True,
        )
        return reused
    return None


def _run_preflight(repo: Path, scratch: Path, evidence: Path) -> dict[str, Any]:
    reused = _reusable_g5(repo, evidence)
    if reused is not None:
        return reused
    result = _ORIGINAL_RUN_PREFLIGHT(repo, scratch, evidence)
    return {**result, "reused": False}


engine.run_preflight = _run_preflight
# The frozen engine constructs its worker subprocess from engine.__file__.  Route
# every child through this outer wrapper so evidence reuse and all lower wrapper
# adaptations apply identically in supervisor and worker modes.
engine.__file__ = __file__


if __name__ == "__main__":
    raise SystemExit(engine.main())
