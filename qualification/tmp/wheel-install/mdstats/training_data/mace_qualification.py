"""Installed/source MACE qualification records for MLFF-DATA9A.

The qualification probe is intentionally non-installing.  It records exactly
which supplied source tree and interpreter were tested, compiles the source,
imports the top-level package, and attempts to import ``mace.cli.run_train``.
Missing dependencies are reported rather than hidden behind compatibility
stubs.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import os
import platform
import subprocess
import sys

from ._common import sha256_file_cached
from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest

INSTALLED_MACE_QUALIFICATION_SCHEMA = "mdstats.installed-mace-qualification-record.v1"
MACE_QUALIFICATION_POLICY_SCHEMA = "mdstats.mace-qualification-policy.v1"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _tree_digest(root: Path) -> str:
    entries = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        entries.append((str(path.relative_to(root)), _sha256_file(path)))
    return digest({"files": entries})


@dataclass(frozen=True, slots=True)
class MaceQualificationPolicy:
    required_version: str = "0.3.16"
    required_imports: tuple[str, ...] = (
        "torch",
        "e3nn",
        "numpy",
        "opt_einsum",
        "ase",
        "torch_ema",
        "prettytable",
        "matscipy",
        "h5py",
        "torchmetrics",
        "hostlist",
        "configargparse",
        "git",
        "yaml",
        "tqdm",
        "lmdb",
        "orjson",
        "matplotlib",
        "pandas",
    )
    optional_imports: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.required_version.strip():
            raise TrainingDataInputError("MACE qualification version must be non-empty.")
        object.__setattr__(self, "required_imports", tuple(str(v) for v in self.required_imports))
        object.__setattr__(self, "optional_imports", tuple(str(v) for v in self.optional_imports))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_QUALIFICATION_POLICY_SCHEMA,
            "required_version": self.required_version,
            "required_imports": list(self.required_imports),
            "optional_imports": list(self.optional_imports),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceQualificationPolicy":
        if payload.get("schema") != MACE_QUALIFICATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE qualification policy schema.")
        result = cls(
            required_version=str(payload["required_version"]),
            required_imports=tuple(str(v) for v in payload["required_imports"]),
            optional_imports=tuple(str(v) for v in payload["optional_imports"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE qualification policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class InstalledMaceQualificationRecord:
    policy: MaceQualificationPolicy
    mace_source_root: str
    mace_source_digest: str
    ase_source_root: str | None
    python_executable: str
    python_version: str
    platform: str
    mace_version: str | None
    torch_version: str | None
    source_compile_passed: bool
    top_level_import_passed: bool
    run_train_import_passed: bool
    required_dependency_status: tuple[tuple[str, bool, str | None], ...]
    optional_dependency_status: tuple[tuple[str, bool, str | None], ...]
    run_train_error_type: str | None
    run_train_error_message: str | None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "mace_source_digest", validate_digest(self.mace_source_digest, name="mace_source_digest"))
        required = tuple((str(name), bool(ok), None if version is None else str(version)) for name, ok, version in self.required_dependency_status)
        optional = tuple((str(name), bool(ok), None if version is None else str(version)) for name, ok, version in self.optional_dependency_status)
        object.__setattr__(self, "required_dependency_status", required)
        object.__setattr__(self, "optional_dependency_status", optional)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        if self.run_train_import_passed and not self.top_level_import_passed:
            raise TrainingDataInputError("run_train cannot pass when top-level MACE import failed.")

    @property
    def missing_required_dependencies(self) -> tuple[str, ...]:
        return tuple(name for name, ok, _ in self.required_dependency_status if not ok)

    @property
    def missing_optional_dependencies(self) -> tuple[str, ...]:
        return tuple(name for name, ok, _ in self.optional_dependency_status if not ok)

    @property
    def qualified_for_training_smoke(self) -> bool:
        return (
            self.source_compile_passed
            and self.top_level_import_passed
            and self.run_train_import_passed
            and not self.missing_required_dependencies
            and self.mace_version == self.policy.required_version
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": INSTALLED_MACE_QUALIFICATION_SCHEMA,
            "policy": self.policy.to_dict(),
            "mace_source_root": self.mace_source_root,
            "mace_source_digest": self.mace_source_digest,
            "ase_source_root": self.ase_source_root,
            "python_executable": self.python_executable,
            "python_version": self.python_version,
            "platform": self.platform,
            "mace_version": self.mace_version,
            "torch_version": self.torch_version,
            "source_compile_passed": self.source_compile_passed,
            "top_level_import_passed": self.top_level_import_passed,
            "run_train_import_passed": self.run_train_import_passed,
            "required_dependency_status": [list(v) for v in self.required_dependency_status],
            "optional_dependency_status": [list(v) for v in self.optional_dependency_status],
            "run_train_error_type": self.run_train_error_type,
            "run_train_error_message": self.run_train_error_message,
            "missing_required_dependencies": list(self.missing_required_dependencies),
            "missing_optional_dependencies": list(self.missing_optional_dependencies),
            "qualified_for_training_smoke": self.qualified_for_training_smoke,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "InstalledMaceQualificationRecord":
        if payload.get("schema") != INSTALLED_MACE_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported installed-MACE qualification schema.")
        result = cls(
            policy=MaceQualificationPolicy.from_dict(payload["policy"]),
            mace_source_root=str(payload["mace_source_root"]),
            mace_source_digest=str(payload["mace_source_digest"]),
            ase_source_root=None if payload.get("ase_source_root") is None else str(payload["ase_source_root"]),
            python_executable=str(payload["python_executable"]),
            python_version=str(payload["python_version"]),
            platform=str(payload["platform"]),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
            source_compile_passed=bool(payload["source_compile_passed"]),
            top_level_import_passed=bool(payload["top_level_import_passed"]),
            run_train_import_passed=bool(payload["run_train_import_passed"]),
            required_dependency_status=tuple((str(v[0]), bool(v[1]), None if v[2] is None else str(v[2])) for v in payload["required_dependency_status"]),
            optional_dependency_status=tuple((str(v[0]), bool(v[1]), None if v[2] is None else str(v[2])) for v in payload["optional_dependency_status"]),
            run_train_error_type=None if payload.get("run_train_error_type") is None else str(payload["run_train_error_type"]),
            run_train_error_message=None if payload.get("run_train_error_message") is None else str(payload["run_train_error_message"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Installed-MACE qualification digest mismatch.")
        return result


def qualify_mace_source_environment(
    mace_source_root: str | Path,
    *,
    ase_source_root: str | Path | None = None,
    policy: MaceQualificationPolicy | None = None,
    python_executable: str | Path | None = None,
) -> InstalledMaceQualificationRecord:
    active = MaceQualificationPolicy() if policy is None else policy
    root = Path(mace_source_root).resolve()
    if not (root / "mace" / "__init__.py").is_file():
        raise TrainingDataInputError("MACE source root does not contain mace/__init__.py.")
    ase_root = None if ase_source_root is None else Path(ase_source_root).resolve()
    executable = str(Path(python_executable or sys.executable).resolve())
    pythonpath = [str(root)]
    if ase_root is not None:
        pythonpath.append(str(ase_root))
    existing = os.environ.get("PYTHONPATH")
    if existing:
        pythonpath.append(existing)
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath)
    compile_result = subprocess.run(
        [executable, "-m", "compileall", "-q", str(root / "mace")],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    probe_code = r'''
import importlib, importlib.metadata, json, traceback
required = json.loads(__import__("os").environ["MDSTATS_MACE_REQUIRED"])
optional = json.loads(__import__("os").environ["MDSTATS_MACE_OPTIONAL"])
def status(name):
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", None)
        if version is None:
            try: version = importlib.metadata.version(name.replace("_", "-"))
            except Exception: version = None
        return [name, True, None if version is None else str(version)]
    except Exception:
        return [name, False, None]
result = {"required": [status(v) for v in required], "optional": [status(v) for v in optional]}
try:
    import mace
    result["top_level"] = True
    result["mace_version"] = getattr(mace, "__version__", None)
except Exception as exc:
    result["top_level"] = False
    result["mace_version"] = None
    result["top_error"] = [type(exc).__name__, str(exc)]
try:
    import torch
    result["torch_version"] = getattr(torch, "__version__", None)
except Exception:
    result["torch_version"] = None
try:
    import mace.cli.run_train
    result["run_train"] = True
    result["run_train_error"] = None
except Exception as exc:
    result["run_train"] = False
    result["run_train_error"] = [type(exc).__name__, str(exc)]
print(json.dumps(result, sort_keys=True))
'''
    env["MDSTATS_MACE_REQUIRED"] = json.dumps(active.required_imports)
    env["MDSTATS_MACE_OPTIONAL"] = json.dumps(active.optional_imports)
    result = subprocess.run(
        [executable, "-c", probe_code],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception as exc:
        raise TrainingDataInputError(
            f"MACE qualification subprocess did not return JSON: {result.stderr.strip()}"
        ) from exc
    error = payload.get("run_train_error")
    notes = []
    if compile_result.returncode != 0:
        notes.append(f"compileall_failed:{compile_result.stderr.strip()}")
    if sys.version_info >= (3, 13):
        notes.append("python_3_13_environment_requires_explicit_dependency_compatibility_confirmation")
    return InstalledMaceQualificationRecord(
        policy=active,
        mace_source_root=str(root),
        mace_source_digest=_tree_digest(root),
        ase_source_root=None if ase_root is None else str(ase_root),
        python_executable=executable,
        python_version=platform.python_version(),
        platform=platform.platform(),
        mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
        torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
        source_compile_passed=compile_result.returncode == 0,
        top_level_import_passed=bool(payload.get("top_level")),
        run_train_import_passed=bool(payload.get("run_train")),
        required_dependency_status=tuple((str(v[0]), bool(v[1]), None if v[2] is None else str(v[2])) for v in payload["required"]),
        optional_dependency_status=tuple((str(v[0]), bool(v[1]), None if v[2] is None else str(v[2])) for v in payload["optional"]),
        run_train_error_type=None if error is None else str(error[0]),
        run_train_error_message=None if error is None else str(error[1]),
        notes=tuple(notes),
    )
