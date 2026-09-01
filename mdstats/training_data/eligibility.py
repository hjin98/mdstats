"""Post-DFT frame eligibility decisions for MLFF-DATA3."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping

import numpy as np
from numpy.typing import ArrayLike

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

FRAME_ELIGIBILITY_POLICY_SCHEMA = "mdstats.frame-eligibility-policy.v1"
FRAME_ELIGIBILITY_DECISION_SCHEMA = "mdstats.frame-eligibility-decision.v1"
FRAME_ELIGIBILITY_CATALOG_SCHEMA = "mdstats.frame-eligibility-catalog.v1"
FRAME_ELIGIBILITY_POLICY_VERSION = "mdstats.mlff-data3.frame-eligibility.2026-07.v1"


class FrameEligibilityState(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    UNRESOLVED = "unresolved"


class StressRequirement(str, Enum):
    OPTIONAL = "optional"
    REQUIRED = "required"
    FORBIDDEN = "forbidden"


@dataclass(frozen=True, slots=True)
class FrameEligibilityPolicy:
    require_energy: bool = True
    require_forces: bool = True
    stress_requirement: StressRequirement = StressRequirement.OPTIONAL
    reject_scf_iteration_limit: bool = True
    reject_unqualified_source: bool = True
    unresolved_source_quality_is_unresolved: bool = False
    minimum_cell_volume_angstrom3: float = 1.0e-8
    stress_symmetry_tolerance: float = 1.0e-10
    policy_version: str = FRAME_ELIGIBILITY_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "stress_requirement", StressRequirement(self.stress_requirement))
        for name in ("minimum_cell_volume_angstrom3", "stress_symmetry_tolerance"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"{name} must be finite and positive.")
            object.__setattr__(self, name, value)
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_ELIGIBILITY_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "require_energy": self.require_energy,
            "require_forces": self.require_forces,
            "stress_requirement": self.stress_requirement.value,
            "reject_scf_iteration_limit": self.reject_scf_iteration_limit,
            "reject_unqualified_source": self.reject_unqualified_source,
            "unresolved_source_quality_is_unresolved": self.unresolved_source_quality_is_unresolved,
            "minimum_cell_volume_angstrom3": self.minimum_cell_volume_angstrom3,
            "stress_symmetry_tolerance": self.stress_symmetry_tolerance,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameEligibilityPolicy":
        if payload.get("schema") != FRAME_ELIGIBILITY_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-eligibility policy schema.")
        result = cls(
            require_energy=bool(payload["require_energy"]),
            require_forces=bool(payload["require_forces"]),
            stress_requirement=StressRequirement(payload["stress_requirement"]),
            reject_scf_iteration_limit=bool(payload["reject_scf_iteration_limit"]),
            reject_unqualified_source=bool(payload["reject_unqualified_source"]),
            unresolved_source_quality_is_unresolved=bool(payload["unresolved_source_quality_is_unresolved"]),
            minimum_cell_volume_angstrom3=float(payload["minimum_cell_volume_angstrom3"]),
            stress_symmetry_tolerance=float(payload["stress_symmetry_tolerance"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Frame-eligibility policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FrameEligibilityDecision:
    frame_uid: str
    frame_record_digest: str
    policy_digest: str
    state: FrameEligibilityState
    reason_codes: tuple[str, ...]
    warning_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        object.__setattr__(self, "frame_record_digest", validate_digest(self.frame_record_digest, name="frame_record_digest"))
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        object.__setattr__(self, "state", FrameEligibilityState(self.state))
        reasons = tuple(sorted(set(str(v) for v in self.reason_codes)))
        warnings = tuple(sorted(set(str(v) for v in self.warning_codes)))
        if self.state is FrameEligibilityState.ELIGIBLE and reasons:
            raise TrainingDataInputError("Eligible frames cannot carry hard reason codes.")
        if self.state is FrameEligibilityState.INELIGIBLE and not reasons:
            raise TrainingDataInputError("Ineligible frames require reason codes.")
        object.__setattr__(self, "reason_codes", reasons)
        object.__setattr__(self, "warning_codes", warnings)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_ELIGIBILITY_DECISION_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "policy_digest": self.policy_digest,
            "state": self.state.value,
            "reason_codes": list(self.reason_codes),
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameEligibilityDecision":
        if payload.get("schema") != FRAME_ELIGIBILITY_DECISION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-eligibility-decision schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            policy_digest=str(payload["policy_digest"]),
            state=FrameEligibilityState(payload["state"]),
            reason_codes=tuple(str(v) for v in payload.get("reason_codes", ())),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Frame-eligibility-decision digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FrameEligibilityCatalog:
    policy_digest: str
    decisions: tuple[FrameEligibilityDecision, ...]
    _by_frame_uid: Mapping[str, FrameEligibilityDecision] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        decisions = tuple(sorted(self.decisions, key=lambda item: item.frame_uid))
        if len({item.frame_uid for item in decisions}) != len(decisions):
            raise TrainingDataInputError("Duplicate frame decisions.")
        if any(item.policy_digest != self.policy_digest for item in decisions):
            raise TrainingDataInputError("Frame decision policy mismatch.")
        object.__setattr__(self, "decisions", decisions)
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in decisions})

    def for_frame(self, frame_uid: str) -> FrameEligibilityDecision:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FRAME_ELIGIBILITY_CATALOG_SCHEMA,
            "policy_digest": self.policy_digest,
            "decisions": [item.to_dict() for item in self.decisions],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FrameEligibilityCatalog":
        if payload.get("schema") != FRAME_ELIGIBILITY_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported frame-eligibility-catalog schema.")
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            decisions=tuple(FrameEligibilityDecision.from_dict(v) for v in payload.get("decisions", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Frame-eligibility-catalog digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RequiredLabelContractResult:
    is_satisfied: bool
    reason_codes: tuple[str, ...] = ()
    warning_codes: tuple[str, ...] = ()


def evaluate_required_label_contract(
    *,
    atom_count: int,
    energy_ev: float | None,
    forces_ev_per_angstrom: ArrayLike | None,
    stress_ev_per_angstrom3: ArrayLike | None,
    policy: FrameEligibilityPolicy | None = None,
) -> RequiredLabelContractResult:
    """Pure version-agnostic evaluator for required-label numerical validity."""
    active = FrameEligibilityPolicy() if policy is None else policy
    hard: list[str] = []
    warnings: list[str] = []

    if energy_ev is None:
        if active.require_energy:
            hard.append("missing_energy")
    elif not np.isfinite(float(energy_ev)):
        hard.append("nonfinite_energy")

    if forces_ev_per_angstrom is None:
        if active.require_forces:
            hard.append("missing_forces")
    else:
        forces = np.asarray(forces_ev_per_angstrom, dtype=np.float64)
        if forces.shape != (atom_count, 3):
            hard.append("force_shape_mismatch")
        elif np.any(~np.isfinite(forces)):
            hard.append("nonfinite_forces")

    if stress_ev_per_angstrom3 is None:
        if active.stress_requirement is StressRequirement.REQUIRED:
            hard.append("missing_stress")
        elif active.stress_requirement is StressRequirement.OPTIONAL:
            warnings.append("stress_absent_optional")
    else:
        stress = np.asarray(stress_ev_per_angstrom3, dtype=np.float64)
        if active.stress_requirement is StressRequirement.FORBIDDEN:
            hard.append("stress_present_but_forbidden")
        elif stress.shape != (3, 3):
            hard.append("stress_shape_mismatch")
        elif np.any(~np.isfinite(stress)):
            hard.append("nonfinite_stress")
        elif not np.allclose(
            stress, stress.T, rtol=0.0, atol=active.stress_symmetry_tolerance
        ):
            hard.append("nonsymmetric_stress")

    return RequiredLabelContractResult(
        is_satisfied=len(hard) == 0,
        reason_codes=tuple(hard),
        warning_codes=tuple(warnings),
    )


def assess_frame_eligibility(
    *,
    frame_record: Any,
    atomic_numbers: ArrayLike,
    fractional_positions: ArrayLike,
    cell: ArrayLike,
    energy_ev: float | None,
    forces_ev_per_angstrom: ArrayLike | None,
    stress_ev_per_angstrom3: ArrayLike | None,
    scf_iteration_limit_reached: bool | None,
    source_quality_status: str,
    source_quality_outcome: str | None,
    policy: FrameEligibilityPolicy | None = None,
) -> FrameEligibilityDecision:
    active = FrameEligibilityPolicy() if policy is None else policy
    hard: list[str] = []
    warnings: list[str] = []

    numbers = np.asarray(atomic_numbers, dtype=np.int64)
    positions = np.asarray(fractional_positions, dtype=np.float64)
    cell_array = np.asarray(cell, dtype=np.float64)
    if numbers.ndim != 1 or numbers.size != frame_record.atom_count or np.any(numbers <= 0):
        hard.append("atomic_identity_mismatch")
    if positions.shape != (frame_record.atom_count, 3) or np.any(~np.isfinite(positions)):
        hard.append("invalid_fractional_positions")
    if cell_array.shape != (3, 3) or np.any(~np.isfinite(cell_array)):
        hard.append("invalid_cell")
    else:
        volume = float(np.linalg.det(cell_array))
        if not np.isfinite(volume) or volume <= active.minimum_cell_volume_angstrom3:
            hard.append("nonpositive_or_singular_cell")

    label_eval = evaluate_required_label_contract(
        atom_count=frame_record.atom_count,
        energy_ev=energy_ev,
        forces_ev_per_angstrom=forces_ev_per_angstrom,
        stress_ev_per_angstrom3=stress_ev_per_angstrom3,
        policy=active,
    )
    hard.extend(label_eval.reason_codes)
    warnings.extend(label_eval.warning_codes)

    if scf_iteration_limit_reached is True:
        if active.reject_scf_iteration_limit:
            hard.append("scf_iteration_limit_reached")
        else:
            warnings.append("scf_iteration_limit_reached")
    elif scf_iteration_limit_reached is None:
        warnings.append("scf_limit_status_unresolved")

    quality_status = source_quality_status.lower()
    quality_outcome = None if source_quality_outcome is None else source_quality_outcome.lower()
    unresolved_quality = quality_status in {"not_requested", "unavailable", "failed"}
    if quality_outcome == "unqualified" and active.reject_unqualified_source:
        hard.append("source_trajectory_unqualified")
    elif unresolved_quality:
        warnings.append("source_quality_unresolved")

    if hard:
        state = FrameEligibilityState.INELIGIBLE
    elif unresolved_quality and active.unresolved_source_quality_is_unresolved:
        state = FrameEligibilityState.UNRESOLVED
    else:
        state = FrameEligibilityState.ELIGIBLE
    return FrameEligibilityDecision(
        frame_uid=frame_record.frame_uid,
        frame_record_digest=frame_record.content_digest,
        policy_digest=active.policy_digest,
        state=state,
        reason_codes=tuple(hard),
        warning_codes=tuple(warnings),
    )
