"""Offline-capable MACE runtime installation and qualification for DATA9A.

This module never substitutes compatibility shims for third-party packages.
It creates or inspects an isolated Python environment, installs only explicit
local artifacts when requested, records the declared MACE dependency contract,
and fails closed before executing MACE CLI smoke commands when required
packages are absent.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
import configparser
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

MACE_DEPENDENCY_REQUIREMENT_SCHEMA = "mdstats.mace-dependency-requirement.v1"
MACE_DEPENDENCY_MANIFEST_SCHEMA = "mdstats.mace-dependency-manifest.v1"
MACE_RUNTIME_INSTALL_POLICY_SCHEMA = "mdstats.mace-runtime-install-policy.v1"
MACE_RUNTIME_INSTALL_RECORD_SCHEMA = "mdstats.mace-runtime-install-record.v1"
MACE_RUNTIME_ENVIRONMENT_SCHEMA = "mdstats.mace-runtime-environment-record.v1"
MACE_CLI_SMOKE_POLICY_SCHEMA = "mdstats.mace-cli-smoke-policy.v1"
MACE_CLI_COMMAND_RESULT_SCHEMA = "mdstats.mace-cli-command-result.v1"
MACE_CLI_SMOKE_RECORD_SCHEMA = "mdstats.mace-cli-smoke-record.v1"

_IMPORT_NAME_OVERRIDES = {
    "torch-ema": "torch_ema",
    "python-hostlist": "hostlist",
    "gitpython": "git",
    "pyyaml": "yaml",
    "opt-einsum": "opt_einsum",
}


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _normalise_distribution_name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value.strip()).lower()


def _infer_import_name(distribution_name: str) -> str:
    key = _normalise_distribution_name(distribution_name)
    return _IMPORT_NAME_OVERRIDES.get(key, key.replace("-", "_"))


def _split_requirement(value: str) -> tuple[str, str]:
    raw = value.strip()
    if not raw:
        raise TrainingDataInputError("Empty MACE dependency requirement.")
    # MACE 0.3.16 uses simple PEP 508 requirements. Preserve the full suffix
    # after the normalized distribution name for provenance and diagnostics.
    match = re.match(r"^([A-Za-z0-9_.-]+)(.*)$", raw)
    if match is None:
        raise TrainingDataInputError(f"Cannot parse MACE requirement: {raw!r}")
    return match.group(1), match.group(2).strip()


@dataclass(frozen=True, slots=True)
class MaceDependencyRequirement:
    distribution_name: str
    import_name: str
    specifier: str = ""
    required: bool = True

    def __post_init__(self) -> None:
        distribution = _normalise_distribution_name(self.distribution_name)
        if not distribution:
            raise TrainingDataInputError("Dependency distribution name must be non-empty.")
        import_name = self.import_name.strip()
        if not import_name:
            raise TrainingDataInputError("Dependency import name must be non-empty.")
        object.__setattr__(self, "distribution_name", distribution)
        object.__setattr__(self, "import_name", import_name)
        object.__setattr__(self, "specifier", self.specifier.strip())

    @property
    def requirement_text(self) -> str:
        return f"{self.distribution_name}{self.specifier}"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DEPENDENCY_REQUIREMENT_SCHEMA,
            "distribution_name": self.distribution_name,
            "import_name": self.import_name,
            "specifier": self.specifier,
            "required": self.required,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDependencyRequirement":
        if payload.get("schema") != MACE_DEPENDENCY_REQUIREMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE dependency requirement schema.")
        result = cls(
            distribution_name=str(payload["distribution_name"]),
            import_name=str(payload["import_name"]),
            specifier=str(payload.get("specifier", "")),
            required=bool(payload.get("required", True)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE dependency requirement digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceDependencyManifest:
    mace_version: str
    source_setup_cfg_sha256: str
    requirements: tuple[MaceDependencyRequirement, ...]

    def __post_init__(self) -> None:
        if not self.mace_version.strip():
            raise TrainingDataInputError("MACE dependency manifest version must be non-empty.")
        object.__setattr__(
            self,
            "source_setup_cfg_sha256",
            validate_digest(self.source_setup_cfg_sha256, name="source_setup_cfg_sha256"),
        )
        requirements = tuple(self.requirements)
        names = [item.distribution_name for item in requirements]
        if len(names) != len(set(names)):
            raise TrainingDataInputError("MACE dependency manifest contains duplicate distributions.")
        object.__setattr__(self, "requirements", requirements)

    @property
    def required_imports(self) -> tuple[str, ...]:
        return tuple(item.import_name for item in self.requirements if item.required)

    @property
    def requirement_texts(self) -> tuple[str, ...]:
        return tuple(item.requirement_text for item in self.requirements)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_DEPENDENCY_MANIFEST_SCHEMA,
            "mace_version": self.mace_version,
            "source_setup_cfg_sha256": self.source_setup_cfg_sha256,
            "requirements": [item.to_dict() for item in self.requirements],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceDependencyManifest":
        if payload.get("schema") != MACE_DEPENDENCY_MANIFEST_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE dependency manifest schema.")
        result = cls(
            mace_version=str(payload["mace_version"]),
            source_setup_cfg_sha256=str(payload["source_setup_cfg_sha256"]),
            requirements=tuple(
                MaceDependencyRequirement.from_dict(item) for item in payload["requirements"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE dependency manifest digest mismatch.")
        return result


def read_mace_dependency_manifest(mace_source_root: str | Path) -> MaceDependencyManifest:
    root = Path(mace_source_root).resolve()
    setup_cfg = root / "setup.cfg"
    init_py = root / "mace" / "__init__.py"
    if not setup_cfg.is_file() or not init_py.is_file():
        raise TrainingDataInputError("MACE source root must contain setup.cfg and mace/__init__.py.")
    parser = configparser.ConfigParser()
    parser.read(setup_cfg, encoding="utf-8")
    if not parser.has_option("options", "install_requires"):
        raise TrainingDataInputError("MACE setup.cfg has no install_requires contract.")
    raw_requirements = [
        line.strip()
        for line in parser.get("options", "install_requires").splitlines()
        if line.strip()
    ]
    requirements = []
    for raw in raw_requirements:
        distribution, specifier = _split_requirement(raw)
        requirements.append(
            MaceDependencyRequirement(
                distribution_name=distribution,
                import_name=_infer_import_name(distribution),
                specifier=specifier,
                required=True,
            )
        )
    version_text = init_py.read_text()
    version_match = re.search(r'__version__\s*=\s*["\']([^"\']+)', version_text)
    if version_match is None and (root / "mace" / "__version__.py").is_file():
        version_match = re.search(
            r'__version__\s*=\s*["\']([^"\']+)',
            (root / "mace" / "__version__.py").read_text(),
        )
    if version_match is None:
        raise TrainingDataInputError("Cannot resolve MACE version from source tree.")
    return MaceDependencyManifest(
        mace_version=version_match.group(1),
        source_setup_cfg_sha256=_sha256_file(setup_cfg),
        requirements=tuple(requirements),
    )


@dataclass(frozen=True, slots=True)
class MaceRuntimeInstallPolicy:
    system_site_packages: bool = True
    inherit_base_python_paths: bool = True
    offline: bool = True
    force_recreate: bool = False
    timeout_seconds: float = 600.0

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise TrainingDataInputError("MACE runtime installation timeout must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_RUNTIME_INSTALL_POLICY_SCHEMA,
            "system_site_packages": self.system_site_packages,
            "inherit_base_python_paths": self.inherit_base_python_paths,
            "offline": self.offline,
            "force_recreate": self.force_recreate,
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeInstallPolicy":
        if payload.get("schema") != MACE_RUNTIME_INSTALL_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE runtime install policy schema.")
        result = cls(
            system_site_packages=bool(payload.get("system_site_packages", True)),
            inherit_base_python_paths=bool(payload.get("inherit_base_python_paths", True)),
            offline=bool(payload.get("offline", True)),
            force_recreate=bool(payload.get("force_recreate", False)),
            timeout_seconds=float(payload.get("timeout_seconds", 600.0)),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE runtime install policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceInstallCommandRecord:
    argv: tuple[str, ...]
    returncode: int
    stdout_tail: str
    stderr_tail: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", tuple(str(v) for v in self.argv))

    @property
    def passed(self) -> bool:
        return self.returncode == 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "argv": list(self.argv),
            "returncode": self.returncode,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "passed": self.passed,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceInstallCommandRecord":
        return cls(
            argv=tuple(str(v) for v in payload["argv"]),
            returncode=int(payload["returncode"]),
            stdout_tail=str(payload.get("stdout_tail", "")),
            stderr_tail=str(payload.get("stderr_tail", "")),
        )


@dataclass(frozen=True, slots=True)
class MaceRuntimeEnvironmentRecord:
    dependency_manifest: MaceDependencyManifest
    install_policy: MaceRuntimeInstallPolicy
    environment_root: str
    base_python_executable: str
    python_executable: str
    python_version: str
    inherited_python_paths: tuple[str, ...]
    supplied_artifacts: tuple[tuple[str, str], ...]
    install_commands: tuple[MaceInstallCommandRecord, ...]
    dependency_status: tuple[tuple[str, str, bool, str | None], ...]
    mace_version: str | None
    ase_version: str | None
    torch_version: str | None
    run_train_import_passed: bool
    eval_configs_import_passed: bool
    blocking_error_type: str | None
    blocking_error_message: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "base_python_executable", str(self.base_python_executable))
        object.__setattr__(self, "inherited_python_paths", tuple(str(v) for v in self.inherited_python_paths))
        object.__setattr__(
            self,
            "supplied_artifacts",
            tuple((str(name), validate_digest(value, name=f"artifact:{name}")) for name, value in self.supplied_artifacts),
        )
        object.__setattr__(self, "install_commands", tuple(self.install_commands))
        object.__setattr__(
            self,
            "dependency_status",
            tuple((str(d), str(i), bool(ok), None if v is None else str(v)) for d, i, ok, v in self.dependency_status),
        )

    @property
    def missing_required_distributions(self) -> tuple[str, ...]:
        required = {item.distribution_name for item in self.dependency_manifest.requirements if item.required}
        return tuple(d for d, _, ok, _ in self.dependency_status if d in required and not ok)

    @property
    def missing_requirement_texts(self) -> tuple[str, ...]:
        missing = set(self.missing_required_distributions)
        return tuple(
            item.requirement_text
            for item in self.dependency_manifest.requirements
            if item.distribution_name in missing
        )

    @property
    def version_mismatches(self) -> tuple[tuple[str, str, str], ...]:
        observed = {
            distribution: version
            for distribution, _, imported, version in self.dependency_status
            if imported and version is not None
        }
        mismatches: list[tuple[str, str, str]] = []
        for requirement in self.dependency_manifest.requirements:
            if not requirement.specifier:
                continue
            version = observed.get(requirement.distribution_name)
            if version is None:
                continue
            try:
                specifier = SpecifierSet(requirement.specifier)
                parsed_version = Version(version)
            except (InvalidSpecifier, InvalidVersion):
                mismatches.append(
                    (requirement.distribution_name, requirement.specifier, version)
                )
                continue
            if parsed_version not in specifier:
                mismatches.append(
                    (requirement.distribution_name, requirement.specifier, version)
                )
        return tuple(mismatches)

    @property
    def installation_passed(self) -> bool:
        return all(item.passed for item in self.install_commands)

    @property
    def qualified_for_cli_smoke(self) -> bool:
        return (
            self.installation_passed
            and not self.missing_required_distributions
            and not self.version_mismatches
            and self.mace_version == self.dependency_manifest.mace_version
            and self.run_train_import_passed
            and self.eval_configs_import_passed
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_RUNTIME_ENVIRONMENT_SCHEMA,
            "dependency_manifest": self.dependency_manifest.to_dict(),
            "install_policy": self.install_policy.to_dict(),
            "environment_root": self.environment_root,
            "base_python_executable": self.base_python_executable,
            "python_executable": self.python_executable,
            "python_version": self.python_version,
            "inherited_python_paths": list(self.inherited_python_paths),
            "supplied_artifacts": [list(v) for v in self.supplied_artifacts],
            "install_commands": [item.to_dict() for item in self.install_commands],
            "dependency_status": [list(v) for v in self.dependency_status],
            "mace_version": self.mace_version,
            "ase_version": self.ase_version,
            "torch_version": self.torch_version,
            "run_train_import_passed": self.run_train_import_passed,
            "eval_configs_import_passed": self.eval_configs_import_passed,
            "blocking_error_type": self.blocking_error_type,
            "blocking_error_message": self.blocking_error_message,
            "missing_required_distributions": list(self.missing_required_distributions),
            "missing_requirement_texts": list(self.missing_requirement_texts),
            "version_mismatches": [list(v) for v in self.version_mismatches],
            "installation_passed": self.installation_passed,
            "qualified_for_cli_smoke": self.qualified_for_cli_smoke,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeEnvironmentRecord":
        if payload.get("schema") != MACE_RUNTIME_ENVIRONMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE runtime environment schema.")
        result = cls(
            dependency_manifest=MaceDependencyManifest.from_dict(payload["dependency_manifest"]),
            install_policy=MaceRuntimeInstallPolicy.from_dict(payload["install_policy"]),
            environment_root=str(payload["environment_root"]),
            base_python_executable=str(payload.get("base_python_executable", payload["python_executable"])),
            python_executable=str(payload["python_executable"]),
            python_version=str(payload["python_version"]),
            inherited_python_paths=tuple(str(v) for v in payload.get("inherited_python_paths", ())),
            supplied_artifacts=tuple((str(v[0]), str(v[1])) for v in payload["supplied_artifacts"]),
            install_commands=tuple(MaceInstallCommandRecord.from_dict(v) for v in payload["install_commands"]),
            dependency_status=tuple((str(v[0]), str(v[1]), bool(v[2]), None if v[3] is None else str(v[3])) for v in payload["dependency_status"]),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            ase_version=None if payload.get("ase_version") is None else str(payload["ase_version"]),
            torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
            run_train_import_passed=bool(payload["run_train_import_passed"]),
            eval_configs_import_passed=bool(payload["eval_configs_import_passed"]),
            blocking_error_type=None if payload.get("blocking_error_type") is None else str(payload["blocking_error_type"]),
            blocking_error_message=None if payload.get("blocking_error_message") is None else str(payload["blocking_error_message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE runtime environment digest mismatch.")
        return result


def _command_record(result: subprocess.CompletedProcess[str], argv: Sequence[str]) -> MaceInstallCommandRecord:
    return MaceInstallCommandRecord(
        argv=tuple(str(v) for v in argv),
        returncode=int(result.returncode),
        stdout_tail=result.stdout[-4000:],
        stderr_tail=result.stderr[-4000:],
    )


def _run(argv: Sequence[str], *, timeout: float, env: Mapping[str, str] | None = None) -> MaceInstallCommandRecord:
    """Run an installation command without descendant-held PIPE deadlocks."""

    with tempfile.NamedTemporaryFile(prefix="mdstats-mace-install-stdout-", delete=False) as out_handle:
        stdout_path = Path(out_handle.name)
    with tempfile.NamedTemporaryFile(prefix="mdstats-mace-install-stderr-", delete=False) as err_handle:
        stderr_path = Path(err_handle.name)
    returncode = -9
    timed_out = False
    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                list(argv),
                stdout=stdout_handle,
                stderr=stderr_handle,
                env=None if env is None else dict(env),
                start_new_session=(os.name == "posix"),
            )
            deadline = time.monotonic() + timeout
            while True:
                observed = process.poll()
                if observed is not None:
                    returncode = int(observed)
                    break
                if time.monotonic() >= deadline:
                    timed_out = True
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:  # pragma: no cover
                        process.kill()
                    break
                time.sleep(0.1)
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        if timed_out:
            stderr += f"\n[mdstats] command timed out after {timeout} seconds.\n"
        return MaceInstallCommandRecord(
            argv=tuple(str(v) for v in argv),
            returncode=returncode,
            stdout_tail=stdout[-4000:],
            stderr_tail=stderr[-4000:],
        )
    finally:
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)


def _python_in_venv(root: Path) -> Path:
    if os.name == "nt":
        return root / "Scripts" / "python.exe"
    return root / "bin" / "python"


def _artifact_pairs(paths: Sequence[str | Path]) -> tuple[tuple[str, str], ...]:
    result = []
    for raw in paths:
        path = Path(raw).resolve()
        if not path.is_file():
            raise TrainingDataInputError(f"MACE runtime artifact does not exist: {path}")
        result.append((path.name, _sha256_file(path)))
    return tuple(result)




def discover_mace_dependency_artifacts(wheelhouse: str | Path) -> tuple[Path, ...]:
    """Return deterministic local dependency artifacts from an offline wheelhouse."""

    root = Path(wheelhouse).resolve()
    if not root.is_dir():
        raise TrainingDataInputError(f"MACE wheelhouse is not a directory: {root}")
    suffixes = (".whl", ".tar.gz", ".zip")
    artifacts = tuple(
        path
        for path in sorted(root.iterdir(), key=lambda item: item.name.lower())
        if path.is_file() and any(path.name.lower().endswith(suffix) for suffix in suffixes)
    )
    return artifacts


def create_mace_runtime_environment(
    environment_root: str | Path,
    *,
    mace_source_root: str | Path,
    mace_archive: str | Path,
    ase_archive: str | Path,
    dependency_artifacts: Sequence[str | Path] = (),
    build_tool_artifacts: Sequence[str | Path] = (),
    policy: MaceRuntimeInstallPolicy | None = None,
    base_python_executable: str | Path | None = None,
) -> MaceRuntimeEnvironmentRecord:
    """Create and qualify a local MACE environment from explicit artifacts.

    Network access is disabled by default. Missing dependencies remain visible
    in the returned record and prevent CLI smoke execution.
    """

    active = MaceRuntimeInstallPolicy() if policy is None else policy
    root = Path(environment_root).resolve()
    if root.exists() and active.force_recreate:
        shutil.rmtree(root)
    if root.exists() and not _python_in_venv(root).is_file():
        raise TrainingDataInputError(f"Existing path is not a Python environment: {root}")
    manifest = read_mace_dependency_manifest(mace_source_root)
    all_artifacts = tuple(build_tool_artifacts) + (ase_archive, mace_archive) + tuple(dependency_artifacts)
    artifact_digests = _artifact_pairs(all_artifacts)
    commands: list[MaceInstallCommandRecord] = []
    base_python = str(Path(base_python_executable or sys.executable).resolve())
    if not root.exists():
        argv = [base_python, "-m", "venv"]
        if active.system_site_packages:
            argv.append("--system-site-packages")
        argv.append(str(root))
        command = _run(argv, timeout=active.timeout_seconds)
        commands.append(command)
        if not command.passed:
            return _qualify_runtime_after_install(
                root,
                manifest,
                active,
                artifact_digests,
                tuple(commands),
                base_python_executable=base_python,
                inherited_python_paths=(),
            )
    python = _python_in_venv(root)
    inherited_python_paths: tuple[str, ...] = ()
    if active.inherit_base_python_paths:
        base_probe = subprocess.run(
            [base_python, "-c", "import json,sys; print(json.dumps(sys.path))"],
            capture_output=True, text=True, check=False, timeout=active.timeout_seconds,
        )
        try:
            base_paths = [
                value for value in json.loads(base_probe.stdout.strip().splitlines()[-1])
                if value and ("site-packages" in value or value.startswith("/opt/pyvenv"))
            ]
        except Exception:
            base_paths = []
        inherited_python_paths = tuple(dict.fromkeys(str(value) for value in base_paths))
        if base_paths:
            site_probe = subprocess.run(
                [str(python), "-c", "import site; print(site.getsitepackages()[0])"],
                capture_output=True, text=True, check=False, timeout=active.timeout_seconds,
            )
            if site_probe.returncode == 0:
                pth = Path(site_probe.stdout.strip().splitlines()[-1]) / "mdstats_inherited_base_paths.pth"
                pth.write_text("\n".join(dict.fromkeys(base_paths)) + "\n")
    pip_prefix = [str(python), "-m", "pip", "install"]
    if build_tool_artifacts:
        argv = pip_prefix + ["--no-index"] + [str(Path(v).resolve()) for v in build_tool_artifacts]
        commands.append(_run(argv, timeout=active.timeout_seconds))
    # Install explicit dependency artifacts first so source-package metadata and
    # import probes see the intended environment. Pip receives --no-deps because
    # the complete dependency lineage is supplied and audited separately.
    if dependency_artifacts:
        argv = pip_prefix + ["--no-deps", "--no-build-isolation"]
        if active.offline:
            argv.append("--no-index")
        argv += [str(Path(v).resolve()) for v in dependency_artifacts]
        commands.append(_run(argv, timeout=active.timeout_seconds))
    argv = pip_prefix + ["--no-deps", "--no-build-isolation"]
    if active.offline:
        argv.append("--no-index")
    argv += [str(Path(ase_archive).resolve()), str(Path(mace_archive).resolve())]
    commands.append(_run(argv, timeout=active.timeout_seconds))
    return _qualify_runtime_after_install(
        root,
        manifest,
        active,
        artifact_digests,
        tuple(commands),
        base_python_executable=base_python,
        inherited_python_paths=inherited_python_paths,
    )


def _qualify_runtime_after_install(
    root: Path,
    manifest: MaceDependencyManifest,
    policy: MaceRuntimeInstallPolicy,
    artifact_digests: tuple[tuple[str, str], ...],
    commands: tuple[MaceInstallCommandRecord, ...],
    *,
    base_python_executable: str,
    inherited_python_paths: tuple[str, ...],
) -> MaceRuntimeEnvironmentRecord:
    python = _python_in_venv(root)
    if not python.is_file():
        return MaceRuntimeEnvironmentRecord(
            dependency_manifest=manifest,
            install_policy=policy,
            environment_root=str(root),
            base_python_executable=base_python_executable,
            python_executable=str(python),
            python_version="unavailable",
            inherited_python_paths=inherited_python_paths,
            supplied_artifacts=artifact_digests,
            install_commands=commands,
            dependency_status=tuple(
                (item.distribution_name, item.import_name, False, None) for item in manifest.requirements
            ),
            mace_version=None,
            ase_version=None,
            torch_version=None,
            run_train_import_passed=False,
            eval_configs_import_passed=False,
            blocking_error_type="EnvironmentCreationError",
            blocking_error_message="Python executable was not created.",
        )
    probe = r'''
import importlib, importlib.metadata, json, os, platform, sys
requirements = json.loads(os.environ["MDSTATS_MACE_DEPENDENCIES"])
def probe_import(distribution, import_name):
    try:
        module = importlib.import_module(import_name)
        version = getattr(module, "__version__", None)
        if version is None:
            try: version = importlib.metadata.version(distribution)
            except Exception: version = None
        return [distribution, import_name, True, None if version is None else str(version)]
    except Exception:
        return [distribution, import_name, False, None]
result = {"python_version": platform.python_version()}
result["dependencies"] = [probe_import(v[0], v[1]) for v in requirements]
for module_name, distribution_name, field in [("mace", "mace-torch", "mace_version"), ("ase", "ase", "ase_version"), ("torch", "torch", "torch_version")]:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", None)
        if version is None:
            version = importlib.metadata.version(distribution_name)
        result[field] = str(version)
    except Exception:
        result[field] = None
for module_name, field in [("mace.cli.run_train", "run_train"), ("mace.cli.eval_configs", "eval_configs")]:
    try:
        importlib.import_module(module_name)
        result[field] = True
        result[field + "_error"] = None
    except Exception as exc:
        result[field] = False
        result[field + "_error"] = [type(exc).__name__, str(exc)]
print(json.dumps(result, sort_keys=True))
sys.stdout.flush()
os._exit(0)
'''
    env = dict(os.environ)
    env["MDSTATS_MACE_DEPENDENCIES"] = json.dumps(
        [[item.distribution_name, item.import_name] for item in manifest.requirements]
    )
    result = subprocess.run(
        [str(python), "-c", probe],
        capture_output=True,
        text=True,
        check=False,
        timeout=policy.timeout_seconds,
        env=env,
    )
    try:
        payload = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        payload = {
            "python_version": "unknown",
            "dependencies": [
                [item.distribution_name, item.import_name, False, None] for item in manifest.requirements
            ],
            "mace_version": None,
            "ase_version": None,
            "torch_version": None,
            "run_train": False,
            "eval_configs": False,
            "run_train_error": ["ProbeError", result.stderr[-2000:]],
            "eval_configs_error": ["ProbeError", result.stderr[-2000:]],
        }
    blocking = payload.get("run_train_error") or payload.get("eval_configs_error")
    return MaceRuntimeEnvironmentRecord(
        dependency_manifest=manifest,
        install_policy=policy,
        environment_root=str(root),
        base_python_executable=base_python_executable,
        python_executable=str(python),
        python_version=str(payload.get("python_version", "unknown")),
        inherited_python_paths=inherited_python_paths,
        supplied_artifacts=artifact_digests,
        install_commands=commands,
        dependency_status=tuple(
            (str(v[0]), str(v[1]), bool(v[2]), None if v[3] is None else str(v[3]))
            for v in payload["dependencies"]
        ),
        mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
        ase_version=None if payload.get("ase_version") is None else str(payload["ase_version"]),
        torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
        run_train_import_passed=bool(payload.get("run_train")),
        eval_configs_import_passed=bool(payload.get("eval_configs")),
        blocking_error_type=None if blocking is None else str(blocking[0]),
        blocking_error_message=None if blocking is None else str(blocking[1]),
    )


@dataclass(frozen=True, slots=True)
class MaceCliSmokePolicy:
    commands: tuple[tuple[str, ...], ...] = (
        ("mace_run_train", "--help"),
        ("mace_eval_configs", "--help"),
    )
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        commands = tuple(tuple(str(v) for v in command) for command in self.commands)
        if not commands or any(not command for command in commands):
            raise TrainingDataInputError("MACE CLI smoke policy requires non-empty commands.")
        if self.timeout_seconds <= 0:
            raise TrainingDataInputError("MACE CLI smoke timeout must be positive.")
        object.__setattr__(self, "commands", commands)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_CLI_SMOKE_POLICY_SCHEMA,
            "commands": [list(v) for v in self.commands],
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCliSmokePolicy":
        if payload.get("schema") != MACE_CLI_SMOKE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE CLI smoke policy schema.")
        result = cls(
            commands=tuple(tuple(str(v) for v in command) for command in payload["commands"]),
            timeout_seconds=float(payload.get("timeout_seconds", 120.0)),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE CLI smoke policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceCliCommandResult:
    command: tuple[str, ...]
    resolved_executable: str | None
    returncode: int | None
    stdout_sha256: str | None
    stderr_sha256: str | None
    stdout_tail: str
    stderr_tail: str
    skipped_reason: str | None = None

    @property
    def passed(self) -> bool:
        return self.skipped_reason is None and self.returncode == 0

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_CLI_COMMAND_RESULT_SCHEMA,
            "command": list(self.command),
            "resolved_executable": self.resolved_executable,
            "returncode": self.returncode,
            "stdout_sha256": self.stdout_sha256,
            "stderr_sha256": self.stderr_sha256,
            "stdout_tail": self.stdout_tail,
            "stderr_tail": self.stderr_tail,
            "skipped_reason": self.skipped_reason,
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCliCommandResult":
        if payload.get("schema") != MACE_CLI_COMMAND_RESULT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE CLI command result schema.")
        result = cls(
            command=tuple(str(v) for v in payload["command"]),
            resolved_executable=None if payload.get("resolved_executable") is None else str(payload["resolved_executable"]),
            returncode=None if payload.get("returncode") is None else int(payload["returncode"]),
            stdout_sha256=None if payload.get("stdout_sha256") is None else str(payload["stdout_sha256"]),
            stderr_sha256=None if payload.get("stderr_sha256") is None else str(payload["stderr_sha256"]),
            stdout_tail=str(payload.get("stdout_tail", "")),
            stderr_tail=str(payload.get("stderr_tail", "")),
            skipped_reason=None if payload.get("skipped_reason") is None else str(payload["skipped_reason"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE CLI command result digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceCliSmokeRecord:
    environment_digest: str
    policy: MaceCliSmokePolicy
    command_results: tuple[MaceCliCommandResult, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "environment_digest", validate_digest(self.environment_digest, name="environment_digest"))
        object.__setattr__(self, "command_results", tuple(self.command_results))

    @property
    def passed(self) -> bool:
        return bool(self.command_results) and all(item.passed for item in self.command_results)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_CLI_SMOKE_RECORD_SCHEMA,
            "environment_digest": self.environment_digest,
            "policy": self.policy.to_dict(),
            "command_results": [item.to_dict() for item in self.command_results],
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceCliSmokeRecord":
        if payload.get("schema") != MACE_CLI_SMOKE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE CLI smoke record schema.")
        result = cls(
            environment_digest=str(payload["environment_digest"]),
            policy=MaceCliSmokePolicy.from_dict(payload["policy"]),
            command_results=tuple(MaceCliCommandResult.from_dict(v) for v in payload["command_results"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE CLI smoke record digest mismatch.")
        return result


def _run_cli_smoke_command(
    command: tuple[str, ...],
    *,
    executable: str,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> MaceCliCommandResult:
    """Run a CLI probe without relying on interpreter-shutdown EOF."""

    with tempfile.NamedTemporaryFile(prefix="mdstats-mace-cli-stdout-", delete=False) as out_handle:
        stdout_path = Path(out_handle.name)
    with tempfile.NamedTemporaryFile(prefix="mdstats-mace-cli-stderr-", delete=False) as err_handle:
        stderr_path = Path(err_handle.name)
    returncode: int | None = None
    timed_out = False
    completed_by_help_sentinel = False
    try:
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                [executable, *command[1:]],
                stdout=stdout_handle,
                stderr=stderr_handle,
                env=dict(env),
                start_new_session=(os.name == "posix"),
            )
            deadline = time.monotonic() + timeout_seconds
            previous_sizes: tuple[int, int] | None = None
            stable_polls = 0
            is_help = "--help" in command or "-h" in command
            while True:
                observed = process.poll()
                if observed is not None:
                    returncode = int(observed)
                    break
                if is_help:
                    sizes = (stdout_path.stat().st_size, stderr_path.stat().st_size)
                    if sum(sizes) > 0:
                        stable_polls = stable_polls + 1 if sizes == previous_sizes else 0
                        previous_sizes = sizes
                        if stable_polls >= 10:
                            completed_by_help_sentinel = True
                            if os.name == "posix":
                                try:
                                    os.killpg(process.pid, signal.SIGTERM)
                                except ProcessLookupError:
                                    pass
                            else:  # pragma: no cover
                                process.terminate()
                            for _ in range(20):
                                if process.poll() is not None:
                                    break
                                time.sleep(0.1)
                            if process.poll() is None:
                                if os.name == "posix":
                                    try:
                                        os.killpg(process.pid, signal.SIGKILL)
                                    except ProcessLookupError:
                                        pass
                                else:  # pragma: no cover
                                    process.kill()
                            returncode = 0
                            break
                    else:
                        previous_sizes = None
                        stable_polls = 0
                if time.monotonic() >= deadline:
                    timed_out = True
                    if os.name == "posix":
                        try:
                            os.killpg(process.pid, signal.SIGKILL)
                        except ProcessLookupError:
                            pass
                    else:  # pragma: no cover
                        process.kill()
                    break
                time.sleep(0.1)
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        if completed_by_help_sentinel:
            stderr += (
                "\n[mdstats] Stable CLI help output was observed; "
                "a lingering process group was terminated.\n"
            )
        return MaceCliCommandResult(
            command=command,
            resolved_executable=executable,
            returncode=None if timed_out else returncode,
            stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
            stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
            stdout_tail=stdout[-4000:],
            stderr_tail=stderr[-4000:],
            skipped_reason=f"timeout:{timeout_seconds}" if timed_out else None,
        )
    finally:
        stdout_path.unlink(missing_ok=True)
        stderr_path.unlink(missing_ok=True)


def run_mace_cli_smoke(
    environment: MaceRuntimeEnvironmentRecord,
    *,
    policy: MaceCliSmokePolicy | None = None,
) -> MaceCliSmokeRecord:
    active = MaceCliSmokePolicy() if policy is None else policy
    bin_dir = Path(environment.python_executable).parent
    results: list[MaceCliCommandResult] = []
    if not environment.qualified_for_cli_smoke:
        reason = "environment_not_qualified:" + ",".join(environment.missing_required_distributions)
        for command in active.commands:
            results.append(
                MaceCliCommandResult(
                    command=command,
                    resolved_executable=None,
                    returncode=None,
                    stdout_sha256=None,
                    stderr_sha256=None,
                    stdout_tail="",
                    stderr_tail="",
                    skipped_reason=reason,
                )
            )
        return MaceCliSmokeRecord(environment.content_digest, active, tuple(results))
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join([str(bin_dir), env.get("PATH", "")])
    for name in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[name] = "2"
    for command in active.commands:
        executable = shutil.which(command[0], path=env["PATH"])
        if executable is None:
            results.append(
                MaceCliCommandResult(
                    command=command,
                    resolved_executable=None,
                    returncode=None,
                    stdout_sha256=None,
                    stderr_sha256=None,
                    stdout_tail="",
                    stderr_tail="",
                    skipped_reason=f"executable_not_found:{command[0]}",
                )
            )
            continue
        results.append(
            _run_cli_smoke_command(
                command,
                executable=executable,
                env=env,
                timeout_seconds=active.timeout_seconds,
            )
        )
    return MaceCliSmokeRecord(environment.content_digest, active, tuple(results))
