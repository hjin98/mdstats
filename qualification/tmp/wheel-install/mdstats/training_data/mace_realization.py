"""Real MACE parser, dry-run, training, extraction, and evaluation smoke records.

MLFF-DATA9A2 turns DATA8's source-level compatibility claim into executable
proof against the qualified ``mace-torch==0.3.16`` runtime.  The implementation
is intentionally narrow: it operates on immutable DATA8 job artifacts, runs in
an explicit qualified environment, captures command digests/tails, and never
uses held-out labels for training or checkpoint choice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence
import hashlib
import json
import os
import shutil
import signal
import subprocess
import tempfile
import time

import numpy as np

from ._common import sha256_file_cached
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .mace_runtime import (
    MaceCliCommandResult,
    MaceRuntimeEnvironmentRecord,
)
from .protocol import MaceJobArtifact, TrainingMode
from .precision import MacePrecisionTransitionRecord, build_mace_precision_transition_record
from .critical_precision import (
    CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE,
    MaceCriticalPrecisionAudit,
    MaceCriticalPrecisionPolicy,
)

MACE_CONFIG_REALIZATION_POLICY_SCHEMA = "mdstats.mace-config-realization-policy.v1"
MACE_CONFIG_REALIZATION_RECORD_SCHEMA = "mdstats.mace-config-realization-record.v4"
MACE_CONFIG_REALIZATION_RECORD_V3_SCHEMA = "mdstats.mace-config-realization-record.v3"
MACE_CONFIG_REALIZATION_RECORD_LEGACY_SCHEMA = "mdstats.mace-config-realization-record.v2"
MACE_JOB_EXECUTION_SMOKE_POLICY_SCHEMA = "mdstats.mace-job-execution-smoke-policy.v2"
MACE_JOB_EXECUTION_SMOKE_RECORD_SCHEMA = "mdstats.mace-job-execution-smoke-record.v3"
MACE_JOB_EXECUTION_SMOKE_RECORD_LEGACY_SCHEMA = "mdstats.mace-job-execution-smoke-record.v2"


def _sha256_file(path: Path) -> str:
    return sha256_file_cached(path)


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    """Terminate one isolated command group and reap its direct child."""

    if process.poll() is not None:
        return
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    else:  # pragma: no cover - Windows fallback
        process.terminate()
    try:
        process.wait(timeout=2.0)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    else:  # pragma: no cover - Windows fallback
        process.kill()
    try:
        process.wait(timeout=2.0)
    except subprocess.TimeoutExpired:  # pragma: no cover - pathological OS failure
        pass


def _runtime_environment(
    environment: MaceRuntimeEnvironmentRecord,
    *,
    num_threads: int,
) -> dict[str, str]:
    env = dict(os.environ)
    bin_dir = str(Path(environment.python_executable).parent)
    env["PATH"] = os.pathsep.join([bin_dir, env.get("PATH", "")])
    python_paths = list(environment.inherited_python_paths)
    existing = env.get("PYTHONPATH")
    if existing:
        python_paths.extend(part for part in existing.split(os.pathsep) if part)
    if python_paths:
        env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(python_paths))
    for name in (
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "OPENBLAS_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
    ):
        env[name] = str(num_threads)
    return env


def _run_with_file_capture(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    resolved_executable: str,
    completion_paths: Sequence[Path] = (),
    completion_text: str | None = None,
) -> MaceCliCommandResult:
    """Run one command without PIPE EOF dependence on orphaned descendants.

    For MACE commands known to finish their scientific work before third-party
    shutdown workers exit, ``completion_paths`` provides an external artifact
    sentinel. The parent accepts only non-empty, stable files, then terminates
    the lingering process group. Downstream validation still checks every
    required model/prediction field and hash.
    """

    argv = tuple(str(v) for v in command)
    stdout_path: Path | None = None
    stderr_path: Path | None = None
    timed_out = False
    completed_by_sentinel = False
    returncode: int | None = None
    stdout = ""
    stderr = ""
    paths = tuple(Path(path).resolve() for path in completion_paths)
    try:
        with tempfile.NamedTemporaryFile(prefix="mdstats-mace-stdout-", dir=cwd, delete=False) as stdout_handle:
            stdout_path = Path(stdout_handle.name)
        with tempfile.NamedTemporaryFile(prefix="mdstats-mace-stderr-", dir=cwd, delete=False) as stderr_handle:
            stderr_path = Path(stderr_handle.name)
        with stdout_path.open("wb") as stdout_handle, stderr_path.open("wb") as stderr_handle:
            process = subprocess.Popen(
                [resolved_executable, *argv[1:]],
                cwd=cwd,
                env=dict(env),
                stdout=stdout_handle,
                stderr=stderr_handle,
                start_new_session=(os.name == "posix"),
            )
            deadline = time.monotonic() + timeout_seconds
            previous_state: tuple[tuple[int, int], ...] | None = None
            stable_polls = 0
            text_completion_polls = 0
            while True:
                observed = process.poll()
                if observed is not None:
                    returncode = int(observed)
                    break
                if paths:
                    try:
                        state = tuple((path.stat().st_size, path.stat().st_mtime_ns) for path in paths)
                    except OSError:
                        state = ()
                    if state and all(size > 0 for size, _ in state):
                        stable_polls = stable_polls + 1 if state == previous_state else 0
                        previous_state = state
                        if stable_polls >= 10:
                            completed_by_sentinel = True
                            _terminate_process_group(process)
                            returncode = 0
                            break
                    else:
                        previous_state = None
                        stable_polls = 0
                if completion_text is not None:
                    observed_text = (
                        stdout_path.read_text(encoding="utf-8", errors="replace")
                        + "\n"
                        + stderr_path.read_text(encoding="utf-8", errors="replace")
                    )
                    if completion_text in observed_text:
                        text_completion_polls += 1
                        if text_completion_polls >= 5:
                            completed_by_sentinel = True
                            _terminate_process_group(process)
                            returncode = 0
                            break
                    else:
                        text_completion_polls = 0
                if time.monotonic() >= deadline:
                    timed_out = True
                    _terminate_process_group(process)
                    break
                time.sleep(0.1)
        stdout = stdout_path.read_text(encoding="utf-8", errors="replace")
        stderr = stderr_path.read_text(encoding="utf-8", errors="replace")
        if completed_by_sentinel:
            stderr += (
                "\n[mdstats] A stable completion sentinel was observed; "
                "a lingering MACE process group was terminated.\n"
            )
    finally:
        for path in (stdout_path, stderr_path):
            if path is not None:
                path.unlink(missing_ok=True)
    return MaceCliCommandResult(
        command=argv,
        resolved_executable=resolved_executable,
        returncode=None if timed_out else returncode,
        stdout_sha256=hashlib.sha256(stdout.encode()).hexdigest(),
        stderr_sha256=hashlib.sha256(stderr.encode()).hexdigest(),
        stdout_tail=stdout[-4000:],
        stderr_tail=stderr[-4000:],
        skipped_reason=f"timeout:{timeout_seconds}" if timed_out else None,
    )


def _command_result(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
) -> MaceCliCommandResult:
    argv = tuple(str(v) for v in command)
    executable = shutil.which(argv[0], path=env.get("PATH"))
    if executable is None:
        return MaceCliCommandResult(
            command=argv,
            resolved_executable=None,
            returncode=None,
            stdout_sha256=None,
            stderr_sha256=None,
            stdout_tail="",
            stderr_tail="",
            skipped_reason=f"executable_not_found:{argv[0]}",
        )
    return _run_with_file_capture(
        argv,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        resolved_executable=executable,
    )


def _forced_exit_mace_cli_result(
    logical_command: Sequence[str],
    *,
    module: str,
    environment: MaceRuntimeEnvironmentRecord,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: float,
    completion_paths: Sequence[Path] = (),
    completion_text: str | None = None,
    install_critical_fp64: bool = False,
    critical_precision_policy: MaceCriticalPrecisionPolicy | None = None,
) -> MaceCliCommandResult:
    """Run a real MACE CLI main function with external completion sentinels."""

    if critical_precision_policy is not None:
        active_env = dict(env)
        active_env[CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE] = json.dumps(
            critical_precision_policy.to_dict(), sort_keys=True, separators=(",", ":")
        )
        env = active_env
        precision_bootstrap = (
            "import json as _json; "
            "from mdstats.training_data.critical_precision import "
            "CRITICAL_PRECISION_POLICY_ENVIRONMENT_VARIABLE as _cp_env, "
            "MaceCriticalPrecisionPolicy as _CP, "
            "activate_mace_critical_precision_policy as _activate_cp; "
            "_activate_cp(_CP.from_dict(_json.loads(os.environ[_cp_env]))); "
        )
    else:
        precision_bootstrap = (
            "from mdstats.training_data.critical_precision import "
            "install_mace_critical_fp64_patch as _install_critical_fp64; "
            "_install_critical_fp64(); "
            if install_critical_fp64
            else ""
        )
    operation = f"MACE {module} command-line execution"
    code = (
        "import os,sys; "
        + precision_bootstrap
        + "from mdstats.training_data.mace_compatibility import "
        "mace_runtime_warning_scope as _warning_scope; "
        + f"from {module} import main as _main; "
        "_code=0\n"
        "try:\n"
        + f" with _warning_scope({operation!r}):\n  _main()\n"
        "except SystemExit as _exc:\n _code=int(_exc.code or 0)\n"
        "sys.stdout.flush(); sys.stderr.flush(); os._exit(_code)"
    )
    actual = (environment.python_executable, "-c", code, *tuple(logical_command)[1:])
    result = _run_with_file_capture(
        actual,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        resolved_executable=environment.python_executable,
        completion_paths=completion_paths,
        completion_text=completion_text,
    )
    return MaceCliCommandResult(
        command=tuple(str(v) for v in logical_command),
        resolved_executable=result.resolved_executable,
        returncode=result.returncode,
        stdout_sha256=result.stdout_sha256,
        stderr_sha256=result.stderr_sha256,
        stdout_tail=result.stdout_tail,
        stderr_tail=result.stderr_tail,
        skipped_reason=result.skipped_reason,
    )


def _python_probe_result(
    environment: MaceRuntimeEnvironmentRecord,
    *,
    code: str,
    arguments: Sequence[str],
    cwd: Path,
    timeout_seconds: float,
    num_threads: int,
    completion_text: str | None = None,
) -> MaceCliCommandResult:
    env = _runtime_environment(environment, num_threads=num_threads)
    command = (environment.python_executable, "-c", code, *arguments)
    return _run_with_file_capture(
        command,
        cwd=cwd,
        env=env,
        timeout_seconds=timeout_seconds,
        resolved_executable=environment.python_executable,
        completion_text=completion_text,
    )


def _last_json_object(text: str) -> dict[str, Any] | None:
    for line in reversed(text.splitlines()):
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


@dataclass(frozen=True, slots=True)
class MaceConfigRealizationPolicy:
    required_mace_version: str = "0.3.16"
    run_loader_dry_run: bool = True
    num_threads: int = 2
    timeout_seconds: float = 300.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        object.__setattr__(self, "num_threads", int(self.num_threads))
        if self.required_mace_version != "0.3.16":
            raise TrainingDataInputError(
                "The first MACE config-realization policy is locked to v0.3.16."
            )
        if self.timeout_seconds <= 0.0:
            raise TrainingDataInputError("MACE realization timeout must be positive.")
        if self.num_threads <= 0:
            raise TrainingDataInputError("MACE realization thread count must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_CONFIG_REALIZATION_POLICY_SCHEMA,
            "required_mace_version": self.required_mace_version,
            "run_loader_dry_run": self.run_loader_dry_run,
            "num_threads": self.num_threads,
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceConfigRealizationPolicy":
        if payload.get("schema") != MACE_CONFIG_REALIZATION_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE realization-policy schema.")
        result = cls(
            required_mace_version=str(payload["required_mace_version"]),
            run_loader_dry_run=bool(payload["run_loader_dry_run"]),
            num_threads=int(payload.get("num_threads", 2)),
            timeout_seconds=float(payload["timeout_seconds"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE realization-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceConfigRealizationRecord:
    environment_digest: str
    job_digest: str
    config_relative_path: str
    config_sha256: str
    policy: MaceConfigRealizationPolicy
    parser_result: MaceCliCommandResult
    loader_dry_run_result: MaceCliCommandResult | None
    parsed_name: str | None
    parsed_loss: str | None
    parsed_default_dtype: str | None
    parsed_atomic_numbers: tuple[int, ...]
    parsed_head_names: tuple[str, ...]
    parsed_e0_atomic_numbers: tuple[int, ...]
    parsed_enable_cueq: bool
    parsed_only_cueq: bool
    parsed_foundation_model: str | None = None
    parsed_foundation_model_sha256: str | None = None
    parsed_foundation_head: str | None = None
    parsed_multiheads_finetuning: bool = False
    serialization_schema: str = field(default=MACE_CONFIG_REALIZATION_RECORD_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "environment_digest", validate_digest(self.environment_digest, name="environment_digest"))
        object.__setattr__(self, "job_digest", validate_digest(self.job_digest, name="job_digest"))
        object.__setattr__(self, "config_sha256", validate_digest(self.config_sha256, name="config_sha256"))
        numbers = tuple(int(v) for v in self.parsed_atomic_numbers)
        e0_numbers = tuple(int(v) for v in self.parsed_e0_atomic_numbers)
        if numbers != tuple(sorted(set(numbers))):
            raise TrainingDataInputError("Parsed MACE atomic numbers must be sorted and unique.")
        if e0_numbers != tuple(sorted(set(e0_numbers))):
            raise TrainingDataInputError("Parsed MACE E0 atomic numbers must be sorted and unique.")
        object.__setattr__(self, "parsed_atomic_numbers", numbers)
        object.__setattr__(self, "parsed_e0_atomic_numbers", e0_numbers)
        object.__setattr__(self, "parsed_head_names", tuple(str(v) for v in self.parsed_head_names))
        if self.serialization_schema not in {
            MACE_CONFIG_REALIZATION_RECORD_SCHEMA,
            MACE_CONFIG_REALIZATION_RECORD_V3_SCHEMA,
            MACE_CONFIG_REALIZATION_RECORD_LEGACY_SCHEMA,
        }:
            raise TrainingDataInputError("Unsupported internal MACE realization-record schema.")
        if self.parsed_foundation_model_sha256 is not None:
            object.__setattr__(
                self,
                "parsed_foundation_model_sha256",
                validate_digest(self.parsed_foundation_model_sha256, name="parsed_foundation_model_sha256"),
            )
        if self.parsed_foundation_model is not None:
            value = str(self.parsed_foundation_model).strip()
            if not value:
                raise TrainingDataInputError("Parsed MACE foundation-model path cannot be blank.")
            object.__setattr__(self, "parsed_foundation_model", value)
        if self.parsed_foundation_head is not None:
            value = str(self.parsed_foundation_head).strip()
            if not value:
                raise TrainingDataInputError("Parsed MACE foundation head cannot be blank.")
            object.__setattr__(self, "parsed_foundation_head", value)

    @property
    def parser_passed(self) -> bool:
        return (
            self.parser_result.passed
            and self.parsed_loss == "universal"
            and self.parsed_default_dtype in {"float32", "float64"}
            and bool(self.parsed_head_names)
            and bool(self.parsed_atomic_numbers)
            and set(self.parsed_e0_atomic_numbers).issubset(self.parsed_atomic_numbers)
        )

    @property
    def passed(self) -> bool:
        return self.parser_passed and (
            not self.policy.run_loader_dry_run
            or (
                self.loader_dry_run_result is not None
                and self.loader_dry_run_result.passed
            )
        )

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "environment_digest": self.environment_digest,
            "job_digest": self.job_digest,
            "config_relative_path": self.config_relative_path,
            "config_sha256": self.config_sha256,
            "policy": self.policy.to_dict(),
            "parser_result": self.parser_result.to_dict(),
            "loader_dry_run_result": None if self.loader_dry_run_result is None else self.loader_dry_run_result.to_dict(),
            "parsed_name": self.parsed_name,
            "parsed_loss": self.parsed_loss,
            "parsed_default_dtype": self.parsed_default_dtype,
            "parsed_atomic_numbers": list(self.parsed_atomic_numbers),
            "parsed_head_names": list(self.parsed_head_names),
            "parsed_e0_atomic_numbers": list(self.parsed_e0_atomic_numbers),
            "parser_passed": self.parser_passed,
            "passed": self.passed,
        }
        if self.serialization_schema != MACE_CONFIG_REALIZATION_RECORD_LEGACY_SCHEMA:
            payload.update({
                "parsed_enable_cueq": self.parsed_enable_cueq,
                "parsed_only_cueq": self.parsed_only_cueq,
            })
        if self.serialization_schema == MACE_CONFIG_REALIZATION_RECORD_SCHEMA:
            payload.update({
                "parsed_foundation_model": self.parsed_foundation_model,
                "parsed_foundation_model_sha256": self.parsed_foundation_model_sha256,
                "parsed_foundation_head": self.parsed_foundation_head,
                "parsed_multiheads_finetuning": self.parsed_multiheads_finetuning,
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceConfigRealizationRecord":
        if payload.get("schema") not in {
            MACE_CONFIG_REALIZATION_RECORD_SCHEMA,
            MACE_CONFIG_REALIZATION_RECORD_V3_SCHEMA,
            MACE_CONFIG_REALIZATION_RECORD_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported MACE realization-record schema.")
        result = cls(
            environment_digest=str(payload["environment_digest"]),
            job_digest=str(payload["job_digest"]),
            config_relative_path=str(payload["config_relative_path"]),
            config_sha256=str(payload["config_sha256"]),
            policy=MaceConfigRealizationPolicy.from_dict(payload["policy"]),
            parser_result=MaceCliCommandResult.from_dict(payload["parser_result"]),
            loader_dry_run_result=None if payload.get("loader_dry_run_result") is None else MaceCliCommandResult.from_dict(payload["loader_dry_run_result"]),
            parsed_name=None if payload.get("parsed_name") is None else str(payload["parsed_name"]),
            parsed_loss=None if payload.get("parsed_loss") is None else str(payload["parsed_loss"]),
            parsed_default_dtype=None if payload.get("parsed_default_dtype") is None else str(payload["parsed_default_dtype"]),
            parsed_atomic_numbers=tuple(int(v) for v in payload.get("parsed_atomic_numbers", ())),
            parsed_head_names=tuple(str(v) for v in payload.get("parsed_head_names", ())),
            parsed_e0_atomic_numbers=tuple(int(v) for v in payload.get("parsed_e0_atomic_numbers", ())),
            parsed_enable_cueq=bool(payload.get("parsed_enable_cueq", False)),
            parsed_only_cueq=bool(payload.get("parsed_only_cueq", False)),
            parsed_foundation_model=None if payload.get("parsed_foundation_model") is None else str(payload["parsed_foundation_model"]),
            parsed_foundation_model_sha256=None if payload.get("parsed_foundation_model_sha256") is None else str(payload["parsed_foundation_model_sha256"]),
            parsed_foundation_head=None if payload.get("parsed_foundation_head") is None else str(payload["parsed_foundation_head"]),
            parsed_multiheads_finetuning=bool(payload.get("parsed_multiheads_finetuning", False)),
            serialization_schema=str(payload.get("schema")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE realization-record digest mismatch.")
        return result


def realize_mace_job_config(
    environment: MaceRuntimeEnvironmentRecord,
    bundle_root: str | Path,
    job: MaceJobArtifact,
    *,
    policy: MaceConfigRealizationPolicy | None = None,
) -> MaceConfigRealizationRecord:
    active = MaceConfigRealizationPolicy() if policy is None else policy
    root = Path(bundle_root).resolve()
    config_path = root / job.config_relative_path
    if not config_path.is_file():
        raise TrainingDataInputError(f"MACE config does not exist: {config_path}")
    observed_sha256 = _sha256_file(config_path)
    if observed_sha256 != job.config_sha256:
        raise TrainingDataInputError("MACE config digest differs from the DATA8 job artifact.")
    if not environment.qualified_for_cli_smoke:
        skipped = MaceCliCommandResult(
            command=(environment.python_executable, "mace_config_parser_probe", str(config_path)),
            resolved_executable=environment.python_executable,
            returncode=None,
            stdout_sha256=None,
            stderr_sha256=None,
            stdout_tail="",
            stderr_tail="",
            skipped_reason="environment_not_qualified",
        )
        return MaceConfigRealizationRecord(
            environment.content_digest,
            job.content_digest,
            job.config_relative_path,
            observed_sha256,
            active,
            skipped,
            None,
            None,
            None,
            None,
            (),
            (),
            (),
            False,
            False,
        )
    if environment.mace_version != active.required_mace_version:
        raise TrainingDataInputError(
            f"MACE realization requires {active.required_mace_version}, observed {environment.mace_version}."
        )
    probe = r'''
import ast, json, os, sys
from mace.tools.arg_parser import build_default_arg_parser
args = build_default_arg_parser().parse_args(["--config", sys.argv[1]])
heads = ast.literal_eval(args.heads)
atomic_numbers = sorted(set(int(v) for v in ast.literal_eval(args.atomic_numbers)))
e0_numbers = set()
e0_missing_by_head = {}
for head_name, head in heads.items():
    value = head.get("E0s")
    if value is None or value in {"foundation", "estimated"}:
        continue
    mapping = ast.literal_eval(value)
    available = {int(v) for v in mapping}
    e0_numbers.update(available)
    required_value = head.get("atomic_numbers")
    required = (
        set(atomic_numbers)
        if required_value is None
        else {int(v) for v in ast.literal_eval(required_value)}
    )
    missing = sorted(required - available)
    if missing:
        e0_missing_by_head[str(head_name)] = missing
print(json.dumps({
    "name": args.name,
    "loss": args.loss,
    "default_dtype": args.default_dtype,
    "atomic_numbers": atomic_numbers,
    "head_names": list(heads),
    "e0_atomic_numbers": sorted(e0_numbers),
    "e0_missing_by_head": e0_missing_by_head,
    "enable_cueq": bool(args.enable_cueq),
    "only_cueq": bool(args.only_cueq),
    "foundation_model": args.foundation_model,
    "foundation_head": args.foundation_head,
    "multiheads_finetuning": bool(args.multiheads_finetuning),
}, sort_keys=True))
sys.stdout.flush()
os._exit(0)
'''
    parser_result = _python_probe_result(
        environment,
        code=probe,
        arguments=(str(config_path),),
        cwd=config_path.parent,
        timeout_seconds=active.timeout_seconds,
        num_threads=active.num_threads,
        completion_text='"e0_atomic_numbers"',
    )
    payload = _last_json_object(parser_result.stdout_tail) if parser_result.passed else None
    if payload is not None and payload.get("e0_missing_by_head"):
        details = ", ".join(
            f"{head}: {numbers}"
            for head, numbers in sorted(payload["e0_missing_by_head"].items())
        )
        raise TrainingDataInputError(
            "MACE config explicit E0 mappings do not cover the global element table: "
            + details
        )
    dry_run_result = None
    if active.run_loader_dry_run and parser_result.passed:
        dry_run_result = _forced_exit_mace_cli_result(
            ("mace_run_train", "--config", config_path.name, "--dry_run"),
            module="mace.cli.run_train",
            environment=environment,
            cwd=config_path.parent,
            env=_runtime_environment(environment, num_threads=active.num_threads),
            timeout_seconds=active.timeout_seconds,
            completion_text="DRY RUN mode enabled. Stopping now.",
        )
    parsed_foundation_model = None if payload is None else payload.get("foundation_model")
    parsed_foundation_model_sha256 = None
    if parsed_foundation_model:
        foundation_path = Path(str(parsed_foundation_model))
        if not foundation_path.is_absolute():
            foundation_path = (config_path.parent / foundation_path).resolve()
        if foundation_path.is_file():
            parsed_foundation_model_sha256 = _sha256_file(foundation_path)

    result = MaceConfigRealizationRecord(
        environment_digest=environment.content_digest,
        job_digest=job.content_digest,
        config_relative_path=job.config_relative_path,
        config_sha256=observed_sha256,
        policy=active,
        parser_result=parser_result,
        loader_dry_run_result=dry_run_result,
        parsed_name=None if payload is None else str(payload["name"]),
        parsed_loss=None if payload is None else str(payload["loss"]),
        parsed_default_dtype=None if payload is None else str(payload["default_dtype"]),
        parsed_atomic_numbers=() if payload is None else tuple(int(v) for v in payload["atomic_numbers"]),
        parsed_head_names=() if payload is None else tuple(str(v) for v in payload["head_names"]),
        parsed_e0_atomic_numbers=() if payload is None else tuple(int(v) for v in payload["e0_atomic_numbers"]),
        parsed_enable_cueq=False if payload is None else bool(payload["enable_cueq"]),
        parsed_only_cueq=False if payload is None else bool(payload["only_cueq"]),
        parsed_foundation_model=None if parsed_foundation_model is None else str(parsed_foundation_model),
        parsed_foundation_model_sha256=parsed_foundation_model_sha256,
        parsed_foundation_head=None if payload is None or payload.get("foundation_head") is None else str(payload["foundation_head"]),
        parsed_multiheads_finetuning=False if payload is None else bool(payload["multiheads_finetuning"]),
    )
    if result.parsed_default_dtype != job.protocol.optimizer_policy.default_dtype:
        raise TrainingDataInputError(
            "Realized MACE config dtype differs from the immutable DATA8 protocol."
        )
    acceleration = job.protocol.optimizer_policy.acceleration_policy
    if result.parsed_enable_cueq != acceleration.enable_cueq:
        raise TrainingDataInputError(
            "Realized MACE config acceleration backend differs from the immutable DATA8 protocol."
        )
    if result.parsed_only_cueq != acceleration.only_cueq:
        raise TrainingDataInputError(
            "Realized MACE config only_cueq flag differs from the immutable DATA8 protocol."
        )
    expected_foundation_sha = (
        job.protocol.training_foundation_checkpoint_sha256
        or job.protocol.foundation_checkpoint.sha256
    )
    if result.parsed_foundation_model_sha256 != expected_foundation_sha:
        raise TrainingDataInputError(
            "Realized MACE config foundation-model bytes differ from the immutable DATA8 training foundation."
        )
    if result.parsed_foundation_head != job.protocol.foundation_checkpoint.foundation_head:
        raise TrainingDataInputError(
            "Realized MACE config foundation head differs from the immutable scientific foundation identity."
        )
    expected_multihead = job.protocol.training_mode is TrainingMode.MULTIHEAD_REPLAY
    if result.parsed_multiheads_finetuning != expected_multihead:
        raise TrainingDataInputError(
            "Realized MACE config multi-head fine-tuning mode differs from the immutable DATA8 protocol."
        )
    return result


@dataclass(frozen=True, slots=True)
class MaceJobExecutionSmokePolicy:
    max_num_epochs: int = 1
    device: str = "cpu"
    default_dtype: str = "protocol"
    extract_target_head: bool = True
    evaluate_round_trip: bool = True
    num_threads: int = 2
    timeout_seconds: float = 600.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "max_num_epochs", int(self.max_num_epochs))
        object.__setattr__(self, "num_threads", int(self.num_threads))
        object.__setattr__(self, "timeout_seconds", float(self.timeout_seconds))
        if self.max_num_epochs <= 0:
            raise TrainingDataInputError("MACE smoke epoch count must be positive.")
        if self.device not in {"cpu", "cuda"}:
            raise TrainingDataInputError("MACE smoke device must be cpu or cuda.")
        if self.default_dtype not in {"protocol", "float32", "float64"}:
            raise TrainingDataInputError("MACE smoke dtype must be protocol, float32, or float64.")
        if self.timeout_seconds <= 0.0:
            raise TrainingDataInputError("MACE smoke timeout must be positive.")
        if self.num_threads <= 0:
            raise TrainingDataInputError("MACE smoke thread count must be positive.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_JOB_EXECUTION_SMOKE_POLICY_SCHEMA,
            "max_num_epochs": self.max_num_epochs,
            "device": self.device,
            "default_dtype": self.default_dtype,
            "extract_target_head": self.extract_target_head,
            "evaluate_round_trip": self.evaluate_round_trip,
            "num_threads": self.num_threads,
            "timeout_seconds": self.timeout_seconds,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceJobExecutionSmokePolicy":
        if payload.get("schema") != MACE_JOB_EXECUTION_SMOKE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE execution-smoke policy schema.")
        result = cls(
            max_num_epochs=int(payload["max_num_epochs"]),
            device=str(payload["device"]),
            default_dtype=str(payload["default_dtype"]),
            extract_target_head=bool(payload["extract_target_head"]),
            evaluate_round_trip=bool(payload["evaluate_round_trip"]),
            num_threads=int(payload.get("num_threads", 2)),
            timeout_seconds=float(payload["timeout_seconds"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE execution-smoke policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceJobExecutionSmokeRecord:
    environment_digest: str
    job_digest: str
    realization_digest: str
    policy: MaceJobExecutionSmokePolicy
    output_directory: str
    training_result: MaceCliCommandResult
    model_artifacts: tuple[tuple[str, str], ...]
    checkpoint_artifacts: tuple[tuple[str, str], ...]
    head_list_result: MaceCliCommandResult | None
    head_names: tuple[str, ...]
    target_head_extraction_result: MaceCliCommandResult | None
    target_head_model: tuple[str, str] | None
    evaluation_result: MaceCliCommandResult | None
    evaluation_artifact: tuple[str, str] | None
    evaluation_configuration_count: int
    evaluation_fields_finite: bool
    precision_transition: MacePrecisionTransitionRecord | None = None
    critical_precision_audit: MaceCriticalPrecisionAudit | None = None

    def __post_init__(self) -> None:
        for name in ("environment_digest", "job_digest", "realization_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "model_artifacts", tuple((str(path), validate_digest(value, name="model_sha256")) for path, value in self.model_artifacts))
        object.__setattr__(self, "checkpoint_artifacts", tuple((str(path), validate_digest(value, name="checkpoint_sha256")) for path, value in self.checkpoint_artifacts))
        object.__setattr__(self, "head_names", tuple(str(v) for v in self.head_names))
        if self.target_head_model is not None:
            object.__setattr__(self, "target_head_model", (str(self.target_head_model[0]), validate_digest(self.target_head_model[1], name="target_head_sha256")))
        if self.evaluation_artifact is not None:
            object.__setattr__(self, "evaluation_artifact", (str(self.evaluation_artifact[0]), validate_digest(self.evaluation_artifact[1], name="evaluation_sha256")))
        if self.evaluation_configuration_count < 0:
            raise TrainingDataInputError("Evaluation configuration count cannot be negative.")

    @property
    def passed(self) -> bool:
        if not self.training_result.passed or not self.model_artifacts or not self.checkpoint_artifacts:
            return False
        if self.policy.extract_target_head:
            single_target_passthrough = (
                self.head_names == ("target_head",)
                and self.target_head_model is not None
                and self.target_head_extraction_result is None
            )
            explicit_extraction = (
                self.target_head_extraction_result is not None
                and self.target_head_extraction_result.passed
                and self.target_head_model is not None
            )
            if (
                self.head_list_result is None
                or not self.head_list_result.passed
                or "target_head" not in self.head_names
                or not (single_target_passthrough or explicit_extraction)
            ):
                return False
        if self.policy.evaluate_round_trip:
            if (
                self.evaluation_result is None
                or not self.evaluation_result.passed
                or self.evaluation_artifact is None
                or self.evaluation_configuration_count <= 0
                or not self.evaluation_fields_finite
            ):
                return False
        if self.precision_transition is None or not self.precision_transition.passed:
            return False
        if self.critical_precision_audit is None or not self.critical_precision_audit.passed:
            return False
        return True

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_JOB_EXECUTION_SMOKE_RECORD_SCHEMA,
            "environment_digest": self.environment_digest,
            "job_digest": self.job_digest,
            "realization_digest": self.realization_digest,
            "policy": self.policy.to_dict(),
            "output_directory": self.output_directory,
            "training_result": self.training_result.to_dict(),
            "model_artifacts": [list(v) for v in self.model_artifacts],
            "checkpoint_artifacts": [list(v) for v in self.checkpoint_artifacts],
            "head_list_result": None if self.head_list_result is None else self.head_list_result.to_dict(),
            "head_names": list(self.head_names),
            "target_head_extraction_result": None if self.target_head_extraction_result is None else self.target_head_extraction_result.to_dict(),
            "target_head_model": None if self.target_head_model is None else list(self.target_head_model),
            "evaluation_result": None if self.evaluation_result is None else self.evaluation_result.to_dict(),
            "evaluation_artifact": None if self.evaluation_artifact is None else list(self.evaluation_artifact),
            "evaluation_configuration_count": self.evaluation_configuration_count,
            "evaluation_fields_finite": self.evaluation_fields_finite,
            "precision_transition": None if self.precision_transition is None else self.precision_transition.to_dict(),
            "critical_precision_audit": None if self.critical_precision_audit is None else self.critical_precision_audit.to_dict(),
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceJobExecutionSmokeRecord":
        if payload.get("schema") not in {
            MACE_JOB_EXECUTION_SMOKE_RECORD_SCHEMA,
            MACE_JOB_EXECUTION_SMOKE_RECORD_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError("Unsupported MACE execution-smoke record schema.")
        result = cls(
            environment_digest=str(payload["environment_digest"]),
            job_digest=str(payload["job_digest"]),
            realization_digest=str(payload["realization_digest"]),
            policy=MaceJobExecutionSmokePolicy.from_dict(payload["policy"]),
            output_directory=str(payload["output_directory"]),
            training_result=MaceCliCommandResult.from_dict(payload["training_result"]),
            model_artifacts=tuple((str(v[0]), str(v[1])) for v in payload["model_artifacts"]),
            checkpoint_artifacts=tuple((str(v[0]), str(v[1])) for v in payload["checkpoint_artifacts"]),
            head_list_result=None if payload.get("head_list_result") is None else MaceCliCommandResult.from_dict(payload["head_list_result"]),
            head_names=tuple(str(v) for v in payload.get("head_names", ())),
            target_head_extraction_result=None if payload.get("target_head_extraction_result") is None else MaceCliCommandResult.from_dict(payload["target_head_extraction_result"]),
            target_head_model=None if payload.get("target_head_model") is None else (str(payload["target_head_model"][0]), str(payload["target_head_model"][1])),
            evaluation_result=None if payload.get("evaluation_result") is None else MaceCliCommandResult.from_dict(payload["evaluation_result"]),
            evaluation_artifact=None if payload.get("evaluation_artifact") is None else (str(payload["evaluation_artifact"][0]), str(payload["evaluation_artifact"][1])),
            evaluation_configuration_count=int(payload.get("evaluation_configuration_count", 0)),
            evaluation_fields_finite=bool(payload.get("evaluation_fields_finite", False)),
            precision_transition=None if payload.get("precision_transition") is None else MacePrecisionTransitionRecord.from_dict(payload["precision_transition"]),
            critical_precision_audit=(
                None
                if payload.get("critical_precision_audit") is None
                else MaceCriticalPrecisionAudit.from_dict(payload["critical_precision_audit"])
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE execution-smoke record digest mismatch.")
        return result


def _artifact_inventory(root: Path, patterns: Sequence[str]) -> tuple[tuple[str, str], ...]:
    paths = sorted({path for pattern in patterns for path in root.glob(pattern) if path.is_file()})
    return tuple((str(path.relative_to(root)), _sha256_file(path)) for path in paths)


def _parse_head_names(text: str) -> tuple[str, ...]:
    """Parse only the indented head-name block printed by mace_select_head."""

    names: list[str] = []
    active = False
    for line in text.splitlines():
        if line.strip() == "Available heads:":
            active = True
            continue
        if not active:
            continue
        if not line.strip():
            if names:
                break
            continue
        if not line[:1].isspace():
            break
        stripped = line.strip()
        if stripped:
            names.append(stripped)
    return tuple(names)


def _validate_evaluation(path: Path) -> tuple[int, bool]:
    try:
        from ase.io import read
    except ModuleNotFoundError as exc:  # pragma: no cover
        raise TrainingDataInputError("ASE is required to validate MACE evaluation output.") from exc
    atoms_list = read(path, index=":", format="extxyz")
    if not isinstance(atoms_list, list):
        atoms_list = [atoms_list]
    finite = True
    for atoms in atoms_list:
        energy = atoms.info.get("MACE_energy")
        forces = atoms.arrays.get("MACE_forces")
        stress = atoms.info.get("MACE_stress")
        finite = finite and energy is not None and np.all(np.isfinite(np.asarray(energy, dtype=float)))
        finite = finite and forces is not None and np.all(np.isfinite(np.asarray(forces, dtype=float)))
        finite = finite and stress is not None and np.all(np.isfinite(np.asarray(stress, dtype=float)))
    return len(atoms_list), bool(finite)


def _run_critical_precision_audit(
    environment: MaceRuntimeEnvironmentRecord,
    *,
    model_path: Path,
    configuration_path: Path,
    default_dtype: str,
    cwd: Path,
    timeout_seconds: float,
    num_threads: int,
    device: str,
    enable_cueq: bool,
    critical_precision_policy: MaceCriticalPrecisionPolicy,
) -> MaceCriticalPrecisionAudit | None:
    code = r'''
import json, os, sys, torch
from ase.io import read
from mace.calculators import MACECalculator
from mdstats.training_data.critical_precision import (
    MaceCriticalPrecisionPolicy,
    activate_mace_critical_precision_policy,
    audit_mace_critical_precision,
)
from mdstats.training_data.mace_compatibility import mace_runtime_warning_scope

_policy = MaceCriticalPrecisionPolicy.from_dict(json.loads(sys.argv[6]))
activate_mace_critical_precision_policy(_policy)
with mace_runtime_warning_scope("critical-precision subprocess audit"):
    atoms = read(sys.argv[2], index=0)
    calculator = MACECalculator(
        model_paths=sys.argv[1],
        device=sys.argv[4],
        default_dtype=sys.argv[3],
        enable_cueq=(sys.argv[5].lower() == "true"),
    )
    batch = calculator._atoms_to_batch(atoms)
    model = calculator.models[0]
    batch = calculator._clone_batch(batch)
    model_dtype = next(model.parameters()).dtype
    for key in batch.keys:
        value = batch[key]
        if torch.is_tensor(value) and torch.is_floating_point(value):
            batch[key] = value.to(dtype=model_dtype)
    out = model(
        batch.to_dict(),
        compute_force=True,
        compute_virials=True,
        compute_stress=True,
        training=False,
    )
    print(json.dumps(audit_mace_critical_precision(model, out, policy=_policy).to_dict(), sort_keys=True))
    print("MDSTATS_CRITICAL_PRECISION_AUDIT_COMPLETE", flush=True)
sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
'''
    result = _python_probe_result(
        environment,
        code=code,
        arguments=(
            str(model_path),
            str(configuration_path),
            default_dtype,
            device,
            str(bool(enable_cueq)).lower(),
            json.dumps(critical_precision_policy.to_dict(), sort_keys=True, separators=(",", ":")),
        ),
        cwd=cwd,
        timeout_seconds=timeout_seconds,
        num_threads=num_threads,
        completion_text="MDSTATS_CRITICAL_PRECISION_AUDIT_COMPLETE",
    )
    if not result.passed:
        return None
    payload = _last_json_object(result.stdout_tail)
    if payload is None:
        return None
    return MaceCriticalPrecisionAudit.from_dict(payload)


def run_mace_job_execution_smoke(
    environment: MaceRuntimeEnvironmentRecord,
    bundle_root: str | Path,
    job: MaceJobArtifact,
    realization: MaceConfigRealizationRecord,
    output_directory: str | Path,
    *,
    policy: MaceJobExecutionSmokePolicy | None = None,
) -> MaceJobExecutionSmokeRecord:
    active = MaceJobExecutionSmokePolicy() if policy is None else policy
    protocol_dtype = job.protocol.optimizer_policy.default_dtype
    if active.default_dtype != "protocol" and active.default_dtype != protocol_dtype:
        raise TrainingDataInputError(
            "MACE execution-smoke dtype override differs from the DATA8 training protocol."
        )
    execution_dtype = protocol_dtype
    critical_precision_policy = job.protocol.optimizer_policy.critical_precision_policy
    if not realization.passed:
        raise TrainingDataInputError("MACE job execution smoke requires a passing config realization.")
    if realization.environment_digest != environment.content_digest or realization.job_digest != job.content_digest:
        raise TrainingDataInputError("MACE execution-smoke lineage does not match environment/job.")
    root = Path(bundle_root).resolve()
    job_dir = root / job.relative_directory
    config_path = root / job.config_relative_path
    smoke_root = Path(output_directory).resolve()
    if smoke_root.exists():
        shutil.rmtree(smoke_root)
    model_dir = smoke_root / "models"
    checkpoint_dir = smoke_root / "checkpoints"
    log_dir = smoke_root / "logs"
    results_dir = smoke_root / "results"
    for directory in (model_dir, checkpoint_dir, log_dir, results_dir):
        directory.mkdir(parents=True, exist_ok=True)
    name = f"mdstats_{job.job_id}_smoke"
    env = _runtime_environment(environment, num_threads=active.num_threads)
    training_command = (
        "mace_run_train",
        "--config",
        config_path.name,
        "--name",
        name,
        "--max_num_epochs",
        str(active.max_num_epochs),
        "--device",
        active.device,
        "--default_dtype",
        execution_dtype,
        "--model_dir",
        str(model_dir),
        "--checkpoints_dir",
        str(checkpoint_dir),
        "--log_dir",
        str(log_dir),
        "--results_dir",
        str(results_dir),
    )
    training_result = _forced_exit_mace_cli_result(
        training_command,
        module="mace.cli.run_train",
        environment=environment,
        cwd=job_dir,
        env=env,
        timeout_seconds=active.timeout_seconds,
        # The ordinary model is the authoritative scientific completion
        # artifact.  MACE v0.3.16 may log a ``*_compiled.model`` metadata
        # target without materializing that optional file on CPU, so requiring
        # both paths would turn a completed training run into a false timeout.
        completion_paths=(model_dir / f"{name}.model",),
        critical_precision_policy=critical_precision_policy,
    )
    model_artifacts = _artifact_inventory(smoke_root, ("models/**/*.model", "models/**/*.pt"))
    checkpoint_artifacts = _artifact_inventory(smoke_root, ("checkpoints/**/*.model", "checkpoints/**/*.pt"))
    final_model = model_dir / f"{name}.model"
    head_list_result = None
    head_names: tuple[str, ...] = ()
    extraction_result = None
    target_head_model = None
    eval_result = None
    evaluation_artifact = None
    evaluation_count = 0
    evaluation_finite = False
    precision_transition = None
    critical_precision_audit = None
    if training_result.passed and final_model.is_file():
        model_for_evaluation = final_model
        extracted = smoke_root / "target_head.model"
        # Inventory and (when needed) extract the target head in a single
        # authenticated subprocess so nonlinear MH-1-derived models are loaded
        # only once.  This calls the same stock MACE ``remove_pt_head`` function
        # used by ``mace_select_head``; the JSON output is emitted only after the
        # derived artifact has been written successfully.
        head_probe = r"""
