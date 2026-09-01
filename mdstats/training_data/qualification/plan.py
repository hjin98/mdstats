"""Candidate-independent physical validation plan and the qualification plan.

The physical plan is built from the neutral ``OUTER_MONITOR`` role, the P1
split-exclusion/correlation authority, and the frozen specification - and from
nothing else.  It never sees a model prediction, a production seed, an M3 score,
or a previous qualification failure, which is exactly what stops "validation"
from degenerating into a search for configurations the model happens to like.
Because the construction depends on no member, every frozen publication member
is judged on a byte-identical plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .binding import EvidenceRoleMembership, QualificationInputBinding
from .components import COMPONENT_DYNAMICS, COMPONENT_PHYSICAL_PES
from .errors import QualificationError

PHYSICAL_BASE_SCHEMA = "mdstats.qualification-physical-base.v1"
PHYSICAL_PLAN_SCHEMA = "mdstats.qualification-physical-plan.v1"
QUALIFICATION_PLAN_SCHEMA = "mdstats.qualification-plan.v1"

_AXES = ("x", "y", "z")


@dataclass(frozen=True, slots=True)
class PhysicalValidationBase:
    """One deterministic validation configuration and its displacement modes."""

    frame_uid: str
    unit_id: str
    condition_key: str
    atom_count: int
    displaced_atom_indices: tuple[int, ...]
    axes: tuple[str, ...]
    amplitudes_angstrom: tuple[float, ...]

    def __post_init__(self) -> None:
        for name in ("frame_uid", "unit_id", "condition_key"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"Physical base requires {name}.")
            object.__setattr__(self, name, value)
        count = int(self.atom_count)
        if count <= 0:
            raise TrainingDataInputError("Physical base requires a positive atom count.")
        object.__setattr__(self, "atom_count", count)
        indices = tuple(int(v) for v in self.displaced_atom_indices)
        if not indices or len(set(indices)) != len(indices):
            raise TrainingDataInputError("Displaced atom indices must be unique and non-empty.")
        if any(index < 0 or index >= count for index in indices):
            raise TrainingDataInputError("Displaced atom index is outside the configuration.")
        object.__setattr__(self, "displaced_atom_indices", indices)
        axes = tuple(str(v) for v in self.axes)
        if not axes or any(axis not in _AXES for axis in axes):
            raise TrainingDataInputError("Displacement axes must be a non-empty subset of x/y/z.")
        object.__setattr__(self, "axes", axes)
        amplitudes = tuple(float(v) for v in self.amplitudes_angstrom)
        if not amplitudes:
            raise TrainingDataInputError("A physical base requires displacement amplitudes.")
        object.__setattr__(self, "amplitudes_angstrom", amplitudes)

    def modes(self) -> tuple[tuple[int, str, float], ...]:
        """Every ``(atom, axis, amplitude)`` mode, in one deterministic order."""

        return tuple(
            (atom, axis, amplitude)
            for atom in self.displaced_atom_indices
            for axis in self.axes
            for amplitude in self.amplitudes_angstrom
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PHYSICAL_BASE_SCHEMA,
            "frame_uid": self.frame_uid,
            "unit_id": self.unit_id,
            "condition_key": self.condition_key,
            "atom_count": self.atom_count,
            "displaced_atom_indices": list(self.displaced_atom_indices),
            "axes": list(self.axes),
            "amplitudes_angstrom": list(self.amplitudes_angstrom),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PhysicalValidationBase":
        if payload.get("schema") != PHYSICAL_BASE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported physical-base schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            unit_id=str(payload["unit_id"]),
            condition_key=str(payload["condition_key"]),
            atom_count=int(payload["atom_count"]),
            displaced_atom_indices=tuple(payload["displaced_atom_indices"]),
            axes=tuple(payload["axes"]),
            amplitudes_angstrom=tuple(payload["amplitudes_angstrom"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Physical-base digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PhysicalValidationPlan:
    """One immutable, model-blind plan shared by every publication member."""

    evidence_role_digest: str
    split_exclusion_digest: str
    policy_digest: str
    strain_magnitudes: tuple[float, ...]
    bases: tuple[PhysicalValidationBase, ...]

    def __post_init__(self) -> None:
        for name in ("evidence_role_digest", "split_exclusion_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        bases = tuple(self.bases)
        if not bases:
            raise QualificationError(
                "The neutral OUTER_MONITOR role supplied no admissible physical "
                "validation base. Qualification never substitutes development data "
                "for an unavailable independent role."
            )
        uids = [base.frame_uid for base in bases]
        if len(set(uids)) != len(uids):
            raise TrainingDataInputError("Physical validation bases must be unique frames.")
        object.__setattr__(self, "bases", bases)
        object.__setattr__(self, "strain_magnitudes", tuple(float(v) for v in self.strain_magnitudes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PHYSICAL_PLAN_SCHEMA,
            "evidence_role_digest": self.evidence_role_digest,
            "split_exclusion_digest": self.split_exclusion_digest,
            "policy_digest": self.policy_digest,
            "strain_magnitudes": list(self.strain_magnitudes),
            "bases": [base.to_dict() for base in self.bases],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PhysicalValidationPlan":
        if payload.get("schema") != PHYSICAL_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported physical-plan schema.")
        result = cls(
            evidence_role_digest=str(payload["evidence_role_digest"]),
            split_exclusion_digest=str(payload["split_exclusion_digest"]),
            policy_digest=str(payload["policy_digest"]),
            strain_magnitudes=tuple(payload.get("strain_magnitudes", ())),
            bases=tuple(PhysicalValidationBase.from_dict(v) for v in payload["bases"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Physical-plan digest mismatch.")
        return result


def _deterministic_atom_indices(atom_count: int, wanted: int) -> tuple[int, ...]:
    """Evenly spaced atom indices: deterministic and independent of any model."""

    wanted = max(1, min(int(wanted), int(atom_count)))
    stride = atom_count / wanted
    indices = sorted({min(atom_count - 1, int(index * stride)) for index in range(wanted)})
    return tuple(indices)


def build_physical_validation_plan(
    context: Any,
    *,
    evidence_roles: EvidenceRoleMembership,
    specification: Any,
) -> PhysicalValidationPlan:
    """Select bounded, correlation-aware, condition-spread OUTER_MONITOR bases.

    Conditions are visited round-robin so a single thermodynamic condition
    cannot dominate the plan, units inside a condition are taken in canonical
    order, and each unit contributes its temporal midpoint frame - the sample
    least correlated with the unit's boundaries.
    """

    policy = specification.component_policy(COMPONENT_PHYSICAL_PES)
    authorities = context.selected.authorities
    base_units = {unit.unit_id: unit for unit in authorities.neutral_base.unit_catalog.units}
    selected_frames = set(context.selected.selected_membership)

    by_condition: dict[str, list[Any]] = {}
    for unit_id in evidence_roles.outer_monitor_unit_ids:
        unit = base_units[unit_id]
        key = str(getattr(unit.condition, "content_digest", unit.condition))
        by_condition.setdefault(key, []).append(unit)
    for units in by_condition.values():
        units.sort(key=lambda item: item.unit_id)

    ordered_conditions = sorted(by_condition)
    wanted = int(policy["base_count"])
    chosen: list[Any] = []
    depth = 0
    while len(chosen) < wanted:
        progressed = False
        for key in ordered_conditions:
            units = by_condition[key]
            if depth < len(units):
                chosen.append((key, units[depth]))
                progressed = True
                if len(chosen) == wanted:
                    break
        if not progressed:
            break
        depth += 1

    index = authorities.frame_array_index
    bases: list[PhysicalValidationBase] = []
    for condition_key, unit in chosen:
        frame_uids = [uid for uid in unit.frame_uids if uid not in selected_frames]
        if not frame_uids:
            continue
        frame_uid = frame_uids[len(frame_uids) // 2]
        entry = index.get(frame_uid)
        if entry is None:
            continue
        _record, frame_data, _local = entry
        atom_count = int(len(frame_data.atomic_numbers))
        bases.append(
            PhysicalValidationBase(
                frame_uid=frame_uid,
                unit_id=unit.unit_id,
                condition_key=condition_key,
                atom_count=atom_count,
                displaced_atom_indices=_deterministic_atom_indices(
                    atom_count, int(policy["displaced_atoms_per_base"])
                ),
                axes=_AXES,
                amplitudes_angstrom=tuple(float(v) for v in policy["displacement_amplitudes_angstrom"]),
            )
        )
    return PhysicalValidationPlan(
        evidence_role_digest=evidence_roles.outer_monitor_digest,
        split_exclusion_digest=authorities.split_exclusion.content_digest,
        policy_digest=digest({"physical": dict(policy)}),
        strain_magnitudes=tuple(float(v) for v in policy["strain_magnitudes"]),
        bases=tuple(bases),
    )


@dataclass(frozen=True, slots=True)
class ProductionQualificationPlan:
    """The one plan a qualification attempt executes, frozen before evidence."""

    binding: QualificationInputBinding
    physical_plan: PhysicalValidationPlan
    planned_components: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, QualificationInputBinding):
            raise TrainingDataInputError("A qualification plan requires its input binding.")
        if not isinstance(self.physical_plan, PhysicalValidationPlan):
            raise TrainingDataInputError("A qualification plan requires a physical validation plan.")
        components = tuple(str(v) for v in self.planned_components)
        if not components or len(set(components)) != len(components):
            raise TrainingDataInputError("Planned components must be unique and non-empty.")
        object.__setattr__(self, "planned_components", components)

    @property
    def selected_binding_digest(self) -> str:
        return self.binding.selected_binding_digest

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": QUALIFICATION_PLAN_SCHEMA,
            "binding_digest": self.binding.content_digest,
            "selected_binding_digest": self.binding.selected_binding_digest,
            "publication_digest": self.binding.publication_digest,
            "physical_plan_digest": self.physical_plan.content_digest,
            "planned_components": list(self.planned_components),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def attempt_identity(self) -> str:
        return self.binding.attempt_identity

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "binding": self.binding.to_dict(),
            "physical_plan": self.physical_plan.to_dict(),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionQualificationPlan":
        if payload.get("schema") != QUALIFICATION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported qualification-plan schema.")
        result = cls(
            binding=QualificationInputBinding.from_dict(payload["binding"]),
            physical_plan=PhysicalValidationPlan.from_dict(payload["physical_plan"]),
            planned_components=tuple(payload["planned_components"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Qualification-plan digest mismatch.")
        return result


def dynamics_bases(plan: ProductionQualificationPlan) -> tuple[PhysicalValidationBase, ...]:
    """Dynamics cases descend from the same candidate-independent bases."""

    policy = plan.binding.specification.component_policy(COMPONENT_DYNAMICS)
    count = max(1, int(policy["base_count"]))
    return plan.physical_plan.bases[:count]


__all__ = [
    "PHYSICAL_BASE_SCHEMA",
    "PHYSICAL_PLAN_SCHEMA",
    "QUALIFICATION_PLAN_SCHEMA",
    "PhysicalValidationBase",
    "PhysicalValidationPlan",
    "ProductionQualificationPlan",
    "build_physical_validation_plan",
    "dynamics_bases",
]
