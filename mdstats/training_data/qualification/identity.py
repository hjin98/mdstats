"""Executable, environment, and specification identity for P7 qualification.

Qualification makes claims about a *product running somewhere*.  Three
identities therefore have to be pinned before any expensive work starts, and
each of them answers a different question:

``ExecutableCandidateIdentity``
    which mdstats code produced the evidence.  Staleness is decided by a digest
    over the importable package source only, so a workplan, review record, or
    documentation commit cannot invalidate executable evidence while any source
    or generated-runtime change does.  The Git commit/tree travel alongside for
    audit ordering; they are recorded, not trusted as currentness.

``EnvironmentFingerprint``
    where the evidence was produced.  Deployment parity, numerical behaviour,
    runtime stability, and resource claims are all environment-dependent, so
    reusing evidence across a materially different environment would be a
    silent lie.

``QualificationSpecIdentity``
    under which frozen policy the evidence was judged.  Every threshold,
    cohort bound, and required-component decision is fixed here *before* any
    product outcome is observed.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
import hashlib
import os
import platform
import subprocess

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .errors import QualificationError

EXECUTABLE_CANDIDATE_SCHEMA = "mdstats.qualification-executable-candidate.v1"
ENVIRONMENT_FINGERPRINT_SCHEMA = "mdstats.qualification-environment-fingerprint.v1"
QUALIFICATION_SPEC_SCHEMA = "mdstats.qualification-spec-identity.v1"

#: The qualification specification revision.  Bumping it is an explicit,
#: reviewable act that stales every descendant qualification component.
QUALIFICATION_SPEC_REVISION = "mdstats.p7-qualification-spec.2026-08.v1"

_SOURCE_SUFFIXES = (".py",)
_SKIPPED_DIRECTORY_NAMES = frozenset({"__pycache__", ".git", ".mypy_cache", ".pytest_cache"})


def _package_root() -> Path:
    import mdstats

    return Path(mdstats.__file__).resolve().parent


def executable_source_tree_digest(root: str | os.PathLike[str] | None = None) -> str:
    """Digest the importable mdstats source surface.

    Only importable source participates.  Documentation, workplans, review
    records, and generated PDFs are deliberately excluded: a plan-only branch
    change must not make executable qualification evidence stale, and a source
    change must.
    """

    package = _package_root() if root is None else Path(root).resolve()
    entries: list[tuple[str, str]] = []
    for path in sorted(package.rglob("*")):
        if not path.is_file() or path.suffix not in _SOURCE_SUFFIXES:
            continue
        if _SKIPPED_DIRECTORY_NAMES.intersection(path.relative_to(package).parts):
            continue
        entries.append(
            (
                path.relative_to(package).as_posix(),
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    if not entries:
        raise QualificationError(
            "No importable mdstats source was found, so no executable "
            "qualification candidate can be identified."
        )
    return digest({"source_tree": [list(item) for item in entries]})


def _git_identity(root: Path) -> tuple[str | None, str | None]:
    """Best-effort Git commit/tree for audit ordering only."""

    def _run(*argv: str) -> str | None:
        try:
            result = subprocess.run(
                argv,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None

    return _run("git", "rev-parse", "HEAD"), _run("git", "rev-parse", "HEAD^{tree}")


@dataclass(frozen=True, slots=True)
class ExecutableCandidateIdentity:
    """The exact mdstats executable that produced or will produce evidence."""

    source_tree_digest: str
    package_version: str
    git_commit: str | None = None
    git_tree: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "source_tree_digest",
            validate_digest(self.source_tree_digest, name="source_tree_digest"),
        )
        version = str(self.package_version).strip()
        if not version:
            raise TrainingDataInputError("Executable candidate requires a package version.")
        object.__setattr__(self, "package_version", version)
        for name in ("git_commit", "git_tree"):
            value = getattr(self, name)
            object.__setattr__(self, name, None if value is None else str(value).strip() or None)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EXECUTABLE_CANDIDATE_SCHEMA,
            "source_tree_digest": self.source_tree_digest,
            "package_version": self.package_version,
            "git_commit": self.git_commit,
            "git_tree": self.git_tree,
        }

    @property
    def content_digest(self) -> str:
        # Currentness is the source surface alone.  Git identities are audit
        # metadata: a documentation-only commit must not stale this identity.
        return digest(
            {
                "schema": EXECUTABLE_CANDIDATE_SCHEMA,
                "source_tree_digest": self.source_tree_digest,
                "package_version": self.package_version,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ExecutableCandidateIdentity":
        if payload.get("schema") != EXECUTABLE_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification executable-candidate schema."
            )
        result = cls(
            source_tree_digest=str(payload["source_tree_digest"]),
            package_version=str(payload["package_version"]),
            git_commit=(None if payload.get("git_commit") is None else str(payload["git_commit"])),
            git_tree=(None if payload.get("git_tree") is None else str(payload["git_tree"])),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification executable-candidate digest mismatch."
            )
        return result


def resolve_executable_candidate_identity() -> ExecutableCandidateIdentity:
    """Freeze the exact executable candidate running this qualification."""

    from ..._version import __version__ as package_version

    root = _package_root()
    commit, tree = _git_identity(root.parent)
    return ExecutableCandidateIdentity(
        source_tree_digest=executable_source_tree_digest(root),
        package_version=str(package_version),
        git_commit=commit,
        git_tree=tree,
    )


def _optional(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass(frozen=True, slots=True)
class EnvironmentFingerprint:
    """Normalized target-machine identity material to qualification claims."""

    operating_system: str
    kernel_release: str
    machine_architecture: str
    python_version: str
    torch_version: str | None
    cuda_runtime_version: str | None
    accelerator_model: str | None
    accelerator_driver_version: str | None
    mace_version: str | None
    ase_version: str | None
    lammps_version: str | None
    lammps_mliap_available: bool
    default_dtype: str
    device: str
    cpu_thread_count: int
    total_memory_bytes: int | None
    accelerator_memory_bytes: int | None
    package_set_digest: str | None = None
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "operating_system",
            "kernel_release",
            "machine_architecture",
            "python_version",
            "default_dtype",
            "device",
        ):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(
                    f"Environment fingerprint field {name!r} must be non-empty."
                )
            object.__setattr__(self, name, value)
        for name in (
            "torch_version",
            "cuda_runtime_version",
            "accelerator_model",
            "accelerator_driver_version",
            "mace_version",
            "ase_version",
            "lammps_version",
            "package_set_digest",
        ):
            object.__setattr__(self, name, _optional(getattr(self, name)))
        threads = int(self.cpu_thread_count)
        if threads <= 0:
            raise TrainingDataInputError("Environment fingerprint requires a positive thread count.")
        object.__setattr__(self, "cpu_thread_count", threads)
        for name in ("total_memory_bytes", "accelerator_memory_bytes"):
            value = getattr(self, name)
            if value is not None:
                value = int(value)
                if value < 0:
                    raise TrainingDataInputError(f"{name} must be nonnegative.")
            object.__setattr__(self, name, value)
        object.__setattr__(self, "lammps_mliap_available", bool(self.lammps_mliap_available))
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": ENVIRONMENT_FINGERPRINT_SCHEMA,
            "operating_system": self.operating_system,
            "kernel_release": self.kernel_release,
            "machine_architecture": self.machine_architecture,
            "python_version": self.python_version,
            "torch_version": self.torch_version,
            "cuda_runtime_version": self.cuda_runtime_version,
            "accelerator_model": self.accelerator_model,
            "accelerator_driver_version": self.accelerator_driver_version,
            "mace_version": self.mace_version,
            "ase_version": self.ase_version,
            "lammps_version": self.lammps_version,
            "lammps_mliap_available": self.lammps_mliap_available,
            "default_dtype": self.default_dtype,
            "device": self.device,
            "cpu_thread_count": self.cpu_thread_count,
            "total_memory_bytes": self.total_memory_bytes,
            "accelerator_memory_bytes": self.accelerator_memory_bytes,
            "package_set_digest": self.package_set_digest,
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        """Identity of the claim-relevant environment.

        Resource *capacity* (thread count, memory) and free-text notes describe
        the machine but do not by themselves change what a deterministic
        numerical claim means, so they are recorded and excluded from the
        material identity; every version, device, driver, and precision fact is
        included, because those do change it.
        """

        payload = self._payload()
        for key in ("cpu_thread_count", "total_memory_bytes", "accelerator_memory_bytes", "notes"):
            payload.pop(key, None)
        return digest(payload)

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EnvironmentFingerprint":
        if payload.get("schema") != ENVIRONMENT_FINGERPRINT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported qualification environment-fingerprint schema."
            )
        result = cls(
            operating_system=str(payload["operating_system"]),
            kernel_release=str(payload["kernel_release"]),
            machine_architecture=str(payload["machine_architecture"]),
            python_version=str(payload["python_version"]),
            torch_version=payload.get("torch_version"),
            cuda_runtime_version=payload.get("cuda_runtime_version"),
            accelerator_model=payload.get("accelerator_model"),
            accelerator_driver_version=payload.get("accelerator_driver_version"),
            mace_version=payload.get("mace_version"),
            ase_version=payload.get("ase_version"),
            lammps_version=payload.get("lammps_version"),
            lammps_mliap_available=bool(payload.get("lammps_mliap_available", False)),
            default_dtype=str(payload["default_dtype"]),
            device=str(payload["device"]),
            cpu_thread_count=int(payload["cpu_thread_count"]),
            total_memory_bytes=payload.get("total_memory_bytes"),
            accelerator_memory_bytes=payload.get("accelerator_memory_bytes"),
            package_set_digest=payload.get("package_set_digest"),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Qualification environment-fingerprint digest mismatch."
            )
        return result


def _module_version(name: str) -> str | None:
    from importlib import metadata

    try:
        return str(metadata.version(name))
    except Exception:
        return None


def _accelerator_facts(device: str) -> tuple[str | None, str | None, str | None, int | None]:
    """(cuda runtime, accelerator model, driver version, device memory bytes)."""

    if not str(device).startswith("cuda"):
        return None, None, None, None
    try:
        import torch
    except Exception:
        return None, None, None, None
    if not torch.cuda.is_available():
        return None, None, None, None
    cuda_version = _optional(getattr(torch.version, "cuda", None))
    try:
        properties = torch.cuda.get_device_properties(0)
        model = _optional(getattr(properties, "name", None))
        memory = int(getattr(properties, "total_memory", 0)) or None
    except Exception:
        model, memory = None, None
    driver = None
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=30.0,
            check=False,
        )
        if result.returncode == 0:
            driver = _optional(result.stdout.splitlines()[0] if result.stdout.splitlines() else None)
    except (OSError, subprocess.SubprocessError):
        driver = None
    return cuda_version, model, driver, memory


def _lammps_facts() -> tuple[str | None, bool]:
    """Interrogate the supported simulation runtime without asserting it exists."""

    try:
        import lammps  # noqa: F401
    except Exception:
        return None, False
    try:
        from .runtime_capability import probe_lammps_runtime

        probe = probe_lammps_runtime()
    except Exception:
        return None, False
    return probe.version, probe.mliap_available


@dataclass(frozen=True, slots=True)
class QualificationSpecIdentity:
    """The frozen qualification policy, fixed before any product outcome."""

    revision: str
    required_components: tuple[str, ...]
    optional_components: tuple[str, ...]
    policy_payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        revision = str(self.revision).strip()
        if not revision:
            raise TrainingDataInputError("Qualification spec requires a revision.")
        object.__setattr__(self, "revision", revision)
        required = tuple(sorted({str(v) for v in self.required_components}))
        optional = tuple(sorted({str(v) for v in self.optional_components}))
        if not required:
            raise TrainingDataInputError(
                "A qualification specification with no required component would "
                "make every product trivially release-qualified."
            )
        overlap = set(required) & set(optional)
        if overlap:
            raise TrainingDataInputError(
                f"Qualification components cannot be both required and optional: {sorted(overlap)}."
            )
        object.__setattr__(self, "required_components", required)
        object.__setattr__(self, "optional_components", optional)
        from .._common import json_value

        object.__setattr__(self, "policy_payload", json_value(dict(self.policy_payload)))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": QUALIFICATION_SPEC_SCHEMA,
            "revision": self.revision,
            "required_components": list(self.required_components),
            "optional_components": list(self.optional_components),
            "policy_payload": dict(self.policy_payload),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def component_policy(self, component: str) -> Mapping[str, Any]:
        value = self.policy_payload.get(str(component), {})
        if not isinstance(value, Mapping):
            raise TrainingDataInputError(
                f"Qualification policy for component {component!r} must be a table."
            )
        return value

    def requires(self, component: str) -> bool:
        return str(component) in self.required_components

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QualificationSpecIdentity":
        if payload.get("schema") != QUALIFICATION_SPEC_SCHEMA:
            raise TrainingDataSerializationError("Unsupported qualification-spec schema.")
        result = cls(
            revision=str(payload["revision"]),
            required_components=tuple(str(v) for v in payload["required_components"]),
            optional_components=tuple(str(v) for v in payload.get("optional_components", ())),
            policy_payload=dict(payload.get("policy_payload", {})),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Qualification-spec digest mismatch.")
        return result


def _total_physical_memory_bytes() -> int | None:
    """Installed memory, not free memory.

    An environment fingerprint has to be reproducible for the same machine.
    Momentarily available memory is a condition, not an identity, and recording
    it would make an otherwise immutable evidence record differ byte-for-byte
    between two runs on the same host.
    """

    try:
        return int(os.sysconf("SC_PAGE_SIZE")) * int(os.sysconf("SC_PHYS_PAGES"))
    except (ValueError, OSError, AttributeError):
        return None


def capture_environment_fingerprint(
    *, default_dtype: str, device: str, notes: tuple[str, ...] = ()
) -> EnvironmentFingerprint:
    """Observe the current execution environment through real probes."""

    from ..resources import available_cpu_threads

    uname = platform.uname()
    cuda_version, accelerator_model, driver, accelerator_memory = _accelerator_facts(device)
    lammps_version, mliap_available = _lammps_facts()
    package_versions = {
        name: _module_version(name)
        for name in ("torch", "mace-torch", "ase", "numpy", "scipy", "mdstats")
    }
    return EnvironmentFingerprint(
        operating_system=f"{uname.system} {uname.version}".strip(),
        kernel_release=str(uname.release),
        machine_architecture=str(uname.machine),
        python_version=platform.python_version(),
        torch_version=package_versions.get("torch"),
        cuda_runtime_version=cuda_version,
        accelerator_model=accelerator_model,
        accelerator_driver_version=driver,
        mace_version=package_versions.get("mace-torch"),
        ase_version=package_versions.get("ase"),
        lammps_version=lammps_version,
        lammps_mliap_available=mliap_available,
        default_dtype=str(default_dtype),
        device=str(device),
        cpu_thread_count=int(available_cpu_threads()),
        total_memory_bytes=_total_physical_memory_bytes(),
        accelerator_memory_bytes=accelerator_memory,
        package_set_digest=digest({"packages": package_versions}),
        notes=notes,
    )


__all__ = [
    "ENVIRONMENT_FINGERPRINT_SCHEMA",
    "EXECUTABLE_CANDIDATE_SCHEMA",
    "QUALIFICATION_SPEC_REVISION",
    "QUALIFICATION_SPEC_SCHEMA",
    "EnvironmentFingerprint",
    "ExecutableCandidateIdentity",
    "QualificationSpecIdentity",
    "capture_environment_fingerprint",
    "executable_source_tree_digest",
    "resolve_executable_candidate_identity",
]