import json, os, sys, torch
from mace.tools.scripts_utils import remove_pt_head
model = torch.load(sys.argv[1], map_location=sys.argv[4], weights_only=False)
heads = [str(v) for v in model.heads]
extracted = False
if sys.argv[3].lower() == "true" and heads != ["target_head"]:
    torch.set_default_dtype(next(model.parameters()).dtype)
    target = remove_pt_head(model, "target_head")
    target.to(sys.argv[4])
    torch.save(target, sys.argv[2])
    extracted = True
print(json.dumps({"heads": heads, "extracted": extracted}, sort_keys=True))
sys.stdout.flush(); sys.stderr.flush(); os._exit(0)
"""
        head_list_result = _python_probe_result(
            environment,
            code=head_probe,
            arguments=(
                str(final_model),
                str(extracted),
                str(bool(active.extract_target_head)).lower(),
                active.device,
            ),
            cwd=smoke_root,
            timeout_seconds=active.timeout_seconds,
            num_threads=active.num_threads,
            completion_text='"heads"',
        )
        if head_list_result.passed:
            head_payload = _last_json_object(head_list_result.stdout_tail)
            head_names = () if head_payload is None else tuple(str(v) for v in head_payload.get("heads", ()))
            required_heads = {"target_head"}
            if job.protocol.training_mode is TrainingMode.MULTIHEAD_REPLAY:
                required_heads.add("pt_head")
            missing_heads = sorted(required_heads.difference(head_names))
            if missing_heads:
                raise TrainingDataInputError(
                    "Real MACE training completed without the required DATA8 head contract: "
                    + ", ".join(missing_heads)
                )
            if active.extract_target_head:
                if head_names == ("target_head",):
                    target_head_model = (
                        str(final_model.relative_to(smoke_root)),
                        _sha256_file(final_model),
                    )
                    model_for_evaluation = final_model
                elif bool(head_payload.get("extracted")) and extracted.is_file():
                    # The combined probe is also the stock selected-head
                    # extraction command result for record purposes.
                    extraction_result = head_list_result
                    target_head_model = (
                        str(extracted.relative_to(smoke_root)),
                        _sha256_file(extracted),
                    )
                    model_for_evaluation = extracted
        if active.evaluate_round_trip and (not active.extract_target_head or target_head_model is not None):
            evaluation_input = job_dir / "fold_evaluation.xyz"
            if not evaluation_input.is_file():
                evaluation_input = job_dir / "target_valid.xyz"
            output = smoke_root / "evaluation_predictions.xyz"
            evaluation_command = [
                "mace_eval_configs",
                "--configs",
                str(evaluation_input),
                "--model",
                str(model_for_evaluation),
                "--output",
                str(output),
                "--device",
                active.device,
                "--default_dtype",
                execution_dtype,
                "--compute_stress",
            ]
            if job.protocol.optimizer_policy.acceleration_policy.enable_cueq:
                evaluation_command.append("--enable_cueq")
            eval_result = _forced_exit_mace_cli_result(
                tuple(evaluation_command),
                module="mace.cli.eval_configs",
                environment=environment,
                cwd=smoke_root,
                env=env,
                timeout_seconds=active.timeout_seconds,
                completion_paths=(output,),
                critical_precision_policy=critical_precision_policy,
            )
            if eval_result.passed and output.is_file():
                evaluation_artifact = (str(output.relative_to(smoke_root)), _sha256_file(output))
                evaluation_count, evaluation_finite = _validate_evaluation(output)
        if final_model.is_file():
            foundation_reference = (
                job.protocol.training_foundation_checkpoint_reference
                or job.protocol.foundation_checkpoint.reference
            )
            foundation_path = root / foundation_reference
            extracted_path = None
            if target_head_model is not None:
                extracted_path = smoke_root / target_head_model[0]
            precision_transition = build_mace_precision_transition_record(
                job,
                foundation_path,
                final_model,
                extracted_path,
            )
            audit_input = job_dir / "target_valid.xyz"
            if not audit_input.is_file():
                audit_input = job_dir / "fold_evaluation.xyz"
            if audit_input.is_file():
                critical_precision_audit = _run_critical_precision_audit(
                    environment,
                    model_path=model_for_evaluation,
                    configuration_path=audit_input,
                    default_dtype=execution_dtype,
                    cwd=smoke_root,
                    timeout_seconds=active.timeout_seconds,
                    num_threads=active.num_threads,
                    device=active.device,
                    enable_cueq=job.protocol.optimizer_policy.acceleration_policy.enable_cueq,
                    critical_precision_policy=critical_precision_policy,
                )
    return MaceJobExecutionSmokeRecord(
        environment_digest=environment.content_digest,
        job_digest=job.content_digest,
        realization_digest=realization.content_digest,
        policy=active,
        output_directory=str(smoke_root),
        training_result=training_result,
        model_artifacts=model_artifacts,
        checkpoint_artifacts=checkpoint_artifacts,
        head_list_result=head_list_result,
        head_names=head_names,
        target_head_extraction_result=extraction_result,
        target_head_model=target_head_model,
        evaluation_result=eval_result,
        evaluation_artifact=evaluation_artifact,
        evaluation_configuration_count=evaluation_count,
        evaluation_fields_finite=evaluation_finite,
        precision_transition=precision_transition,
        critical_precision_audit=critical_precision_audit,
    )
