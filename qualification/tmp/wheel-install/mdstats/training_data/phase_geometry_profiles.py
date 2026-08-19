"""Phase- and geometry-aware defaults for MLFF structural selection.

This module owns policy composition only. Numerical local-geometry kernels stay
in :mod:`mdstats.analysis.local_structure`; physical validation observables stay
in their authoritative analysis modules.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from mdstats.analysis.local_structure import LocalStructureFeaturePolicy

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .material_profiles import (
    MaterialGeometryKind,
    MaterialPhaseKind,
    MaterialProfileContracts,
)

PHASE_GEOMETRY_SELECTION_PLAN_SCHEMA = "mdstats.phase-geometry-selection-plan.v1"
PHASE_GEOMETRY_SELECTION_PLAN_VERSION = "mdstats.mlff-data9a7c.phase-geometry.2026-07.v1"
MLFF_DATA9A7C_PARSER_VERSION = "0.20.49a0"


class StructuralFeatureFamily(str, Enum):
    PAIR_DISTANCE = "pair_distance"
    RADIAL_ENVIRONMENT = "radial_environment"
    COORDINATION = "coordination"
    CONNECTIVITY = "connectivity"
    CHEMICAL_ENVIRONMENT = "chemical_environment"
    LOCAL_DENSITY = "local_density"
    ANGULAR_ENVIRONMENT = "angular_environment"
    ORIENTATIONAL_ORDER = "orientational_order"


class StructuralEventKind(str, Enum):
    LARGE_DISPLACEMENT = "large_atomic_displacement"
    COORDINATION_CHANGE = "smooth_coordination_change"
    NEIGHBOR_COUNT_CHANGE = "hard_neighbor_count_change"
    LOCAL_DENSITY_CHANGE = "local_density_change"
    ORIENTATIONAL_ORDER_CHANGE = "orientational_order_change"


_PHASE_FEATURES: dict[MaterialPhaseKind, tuple[StructuralFeatureFamily, ...]] = {
    MaterialPhaseKind.CRYSTALLINE_SOLID: tuple(StructuralFeatureFamily),
    MaterialPhaseKind.AMORPHOUS_SOLID: tuple(StructuralFeatureFamily),
    MaterialPhaseKind.LIQUID: tuple(StructuralFeatureFamily),
    MaterialPhaseKind.MOLECULAR_OR_GAS: (
        StructuralFeatureFamily.PAIR_DISTANCE,
        StructuralFeatureFamily.RADIAL_ENVIRONMENT,
        StructuralFeatureFamily.COORDINATION,
        StructuralFeatureFamily.CONNECTIVITY,
        StructuralFeatureFamily.CHEMICAL_ENVIRONMENT,
        StructuralFeatureFamily.LOCAL_DENSITY,
        StructuralFeatureFamily.ANGULAR_ENVIRONMENT,
    ),
    MaterialPhaseKind.OTHER: tuple(StructuralFeatureFamily),
}

_PHASE_EVENTS: dict[MaterialPhaseKind, tuple[StructuralEventKind, ...]] = {
    MaterialPhaseKind.CRYSTALLINE_SOLID: (
        StructuralEventKind.LARGE_DISPLACEMENT,
        StructuralEventKind.COORDINATION_CHANGE,
        StructuralEventKind.NEIGHBOR_COUNT_CHANGE,
        StructuralEventKind.LOCAL_DENSITY_CHANGE,
        StructuralEventKind.ORIENTATIONAL_ORDER_CHANGE,
    ),
    MaterialPhaseKind.AMORPHOUS_SOLID: tuple(StructuralEventKind),
    MaterialPhaseKind.LIQUID: tuple(StructuralEventKind),
    MaterialPhaseKind.MOLECULAR_OR_GAS: (
        StructuralEventKind.LARGE_DISPLACEMENT,
        StructuralEventKind.COORDINATION_CHANGE,
        StructuralEventKind.NEIGHBOR_COUNT_CHANGE,
        StructuralEventKind.LOCAL_DENSITY_CHANGE,
    ),
    MaterialPhaseKind.OTHER: tuple(StructuralEventKind),
}

_PHASE_OBSERVABLE_PROFILES: dict[MaterialPhaseKind, str] = {
    MaterialPhaseKind.CRYSTALLINE_SOLID: "crystalline_solid",
    MaterialPhaseKind.AMORPHOUS_SOLID: "amorphous_solid",
    MaterialPhaseKind.LIQUID: "liquid",
    MaterialPhaseKind.MOLECULAR_OR_GAS: "generic_condensed",
    MaterialPhaseKind.OTHER: "generic_condensed",
}

_GEOMETRY_ROLE_PRIORITIES: dict[MaterialGeometryKind, tuple[str, ...]] = {
    MaterialGeometryKind.BULK: ("bulk_like", "all_atoms"),
    MaterialGeometryKind.SURFACE: ("surface", "subsurface", "bulk_like", "all_atoms"),
    MaterialGeometryKind.INTERFACE: (
        "interface",
        "interfacial",
        "phase_bulk",
        "surface",
        "subsurface",
        "all_atoms",
    ),
    MaterialGeometryKind.CONFINED: (
        "guest",
        "confined",
        "host",
        "confining",
        "interface",
        "all_atoms",
    ),
    MaterialGeometryKind.CLUSTER: ("surface", "core", "all_atoms"),
    MaterialGeometryKind.OTHER: ("all_atoms",),
}


@dataclass(frozen=True, slots=True)
class PhaseGeometrySelectionPlan:
    material_profile_contracts_digest: str
    material_profile_digest: str
    phase_kinds: tuple[str, ...]
    geometry: MaterialGeometryKind
    feature_families: tuple[str, ...]
    event_types: tuple[str, ...]
    priority_group_ids: tuple[str, ...]
    priority_group_roles: tuple[str, ...]
    observable_recommendation_profiles: tuple[str, ...]
    local_structure_policy: LocalStructureFeaturePolicy
    aggregate_statistics: tuple[str, ...]
    warning_codes: tuple[str, ...] = ()
    plan_version: str = PHASE_GEOMETRY_SELECTION_PLAN_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "material_profile_contracts_digest",
            validate_digest(self.material_profile_contracts_digest, name="material_profile_contracts_digest"),
        )
        object.__setattr__(
            self,
            "material_profile_digest",
            validate_digest(self.material_profile_digest, name="material_profile_digest"),
        )
        phase_kinds = tuple(sorted({MaterialPhaseKind(value).value for value in self.phase_kinds}))
        if not phase_kinds:
            raise TrainingDataInputError("Phase/geometry plans require at least one phase kind.")
        object.__setattr__(self, "phase_kinds", phase_kinds)
        object.__setattr__(self, "geometry", MaterialGeometryKind(self.geometry))
        features = tuple(sorted({StructuralFeatureFamily(value).value for value in self.feature_families}))
        events = tuple(sorted({StructuralEventKind(value).value for value in self.event_types}))
        if not features:
            raise TrainingDataInputError("Phase/geometry plans require structural feature families.")
        object.__setattr__(self, "feature_families", features)
        object.__setattr__(self, "event_types", events)
        object.__setattr__(self, "priority_group_ids", tuple(dict.fromkeys(str(v) for v in self.priority_group_ids)))
        object.__setattr__(self, "priority_group_roles", tuple(dict.fromkeys(str(v) for v in self.priority_group_roles)))
        object.__setattr__(
            self,
            "observable_recommendation_profiles",
            tuple(sorted(set(str(v) for v in self.observable_recommendation_profiles))),
        )
        if not isinstance(self.local_structure_policy, LocalStructureFeaturePolicy):
            raise TrainingDataInputError("local_structure_policy has the wrong type.")
        statistics = tuple(str(value) for value in self.aggregate_statistics)
        allowed_statistics = {"mean", "std", "min", "max", "q10", "q50", "q90"}
        if not statistics or len(set(statistics)) != len(statistics) or any(v not in allowed_statistics for v in statistics):
            raise TrainingDataInputError("Phase/geometry aggregate statistics are invalid.")
        object.__setattr__(self, "aggregate_statistics", statistics)
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(v) for v in self.warning_codes))))
        if not str(self.plan_version).strip():
            raise TrainingDataInputError("plan_version must be non-empty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PHASE_GEOMETRY_SELECTION_PLAN_SCHEMA,
            "parser_version": MLFF_DATA9A7C_PARSER_VERSION,
            "plan_version": self.plan_version,
            "material_profile_contracts_digest": self.material_profile_contracts_digest,
            "material_profile_digest": self.material_profile_digest,
            "phase_kinds": list(self.phase_kinds),
            "geometry": self.geometry.value,
            "feature_families": list(self.feature_families),
            "event_types": list(self.event_types),
            "priority_group_ids": list(self.priority_group_ids),
            "priority_group_roles": list(self.priority_group_roles),
            "observable_recommendation_profiles": list(self.observable_recommendation_profiles),
            "local_structure_policy": self.local_structure_policy.to_dict(),
            "aggregate_statistics": list(self.aggregate_statistics),
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PhaseGeometrySelectionPlan":
        if payload.get("schema") != PHASE_GEOMETRY_SELECTION_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported phase/geometry selection-plan schema.")
        if payload.get("parser_version") not in (None, MLFF_DATA9A7C_PARSER_VERSION):
            raise TrainingDataSerializationError("Unsupported phase/geometry selection-plan parser version.")
        result = cls(
            material_profile_contracts_digest=str(payload["material_profile_contracts_digest"]),
            material_profile_digest=str(payload["material_profile_digest"]),
            phase_kinds=tuple(str(v) for v in payload["phase_kinds"]),
            geometry=MaterialGeometryKind(str(payload["geometry"])),
            feature_families=tuple(str(v) for v in payload["feature_families"]),
            event_types=tuple(str(v) for v in payload["event_types"]),
            priority_group_ids=tuple(str(v) for v in payload.get("priority_group_ids", ())),
            priority_group_roles=tuple(str(v) for v in payload.get("priority_group_roles", ())),
            observable_recommendation_profiles=tuple(
                str(v) for v in payload.get("observable_recommendation_profiles", ())
            ),
            local_structure_policy=LocalStructureFeaturePolicy.from_dict(payload["local_structure_policy"]),
            aggregate_statistics=tuple(str(v) for v in payload["aggregate_statistics"]),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
            plan_version=str(payload.get("plan_version", PHASE_GEOMETRY_SELECTION_PLAN_VERSION)),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Phase/geometry selection-plan digest mismatch.")
        return result


def _local_policy_for_phase_kinds(phase_kinds: set[MaterialPhaseKind]) -> LocalStructureFeaturePolicy:
    """Return transparent, conservative numerical defaults for the phase union."""

    disordered = bool({MaterialPhaseKind.AMORPHOUS_SOLID, MaterialPhaseKind.LIQUID} & phase_kinds)
    molecular_only = phase_kinds <= {MaterialPhaseKind.MOLECULAR_OR_GAS}
    if disordered:
        return LocalStructureFeaturePolicy(
            normalized_switch_start=1.10,
            normalized_switch_end=1.90,
            radial_centers_angstrom=(1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0),
            radial_width_angstrom=0.40,
            density_radius_angstrom=5.0,
        )
    if molecular_only:
        return LocalStructureFeaturePolicy(
            normalized_switch_start=1.10,
            normalized_switch_end=1.70,
            radial_centers_angstrom=(0.8, 1.2, 1.6, 2.0, 2.5, 3.0, 4.0),
            radial_width_angstrom=0.30,
            density_radius_angstrom=4.0,
            orientational_orders=(4, 6),
        )
    return LocalStructureFeaturePolicy()


def derive_phase_geometry_selection_plan(
    contracts: MaterialProfileContracts,
) -> PhaseGeometrySelectionPlan:
    """Derive deterministic selection defaults from explicit user contracts.

    The result is advisory policy evidence, not automatic material inference.
    Users may override the resulting universal structural policy explicitly.
    """

    profile = contracts.profile
    phase_kinds = {phase.phase_kind for phase in profile.phases}
    feature_families = {
        family
        for phase_kind in phase_kinds
        for family in _PHASE_FEATURES[phase_kind]
    }
    event_types = {
        event
        for phase_kind in phase_kinds
        for event in _PHASE_EVENTS[phase_kind]
    }
    if profile.geometry in {MaterialGeometryKind.SURFACE, MaterialGeometryKind.INTERFACE, MaterialGeometryKind.CONFINED}:
        feature_families.update(
            {
                StructuralFeatureFamily.COORDINATION,
                StructuralFeatureFamily.CONNECTIVITY,
                StructuralFeatureFamily.LOCAL_DENSITY,
                StructuralFeatureFamily.CHEMICAL_ENVIRONMENT,
            }
        )
        event_types.update(
            {
                StructuralEventKind.LARGE_DISPLACEMENT,
                StructuralEventKind.COORDINATION_CHANGE,
                StructuralEventKind.LOCAL_DENSITY_CHANGE,
            }
        )

    role_order = _GEOMETRY_ROLE_PRIORITIES[profile.geometry]
    groups = contracts.atom_groups.groups
    priority_groups: list[str] = []
    for role in role_order:
        for group in groups:
            if role in group.roles and group.group_id not in priority_groups:
                priority_groups.append(group.group_id)
    # Phase-defining groups are always scientifically important and provide the
    # fallback when optional surface/interface roles were not declared.
    for phase in profile.phases:
        for group_id in phase.atom_group_ids:
            if group_id not in priority_groups:
                priority_groups.append(group_id)

    warnings: list[str] = []
    declared_roles = {role for group in groups for role in group.roles}
    if profile.geometry is MaterialGeometryKind.SURFACE and not declared_roles.intersection({"surface", "subsurface"}):
        warnings.append("surface_region_groups_not_declared")
    if profile.geometry is MaterialGeometryKind.INTERFACE and not declared_roles.intersection({"interface", "interfacial"}):
        warnings.append("interface_region_group_not_declared")
    if profile.geometry is MaterialGeometryKind.CONFINED and not declared_roles.intersection({"guest", "confined", "host", "confining"}):
        warnings.append("confinement_role_groups_not_declared")

    recommendation_profiles = {_PHASE_OBSERVABLE_PROFILES[kind] for kind in phase_kinds}
    if profile.geometry is MaterialGeometryKind.INTERFACE:
        recommendation_profiles.add("interface")

    return PhaseGeometrySelectionPlan(
        material_profile_contracts_digest=contracts.content_digest,
        material_profile_digest=profile.content_digest,
        phase_kinds=tuple(kind.value for kind in phase_kinds),
        geometry=profile.geometry,
        feature_families=tuple(family.value for family in feature_families),
        event_types=tuple(event.value for event in event_types),
        priority_group_ids=tuple(priority_groups),
        priority_group_roles=role_order,
        observable_recommendation_profiles=tuple(recommendation_profiles),
        local_structure_policy=_local_policy_for_phase_kinds(phase_kinds),
        aggregate_statistics=("mean", "std", "min", "max", "q10", "q50", "q90"),
        warning_codes=tuple(warnings),
    )


def recommended_observable_profile_ids(
    contracts: MaterialProfileContracts,
) -> tuple[str, ...]:
    """Return advisory observable-call profile IDs for the compositional profile."""

    return derive_phase_geometry_selection_plan(contracts).observable_recommendation_profiles


def universal_structural_policy_from_plan(
    plan: PhaseGeometrySelectionPlan,
    *,
    override: Any | None = None,
) -> Any:
    """Bind a universal structural policy to one phase/geometry plan.

    ``Any`` avoids an import cycle in the public contract module; the returned
    object is ``UniversalStructuralSelectionPolicy``.
    """

    from .structural_selection import UniversalStructuralSelectionPolicy

    if override is None:
        return UniversalStructuralSelectionPolicy(
            local_structure_policy=plan.local_structure_policy,
            aggregate_statistics=plan.aggregate_statistics,
            enabled_feature_families=plan.feature_families,
            enabled_event_types=plan.event_types,
            phase_geometry_plan_digest=plan.content_digest,
        )
    if not isinstance(override, UniversalStructuralSelectionPolicy):
        raise TrainingDataInputError("override has the wrong universal-structural policy type.")
    if override.phase_geometry_plan_digest not in (None, plan.content_digest):
        raise TrainingDataInputError("Universal structural policy belongs to a different phase/geometry plan.")
    return UniversalStructuralSelectionPolicy(
        local_structure_policy=override.local_structure_policy,
        aggregate_statistics=override.aggregate_statistics,
        include_declared_atom_groups=override.include_declared_atom_groups,
        include_element_groups=override.include_element_groups,
        materialize_atomic_environments=override.materialize_atomic_environments,
        displacement_event_threshold_angstrom=override.displacement_event_threshold_angstrom,
        coordination_event_threshold=override.coordination_event_threshold,
        hard_neighbor_event_threshold=override.hard_neighbor_event_threshold,
        density_event_threshold_angstrom3_inv=override.density_event_threshold_angstrom3_inv,
        orientational_event_threshold=override.orientational_event_threshold,
        maximum_source_frame_gap=override.maximum_source_frame_gap,
        missing_value_fill=override.missing_value_fill,
        enabled_feature_families=override.enabled_feature_families,
        enabled_event_types=override.enabled_event_types,
        phase_geometry_plan_digest=plan.content_digest,
        policy_version=override.policy_version,
    )
