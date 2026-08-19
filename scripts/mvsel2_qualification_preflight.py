"""Cheap candidate-bound G5 checks for the REV8 one-command qualifier."""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tarfile
from typing import Any
import zipfile

MAX_LOG_BYTES = 256 * 1024
FOCUSED_TESTS = (
    "tests/test_mlff_repair2.py",
    "tests/test_mlff_mvstate2.py",
    "tests/test_mlff_mvsel2_forward.py",
    "tests/test_mlff_mvmigrate2.py",
    "tests/test_mlff_mvsel2_hardening.py",
    "tests/test_mlff_mvsel2_oracle.py",
    "tests/test_mlff_mvsel2_rev8_qualification.py",
    "tests/test_mlff_target_data2c_repair1.py",
)


class PreflightProductFailure(RuntimeError):
    """Candidate regression/package failure demonstrated by a bounded check."""


def _tail(path: Path, text: str) -> None:
    encoded = text.encode("utf-8", errors="replace")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(encoded[-MAX_LOG_BYTES:])


def _run(
    command: list[str],
    *,
    cwd: Path,
    timeout: float,
    log_path: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    _tail(log_path, result.stdout + result.stderr)
    return result


def _require_clean_tracked_candidate(repo: Path) -> str:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    for command in (
        ["git", "diff", "--quiet"],
        ["git", "diff", "--cached", "--quiet"],
    ):
        result = subprocess.run(command, cwd=repo, check=False)
        if result.returncode != 0:
            raise RuntimeError(
                "tracked/staged working-tree changes make the candidate ambiguous"
            )
    return head


def run_preflight(repo: Path, scratch: Path, evidence: Path) -> dict[str, Any]:
    """Run cheap affected tests and isolated wheel/import qualification."""

    head = _require_clean_tracked_candidate(repo)
    preflight = scratch / "g5-preflight"
    preflight.mkdir(parents=True, exist_ok=True)

    pytest = _run(
        [sys.executable, "-m", "pytest", "-q", *FOCUSED_TESTS],
        cwd=repo,
        timeout=180.0,
        log_path=evidence / "g5_focused.log",
    )
    if pytest.returncode == 1:
        raise PreflightProductFailure(
            "affected focused/adjacent regression tests failed"
        )
    if pytest.returncode != 0:
        raise RuntimeError(
            f"focused regression execution unavailable: pytest exit {pytest.returncode}"
        )

    if importlib.util.find_spec("build") is None:
        raise RuntimeError(
            "Python package 'build' is unavailable for isolated wheel qualification"
        )

    archive = preflight / "candidate.tar"
    archive_result = _run(
        ["git", "archive", "--format=tar", "HEAD", "-o", str(archive)],
        cwd=repo,
        timeout=30.0,
        log_path=evidence / "g5_archive.log",
    )
    if archive_result.returncode != 0:
        raise RuntimeError("cannot materialize clean tracked candidate archive")

    source = preflight / "source"
    source.mkdir()
    # The tar is produced by git from this trusted repository.  Avoid the newer
    # tarfile extraction-filter API so the qualifier remains compatible with
    # the bound Python 3.11 workstation environment.
    with tarfile.open(archive, "r") as handle:
        handle.extractall(source)
    archive.unlink(missing_ok=True)

    wheel_dir = preflight / "wheel"
    wheel_dir.mkdir()
    build = _run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--no-isolation",
            "--outdir",
            str(wheel_dir),
        ],
        cwd=source,
        timeout=90.0,
        log_path=evidence / "g5_wheel_build.log",
    )
    if build.returncode != 0:
        raise PreflightProductFailure("clean candidate wheel build failed")
    wheels = tuple(wheel_dir.glob("mdstats-*.whl"))
    if len(wheels) != 1:
        raise PreflightProductFailure(
            f"expected one mdstats wheel, found {len(wheels)}"
        )
    wheel = wheels[0]

    with zipfile.ZipFile(wheel) as bundle:
        names = tuple(bundle.namelist())
    if any(name.startswith("workplans/") for name in names):
        raise PreflightProductFailure("wheel unexpectedly contains workplans/")

    install = preflight / "install"
    install.mkdir()
    pip_install = _run(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-deps",
            "--target",
            str(install),
            str(wheel),
        ],
        cwd=preflight,
        timeout=90.0,
        log_path=evidence / "g5_wheel_install.log",
    )
    if pip_install.returncode != 0:
        raise PreflightProductFailure("isolated wheel install failed")

    import_cwd = preflight / "import-cwd"
    import_cwd.mkdir()
    import_env = {
        **os.environ,
        "PYTHONPATH": str(install),
        "R8_INSTALL_ROOT": str(install),
    }
    import_check = _run(
        [
            sys.executable,
            "-c",
            (
                "import os,pathlib,mdstats; "
                "p=pathlib.Path(mdstats.__file__).resolve(); "
                "r=pathlib.Path(os.environ['R8_INSTALL_ROOT']).resolve(); "
                "assert p.is_relative_to(r),(p,r); "
                "assert mdstats.__version__=='0.20.242a0',mdstats.__version__; "
                "print(mdstats.__version__,p)"
            ),
        ],
        cwd=import_cwd,
        timeout=30.0,
        log_path=evidence / "g5_wheel_import.log",
        env=import_env,
    )
    if import_check.returncode != 0:
        raise PreflightProductFailure("isolated installed-wheel import failed")

    return {
        "status": "PASS",
        "candidate_git_head": head,
        "focused_test_files": FOCUSED_TESTS,
        "focused_pytest_returncode": pytest.returncode,
        "wheel_name": wheel.name,
        "wheel_entry_count": len(names),
        "workplans_excluded": True,
        "isolated_import_passed": True,
    }
