"""Content-addressed accelerator runtime freeze for CUEQ-DEP1.

CUEQ-DEP1 is intentionally a dependency/runtime gate rather than a numerical
parity gate.  It records the exact installed accelerator stack, CUDA-visible
hardware/runtime, MACE source compatibility, and execution-mode contract used
by later CuEq phases.  The record never falls back to e3nn when CuEq is absent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest
from .mace_runtime_freeze import MaceRuntimeFreezePolicy, MaceRuntimeFreezeRecord, probe_mace_runtime_freeze

CUEQ_DEP1_POLICY_SCHEMA = "mdstats.cueq-dep1-policy.v1"
CUEQ_DEP1_DISTRIBUTION_SCHEMA = "mdstats.cueq-dep1-distribution.v1"
CUEQ_DEP1_DEVICE_SCHEMA = "mdstats.cueq-dep1-device.v1"
CUEQ_DEP1_RUNTIME_SCHEMA = "mdstats.cueq-dep1-runtime.v1"

# CUDA-13 wheels are now part of the public cuEquivariance package matrix.  The
# import name remains invariant across the CUDA-major-specific distributions.
CUEQ_DEP1_COMPONENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("torch", "torch", ("torch",)),
    ("mace", "mace", ("mace-torch",)),
    ("e3nn", "e3nn", ("e3nn",)),
    ("cueq-core", "cuequivariance", ("cuequivariance",)),
    ("cueq-torch", "cuequivariance_torch", ("cuequivariance-torch",)),
    (
        "cueq-ops",
        "cuequivariance_ops_torch",
        (
            "cuequivariance-ops-torch-cu13",
            "cuequivariance-ops-torch-cu12",
            "cuequivariance-ops-torch-cu11",
            "cuequivariance-ops-torch",
        ),
    ),
    ("oeq", "openequivariance", ("openequivariance", "OpenEquivariance")),
)

_DEFAULT_ENV_KEYS = (
    "CUDA_VISIBLE_DEVICES",
    "CUDA_DEVICE_ORDER",
    "CUBLAS_WORKSPACE_CONFIG",
    "CUDA_LAUNCH_BLOCKING",
    "PYTORCH_ALLOC_CONF",
    "PYTORCH_CUDA_ALLOC_CONF",
    "CUEQ_TRITON_CACHE_DIR",
    "CUEQ_TRITON_IGNORE_EXISTING_CACHE",
)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _dist_text_hash(dist: importlib.metadata.Distribution, name: str) -> str | None:
    text = dist.read_text(name)
    if text is None:
        return None
    return _sha256_bytes(text.encode("utf-8"))


def _distribution(candidates: Sequence[str]) -> tuple[importlib.metadata.Distribution | None, str | None]:
    for name in candidates:
        try:
            return importlib.metadata.distribution(name), name
        except importlib.metadata.PackageNotFoundError:
            continue
    return None, None


@dataclass(frozen=True, slots=True)
class CueqDep1Policy:
    """Exact dependency target for the first phase-separated CuEq experiment."""

    required_mace_version: str = "0.3.16"
    required_e3nn_version: str = "0.4.4"
    require_cuda: bool = True
    require_oeq: bool = False
    source_inference_kernel_mode: str = "e3nn"
    training_kernel_mode: str = "cueq_pure"
    environment_keys: tuple[str, ...] = _DEFAULT_ENV_KEYS

    def __post_init__(self) -> None:
        if not self.required_mace_version or not self.required_e3nn_version:
            raise TrainingDataInputError("CUEQ-DEP1 MACE/e3nn versions must be non-empty.")
        if self.source_inference_kernel_mode != "e3nn":
            raise TrainingDataInputError("CUEQ-PHASE1 source inference must remain e3nn.")
        if self.training_kernel_mode != "cueq_pure":
            raise TrainingDataInputError("CUEQ-PHASE1 training mode must be cueq_pure.")
        keys = tuple(str(v).strip() for v in self.environment_keys)
        if any(not v for v in keys) or len(set(keys)) != len(keys):
            raise TrainingDataInputError("CUEQ-DEP1 environment keys must be unique and non-empty.")
        object.__setattr__(self, "environment_keys", keys)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_DEP1_POLICY_SCHEMA,
            "required_mace_version": self.required_mace_version,
            "required_e3nn_version": self.required_e3nn_version,
            "require_cuda": bool(self.require_cuda),
            "require_oeq": bool(self.require_oeq),
            "source_inference_kernel_mode": self.source_inference_kernel_mode,
            "training_kernel_mode": self.training_kernel_mode,
            "environment_keys": list(self.environment_keys),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqDep1Policy":
        if payload.get("schema") != CUEQ_DEP1_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-DEP1 policy schema.")
        result = cls(
            required_mace_version=str(payload["required_mace_version"]),
            required_e3nn_version=str(payload["required_e3nn_version"]),
            require_cuda=bool(payload.get("require_cuda", True)),
            require_oeq=bool(payload.get("require_oeq", False)),
            source_inference_kernel_mode=str(payload.get("source_inference_kernel_mode", "e3nn")),
            training_kernel_mode=str(payload.get("training_kernel_mode", "cueq_pure")),
            environment_keys=tuple(str(v) for v in payload.get("environment_keys", _DEFAULT_ENV_KEYS)),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("CUEQ-DEP1 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AcceleratorDistributionEvidence:
    logical_name: str
    import_name: str
    candidate_distributions: tuple[str, ...]
    required: bool
    import_passed: bool
    distribution_name: str | None
    version: str | None
    metadata_sha256: str | None
    record_sha256: str | None
    wheel_sha256: str | None
    direct_url_sha256: str | None
    module_file: str | None
    module_file_sha256: str | None
    error_type: str | None = None
    error_message: str | None = None

    @property
    def content_addressed(self) -> bool:
        # METADATA + RECORD identifies the installed wheel/file inventory.  The
        # imported module byte hash additionally detects an altered import root.
        return bool(self.import_passed and self.metadata_sha256 and self.record_sha256 and self.module_file_sha256)

    @property
    def passed(self) -> bool:
        return bool((not self.required) or self.content_addressed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_DEP1_DISTRIBUTION_SCHEMA,
            "logical_name": self.logical_name,
            "import_name": self.import_name,
            "candidate_distributions": list(self.candidate_distributions),
            "required": self.required,
            "import_passed": self.import_passed,
            "distribution_name": self.distribution_name,
            "version": self.version,
            "metadata_sha256": self.metadata_sha256,
            "record_sha256": self.record_sha256,
            "wheel_sha256": self.wheel_sha256,
            "direct_url_sha256": self.direct_url_sha256,
            "module_file": self.module_file,
            "module_file_sha256": self.module_file_sha256,
            "content_addressed": self.content_addressed,
            "passed": self.passed,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AcceleratorDistributionEvidence":
        if payload.get("schema") != CUEQ_DEP1_DISTRIBUTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-DEP1 distribution schema.")
        result = cls(
            logical_name=str(payload["logical_name"]),
            import_name=str(payload["import_name"]),
            candidate_distributions=tuple(str(v) for v in payload["candidate_distributions"]),
            required=bool(payload["required"]),
            import_passed=bool(payload["import_passed"]),
            distribution_name=None if payload.get("distribution_name") is None else str(payload["distribution_name"]),
            version=None if payload.get("version") is None else str(payload["version"]),
            metadata_sha256=None if payload.get("metadata_sha256") is None else str(payload["metadata_sha256"]),
            record_sha256=None if payload.get("record_sha256") is None else str(payload["record_sha256"]),
            wheel_sha256=None if payload.get("wheel_sha256") is None else str(payload["wheel_sha256"]),
            direct_url_sha256=None if payload.get("direct_url_sha256") is None else str(payload["direct_url_sha256"]),
            module_file=None if payload.get("module_file") is None else str(payload["module_file"]),
            module_file_sha256=None if payload.get("module_file_sha256") is None else str(payload["module_file_sha256"]),
            error_type=None if payload.get("error_type") is None else str(payload["error_type"]),
            error_message=None if payload.get("error_message") is None else str(payload["error_message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-DEP1 distribution digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class AcceleratorDeviceEvidence:
    torch_version: str | None
    torch_cuda_version: str | None
    cuda_available: bool
    cudnn_version: int | None
    deterministic_algorithms: bool | None
    deterministic_debug_mode: int | None
    cudnn_benchmark: bool | None
    cudnn_deterministic: bool | None
    cuda_matmul_allow_tf32: bool | None
    cudnn_allow_tf32: bool | None
    float32_matmul_precision: str | None
    devices: tuple[tuple[int, str, int, int, int], ...]
    nvidia_smi: str | None
    nvcc: str | None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_DEP1_DEVICE_SCHEMA,
            "torch_version": self.torch_version,
            "torch_cuda_version": self.torch_cuda_version,
            "cuda_available": self.cuda_available,
            "cudnn_version": self.cudnn_version,
            "deterministic_algorithms": self.deterministic_algorithms,
            "deterministic_debug_mode": self.deterministic_debug_mode,
            "cudnn_benchmark": self.cudnn_benchmark,
            "cudnn_deterministic": self.cudnn_deterministic,
            "cuda_matmul_allow_tf32": self.cuda_matmul_allow_tf32,
            "cudnn_allow_tf32": self.cudnn_allow_tf32,
            "float32_matmul_precision": self.float32_matmul_precision,
            "devices": [
                {
                    "index": i,
                    "name": name,
                    "compute_capability": [major, minor],
                    "total_memory_bytes": memory,
                }
                for i, name, major, minor, memory in self.devices
            ],
            "nvidia_smi": self.nvidia_smi,
            "nvcc": self.nvcc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "AcceleratorDeviceEvidence":
        if payload.get("schema") != CUEQ_DEP1_DEVICE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-DEP1 device schema.")
        result = cls(
            torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
            torch_cuda_version=None if payload.get("torch_cuda_version") is None else str(payload["torch_cuda_version"]),
            cuda_available=bool(payload["cuda_available"]),
            cudnn_version=None if payload.get("cudnn_version") is None else int(payload["cudnn_version"]),
            deterministic_algorithms=None if payload.get("deterministic_algorithms") is None else bool(payload["deterministic_algorithms"]),
            deterministic_debug_mode=None if payload.get("deterministic_debug_mode") is None else int(payload["deterministic_debug_mode"]),
            cudnn_benchmark=None if payload.get("cudnn_benchmark") is None else bool(payload["cudnn_benchmark"]),
            cudnn_deterministic=None if payload.get("cudnn_deterministic") is None else bool(payload["cudnn_deterministic"]),
            cuda_matmul_allow_tf32=None if payload.get("cuda_matmul_allow_tf32") is None else bool(payload["cuda_matmul_allow_tf32"]),
            cudnn_allow_tf32=None if payload.get("cudnn_allow_tf32") is None else bool(payload["cudnn_allow_tf32"]),
            float32_matmul_precision=None if payload.get("float32_matmul_precision") is None else str(payload["float32_matmul_precision"]),
            devices=tuple(
                (
                    int(v["index"]), str(v["name"]), int(v["compute_capability"][0]),
                    int(v["compute_capability"][1]), int(v["total_memory_bytes"]),
                )
                for v in payload.get("devices", ())
            ),
            nvidia_smi=None if payload.get("nvidia_smi") is None else str(payload["nvidia_smi"]),
            nvcc=None if payload.get("nvcc") is None else str(payload["nvcc"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-DEP1 device digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CueqDep1RuntimeRecord:
    policy: CueqDep1Policy
    python_version: str
    platform: str
    mace_runtime: MaceRuntimeFreezeRecord
    distributions: tuple[AcceleratorDistributionEvidence, ...]
    device: AcceleratorDeviceEvidence
    environment: tuple[tuple[str, str | None], ...]
    qualification_deferred_to_final_gpu: bool = True
    serialization_schema: str = field(default=CUEQ_DEP1_RUNTIME_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != CUEQ_DEP1_RUNTIME_SCHEMA:
            raise TrainingDataInputError("Unsupported CUEQ-DEP1 runtime schema.")
        object.__setattr__(self, "distributions", tuple(self.distributions))
        object.__setattr__(self, "environment", tuple((str(k), None if v is None else str(v)) for k, v in self.environment))
        names = tuple(item.logical_name for item in self.distributions)
        expected = tuple(item[0] for item in CUEQ_DEP1_COMPONENTS)
        if names != expected:
            raise TrainingDataInputError("CUEQ-DEP1 distribution evidence is incomplete or out of order.")

    def _dist(self, name: str) -> AcceleratorDistributionEvidence:
        return next(item for item in self.distributions if item.logical_name == name)

    @property
    def required_stack_content_addressed(self) -> bool:
        required_names = ("torch", "mace", "e3nn", "cueq-core", "cueq-torch", "cueq-ops")
        if self.policy.require_oeq:
            required_names += ("oeq",)
        return all(self._dist(name).content_addressed for name in required_names)

    @property
    def version_contract_passed(self) -> bool:
        return bool(
            self._dist("mace").version == self.policy.required_mace_version
            and self._dist("e3nn").version == self.policy.required_e3nn_version
        )

    @property
    def accelerator_capability_passed(self) -> bool:
        cuda_ok = (not self.policy.require_cuda) or bool(self.device.cuda_available and self.device.devices)
        cueq_ok = all(self._dist(name).import_passed for name in ("cueq-core", "cueq-torch", "cueq-ops"))
        oeq_ok = (not self.policy.require_oeq) or self._dist("oeq").import_passed
        return bool(cuda_ok and cueq_ok and oeq_ok)

    @property
    def passed(self) -> bool:
        return bool(
            self.mace_runtime.core_runtime_passed
            and self.version_contract_passed
            and self.required_stack_content_addressed
            and self.accelerator_capability_passed
        )

    @property
    def blocking_reasons(self) -> tuple[str, ...]:
        reasons: list[str] = []
        if not self.mace_runtime.core_runtime_passed:
            reasons.append("mace_e3nn_runtime_or_source_contract")
        if not self.version_contract_passed:
            reasons.append("mace_e3nn_version_contract")
        for name in ("cueq-core", "cueq-torch", "cueq-ops"):
            item = self._dist(name)
            if not item.import_passed:
                reasons.append(f"{name}_import")
            elif not item.content_addressed:
                reasons.append(f"{name}_content_identity")
        if self.policy.require_oeq:
            item = self._dist("oeq")
            if not item.import_passed:
                reasons.append("oeq_import")
            elif not item.content_addressed:
                reasons.append("oeq_content_identity")
        if self.policy.require_cuda and not self.device.cuda_available:
            reasons.append("torch_cuda_available")
        if self.policy.require_cuda and not self.device.devices:
            reasons.append("cuda_device_inventory")
        return tuple(dict.fromkeys(reasons))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CUEQ_DEP1_RUNTIME_SCHEMA,
            "policy": self.policy.to_dict(),
            "python_version": self.python_version,
            "platform": self.platform,
            "mace_runtime": self.mace_runtime.to_dict(),
            "distributions": [item.to_dict() for item in self.distributions],
            "device": self.device.to_dict(),
            "environment": [[k, v] for k, v in self.environment],
            "qualification_deferred_to_final_gpu": self.qualification_deferred_to_final_gpu,
            "required_stack_content_addressed": self.required_stack_content_addressed,
            "version_contract_passed": self.version_contract_passed,
            "accelerator_capability_passed": self.accelerator_capability_passed,
            "passed": self.passed,
            "blocking_reasons": list(self.blocking_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CueqDep1RuntimeRecord":
        if payload.get("schema") != CUEQ_DEP1_RUNTIME_SCHEMA:
            raise TrainingDataSerializationError("Unsupported CUEQ-DEP1 runtime schema.")
        result = cls(
            policy=CueqDep1Policy.from_dict(payload["policy"]),
            python_version=str(payload["python_version"]),
            platform=str(payload["platform"]),
            mace_runtime=MaceRuntimeFreezeRecord.from_dict(payload["mace_runtime"]),
            distributions=tuple(AcceleratorDistributionEvidence.from_dict(v) for v in payload["distributions"]),
            device=AcceleratorDeviceEvidence.from_dict(payload["device"]),
            environment=tuple((str(v[0]), None if v[1] is None else str(v[1])) for v in payload.get("environment", ())),
            qualification_deferred_to_final_gpu=bool(payload.get("qualification_deferred_to_final_gpu", True)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CUEQ-DEP1 runtime digest mismatch.")
        return result


def _probe_distribution(
    logical_name: str,
    import_name: str,
    candidates: tuple[str, ...],
    *,
    required: bool,
) -> AcceleratorDistributionEvidence:
    module = None
    error_type = None
    error_message = None
    try:
        module = importlib.import_module(import_name)
    except Exception as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
    dist, dist_name = _distribution(candidates)
    version = None if dist is None else str(dist.version)
    metadata_sha = None if dist is None else _dist_text_hash(dist, "METADATA")
    record_sha = None if dist is None else _dist_text_hash(dist, "RECORD")
    wheel_sha = None if dist is None else _dist_text_hash(dist, "WHEEL")
    direct_sha = None if dist is None else _dist_text_hash(dist, "direct_url.json")
    module_file = None
    module_file_sha = None
    if module is not None:
        raw_file = getattr(module, "__file__", None)
        if raw_file:
            path = Path(raw_file).resolve()
            module_file = str(path)
            if path.is_file():
                h = hashlib.sha256()
                with path.open("rb") as handle:
                    for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
                        h.update(block)
                module_file_sha = h.hexdigest()
    return AcceleratorDistributionEvidence(
        logical_name=logical_name,
        import_name=import_name,
        candidate_distributions=candidates,
        required=required,
        import_passed=module is not None,
        distribution_name=dist_name,
        version=version,
        metadata_sha256=metadata_sha,
        record_sha256=record_sha,
        wheel_sha256=wheel_sha,
        direct_url_sha256=direct_sha,
        module_file=module_file,
        module_file_sha256=module_file_sha,
        error_type=error_type,
        error_message=error_message,
    )


def _command_text(command: Sequence[str]) -> str | None:
    try:
        completed = subprocess.run(command, check=False, capture_output=True, text=True, timeout=15)
    except Exception:
        return None
    text = (completed.stdout + "\n" + completed.stderr).strip()
    if not text:
        return f"returncode={completed.returncode}"
    return f"returncode={completed.returncode}\n{text}"


def _device_evidence() -> AcceleratorDeviceEvidence:
    torch_version = None
    torch_cuda_version = None
    cuda_available = False
    cudnn_version = None
    deterministic_algorithms = None
    deterministic_debug_mode = None
    cudnn_benchmark = None
    cudnn_deterministic = None
    cuda_matmul_allow_tf32 = None
    cudnn_allow_tf32 = None
    float32_matmul_precision = None
    devices: list[tuple[int, str, int, int, int]] = []
    try:
        import torch

        torch_version = str(torch.__version__)
        torch_cuda_version = None if torch.version.cuda is None else str(torch.version.cuda)
        cuda_available = bool(torch.cuda.is_available())
        try:
            deterministic_algorithms = bool(torch.are_deterministic_algorithms_enabled())
            deterministic_debug_mode = int(torch.get_deterministic_debug_mode())
        except Exception:
            pass
        try:
            cudnn_benchmark = bool(torch.backends.cudnn.benchmark)
            cudnn_deterministic = bool(torch.backends.cudnn.deterministic)
            cudnn_allow_tf32 = bool(torch.backends.cudnn.allow_tf32)
        except Exception:
            pass
        try:
            cuda_matmul_allow_tf32 = bool(torch.backends.cuda.matmul.allow_tf32)
        except Exception:
            pass
        try:
            float32_matmul_precision = str(torch.get_float32_matmul_precision())
        except Exception:
            pass
        try:
            raw_cudnn = torch.backends.cudnn.version()
            cudnn_version = None if raw_cudnn is None else int(raw_cudnn)
        except Exception:
            cudnn_version = None
        if cuda_available:
            for index in range(int(torch.cuda.device_count())):
                props = torch.cuda.get_device_properties(index)
                devices.append((index, str(props.name), int(props.major), int(props.minor), int(props.total_memory)))
    except Exception:
        pass
    smi = shutil.which("nvidia-smi")
    nvcc = shutil.which("nvcc")
    return AcceleratorDeviceEvidence(
        torch_version=torch_version,
        torch_cuda_version=torch_cuda_version,
        cuda_available=cuda_available,
        cudnn_version=cudnn_version,
        deterministic_algorithms=deterministic_algorithms,
        deterministic_debug_mode=deterministic_debug_mode,
        cudnn_benchmark=cudnn_benchmark,
        cudnn_deterministic=cudnn_deterministic,
        cuda_matmul_allow_tf32=cuda_matmul_allow_tf32,
        cudnn_allow_tf32=cudnn_allow_tf32,
        float32_matmul_precision=float32_matmul_precision,
        devices=tuple(devices),
        nvidia_smi=None if smi is None else _command_text((smi, "-q")),
        nvcc=None if nvcc is None else _command_text((nvcc, "--version")),
    )


def capture_cueq_dep1_runtime(
    *,
    policy: CueqDep1Policy | None = None,
    supplied_artifacts: Sequence[str | Path] = (),
) -> CueqDep1RuntimeRecord:
    """Capture the exact accelerator dependency/runtime state without fallback.

    A CPU-only or CuEq-missing host returns a valid negative record.  Such a
    record is evidence that CUEQ-DEP1 is not yet qualified, never a pass.
    """

    active = CueqDep1Policy() if policy is None else policy
    mace_policy = MaceRuntimeFreezePolicy(
        required_mace_version=active.required_mace_version,
        required_e3nn_version=active.required_e3nn_version,
        require_cueq_stack=False,
        require_oeq=False,
    )
    mace_runtime = probe_mace_runtime_freeze(
        policy=mace_policy,
        checkpoint_requests=(),
        supplied_artifacts=supplied_artifacts,
    )
    distributions = []
    for logical_name, import_name, candidates in CUEQ_DEP1_COMPONENTS:
        required = logical_name != "oeq" or active.require_oeq
        distributions.append(_probe_distribution(logical_name, import_name, candidates, required=required))
    environment = tuple((name, os.environ.get(name)) for name in active.environment_keys)
    return CueqDep1RuntimeRecord(
        policy=active,
        python_version=platform.python_version(),
        platform=platform.platform(),
        mace_runtime=mace_runtime,
        distributions=tuple(distributions),
        device=_device_evidence(),
        environment=environment,
        qualification_deferred_to_final_gpu=True,
    )


def write_cueq_dep1_runtime(path: str | Path, record: CueqDep1RuntimeRecord) -> Path:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(record.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination
