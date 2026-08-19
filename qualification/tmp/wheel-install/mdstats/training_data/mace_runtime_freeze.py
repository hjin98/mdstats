"""Version-locked MACE runtime/dependency evidence for generalized foundations.

MH1-DEP0 freezes the *runtime* before the foundation identity and campaign
configuration are generalized.  This module intentionally does not choose a
foundation model, head, or acceleration backend.  It records what the current
interpreter can actually support, independently probes cuEquivariance and
OpenEquivariance, verifies the exact MACE 0.3.16 source files used by the MLFF
adapter, and can prove that explicitly supplied foundation checkpoints load
through the ordinary e3nn calculator path.

The record is fail-closed evidence.  It never mutates a campaign policy and it
never substitutes e3nn for a requested accelerator.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import importlib
import importlib.metadata
import inspect
from pathlib import Path
import platform
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)
from .mace_compatibility import mace_runtime_warning_handled, probe_mace_source_tree


MACE_RUNTIME_FREEZE_POLICY_SCHEMA = "mdstats.mace-runtime-freeze-policy.v1"
MACE_RUNTIME_COMPONENT_CAPABILITY_SCHEMA = "mdstats.mace-runtime-component-capability.v1"
MACE_RUNTIME_SOURCE_EVIDENCE_SCHEMA = "mdstats.mace-runtime-source-evidence.v1"
MACE_RUNTIME_CHECKPOINT_LOAD_SCHEMA = "mdstats.mace-runtime-checkpoint-load.v1"
MACE_RUNTIME_FREEZE_RECORD_SCHEMA = "mdstats.mace-runtime-freeze-record.v2"
MACE_RUNTIME_FREEZE_RECORD_LEGACY_SCHEMA = "mdstats.mace-runtime-freeze-record.v1"

# Exact source shipped by mace-torch 0.3.16 in the supplied/official sdist.
# These files cover the fixed-file trainer, selected-head reconstruction,
# calculator acceleration interface, argument parser, and the CuEq/OEq
# conversion paths required by the MH-1 revision.
MACE_V0316_RUNTIME_SOURCE_LOCK: tuple[tuple[str, str], ...] = (
    ("mace/cli/run_train.py", "4f219fce454279b54cb7a10af30e8e8508cb7b83b3ffa6981ed89dbe7dc8de8b"),
    ("mace/tools/train.py", "ca700fa6685e75124ca725d83b2fa55303c0803c48a2ac0c4b543f8f63aa4dfc"),
    ("mace/tools/multihead_tools.py", "a8b0d86bc314c8587e9140afe147553dcae7c4691f049c7d409e815854d9412f"),
    ("mace/tools/scripts_utils.py", "de6b33ef2fc59e32408f0436d15a135ad0c63df3d23feeef8cc23e4a1b86bdb1"),
    ("mace/calculators/mace.py", "97b17cef8d5880071068d1a05a97f1d432ffc57db00d23ba86c2c3049114a8ad"),
    ("mace/tools/arg_parser.py", "9e583bbadc58492861655932c2dc71a069731eece3946ebc681e43f628149d86"),
    ("mace/cli/convert_e3nn_hybrid.py", "11f7f601734182d00ce7cb21aa0c4efc096bad7341c0bdcbd211018ead731f20"),
    ("mace/cli/convert_e3nn_oeq.py", "42511f11713e3b9b2569b78649da39ad4eadd676793666f3024c5222f06db7e9"),
)

_CUEQ_COMPONENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
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
)
_OEQ_COMPONENTS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("oeq", "openequivariance", ("openequivariance", "OpenEquivariance")),
)


def _distribution_version(candidates: Sequence[str], module: Any | None = None) -> tuple[str | None, str | None]:
    if module is not None:
        module_version = getattr(module, "__version__", None)
    else:
        module_version = None
    for name in candidates:
        try:
            return name, str(importlib.metadata.version(name))
        except importlib.metadata.PackageNotFoundError:
            continue
    return None, None if module_version is None else str(module_version)


@dataclass(frozen=True, slots=True)
class MaceRuntimeFreezePolicy:
    """Immutable dependency/source target for the generalized-MACE revision."""

    required_mace_version: str = "0.3.16"
    required_e3nn_version: str = "0.4.4"
    require_cueq_stack: bool = True
    require_oeq: bool = False
    source_lock: tuple[tuple[str, str], ...] = MACE_V0316_RUNTIME_SOURCE_LOCK

    def __post_init__(self) -> None:
        if not self.required_mace_version.strip() or not self.required_e3nn_version.strip():
            raise TrainingDataInputError("MACE/e3nn runtime-freeze versions must be non-empty.")
        normalized = []
        seen: set[str] = set()
        for relative_path, expected_sha256 in self.source_lock:
            path = str(relative_path).replace("\\", "/").strip("/")
            if not path or path in seen:
                raise TrainingDataInputError("MACE runtime source lock contains an empty/duplicate path.")
            seen.add(path)
            normalized.append((path, validate_digest(expected_sha256, name=f"source_lock:{path}")))
        object.__setattr__(self, "source_lock", tuple(normalized))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_RUNTIME_FREEZE_POLICY_SCHEMA,
            "required_mace_version": self.required_mace_version,
            "required_e3nn_version": self.required_e3nn_version,
            "require_cueq_stack": bool(self.require_cueq_stack),
            "require_oeq": bool(self.require_oeq),
            "source_lock": [list(v) for v in self.source_lock],
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeFreezePolicy":
        if payload.get("schema") != MACE_RUNTIME_FREEZE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE runtime-freeze policy schema.")
        result = cls(
            required_mace_version=str(payload["required_mace_version"]),
            required_e3nn_version=str(payload["required_e3nn_version"]),
            require_cueq_stack=bool(payload.get("require_cueq_stack", True)),
            require_oeq=bool(payload.get("require_oeq", False)),
            source_lock=tuple((str(v[0]), str(v[1])) for v in payload["source_lock"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MACE runtime-freeze policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceRuntimeComponentCapability:
    logical_name: str
    import_name: str
    candidate_distributions: tuple[str, ...]
    import_passed: bool
    installed_distribution: str | None
    version: str | None
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not self.logical_name.strip() or not self.import_name.strip():
            raise TrainingDataInputError("Runtime component names must be non-empty.")
        candidates = tuple(str(v) for v in self.candidate_distributions)
        if not candidates:
            raise TrainingDataInputError("Runtime component must declare a distribution candidate.")
        object.__setattr__(self, "candidate_distributions", candidates)
        if self.import_passed and self.error_type is not None:
            raise TrainingDataInputError("Passing runtime component cannot carry an import error.")

    @property
    def available(self) -> bool:
        return bool(self.import_passed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_RUNTIME_COMPONENT_CAPABILITY_SCHEMA,
            "logical_name": self.logical_name,
            "import_name": self.import_name,
            "candidate_distributions": list(self.candidate_distributions),
            "import_passed": bool(self.import_passed),
            "installed_distribution": self.installed_distribution,
            "version": self.version,
            "available": self.available,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeComponentCapability":
        if payload.get("schema") != MACE_RUNTIME_COMPONENT_CAPABILITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported runtime-component capability schema.")
        result = cls(
            logical_name=str(payload["logical_name"]),
            import_name=str(payload["import_name"]),
            candidate_distributions=tuple(str(v) for v in payload["candidate_distributions"]),
            import_passed=bool(payload["import_passed"]),
            installed_distribution=None if payload.get("installed_distribution") is None else str(payload["installed_distribution"]),
            version=None if payload.get("version") is None else str(payload["version"]),
            error_type=None if payload.get("error_type") is None else str(payload["error_type"]),
            error_message=None if payload.get("error_message") is None else str(payload["error_message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Runtime-component capability digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceRuntimeSourceEvidence:
    relative_path: str
    expected_sha256: str
    observed_sha256: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "relative_path", self.relative_path.replace("\\", "/").strip("/"))
        object.__setattr__(self, "expected_sha256", validate_digest(self.expected_sha256, name="expected_sha256"))
        if self.observed_sha256 is not None:
            object.__setattr__(self, "observed_sha256", validate_digest(self.observed_sha256, name="observed_sha256"))

    @property
    def matched(self) -> bool:
        return self.observed_sha256 == self.expected_sha256

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_RUNTIME_SOURCE_EVIDENCE_SCHEMA,
            "relative_path": self.relative_path,
            "expected_sha256": self.expected_sha256,
            "observed_sha256": self.observed_sha256,
            "matched": self.matched,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeSourceEvidence":
        if payload.get("schema") != MACE_RUNTIME_SOURCE_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MACE runtime-source evidence schema.")
        result = cls(
            relative_path=str(payload["relative_path"]),
            expected_sha256=str(payload["expected_sha256"]),
            observed_sha256=None if payload.get("observed_sha256") is None else str(payload["observed_sha256"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE runtime-source evidence digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceRuntimeCheckpointLoadEvidence:
    checkpoint_path: str
    checkpoint_sha256: str
    requested_head: str | None
    torch_load_passed: bool
    e3nn_calculator_load_passed: bool
    model_class: str | None
    available_heads: tuple[str, ...]
    error_type: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "checkpoint_sha256", validate_digest(self.checkpoint_sha256, name="checkpoint_sha256"))
        object.__setattr__(self, "available_heads", tuple(str(v) for v in self.available_heads))
        if self.e3nn_calculator_load_passed and not self.torch_load_passed:
            raise TrainingDataInputError("e3nn calculator load cannot pass when direct Torch load failed.")

    @property
    def passed(self) -> bool:
        return bool(self.torch_load_passed and self.e3nn_calculator_load_passed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_RUNTIME_CHECKPOINT_LOAD_SCHEMA,
            "checkpoint_path": self.checkpoint_path,
            "checkpoint_sha256": self.checkpoint_sha256,
            "requested_head": self.requested_head,
            "torch_load_passed": self.torch_load_passed,
            "e3nn_calculator_load_passed": self.e3nn_calculator_load_passed,
            "model_class": self.model_class,
            "available_heads": list(self.available_heads),
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeCheckpointLoadEvidence":
        if payload.get("schema") != MACE_RUNTIME_CHECKPOINT_LOAD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported runtime checkpoint-load schema.")
        result = cls(
            checkpoint_path=str(payload["checkpoint_path"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            requested_head=None if payload.get("requested_head") is None else str(payload["requested_head"]),
            torch_load_passed=bool(payload["torch_load_passed"]),
            e3nn_calculator_load_passed=bool(payload["e3nn_calculator_load_passed"]),
            model_class=None if payload.get("model_class") is None else str(payload["model_class"]),
            available_heads=tuple(str(v) for v in payload.get("available_heads", ())),
            error_type=None if payload.get("error_type") is None else str(payload["error_type"]),
            error_message=None if payload.get("error_message") is None else str(payload["error_message"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Runtime checkpoint-load digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceRuntimeFreezeRecord:
    policy: MaceRuntimeFreezePolicy
    python_version: str
    platform: str
    torch_version: str | None
    torch_cuda_version: str | None
    cuda_available: bool
    mace_version: str | None
    e3nn_version: str | None
    calculator_enable_cueq_supported: bool
    calculator_enable_oeq_supported: bool
    training_enable_cueq_supported: bool
    training_enable_oeq_supported: bool
    source_evidence: tuple[MaceRuntimeSourceEvidence, ...]
    component_capabilities: tuple[MaceRuntimeComponentCapability, ...]
    supplied_artifacts: tuple[tuple[str, str], ...] = ()
    checkpoint_loads: tuple[MaceRuntimeCheckpointLoadEvidence, ...] = ()
    blocking_error_type: str | None = None
    blocking_error_message: str | None = None
    semantic_source_compatibility_passed: bool = False
    semantic_source_compatibility_notes: tuple[str, ...] = ()
    serialization_schema: str = field(
        default=MACE_RUNTIME_FREEZE_RECORD_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_evidence", tuple(self.source_evidence))
        object.__setattr__(self, "component_capabilities", tuple(self.component_capabilities))
        object.__setattr__(
            self,
            "supplied_artifacts",
            tuple((str(name), validate_digest(value, name=f"supplied_artifact:{name}")) for name, value in self.supplied_artifacts),
        )
        object.__setattr__(self, "checkpoint_loads", tuple(self.checkpoint_loads))
        object.__setattr__(
            self, "semantic_source_compatibility_notes",
            tuple(str(v) for v in self.semantic_source_compatibility_notes),
        )
        if self.serialization_schema not in {
            MACE_RUNTIME_FREEZE_RECORD_SCHEMA, MACE_RUNTIME_FREEZE_RECORD_LEGACY_SCHEMA
        }:
            raise TrainingDataInputError("Unsupported internal MACE runtime-freeze serialization schema.")
        expected_paths = tuple(path for path, _ in self.policy.source_lock)
        observed_paths = tuple(item.relative_path for item in self.source_evidence)
        if observed_paths != expected_paths:
            raise TrainingDataInputError("Runtime-freeze source evidence does not follow the policy source-lock order.")

    @property
    def source_lock_passed(self) -> bool:
        return bool(self.source_evidence) and all(item.matched for item in self.source_evidence)

    @property
    def source_compatibility_passed(self) -> bool:
        """Accept the exact byte lock or a positive semantic compatibility probe.

        The byte lock remains the strongest reproducibility evidence, but installed
        0.3.16 wheels/source trees can differ in non-semantic bytes.  Such a runtime
        is authorized only when the required MACE source behaviors are positively
        re-probed; version equality alone is never enough.
        """

        return bool(self.source_lock_passed or self.semantic_source_compatibility_passed)

    def _component(self, logical_name: str) -> MaceRuntimeComponentCapability | None:
        return next((item for item in self.component_capabilities if item.logical_name == logical_name), None)

    @property
    def cueq_stack_available(self) -> bool:
        components = [self._component(name) for name, _, _ in _CUEQ_COMPONENTS]
        return bool(
            all(item is not None and item.available for item in components)
            and self.calculator_enable_cueq_supported
            and self.training_enable_cueq_supported
        )

    @property
    def oeq_available(self) -> bool:
        component = self._component("oeq")
        return bool(
            component is not None
            and component.available
            and self.calculator_enable_oeq_supported
            and self.training_enable_oeq_supported
        )

    @property
    def core_runtime_passed(self) -> bool:
        return bool(
            self.blocking_error_type is None
            and self.mace_version == self.policy.required_mace_version
            and self.e3nn_version == self.policy.required_e3nn_version
            and self.source_compatibility_passed
        )

    @property
    def checkpoints_passed(self) -> bool:
        # DEP0 qualification is only complete when an explicit real-checkpoint
        # load request was recorded; an empty tuple is not affirmative evidence.
        return bool(self.checkpoint_loads) and all(item.passed for item in self.checkpoint_loads)

    @property
    def dependency_target_passed(self) -> bool:
        return bool(
            self.core_runtime_passed
            and (not self.policy.require_cueq_stack or self.cueq_stack_available)
            and (not self.policy.require_oeq or self.oeq_available)
        )

    @property
    def qualified_for_mh1_dep0(self) -> bool:
        return bool(self.dependency_target_passed and self.checkpoints_passed)

    def passed_for_backend(self, backend: str) -> bool:
        """Return dependency-gate capability for an explicit public backend.

        This method never resolves or substitutes a backend.  Pure CuEq is a
        complete training/inference implementation under MACE 0.3.16; OEq is an
        optional capability used only when hybrid inference is actually selected.
        """

        normalized = str(backend).strip().lower()
        if normalized == "e3nn":
            return self.core_runtime_passed
        if normalized == "cueq":
            return bool(
                self.core_runtime_passed
                and self.cueq_stack_available
                and (not self.policy.require_oeq or self.oeq_available)
            )
        raise TrainingDataInputError(f"Unsupported runtime-freeze backend: {backend!r}")

    def backend_failure_reasons(self, backend: str) -> tuple[str, ...]:
        normalized = str(backend).strip().lower()
        if normalized not in {"e3nn", "cueq"}:
            raise TrainingDataInputError(f"Unsupported runtime-freeze backend: {backend!r}")
        reasons: list[str] = []
        if self.mace_version != self.policy.required_mace_version:
            reasons.append(
                f"mace-torch=={self.policy.required_mace_version} required; observed {self.mace_version or 'unavailable'}"
            )
        if self.e3nn_version != self.policy.required_e3nn_version:
            reasons.append(
                f"e3nn=={self.policy.required_e3nn_version} required; observed {self.e3nn_version or 'unavailable'}"
            )
        if not self.source_compatibility_passed:
            reasons.append(
                "MACE 0.3.16 source compatibility failed (exact byte lock and semantic probe)"
            )
            reasons.extend(
                f"MACE semantic source probe: {note}"
                for note in self.semantic_source_compatibility_notes
            )
        if self.blocking_error_type is not None:
            reasons.append(f"{self.blocking_error_type}: {self.blocking_error_message or 'runtime import failed'}")
        if normalized == "cueq":
            if not self.cueq_stack_available:
                reasons.append("cuEquivariance core/torch/ops capability is incomplete")
            if self.policy.require_oeq and not self.oeq_available:
                reasons.append(
                    "OpenEquivariance capability is unavailable"
                    if self.serialization_schema == MACE_RUNTIME_FREEZE_RECORD_LEGACY_SCHEMA
                    else "OpenEquivariance capability is unavailable but is required by policy"
                )
        return tuple(reasons)

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "policy": self.policy.to_dict(),
            "python_version": self.python_version,
            "platform": self.platform,
            "torch_version": self.torch_version,
            "torch_cuda_version": self.torch_cuda_version,
            "cuda_available": self.cuda_available,
            "mace_version": self.mace_version,
            "e3nn_version": self.e3nn_version,
            "calculator_enable_cueq_supported": self.calculator_enable_cueq_supported,
            "calculator_enable_oeq_supported": self.calculator_enable_oeq_supported,
            "training_enable_cueq_supported": self.training_enable_cueq_supported,
            "training_enable_oeq_supported": self.training_enable_oeq_supported,
            "source_evidence": [item.to_dict() for item in self.source_evidence],
            "component_capabilities": [item.to_dict() for item in self.component_capabilities],
            "supplied_artifacts": [list(v) for v in self.supplied_artifacts],
            "checkpoint_loads": [item.to_dict() for item in self.checkpoint_loads],
            "blocking_error_type": self.blocking_error_type,
            "blocking_error_message": self.blocking_error_message,
            "source_lock_passed": self.source_lock_passed,
            "cueq_stack_available": self.cueq_stack_available,
            "oeq_available": self.oeq_available,
            "core_runtime_passed": self.core_runtime_passed,
            "checkpoints_passed": self.checkpoints_passed,
            "dependency_target_passed": self.dependency_target_passed,
            "qualified_for_mh1_dep0": self.qualified_for_mh1_dep0,
            "e3nn_backend_capability_passed": self.passed_for_backend("e3nn"),
            "cueq_backend_capability_passed": self.passed_for_backend("cueq"),
            "e3nn_backend_failure_reasons": list(self.backend_failure_reasons("e3nn")),
            "cueq_backend_failure_reasons": list(self.backend_failure_reasons("cueq")),
        }
        if self.serialization_schema == MACE_RUNTIME_FREEZE_RECORD_SCHEMA:
            payload.update({
                "semantic_source_compatibility_passed": bool(self.semantic_source_compatibility_passed),
                "semantic_source_compatibility_notes": list(self.semantic_source_compatibility_notes),
                "source_compatibility_passed": bool(self.source_compatibility_passed),
            })
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceRuntimeFreezeRecord":
        schema = payload.get("schema")
        if schema not in {MACE_RUNTIME_FREEZE_RECORD_SCHEMA, MACE_RUNTIME_FREEZE_RECORD_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported MACE runtime-freeze record schema.")
        result = cls(
            policy=MaceRuntimeFreezePolicy.from_dict(payload["policy"]),
            python_version=str(payload["python_version"]),
            platform=str(payload["platform"]),
            torch_version=None if payload.get("torch_version") is None else str(payload["torch_version"]),
            torch_cuda_version=None if payload.get("torch_cuda_version") is None else str(payload["torch_cuda_version"]),
            cuda_available=bool(payload["cuda_available"]),
            mace_version=None if payload.get("mace_version") is None else str(payload["mace_version"]),
            e3nn_version=None if payload.get("e3nn_version") is None else str(payload["e3nn_version"]),
            calculator_enable_cueq_supported=bool(payload["calculator_enable_cueq_supported"]),
            calculator_enable_oeq_supported=bool(payload["calculator_enable_oeq_supported"]),
            training_enable_cueq_supported=bool(payload["training_enable_cueq_supported"]),
            training_enable_oeq_supported=bool(payload["training_enable_oeq_supported"]),
            source_evidence=tuple(MaceRuntimeSourceEvidence.from_dict(v) for v in payload["source_evidence"]),
            component_capabilities=tuple(MaceRuntimeComponentCapability.from_dict(v) for v in payload["component_capabilities"]),
            supplied_artifacts=tuple((str(v[0]), str(v[1])) for v in payload.get("supplied_artifacts", ())),
            checkpoint_loads=tuple(MaceRuntimeCheckpointLoadEvidence.from_dict(v) for v in payload.get("checkpoint_loads", ())),
            blocking_error_type=None if payload.get("blocking_error_type") is None else str(payload["blocking_error_type"]),
            blocking_error_message=None if payload.get("blocking_error_message") is None else str(payload["blocking_error_message"]),
            semantic_source_compatibility_passed=bool(payload.get("semantic_source_compatibility_passed", False)),
            semantic_source_compatibility_notes=tuple(str(v) for v in payload.get("semantic_source_compatibility_notes", ())),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MACE runtime-freeze record digest mismatch.")
        return result


def _probe_component(logical_name: str, import_name: str, distributions: tuple[str, ...]) -> MaceRuntimeComponentCapability:
    try:
        module = importlib.import_module(import_name)
        installed_distribution, version = _distribution_version(distributions, module)
        return MaceRuntimeComponentCapability(
            logical_name=logical_name,
            import_name=import_name,
            candidate_distributions=distributions,
            import_passed=True,
            installed_distribution=installed_distribution,
            version=version,
        )
    except Exception as exc:
        installed_distribution, version = _distribution_version(distributions, None)
        return MaceRuntimeComponentCapability(
            logical_name=logical_name,
            import_name=import_name,
            candidate_distributions=distributions,
            import_passed=False,
            installed_distribution=installed_distribution,
            version=version,
            error_type=type(exc).__name__,
            error_message=str(exc),
        )


def _sha256_optional(path: Path) -> str | None:
    return sha256_file_cached(path) if path.is_file() else None


def _mace_source_root(mace_module: Any) -> Path | None:
    module_file = getattr(mace_module, "__file__", None)
    if module_file is None:
        return None
    package = Path(module_file).resolve().parent
    return package.parent


def _probe_mace_source_semantics(source_root: Path | None) -> tuple[bool, tuple[str, ...]]:
    """Verify the MACE behaviors mdstats relies on when byte hashes differ.

    This is intentionally stricter than a version check and intentionally
    narrower than an exact source-tree lock.  Later EXTRACT1/ACCEL1 gates still
    perform real-model numerical qualification.
    """

    if source_root is None:
        return False, ("MACE package source root is unavailable",)
    notes: list[str] = []
    try:
        fixed_file = probe_mace_source_tree(source_root)
        if not fixed_file.fixed_file_adapter_supported:
            notes.append("fixed-file DATA8 source semantics failed")
    except Exception as exc:
        return False, (f"fixed-file source semantic probe failed: {type(exc).__name__}: {exc}",)

    required_text_checks = (
        (source_root / "mace" / "tools" / "scripts_utils.py", ("def remove_pt_head", "def extract_config_mace_model")),
        (source_root / "mace" / "tools" / "arg_parser.py", ("--foundation_head", "--enable_cueq")),
        (source_root / "mace" / "cli" / "run_train.py", ("remove_pt_head", "foundation_head")),
    )
    for path, needles in required_text_checks:
        if not path.is_file():
            notes.append(f"required MACE source file is missing: {path.name}")
            continue
        text = path.read_text(encoding="utf-8")
        missing = tuple(needle for needle in needles if needle not in text)
        if missing:
            notes.append(f"{path.name} is missing required semantics: {missing}")
    if notes:
        return False, tuple(notes)
    return True, (
        "Exact MACE byte lock differs, but fixed-file training, selected-head, and CuEq CLI semantics passed.",
    )


def _checkpoint_load_evidence(
    path: str | Path,
    requested_head: str | None,
    *,
    MACECalculator: Any,
) -> MaceRuntimeCheckpointLoadEvidence:
    source = Path(path).resolve()
    if not source.is_file():
        raise TrainingDataInputError(f"Runtime-freeze checkpoint does not exist: {source}")
    checkpoint_sha256 = sha256_file_cached(source)
    torch_load_passed = False
    calculator_load_passed = False
    model_class: str | None = None
    heads: tuple[str, ...] = ()
    error_type: str | None = None
    error_message: str | None = None
    try:
        import torch

        model = torch.load(source, map_location="cpu", weights_only=False)
        torch_load_passed = True
        model_class = type(model).__name__
        heads = tuple(str(v) for v in getattr(model, "heads", ("default",)))
        del model
        kwargs: dict[str, Any] = {}
        if requested_head is not None:
            if requested_head not in heads:
                raise TrainingDataInputError(
                    f"Requested checkpoint head {requested_head!r} is absent; available heads={list(heads)}"
                )
            kwargs["head"] = requested_head
        calculator = MACECalculator(
            model_paths=str(source),
            device="cpu",
            default_dtype="",
            enable_cueq=False,
            enable_oeq=False,
            **kwargs,
        )
        calculator_load_passed = True
        del calculator
    except Exception as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
    return MaceRuntimeCheckpointLoadEvidence(
        checkpoint_path=str(source),
        checkpoint_sha256=checkpoint_sha256,
        requested_head=requested_head,
        torch_load_passed=torch_load_passed,
        e3nn_calculator_load_passed=calculator_load_passed,
        model_class=model_class,
        available_heads=heads,
        error_type=error_type,
        error_message=error_message,
    )


@mace_runtime_warning_handled("MACE runtime dependency freeze")
def probe_mace_runtime_freeze(
    *,
    policy: MaceRuntimeFreezePolicy | None = None,
    checkpoint_requests: Sequence[tuple[str | Path, str | None]] = (),
    supplied_artifacts: Sequence[str | Path] = (),
) -> MaceRuntimeFreezeRecord:
    """Record exact MACE/e3nn/CuEq/OEq capabilities without changing policy.

    ``checkpoint_requests`` contains ``(path, requested_head)`` pairs.  Each is
    loaded twice: directly through Torch for serialized-object viability and
    through ``MACECalculator(enable_cueq=False, enable_oeq=False)`` to prove the
    ordinary e3nn reference path.  ``supplied_artifacts`` are content-addressed
    into the record (for example the offline dependency archive).  No
    energy/force evaluation is performed in this dependency gate.
    """

    active = MaceRuntimeFreezePolicy() if policy is None else policy
    torch_version: str | None = None
    torch_cuda_version: str | None = None
    cuda_available = False
    mace_version: str | None = None
    e3nn_version: str | None = None
    calculator_enable_cueq_supported = False
    calculator_enable_oeq_supported = False
    training_enable_cueq_supported = False
    training_enable_oeq_supported = False
    blocking_error_type: str | None = None
    blocking_error_message: str | None = None
    semantic_source_compatibility_passed = False
    semantic_source_compatibility_notes: tuple[str, ...] = ()
    source_root: Path | None = None
    MACECalculator: Any | None = None

    try:
        import torch

        torch_version = str(torch.__version__)
        torch_cuda_version = None if torch.version.cuda is None else str(torch.version.cuda)
        cuda_available = bool(torch.cuda.is_available())

        import e3nn
        import mace
        from mace.calculators import MACECalculator as _MACECalculator

        MACECalculator = _MACECalculator
        raw_mace_version = getattr(mace, "__version__", None)
        if raw_mace_version is None:
            raw_mace_version = importlib.metadata.version("mace-torch")
        raw_e3nn_version = getattr(e3nn, "__version__", None)
        if raw_e3nn_version is None:
            raw_e3nn_version = importlib.metadata.version("e3nn")
        mace_version = str(raw_mace_version)
        e3nn_version = str(raw_e3nn_version)
        signature = inspect.signature(_MACECalculator.__init__)
        calculator_enable_cueq_supported = "enable_cueq" in signature.parameters
        calculator_enable_oeq_supported = "enable_oeq" in signature.parameters
        source_root = _mace_source_root(mace)
        if source_root is not None:
            arg_parser = source_root / "mace" / "tools" / "arg_parser.py"
            if arg_parser.is_file():
                text = arg_parser.read_text(encoding="utf-8")
                training_enable_cueq_supported = '"--enable_cueq"' in text or "'--enable_cueq'" in text
                training_enable_oeq_supported = '"--enable_oeq"' in text or "'--enable_oeq'" in text
    except Exception as exc:
        blocking_error_type = type(exc).__name__
        blocking_error_message = str(exc)

    if blocking_error_type is None:
        semantic_source_compatibility_passed, semantic_source_compatibility_notes = (
            _probe_mace_source_semantics(source_root)
        )

    source_evidence = []
    for relative_path, expected_sha256 in active.source_lock:
        observed = None if source_root is None else _sha256_optional(source_root / relative_path)
        source_evidence.append(
            MaceRuntimeSourceEvidence(
                relative_path=relative_path,
                expected_sha256=expected_sha256,
                observed_sha256=observed,
            )
        )

    capabilities = tuple(
        _probe_component(logical_name, import_name, distributions)
        for logical_name, import_name, distributions in (*_CUEQ_COMPONENTS, *_OEQ_COMPONENTS)
    )

    checkpoint_loads: list[MaceRuntimeCheckpointLoadEvidence] = []
    if MACECalculator is not None:
        for checkpoint_path, requested_head in checkpoint_requests:
            checkpoint_loads.append(
                _checkpoint_load_evidence(
                    checkpoint_path,
                    requested_head,
                    MACECalculator=MACECalculator,
                )
            )
    elif checkpoint_requests:
        # Preserve evidence for every requested fixture even when MACE itself is
        # unavailable; do not make absence look like an unattempted success.
        for checkpoint_path, requested_head in checkpoint_requests:
            source = Path(checkpoint_path).resolve()
            if not source.is_file():
                raise TrainingDataInputError(f"Runtime-freeze checkpoint does not exist: {source}")
            checkpoint_loads.append(
                MaceRuntimeCheckpointLoadEvidence(
                    checkpoint_path=str(source),
                    checkpoint_sha256=sha256_file_cached(source),
                    requested_head=requested_head,
                    torch_load_passed=False,
                    e3nn_calculator_load_passed=False,
                    model_class=None,
                    available_heads=(),
                    error_type=blocking_error_type or "MaceUnavailable",
                    error_message=blocking_error_message or "MACE calculator is unavailable.",
                )
            )

    artifact_digests: list[tuple[str, str]] = []
    for raw in supplied_artifacts:
        artifact = Path(raw).resolve()
        if not artifact.is_file():
            raise TrainingDataInputError(f"Runtime-freeze supplied artifact does not exist: {artifact}")
        artifact_digests.append((artifact.name, sha256_file_cached(artifact)))

    return MaceRuntimeFreezeRecord(
        policy=active,
        python_version=platform.python_version(),
        platform=platform.platform(),
        torch_version=torch_version,
        torch_cuda_version=torch_cuda_version,
        cuda_available=cuda_available,
        mace_version=mace_version,
        e3nn_version=e3nn_version,
        calculator_enable_cueq_supported=calculator_enable_cueq_supported,
        calculator_enable_oeq_supported=calculator_enable_oeq_supported,
        training_enable_cueq_supported=training_enable_cueq_supported,
        training_enable_oeq_supported=training_enable_oeq_supported,
        source_evidence=tuple(source_evidence),
        component_capabilities=capabilities,
        supplied_artifacts=tuple(artifact_digests),
        checkpoint_loads=tuple(checkpoint_loads),
        blocking_error_type=blocking_error_type,
        blocking_error_message=blocking_error_message,
        semantic_source_compatibility_passed=semantic_source_compatibility_passed,
        semantic_source_compatibility_notes=semantic_source_compatibility_notes,
    )
