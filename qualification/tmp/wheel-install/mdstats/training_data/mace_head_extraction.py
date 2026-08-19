"""Checkpoint-faithful selected-head extraction for generalized MACE foundations.

MH1-EXTRACT1 isolates a known mace-torch==0.3.16 reconstruction defect for the
public MACE-MH-1 architecture.  The source checkpoint and installed MACE package
remain immutable.  A derived single-head checkpoint is accepted only after its
source/shim provenance is authenticated and source-vs-derived numerical parity
is demonstrated explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import hashlib
import math
import os
import tempfile
import warnings

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    sha256_file_cached,
    validate_digest,
)
from .foundation import (
    FoundationPotentialIdentity,
    MaceFoundationFamily,
    inspect_mace_foundation,
)
from .mace_compatibility import (
    MaceSelectedHeadCompatibilityPolicy,
)

MACE_SELECTED_HEAD_EXTRACTION_SCHEMA = "mdstats.mace-selected-head-extraction.v1"
MACE_SELECTED_HEAD_PARITY_POLICY_SCHEMA = "mdstats.mace-selected-head-parity-policy.v1"
MACE_SELECTED_HEAD_PARITY_SCHEMA = "mdstats.mace-selected-head-parity.v1"
MACE_SELECTED_HEAD_QUALIFICATION_SCHEMA = "mdstats.mace-selected-head-qualification.v1"


def _mace_version() -> str:
    try:
        return str(metadata.version("mace-torch"))
    except metadata.PackageNotFoundError:
        try:
            import mace

            return str(getattr(mace, "__version__", "unknown"))
        except Exception:
            return "unknown"


def _model_dtype(model: Any) -> str:
    try:
        for parameter in model.parameters():
            if getattr(parameter, "is_floating_point", lambda: False)():
                return str(parameter.dtype).removeprefix("torch.")
    except Exception as exc:  # pragma: no cover - defensive foreign-module guard
        raise TrainingDataInputError("Unable to determine selected-head source model dtype.") from exc
    raise TrainingDataInputError("Selected-head source model has no floating parameters.")


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _first_parameter_dtype(model: Any) -> Any:
    for parameter in model.parameters():
        if getattr(parameter, "is_floating_point", lambda: False)():
            return parameter.dtype
    raise TrainingDataInputError("Selected-head source model has no floating parameters.")


def _first_interaction_signature(model: Any) -> dict[str, Any]:
    interactions = getattr(model, "interactions", None)
    if interactions is None or len(interactions) == 0:
        raise TrainingDataInputError("Selected-head source model exposes no interaction blocks.")
    first = interactions[0]
    linear_up = getattr(first, "linear_up", None)
    return {
        "model_class": type(model).__name__,
        "first_interaction_class": type(first).__name__,
        "model_edge_irreps": None if getattr(model, "edge_irreps", None) is None else str(model.edge_irreps),
        "first_interaction_edge_irreps": None if getattr(first, "edge_irreps", None) is None else str(first.edge_irreps),
        "linear_up_irreps_in": None if linear_up is None or getattr(linear_up, "irreps_in", None) is None else str(linear_up.irreps_in),
        "linear_up_irreps_out": None if linear_up is None or getattr(linear_up, "irreps_out", None) is None else str(linear_up.irreps_out),
        "has_use_edge_irreps_first": hasattr(model, "use_edge_irreps_first"),
        "use_edge_irreps_first": None if not hasattr(model, "use_edge_irreps_first") else bool(model.use_edge_irreps_first),
    }


def _affected_mh1_edge_projection_condition(
    model: Any,
    *,
    mace_version: str,
    source_identity: FoundationPotentialIdentity,
    policy: MaceSelectedHeadCompatibilityPolicy,
) -> tuple[bool, dict[str, Any]]:
    """Return whether the exact v0.3.16 MH-1 metadata correction is justified."""

    signature = _first_interaction_signature(model)
    evidence = {
        **signature,
        "mace_version": str(mace_version),
        "source_model_family": source_identity.family.value,
        "source_architecture_signature": source_identity.architecture_signature,
        "policy_digest": policy.policy_digest,
    }
    if mace_version != policy.affected_package_version:
        return False, evidence
    if source_identity.family is not MaceFoundationFamily.MH_1:
        return False, evidence
    if signature["model_class"] != policy.affected_model_class:
        return False, evidence
    if signature["first_interaction_class"] != policy.affected_first_interaction_class:
        return False, evidence
    if signature["has_use_edge_irreps_first"]:
        # If upstream/new serialized checkpoints carry the attribute, mdstats
        # must never overwrite it.  Stock extraction is authoritative.
        return False, evidence
    if not signature["model_edge_irreps"] or not signature["first_interaction_edge_irreps"]:
        return False, evidence

    try:
        from e3nn import o3

        model_edge = o3.Irreps(str(signature["model_edge_irreps"]))
        expected_first = o3.Irreps(f"{model_edge.count(o3.Irrep(0, 1))}x0e")
        actual_first = o3.Irreps(str(signature["first_interaction_edge_irreps"]))
        linear_out = o3.Irreps(str(signature["linear_up_irreps_out"]))
    except Exception:
        return False, evidence
    evidence["inferred_first_edge_irreps"] = str(expected_first)
    evidence["edge_projection_matches_serialized_modules"] = bool(
        actual_first == expected_first and linear_out == expected_first
    )
    return bool(evidence["edge_projection_matches_serialized_modules"]), evidence


def _remove_head_preserving_source_dtype(
    model: Any,
    head: str,
    extractor: Callable[[Any, str], Any],
) -> Any:
    import torch

    source_dtype = _first_parameter_dtype(model)
    if source_dtype not in (torch.float32, torch.float64):
        raise TrainingDataInputError(
            f"Selected-head extraction supports float32/float64 source parameters, got {source_dtype}."
        )
    old_dtype = torch.get_default_dtype()
    try:
        torch.set_default_dtype(source_dtype)
        return extractor(model, head)
    finally:
        torch.set_default_dtype(old_dtype)


def _extract_selected_head_model(
    model: Any,
    *,
    head: str,
    source_identity: FoundationPotentialIdentity,
    mace_version: str,
    policy: MaceSelectedHeadCompatibilityPolicy,
    stock_extractor: Callable[[Any, str], Any],
) -> tuple[Any, bool, str | None, str | None, str | None, dict[str, Any]]:
    """Extract one head, using the architecture shim only after stock failure.

    Returns ``(model, stock_passed, failure_type, failure_digest,
    failure_excerpt, compatibility_evidence)``.
    """

    stock_failure_type: str | None = None
    stock_failure_digest: str | None = None
    stock_failure_excerpt: str | None = None
    try:
        derived = _remove_head_preserving_source_dtype(model, head, stock_extractor)
        return derived, True, None, None, None, {
            "shim_applied": False,
            "self_disabled_reason": "stock_selected_head_extraction_passed",
            "source_dtype_preserved": True,
        }
    except Exception as exc:  # upstream failure is part of compatibility evidence
        stock_failure_type = type(exc).__name__
        message = str(exc)
        stock_failure_digest = _sha256_text(message)
        stock_failure_excerpt = message[:1200]

    affected, evidence = _affected_mh1_edge_projection_condition(
        model,
        mace_version=mace_version,
        source_identity=source_identity,
        policy=policy,
    )
    if not affected:
        raise TrainingDataInputError(
            "Stock MACE selected-head extraction failed, but the checkpoint does not match "
            "the exact version/architecture conditions authorized for the MH1-EXTRACT1 shim. "
            f"stock_failure={stock_failure_type}: {stock_failure_excerpt}"
        )

    attribute = policy.inferred_attribute
    if hasattr(model, attribute):  # defensive; affected predicate already rejects this
        raise TrainingDataInputError("MH1-EXTRACT1 refuses to overwrite serialized architecture metadata.")
    setattr(model, attribute, bool(policy.inferred_value))
    try:
        derived = _remove_head_preserving_source_dtype(model, head, stock_extractor)
    except Exception as exc:
        raise TrainingDataInputError(
            "The version-guarded MH-1 selected-head compatibility correction did not restore "
            f"architecture-faithful extraction: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        delattr(model, attribute)

    evidence = {
        **evidence,
        "shim_applied": True,
        "shim_attribute": attribute,
        "shim_value": bool(policy.inferred_value),
        "shim_version": policy.shim_version,
        "source_dtype_preserved": True,
        "stock_failure_type": stock_failure_type,
        "stock_failure_message_sha256": stock_failure_digest,
    }
    return (
        derived,
        False,
        stock_failure_type,
        stock_failure_digest,
        stock_failure_excerpt,
        evidence,
    )


@dataclass(frozen=True, slots=True)
class MaceSelectedHeadExtractionRecord:
    source_potential_digest: str
    source_checkpoint_sha256: str
    source_architecture_signature: str
    source_head: str
    source_model_dtype: str
    mace_version: str
    compatibility_policy_digest: str
    stock_extraction_succeeded: bool
    stock_failure_type: str | None
    stock_failure_message_sha256: str | None
    stock_failure_excerpt: str | None
    compatibility_shim_applied: bool
    compatibility_evidence_digest: str
    derived_checkpoint_reference: str
    derived_checkpoint_sha256: str
    derived_architecture_signature: str
    derived_model_dtype: str
    source_bytes_preserved: bool

    def __post_init__(self) -> None:
        for name in (
            "source_potential_digest",
            "source_checkpoint_sha256",
            "source_architecture_signature",
            "compatibility_policy_digest",
            "compatibility_evidence_digest",
            "derived_checkpoint_sha256",
            "derived_architecture_signature",
        ):
            object.__setattr__(self, name, validate_digest(str(getattr(self, name)), name=name))
        for name in (
            "source_head",
            "source_model_dtype",
            "mace_version",
            "derived_checkpoint_reference",
            "derived_model_dtype",
        ):
            if not str(getattr(self, name)).strip():
                raise TrainingDataInputError(f"Selected-head extraction {name} must be non-empty.")
        if self.source_model_dtype not in {"float32", "float64"} or self.derived_model_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Selected-head extraction dtype must be float32 or float64.")
        if self.source_model_dtype != self.derived_model_dtype:
            raise TrainingDataInputError("Selected-head extraction changed the foundation model dtype.")
        if self.stock_extraction_succeeded and self.compatibility_shim_applied:
            raise TrainingDataInputError("Compatibility shim must self-disable when stock extraction succeeds.")
        if not self.stock_extraction_succeeded and not self.compatibility_shim_applied:
            raise TrainingDataInputError("A failed stock extraction requires an authorized compatibility shim.")
        if self.stock_extraction_succeeded and any(
            value is not None for value in (self.stock_failure_type, self.stock_failure_message_sha256, self.stock_failure_excerpt)
        ):
            raise TrainingDataInputError("Passing stock extraction cannot carry failure evidence.")
        if not self.stock_extraction_succeeded:
            if not self.stock_failure_type or not self.stock_failure_message_sha256:
                raise TrainingDataInputError("Shim extraction requires authenticated stock-failure evidence.")
            object.__setattr__(
                self,
                "stock_failure_message_sha256",
                validate_digest(str(self.stock_failure_message_sha256), name="stock_failure_message_sha256"),
            )
        if not self.source_bytes_preserved:
            raise TrainingDataInputError("Selected-head extraction requires the source checkpoint to remain byte-identical.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_SELECTED_HEAD_EXTRACTION_SCHEMA,
            "source_potential_digest": self.source_potential_digest,
            "source_checkpoint_sha256": self.source_checkpoint_sha256,
            "source_architecture_signature": self.source_architecture_signature,
            "source_head": self.source_head,
            "source_model_dtype": self.source_model_dtype,
            "mace_version": self.mace_version,
            "compatibility_policy_digest": self.compatibility_policy_digest,
            "stock_extraction_succeeded": self.stock_extraction_succeeded,
            "stock_failure_type": self.stock_failure_type,
            "stock_failure_message_sha256": self.stock_failure_message_sha256,
            "stock_failure_excerpt": self.stock_failure_excerpt,
            "compatibility_shim_applied": self.compatibility_shim_applied,
            "compatibility_evidence_digest": self.compatibility_evidence_digest,
            "derived_checkpoint_reference": self.derived_checkpoint_reference,
            "derived_checkpoint_sha256": self.derived_checkpoint_sha256,
            "derived_architecture_signature": self.derived_architecture_signature,
            "derived_model_dtype": self.derived_model_dtype,
            "source_bytes_preserved": self.source_bytes_preserved,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSelectedHeadExtractionRecord":
        if payload.get("schema") != MACE_SELECTED_HEAD_EXTRACTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selected-head extraction schema.")
        result = cls(
            source_potential_digest=str(payload["source_potential_digest"]),
            source_checkpoint_sha256=str(payload["source_checkpoint_sha256"]),
            source_architecture_signature=str(payload["source_architecture_signature"]),
            source_head=str(payload["source_head"]),
            source_model_dtype=str(payload["source_model_dtype"]),
            mace_version=str(payload["mace_version"]),
            compatibility_policy_digest=str(payload["compatibility_policy_digest"]),
            stock_extraction_succeeded=bool(payload["stock_extraction_succeeded"]),
            stock_failure_type=None if payload.get("stock_failure_type") is None else str(payload["stock_failure_type"]),
            stock_failure_message_sha256=None if payload.get("stock_failure_message_sha256") is None else str(payload["stock_failure_message_sha256"]),
            stock_failure_excerpt=None if payload.get("stock_failure_excerpt") is None else str(payload["stock_failure_excerpt"]),
            compatibility_shim_applied=bool(payload["compatibility_shim_applied"]),
            compatibility_evidence_digest=str(payload["compatibility_evidence_digest"]),
            derived_checkpoint_reference=str(payload["derived_checkpoint_reference"]),
            derived_checkpoint_sha256=str(payload["derived_checkpoint_sha256"]),
            derived_architecture_signature=str(payload["derived_architecture_signature"]),
            derived_model_dtype=str(payload["derived_model_dtype"]),
            source_bytes_preserved=bool(payload["source_bytes_preserved"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Selected-head extraction digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceSelectedHeadParityPolicy:
    default_dtype: str = "float64"
    energy_rtol: float = 1.0e-9
    energy_atol: float = 1.0e-10
    force_rtol: float = 1.0e-9
    force_atol: float = 1.0e-10
    stress_rtol: float = 1.0e-9
    stress_atol: float = 1.0e-10
    descriptor_rtol: float = 1.0e-9
    descriptor_atol: float = 1.0e-10
    e0_rtol: float = 0.0
    e0_atol: float = 0.0
    invariants_only: bool = True

    def __post_init__(self) -> None:
        if self.default_dtype not in {"float32", "float64"}:
            raise TrainingDataInputError("Selected-head parity dtype must be float32 or float64.")
        for name in (
            "energy_rtol", "energy_atol", "force_rtol", "force_atol",
            "stress_rtol", "stress_atol", "descriptor_rtol", "descriptor_atol",
            "e0_rtol", "e0_atol",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"Selected-head parity {name} must be finite and non-negative.")
            object.__setattr__(self, name, value)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_SELECTED_HEAD_PARITY_POLICY_SCHEMA,
            "default_dtype": self.default_dtype,
            "energy_rtol": self.energy_rtol,
            "energy_atol": self.energy_atol,
            "force_rtol": self.force_rtol,
            "force_atol": self.force_atol,
            "stress_rtol": self.stress_rtol,
            "stress_atol": self.stress_atol,
            "descriptor_rtol": self.descriptor_rtol,
            "descriptor_atol": self.descriptor_atol,
            "e0_rtol": self.e0_rtol,
            "e0_atol": self.e0_atol,
            "invariants_only": self.invariants_only,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSelectedHeadParityPolicy":
        if payload.get("schema") != MACE_SELECTED_HEAD_PARITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selected-head parity policy schema.")
        result = cls(**{k: payload[k] for k in (
            "default_dtype", "energy_rtol", "energy_atol", "force_rtol", "force_atol",
            "stress_rtol", "stress_atol", "descriptor_rtol", "descriptor_atol", "e0_rtol", "e0_atol", "invariants_only",
        )})
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Selected-head parity policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceSelectedHeadParityRecord:
    extraction_digest: str
    parity_policy_digest: str
    structure_count: int
    atom_count: int
    descriptor_width: int
    energy_abs_max_ev: float
    force_abs_max_ev_per_angstrom: float
    stress_abs_max_ev_per_angstrom3: float
    descriptor_abs_max: float
    atomic_e0_abs_max_ev: float
    energy_allclose: bool
    forces_allclose: bool
    stress_allclose: bool
    descriptors_allclose: bool
    atomic_e0_allclose: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "extraction_digest", validate_digest(self.extraction_digest, name="extraction_digest"))
        object.__setattr__(self, "parity_policy_digest", validate_digest(self.parity_policy_digest, name="parity_policy_digest"))
        if int(self.structure_count) <= 0 or int(self.atom_count) <= 0 or int(self.descriptor_width) <= 0:
            raise TrainingDataInputError("Selected-head parity requires non-empty structures/descriptors.")
        object.__setattr__(self, "structure_count", int(self.structure_count))
        object.__setattr__(self, "atom_count", int(self.atom_count))
        object.__setattr__(self, "descriptor_width", int(self.descriptor_width))
        for name in (
            "energy_abs_max_ev", "force_abs_max_ev_per_angstrom", "stress_abs_max_ev_per_angstrom3",
            "descriptor_abs_max", "atomic_e0_abs_max_ev",
        ):
            value = float(getattr(self, name))
            if not math.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(f"Selected-head parity {name} must be finite and non-negative.")
            object.__setattr__(self, name, value)

    @property
    def passed(self) -> bool:
        return bool(
            self.energy_allclose
            and self.forces_allclose
            and self.stress_allclose
            and self.descriptors_allclose
            and self.atomic_e0_allclose
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_SELECTED_HEAD_PARITY_SCHEMA,
            "extraction_digest": self.extraction_digest,
            "parity_policy_digest": self.parity_policy_digest,
            "structure_count": self.structure_count,
            "atom_count": self.atom_count,
            "descriptor_width": self.descriptor_width,
            "energy_abs_max_ev": self.energy_abs_max_ev,
            "force_abs_max_ev_per_angstrom": self.force_abs_max_ev_per_angstrom,
            "stress_abs_max_ev_per_angstrom3": self.stress_abs_max_ev_per_angstrom3,
            "descriptor_abs_max": self.descriptor_abs_max,
            "atomic_e0_abs_max_ev": self.atomic_e0_abs_max_ev,
            "energy_allclose": self.energy_allclose,
            "forces_allclose": self.forces_allclose,
            "stress_allclose": self.stress_allclose,
            "descriptors_allclose": self.descriptors_allclose,
            "atomic_e0_allclose": self.atomic_e0_allclose,
            "passed": self.passed,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSelectedHeadParityRecord":
        if payload.get("schema") != MACE_SELECTED_HEAD_PARITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selected-head parity schema.")
        result = cls(
            extraction_digest=str(payload["extraction_digest"]),
            parity_policy_digest=str(payload["parity_policy_digest"]),
            structure_count=int(payload["structure_count"]),
            atom_count=int(payload["atom_count"]),
            descriptor_width=int(payload["descriptor_width"]),
            energy_abs_max_ev=float(payload["energy_abs_max_ev"]),
            force_abs_max_ev_per_angstrom=float(payload["force_abs_max_ev_per_angstrom"]),
            stress_abs_max_ev_per_angstrom3=float(payload["stress_abs_max_ev_per_angstrom3"]),
            descriptor_abs_max=float(payload["descriptor_abs_max"]),
            atomic_e0_abs_max_ev=float(payload["atomic_e0_abs_max_ev"]),
            energy_allclose=bool(payload["energy_allclose"]),
            forces_allclose=bool(payload["forces_allclose"]),
            stress_allclose=bool(payload["stress_allclose"]),
            descriptors_allclose=bool(payload["descriptors_allclose"]),
            atomic_e0_allclose=bool(payload["atomic_e0_allclose"]),
        )
        if payload.get("passed") not in (None, result.passed):
            raise TrainingDataSerializationError("Selected-head parity pass state mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Selected-head parity digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class MaceSelectedHeadQualificationRecord:
    extraction: MaceSelectedHeadExtractionRecord
    parity: MaceSelectedHeadParityRecord

    def __post_init__(self) -> None:
        if self.parity.extraction_digest != self.extraction.content_digest:
            raise TrainingDataInputError("Selected-head qualification parity lineage does not match extraction.")
        if not self.parity.passed:
            raise TrainingDataInputError("Selected-head checkpoint is not numerically parity-qualified.")

    @property
    def training_qualified(self) -> bool:
        return True

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": MACE_SELECTED_HEAD_QUALIFICATION_SCHEMA,
            "extraction": self.extraction.to_dict(),
            "parity": self.parity.to_dict(),
            "training_qualified": self.training_qualified,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "MaceSelectedHeadQualificationRecord":
        if payload.get("schema") != MACE_SELECTED_HEAD_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported selected-head qualification schema.")
        result = cls(
            extraction=MaceSelectedHeadExtractionRecord.from_dict(payload["extraction"]),
            parity=MaceSelectedHeadParityRecord.from_dict(payload["parity"]),
        )
        if payload.get("training_qualified") not in (None, result.training_qualified):
            raise TrainingDataSerializationError("Selected-head qualification state mismatch.")
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Selected-head qualification digest mismatch.")
        return result


def extract_mace_selected_foundation_head(
    source_checkpoint: str | Path,
    output_checkpoint: str | Path,
    *,
    source_identity: FoundationPotentialIdentity,
    policy: MaceSelectedHeadCompatibilityPolicy | None = None,
) -> tuple[MaceSelectedHeadExtractionRecord, Mapping[str, Any]]:
    """Create one immutable-provenance single-head foundation checkpoint.

    The original checkpoint is never rewritten.  Stock MACE extraction is tried
    first under a source-dtype guard.  The v0.3.16 MH-1 edge-projection metadata
    correction is applied only after stock failure and only when the loaded model
    itself proves the exact affected architecture condition.
    """

    source = Path(source_checkpoint).resolve()
    target = Path(output_checkpoint).resolve()
    if source == target:
        raise TrainingDataInputError("Selected-head derived checkpoint must not overwrite the source checkpoint.")
    if not source.is_file():
        raise TrainingDataInputError(f"Selected-head source checkpoint does not exist: {source!s}.")
    active = MaceSelectedHeadCompatibilityPolicy() if policy is None else policy
    source_sha_before = sha256_file_cached(source)
    canonical = source_identity.canonicalized()
    if canonical.sha256 != source_sha_before:
        raise TrainingDataInputError("Selected-head source identity SHA does not match checkpoint bytes.")
    if canonical.reference and Path(canonical.reference).is_file():
        if Path(canonical.reference).resolve() != source:
            raise TrainingDataInputError("Selected-head source identity references a different checkpoint.")
    if canonical.architecture_signature is None:
        raise TrainingDataInputError("Selected-head source identity is missing inspected architecture identity.")

    try:
        import torch
        from mace.tools.scripts_utils import remove_pt_head
    except Exception as exc:
        raise TrainingDataInputError("Selected-head extraction requires torch and mace-torch.") from exc

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        model = torch.load(str(source), map_location="cpu", weights_only=False)
    heads = tuple(str(v) for v in getattr(model, "heads", ()))
    if len(heads) <= 1:
        raise TrainingDataInputError("Selected-head extraction requires a genuinely multi-head source checkpoint.")
    if canonical.foundation_head not in heads:
        raise TrainingDataInputError(
            f"Selected foundation head {canonical.foundation_head!r} is unavailable; checkpoint heads={list(heads)!r}."
        )
    source_dtype = _model_dtype(model)
    mace_version = _mace_version()
    derived, stock_ok, failure_type, failure_digest, failure_excerpt, compatibility_evidence = _extract_selected_head_model(
        model,
        head=canonical.foundation_head,
        source_identity=canonical,
        mace_version=mace_version,
        policy=active,
        stock_extractor=remove_pt_head,
    )
    derived_heads = tuple(str(v) for v in getattr(derived, "heads", ()))
    if derived_heads != (canonical.foundation_head,):
        raise TrainingDataInputError(
            f"Selected-head extraction produced unexpected heads {list(derived_heads)!r}."
        )
    derived_dtype = _model_dtype(derived)
    if derived_dtype != source_dtype:
        raise TrainingDataInputError(
            f"Selected-head extraction changed model dtype {source_dtype} -> {derived_dtype}."
        )

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=target.name + ".", suffix=".tmp", dir=target.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        torch.save(derived, str(tmp))
        if tmp.stat().st_size <= 0:
            raise TrainingDataInputError("Selected-head derived checkpoint is empty.")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)

    source_sha_after = sha256_file_cached(source)
    derived_sha = sha256_file_cached(target)
    if source_sha_before != source_sha_after:
        target.unlink(missing_ok=True)
        raise TrainingDataInputError("Source foundation checkpoint changed during selected-head extraction.")
    derived_inspection = inspect_mace_foundation(target)
    if derived_inspection.available_heads != (canonical.foundation_head,):
        target.unlink(missing_ok=True)
        raise TrainingDataInputError("Derived selected-head checkpoint inspection reports unexpected heads.")
    if derived_inspection.model_dtype != source_dtype:
        target.unlink(missing_ok=True)
        raise TrainingDataInputError("Derived selected-head checkpoint inspection reports a dtype change.")

    compatibility_evidence = {
        **dict(compatibility_evidence),
        "source_head": canonical.foundation_head,
        "source_checkpoint_sha256": source_sha_before,
        "source_architecture_signature": canonical.architecture_signature,
        "derived_checkpoint_sha256": derived_sha,
        "derived_architecture_signature": derived_inspection.architecture_signature,
        "source_model_dtype": source_dtype,
        "derived_model_dtype": derived_dtype,
    }
    compatibility_evidence_digest = digest(compatibility_evidence)
    record = MaceSelectedHeadExtractionRecord(
        source_potential_digest=canonical.canonical_content_digest,
        source_checkpoint_sha256=source_sha_before,
        source_architecture_signature=canonical.architecture_signature,
        source_head=canonical.foundation_head,
        source_model_dtype=source_dtype,
        mace_version=mace_version,
        compatibility_policy_digest=active.policy_digest,
        stock_extraction_succeeded=stock_ok,
        stock_failure_type=failure_type,
        stock_failure_message_sha256=failure_digest,
        stock_failure_excerpt=failure_excerpt,
        compatibility_shim_applied=bool(compatibility_evidence.get("shim_applied", False)),
        compatibility_evidence_digest=compatibility_evidence_digest,
        derived_checkpoint_reference=str(target),
        derived_checkpoint_sha256=derived_sha,
        derived_architecture_signature=derived_inspection.architecture_signature,
        derived_model_dtype=derived_dtype,
        source_bytes_preserved=(source_sha_before == source_sha_after),
    )
    return record, compatibility_evidence


def _max_abs(a: Any, b: Any) -> float:
    import numpy as np

    aa = np.asarray(a, dtype=float)
    bb = np.asarray(b, dtype=float)
    if aa.shape != bb.shape:
        return math.inf
    if aa.size == 0:
        return 0.0
    return float(np.max(np.abs(aa - bb)))


def qualify_mace_selected_foundation_head(
    source_checkpoint: str | Path,
    extraction: MaceSelectedHeadExtractionRecord,
    structures: Sequence[Any],
    *,
    policy: MaceSelectedHeadParityPolicy | None = None,
    device: str = "cpu",
) -> MaceSelectedHeadQualificationRecord:
    """Prove source multi-head vs derived single-head numerical equivalence."""

    active = MaceSelectedHeadParityPolicy() if policy is None else policy
    items = tuple(structures)
    if not items:
        raise TrainingDataInputError("Selected-head parity requires at least one structure.")
    source = Path(source_checkpoint).resolve()
    derived = Path(extraction.derived_checkpoint_reference).resolve()
    if not source.is_file() or sha256_file_cached(source) != extraction.source_checkpoint_sha256:
        raise TrainingDataInputError("Selected-head parity source checkpoint is missing or changed.")
    if not derived.is_file() or sha256_file_cached(derived) != extraction.derived_checkpoint_sha256:
        raise TrainingDataInputError("Selected-head parity derived checkpoint is missing or changed.")

    try:
        import numpy as np
        import torch
        from mace.calculators import MACECalculator
    except Exception as exc:
        raise TrainingDataInputError("Selected-head parity requires numpy, torch, ASE, and mace-torch.") from exc

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        source_calc = MACECalculator(
            model_paths=str(source),
            head=extraction.source_head,
            device=device,
            default_dtype=active.default_dtype,
            enable_cueq=False,
        )
        derived_calc = MACECalculator(
            model_paths=str(derived),
            head=extraction.source_head,
            device=device,
            default_dtype=active.default_dtype,
            enable_cueq=False,
        )

    energy_ok = True
    force_ok = True
    stress_ok = True
    descriptor_ok = True
    energy_max = 0.0
    force_max = 0.0
    stress_max = 0.0
    descriptor_max = 0.0
    descriptor_width: int | None = None
    atom_count = 0

    for structure in items:
        source_atoms = structure.copy()
        derived_atoms = structure.copy()
        source_atoms.calc = source_calc
        derived_atoms.calc = derived_calc
        e_source = float(source_atoms.get_potential_energy())
        e_derived = float(derived_atoms.get_potential_energy())
        f_source = np.asarray(source_atoms.get_forces(), dtype=float)
        f_derived = np.asarray(derived_atoms.get_forces(), dtype=float)
        s_source = np.asarray(source_atoms.get_stress(voigt=False), dtype=float)
        s_derived = np.asarray(derived_atoms.get_stress(voigt=False), dtype=float)
        d_source = np.asarray(source_calc.get_descriptors(structure, invariants_only=active.invariants_only), dtype=float)
        d_derived = np.asarray(derived_calc.get_descriptors(structure, invariants_only=active.invariants_only), dtype=float)
        if d_source.ndim != 2 or d_derived.shape != d_source.shape:
            descriptor_ok = False
            descriptor_max = math.inf
        else:
            width = int(d_source.shape[1])
            if descriptor_width is None:
                descriptor_width = width
            elif descriptor_width != width:
                raise TrainingDataInputError("Selected-head parity descriptor width changed across structures.")
            descriptor_ok &= bool(np.allclose(d_source, d_derived, rtol=active.descriptor_rtol, atol=active.descriptor_atol))
            descriptor_max = max(descriptor_max, _max_abs(d_source, d_derived))
        energy_ok &= bool(np.allclose(e_source, e_derived, rtol=active.energy_rtol, atol=active.energy_atol))
        force_ok &= bool(np.allclose(f_source, f_derived, rtol=active.force_rtol, atol=active.force_atol))
        stress_ok &= bool(np.allclose(s_source, s_derived, rtol=active.stress_rtol, atol=active.stress_atol))
        energy_max = max(energy_max, abs(e_source - e_derived))
        force_max = max(force_max, _max_abs(f_source, f_derived))
        stress_max = max(stress_max, _max_abs(s_source, s_derived))
        atom_count += len(structure)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning)
        source_model = torch.load(str(source), map_location="cpu", weights_only=False)
        derived_model = torch.load(str(derived), map_location="cpu", weights_only=False)
    source_heads = tuple(str(v) for v in getattr(source_model, "heads", ()))
    try:
        head_idx = source_heads.index(extraction.source_head)
    except ValueError as exc:
        raise TrainingDataInputError("Selected-head parity cannot resolve source E0 head.") from exc
    source_e0 = source_model.atomic_energies_fn.atomic_energies
    if source_e0.ndim == 2:
        source_e0 = source_e0[head_idx]
    derived_e0 = derived_model.atomic_energies_fn.atomic_energies
    if derived_e0.ndim == 2:
        if derived_e0.shape[0] != 1:
            raise TrainingDataInputError("Derived selected-head checkpoint has a non-singleton E0 head table.")
        derived_e0 = derived_e0[0]
    source_e0 = source_e0.detach().cpu().numpy()
    derived_e0 = derived_e0.detach().cpu().numpy()
    e0_ok = bool(np.allclose(source_e0, derived_e0, rtol=active.e0_rtol, atol=active.e0_atol))
    e0_max = _max_abs(source_e0, derived_e0)

    record = MaceSelectedHeadParityRecord(
        extraction_digest=extraction.content_digest,
        parity_policy_digest=active.policy_digest,
        structure_count=len(items),
        atom_count=atom_count,
        descriptor_width=0 if descriptor_width is None else descriptor_width,
        energy_abs_max_ev=energy_max,
        force_abs_max_ev_per_angstrom=force_max,
        stress_abs_max_ev_per_angstrom3=stress_max,
        descriptor_abs_max=descriptor_max,
        atomic_e0_abs_max_ev=e0_max,
        energy_allclose=energy_ok,
        forces_allclose=force_ok,
        stress_allclose=stress_ok,
        descriptors_allclose=descriptor_ok,
        atomic_e0_allclose=e0_ok,
    )
    return MaceSelectedHeadQualificationRecord(extraction=extraction, parity=record)
