"""Partition-independent physical feature records for MLFF-DATA4."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from ase.data import atomic_masses, chemical_symbols

from .resources import isolated_process_map
from .progress_timing import format_progress_fraction
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .eligibility import FrameEligibilityState

PAIR_FEATURE_RULE_SCHEMA = "mdstats.pair-feature-rule.v1"
RAW_FEATURE_POLICY_SCHEMA = "mdstats.raw-feature-policy.v1"
SPECIES_FORCE_STATISTICS_SCHEMA = "mdstats.species-force-statistics.v1"
PAIR_GEOMETRY_STATISTICS_SCHEMA = "mdstats.pair-geometry-statistics.v1"
RAW_FRAME_FEATURE_SCHEMA = "mdstats.raw-frame-feature.v1"
RAW_FEATURE_CATALOG_SCHEMA = "mdstats.raw-feature-catalog.v1"
RAW_FEATURE_POLICY_VERSION = "mdstats.mlff-data4.raw-feature.2026-07.v1"
MLFF_DATA4_PARSER_VERSION = "0.20.32a0"

_AMU_PER_A3_TO_G_PER_CM3 = 1.66053906660


def _finite_positive(value: float, *, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result <= 0.0:
        raise TrainingDataInputError(f"{name} must be finite and positive.")
    return result


def _optional_finite(value: Any, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not np.isfinite(result):
        raise TrainingDataInputError(f"{name} must be finite when present.")
    return result


def _optional_nonnegative(value: Any, *, name: str) -> float | None:
    result = _optional_finite(value, name=name)
    if result is not None and result < 0.0:
        raise TrainingDataInputError(f"{name} must be nonnegative when present.")
    return result


def _tuple3(value: Sequence[float], *, name: str) -> tuple[float, float, float]:
    result = tuple(float(v) for v in value)
    if len(result) != 3 or any(not np.isfinite(v) for v in result):
        raise TrainingDataInputError(f"{name} must contain three finite values.")
    return result  # type: ignore[return-value]


@dataclass(frozen=True, slots=True)
class PairFeatureRule:
    rule_id: str
    center_atomic_number: int
    neighbor_atomic_number: int
    coordination_cutoff_angstrom: float | None = None
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.rule_id.strip():
            raise TrainingDataInputError("rule_id must be non-empty.")
        if self.center_atomic_number <= 0 or self.neighbor_atomic_number <= 0:
            raise TrainingDataInputError("Atomic numbers must be positive.")
        object.__setattr__(
            self,
            "coordination_cutoff_angstrom",
            None
            if self.coordination_cutoff_angstrom is None
            else _finite_positive(
                self.coordination_cutoff_angstrom,
                name="coordination_cutoff_angstrom",
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PAIR_FEATURE_RULE_SCHEMA,
            "rule_id": self.rule_id,
            "center_atomic_number": self.center_atomic_number,
            "neighbor_atomic_number": self.neighbor_atomic_number,
            "coordination_cutoff_angstrom": self.coordination_cutoff_angstrom,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PairFeatureRule":
        if payload.get("schema") != PAIR_FEATURE_RULE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported pair-feature-rule schema.")
        result = cls(
            rule_id=str(payload["rule_id"]),
            center_atomic_number=int(payload["center_atomic_number"]),
            neighbor_atomic_number=int(payload["neighbor_atomic_number"]),
            coordination_cutoff_angstrom=(
                None
                if payload.get("coordination_cutoff_angstrom") is None
                else float(payload["coordination_cutoff_angstrom"])
            ),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("Pair-feature-rule digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RawFeaturePolicy:
    pair_rules: tuple[PairFeatureRule, ...] = ()
    force_quantiles: tuple[float, ...] = (0.5, 0.9, 0.95, 0.99)
    minimum_cell_volume_angstrom3: float = 1.0e-8
    pair_distance_zero_tolerance_angstrom: float = 1.0e-10
    stress_convention: str = "ase-positive-tension-ev-per-angstrom3"
    mass_table_identity: str = "ase.atomic_masses"
    policy_version: str = RAW_FEATURE_POLICY_VERSION

    def __post_init__(self) -> None:
        rules = tuple(sorted(self.pair_rules, key=lambda item: item.rule_id))
        if len({item.rule_id for item in rules}) != len(rules):
            raise TrainingDataInputError("Pair-feature rule IDs must be unique.")
        quantiles = tuple(float(v) for v in self.force_quantiles)
        if not quantiles or any(not 0.0 < v < 1.0 for v in quantiles):
            raise TrainingDataInputError("force_quantiles must lie strictly between zero and one.")
        if tuple(sorted(set(quantiles))) != quantiles:
            raise TrainingDataInputError("force_quantiles must be strictly increasing and unique.")
        object.__setattr__(self, "pair_rules", rules)
        object.__setattr__(self, "force_quantiles", quantiles)
        object.__setattr__(
            self,
            "minimum_cell_volume_angstrom3",
            _finite_positive(
                self.minimum_cell_volume_angstrom3,
                name="minimum_cell_volume_angstrom3",
            ),
        )
        object.__setattr__(
            self,
            "pair_distance_zero_tolerance_angstrom",
            _finite_positive(
                self.pair_distance_zero_tolerance_angstrom,
                name="pair_distance_zero_tolerance_angstrom",
            ),
        )
        if not self.stress_convention.strip() or not self.mass_table_identity.strip() or not self.policy_version.strip():
            raise TrainingDataInputError("Raw-feature policy identifiers must be non-empty.")

    @classmethod
    def lta_default(cls) -> "RawFeaturePolicy":
        # Coarse partitioning cutoffs; they are policy values, not experimental bond claims.
        return cls(
            pair_rules=(
                PairFeatureRule("al-o", 13, 8, 2.35),
                PairFeatureRule("k-o", 19, 8, 3.75),
                PairFeatureRule("li-o", 3, 8, 2.85),
                PairFeatureRule("na-o", 11, 8, 3.35),
                PairFeatureRule("si-o", 14, 8, 2.20),
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": RAW_FEATURE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "pair_rules": [item.to_dict() for item in self.pair_rules],
            "force_quantiles": list(self.force_quantiles),
            "minimum_cell_volume_angstrom3": self.minimum_cell_volume_angstrom3,
            "pair_distance_zero_tolerance_angstrom": self.pair_distance_zero_tolerance_angstrom,
            "stress_convention": self.stress_convention,
            "mass_table_identity": self.mass_table_identity,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RawFeaturePolicy":
        if payload.get("schema") != RAW_FEATURE_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported raw-feature policy schema.")
        result = cls(
            pair_rules=tuple(PairFeatureRule.from_dict(item) for item in payload.get("pair_rules", ())),
            force_quantiles=tuple(float(v) for v in payload["force_quantiles"]),
            minimum_cell_volume_angstrom3=float(payload["minimum_cell_volume_angstrom3"]),
            pair_distance_zero_tolerance_angstrom=float(payload["pair_distance_zero_tolerance_angstrom"]),
            stress_convention=str(payload["stress_convention"]),
            mass_table_identity=str(payload["mass_table_identity"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Raw-feature policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SpeciesForceStatistics:
    atomic_number: int
    symbol: str
    atom_count: int
    component_rms_ev_per_angstrom: float
    norm_mean_ev_per_angstrom: float
    norm_max_ev_per_angstrom: float
    norm_quantiles_ev_per_angstrom: tuple[tuple[str, float], ...]
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.atomic_number <= 0 or self.atom_count <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid species-force identity.")
        for name in (
            "component_rms_ev_per_angstrom",
            "norm_mean_ev_per_angstrom",
            "norm_max_ev_per_angstrom",
        ):
            object.__setattr__(self, name, _optional_nonnegative(getattr(self, name), name=name))
        quantiles = tuple((str(key), _optional_nonnegative(value, name="force quantile")) for key, value in self.norm_quantiles_ev_per_angstrom)
        if any(value is None for _, value in quantiles):
            raise TrainingDataInputError("Species force quantiles cannot be missing.")
        object.__setattr__(self, "norm_quantiles_ev_per_angstrom", tuple((key, float(value)) for key, value in quantiles if value is not None))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SPECIES_FORCE_STATISTICS_SCHEMA,
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "atom_count": self.atom_count,
            "component_rms_ev_per_angstrom": self.component_rms_ev_per_angstrom,
            "norm_mean_ev_per_angstrom": self.norm_mean_ev_per_angstrom,
            "norm_max_ev_per_angstrom": self.norm_max_ev_per_angstrom,
            "norm_quantiles_ev_per_angstrom": dict(self.norm_quantiles_ev_per_angstrom),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SpeciesForceStatistics":
        if payload.get("schema") != SPECIES_FORCE_STATISTICS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported species-force-statistics schema.")
        result = cls(
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            atom_count=int(payload["atom_count"]),
            component_rms_ev_per_angstrom=float(payload["component_rms_ev_per_angstrom"]),
            norm_mean_ev_per_angstrom=float(payload["norm_mean_ev_per_angstrom"]),
            norm_max_ev_per_angstrom=float(payload["norm_max_ev_per_angstrom"]),
            norm_quantiles_ev_per_angstrom=tuple(sorted((str(k), float(v)) for k, v in payload["norm_quantiles_ev_per_angstrom"].items())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("Species-force-statistics digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class PairGeometryStatistics:
    rule_id: str
    center_atomic_number: int
    neighbor_atomic_number: int
    center_count: int
    neighbor_count: int
    minimum_pair_distance_angstrom: float | None
    mean_nearest_neighbor_distance_angstrom: float | None
    maximum_nearest_neighbor_distance_angstrom: float | None
    coordination_cutoff_angstrom: float | None
    coordination_mean: float | None
    coordination_maximum: int | None
    warning_codes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        if not self.rule_id.strip() or self.center_atomic_number <= 0 or self.neighbor_atomic_number <= 0:
            raise TrainingDataInputError("Invalid pair-geometry identity.")
        if self.center_count < 0 or self.neighbor_count < 0:
            raise TrainingDataInputError("Pair counts must be nonnegative.")
        for name in (
            "minimum_pair_distance_angstrom",
            "mean_nearest_neighbor_distance_angstrom",
            "maximum_nearest_neighbor_distance_angstrom",
            "coordination_cutoff_angstrom",
            "coordination_mean",
        ):
            object.__setattr__(self, name, _optional_nonnegative(getattr(self, name), name=name))
        if self.coordination_maximum is not None and self.coordination_maximum < 0:
            raise TrainingDataInputError("coordination_maximum must be nonnegative.")
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(v) for v in self.warning_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PAIR_GEOMETRY_STATISTICS_SCHEMA,
            "rule_id": self.rule_id,
            "center_atomic_number": self.center_atomic_number,
            "neighbor_atomic_number": self.neighbor_atomic_number,
            "center_count": self.center_count,
            "neighbor_count": self.neighbor_count,
            "minimum_pair_distance_angstrom": self.minimum_pair_distance_angstrom,
            "mean_nearest_neighbor_distance_angstrom": self.mean_nearest_neighbor_distance_angstrom,
            "maximum_nearest_neighbor_distance_angstrom": self.maximum_nearest_neighbor_distance_angstrom,
            "coordination_cutoff_angstrom": self.coordination_cutoff_angstrom,
            "coordination_mean": self.coordination_mean,
            "coordination_maximum": self.coordination_maximum,
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PairGeometryStatistics":
        if payload.get("schema") != PAIR_GEOMETRY_STATISTICS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported pair-geometry-statistics schema.")
        result = cls(
            rule_id=str(payload["rule_id"]),
            center_atomic_number=int(payload["center_atomic_number"]),
            neighbor_atomic_number=int(payload["neighbor_atomic_number"]),
            center_count=int(payload["center_count"]),
            neighbor_count=int(payload["neighbor_count"]),
            minimum_pair_distance_angstrom=None if payload.get("minimum_pair_distance_angstrom") is None else float(payload["minimum_pair_distance_angstrom"]),
            mean_nearest_neighbor_distance_angstrom=None if payload.get("mean_nearest_neighbor_distance_angstrom") is None else float(payload["mean_nearest_neighbor_distance_angstrom"]),
            maximum_nearest_neighbor_distance_angstrom=None if payload.get("maximum_nearest_neighbor_distance_angstrom") is None else float(payload["maximum_nearest_neighbor_distance_angstrom"]),
            coordination_cutoff_angstrom=None if payload.get("coordination_cutoff_angstrom") is None else float(payload["coordination_cutoff_angstrom"]),
            coordination_mean=None if payload.get("coordination_mean") is None else float(payload["coordination_mean"]),
            coordination_maximum=None if payload.get("coordination_maximum") is None else int(payload["coordination_maximum"]),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("Pair-geometry-statistics digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RawFrameFeatureRecord:
    frame_uid: str
    frame_record_digest: str
    policy_digest: str
    eligibility_state: str
    energy_total_ev: float | None
    energy_per_atom_ev: float | None
    instantaneous_temperature_kelvin: float | None
    cell_volume_angstrom3: float
    mass_density_g_cm3: float
    cell_lengths_angstrom: tuple[float, float, float]
    cell_angles_degrees: tuple[float, float, float]
    force_component_rms_ev_per_angstrom: float | None
    force_norm_mean_ev_per_angstrom: float | None
    force_norm_max_ev_per_angstrom: float | None
    force_norm_quantiles_ev_per_angstrom: tuple[tuple[str, float], ...]
    pressure_ev_per_angstrom3: float | None
    stress_deviatoric_norm_ev_per_angstrom3: float | None
    stress_von_mises_ev_per_angstrom3: float | None
    hydrostatic_strain: float | None
    deviatoric_strain_norm: float | None
    engineering_shear: tuple[float, float, float] | None
    species_force_statistics: tuple[SpeciesForceStatistics, ...]
    pair_geometry_statistics: tuple[PairGeometryStatistics, ...]
    warning_codes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_uid", "frame_record_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "cell_volume_angstrom3", _finite_positive(self.cell_volume_angstrom3, name="cell_volume_angstrom3"))
        object.__setattr__(self, "mass_density_g_cm3", _finite_positive(self.mass_density_g_cm3, name="mass_density_g_cm3"))
        object.__setattr__(self, "cell_lengths_angstrom", _tuple3(self.cell_lengths_angstrom, name="cell_lengths_angstrom"))
        object.__setattr__(self, "cell_angles_degrees", _tuple3(self.cell_angles_degrees, name="cell_angles_degrees"))
        for name in (
            "energy_total_ev", "energy_per_atom_ev", "instantaneous_temperature_kelvin",
            "force_component_rms_ev_per_angstrom", "force_norm_mean_ev_per_angstrom",
            "force_norm_max_ev_per_angstrom", "pressure_ev_per_angstrom3",
            "stress_deviatoric_norm_ev_per_angstrom3", "stress_von_mises_ev_per_angstrom3",
            "hydrostatic_strain", "deviatoric_strain_norm",
        ):
            object.__setattr__(self, name, _optional_finite(getattr(self, name), name=name))
        if self.engineering_shear is not None:
            object.__setattr__(self, "engineering_shear", _tuple3(self.engineering_shear, name="engineering_shear"))
        quantiles = tuple(sorted((str(k), float(v)) for k, v in self.force_norm_quantiles_ev_per_angstrom))
        if any(not np.isfinite(v) or v < 0.0 for _, v in quantiles):
            raise TrainingDataInputError("Force quantiles must be finite and nonnegative.")
        object.__setattr__(self, "force_norm_quantiles_ev_per_angstrom", quantiles)
        object.__setattr__(self, "species_force_statistics", tuple(sorted(self.species_force_statistics, key=lambda item: item.atomic_number)))
        object.__setattr__(self, "pair_geometry_statistics", tuple(sorted(self.pair_geometry_statistics, key=lambda item: item.rule_id)))
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(v) for v in self.warning_codes))))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": RAW_FRAME_FEATURE_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "policy_digest": self.policy_digest,
            "eligibility_state": self.eligibility_state,
            "energy_total_ev": self.energy_total_ev,
            "energy_per_atom_ev": self.energy_per_atom_ev,
            "instantaneous_temperature_kelvin": self.instantaneous_temperature_kelvin,
            "cell_volume_angstrom3": self.cell_volume_angstrom3,
            "mass_density_g_cm3": self.mass_density_g_cm3,
            "cell_lengths_angstrom": list(self.cell_lengths_angstrom),
            "cell_angles_degrees": list(self.cell_angles_degrees),
            "force_component_rms_ev_per_angstrom": self.force_component_rms_ev_per_angstrom,
            "force_norm_mean_ev_per_angstrom": self.force_norm_mean_ev_per_angstrom,
            "force_norm_max_ev_per_angstrom": self.force_norm_max_ev_per_angstrom,
            "force_norm_quantiles_ev_per_angstrom": dict(self.force_norm_quantiles_ev_per_angstrom),
            "pressure_ev_per_angstrom3": self.pressure_ev_per_angstrom3,
            "stress_deviatoric_norm_ev_per_angstrom3": self.stress_deviatoric_norm_ev_per_angstrom3,
            "stress_von_mises_ev_per_angstrom3": self.stress_von_mises_ev_per_angstrom3,
            "hydrostatic_strain": self.hydrostatic_strain,
            "deviatoric_strain_norm": self.deviatoric_strain_norm,
            "engineering_shear": None if self.engineering_shear is None else list(self.engineering_shear),
            "species_force_statistics": [item.to_dict() for item in self.species_force_statistics],
            "pair_geometry_statistics": [item.to_dict() for item in self.pair_geometry_statistics],
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RawFrameFeatureRecord":
        if payload.get("schema") != RAW_FRAME_FEATURE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported raw-frame-feature schema.")
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            policy_digest=str(payload["policy_digest"]),
            eligibility_state=str(payload["eligibility_state"]),
            energy_total_ev=None if payload.get("energy_total_ev") is None else float(payload["energy_total_ev"]),
            energy_per_atom_ev=None if payload.get("energy_per_atom_ev") is None else float(payload["energy_per_atom_ev"]),
            instantaneous_temperature_kelvin=None if payload.get("instantaneous_temperature_kelvin") is None else float(payload["instantaneous_temperature_kelvin"]),
            cell_volume_angstrom3=float(payload["cell_volume_angstrom3"]),
            mass_density_g_cm3=float(payload["mass_density_g_cm3"]),
            cell_lengths_angstrom=tuple(float(v) for v in payload["cell_lengths_angstrom"]),
            cell_angles_degrees=tuple(float(v) for v in payload["cell_angles_degrees"]),
            force_component_rms_ev_per_angstrom=None if payload.get("force_component_rms_ev_per_angstrom") is None else float(payload["force_component_rms_ev_per_angstrom"]),
            force_norm_mean_ev_per_angstrom=None if payload.get("force_norm_mean_ev_per_angstrom") is None else float(payload["force_norm_mean_ev_per_angstrom"]),
            force_norm_max_ev_per_angstrom=None if payload.get("force_norm_max_ev_per_angstrom") is None else float(payload["force_norm_max_ev_per_angstrom"]),
            force_norm_quantiles_ev_per_angstrom=tuple(sorted((str(k), float(v)) for k, v in payload.get("force_norm_quantiles_ev_per_angstrom", {}).items())),
            pressure_ev_per_angstrom3=None if payload.get("pressure_ev_per_angstrom3") is None else float(payload["pressure_ev_per_angstrom3"]),
            stress_deviatoric_norm_ev_per_angstrom3=None if payload.get("stress_deviatoric_norm_ev_per_angstrom3") is None else float(payload["stress_deviatoric_norm_ev_per_angstrom3"]),
            stress_von_mises_ev_per_angstrom3=None if payload.get("stress_von_mises_ev_per_angstrom3") is None else float(payload["stress_von_mises_ev_per_angstrom3"]),
            hydrostatic_strain=None if payload.get("hydrostatic_strain") is None else float(payload["hydrostatic_strain"]),
            deviatoric_strain_norm=None if payload.get("deviatoric_strain_norm") is None else float(payload["deviatoric_strain_norm"]),
            engineering_shear=None if payload.get("engineering_shear") is None else tuple(float(v) for v in payload["engineering_shear"]),
            species_force_statistics=tuple(SpeciesForceStatistics.from_dict(item) for item in payload.get("species_force_statistics", ())),
            pair_geometry_statistics=tuple(PairGeometryStatistics.from_dict(item) for item in payload.get("pair_geometry_statistics", ())),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("Raw-frame-feature digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class RawFeatureCatalog:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    policy: RawFeaturePolicy
    records: tuple[RawFrameFeatureRecord, ...]
    _by_frame_uid: Mapping[str, RawFrameFeatureRecord] = field(default_factory=dict, init=False, repr=False, compare=False)
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_catalog_digest", validate_digest(self.source_catalog_digest, name="source_catalog_digest"))
        object.__setattr__(self, "frame_catalog_digest", validate_digest(self.frame_catalog_digest, name="frame_catalog_digest"))
        records = tuple(sorted(self.records, key=lambda item: item.frame_uid))
        if len({item.frame_uid for item in records}) != len(records):
            raise TrainingDataInputError("Raw feature frame UIDs must be unique.")
        if any(item.policy_digest != self.policy.policy_digest for item in records):
            raise TrainingDataInputError("Raw feature record policy mismatch.")
        object.__setattr__(self, "records", records)
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in records})

    def for_frame(self, frame_uid: str) -> RawFrameFeatureRecord:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": RAW_FEATURE_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "policy": self.policy.to_dict(),
            "records": [item.to_dict() for item in self.records],
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if cached is None:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RawFeatureCatalog":
        if payload.get("schema") != RAW_FEATURE_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported raw-feature-catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            policy=RawFeaturePolicy.from_dict(payload["policy"]),
            records=tuple(RawFrameFeatureRecord.from_dict(item) for item in payload.get("records", ())),
        )
        supplied_digest = payload.get("content_digest")
        if supplied_digest is not None and supplied_digest != result.content_digest:
            raise TrainingDataSerializationError("Raw-feature-catalog digest mismatch.")
        return result


def _cell_lengths_angles(cell: np.ndarray) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    lengths = np.linalg.norm(cell, axis=1)
    if np.any(lengths <= 0.0):
        raise TrainingDataInputError("Cell vectors must have positive length.")
    a, b, c = cell
    alpha = np.degrees(np.arccos(np.clip(np.dot(b, c) / (lengths[1] * lengths[2]), -1.0, 1.0)))
    beta = np.degrees(np.arccos(np.clip(np.dot(a, c) / (lengths[0] * lengths[2]), -1.0, 1.0)))
    gamma = np.degrees(np.arccos(np.clip(np.dot(a, b) / (lengths[0] * lengths[1]), -1.0, 1.0)))
    return tuple(float(v) for v in lengths), (float(alpha), float(beta), float(gamma))


def minimum_image_displacements(
    center_fractional: np.ndarray,
    neighbor_fractional: np.ndarray,
    *,
    cell: np.ndarray,
    pbc: np.ndarray,
) -> np.ndarray:
    """Return center-neighbor Cartesian displacement tensor under MIC."""

    delta = neighbor_fractional[None, :, :] - center_fractional[:, None, :]
    for axis in range(3):
        if bool(pbc[axis]):
            delta[..., axis] -= np.rint(delta[..., axis])
    return delta @ cell


def _pair_statistics_from_distances(
    *,
    rule: PairFeatureRule,
    center_indices: np.ndarray,
    neighbor_indices: np.ndarray,
    distances: np.ndarray | None,
    zero_tolerance: float,
) -> PairGeometryStatistics:
    warnings: list[str] = []
    if center_indices.size == 0:
        warnings.append("center_species_absent")
    if neighbor_indices.size == 0:
        warnings.append("neighbor_species_absent")
    if distances is None:
        return PairGeometryStatistics(
            rule_id=rule.rule_id,
            center_atomic_number=rule.center_atomic_number,
            neighbor_atomic_number=rule.neighbor_atomic_number,
            center_count=int(center_indices.size),
            neighbor_count=int(neighbor_indices.size),
            minimum_pair_distance_angstrom=None,
            mean_nearest_neighbor_distance_angstrom=None,
            maximum_nearest_neighbor_distance_angstrom=None,
            coordination_cutoff_angstrom=rule.coordination_cutoff_angstrom,
            coordination_mean=None,
            coordination_maximum=None,
            warning_codes=tuple(warnings),
        )
    finite = distances[np.isfinite(distances)]
    if finite.size == 0:
        warnings.append("no_distinct_pairs")
        return PairGeometryStatistics(
            rule_id=rule.rule_id,
            center_atomic_number=rule.center_atomic_number,
            neighbor_atomic_number=rule.neighbor_atomic_number,
            center_count=int(center_indices.size),
            neighbor_count=int(neighbor_indices.size),
            minimum_pair_distance_angstrom=None,
            mean_nearest_neighbor_distance_angstrom=None,
            maximum_nearest_neighbor_distance_angstrom=None,
            coordination_cutoff_angstrom=rule.coordination_cutoff_angstrom,
            coordination_mean=None,
            coordination_maximum=None,
            warning_codes=tuple(warnings),
        )
    minimum = float(np.min(finite))
    if minimum <= zero_tolerance:
        warnings.append("near_zero_pair_distance")
    nearest = np.min(distances, axis=1)
    nearest = nearest[np.isfinite(nearest)]
    coordination_mean = None
    coordination_maximum = None
    if rule.coordination_cutoff_angstrom is not None:
        counts = np.sum(distances <= rule.coordination_cutoff_angstrom, axis=1)
        coordination_mean = float(np.mean(counts))
        coordination_maximum = int(np.max(counts))
    return PairGeometryStatistics(
        rule_id=rule.rule_id,
        center_atomic_number=rule.center_atomic_number,
        neighbor_atomic_number=rule.neighbor_atomic_number,
        center_count=int(center_indices.size),
        neighbor_count=int(neighbor_indices.size),
        minimum_pair_distance_angstrom=minimum,
        mean_nearest_neighbor_distance_angstrom=float(np.mean(nearest)),
        maximum_nearest_neighbor_distance_angstrom=float(np.max(nearest)),
        coordination_cutoff_angstrom=rule.coordination_cutoff_angstrom,
        coordination_mean=coordination_mean,
        coordination_maximum=coordination_maximum,
        warning_codes=tuple(warnings),
    )


def _pair_statistics(
    *,
    atomic_numbers: np.ndarray,
    fractional_positions: np.ndarray,
    cell: np.ndarray,
    pbc: np.ndarray,
    rule: PairFeatureRule,
    zero_tolerance: float,
    center_indices: np.ndarray | None = None,
    neighbor_indices: np.ndarray | None = None,
) -> PairGeometryStatistics:
    if center_indices is None:
        center_indices = np.flatnonzero(
            atomic_numbers == rule.center_atomic_number
        )
    if neighbor_indices is None:
        neighbor_indices = np.flatnonzero(
            atomic_numbers == rule.neighbor_atomic_number
        )
    distances: np.ndarray | None = None
    if center_indices.size and neighbor_indices.size:
        displacement = minimum_image_displacements(
            fractional_positions[center_indices],
            fractional_positions[neighbor_indices],
            cell=cell,
            pbc=pbc,
        )
        distances = np.linalg.norm(displacement, axis=-1)
        if rule.center_atomic_number == rule.neighbor_atomic_number:
            same = center_indices[:, None] == neighbor_indices[None, :]
            distances[same] = np.inf
    return _pair_statistics_from_distances(
        rule=rule,
        center_indices=center_indices,
        neighbor_indices=neighbor_indices,
        distances=distances,
        zero_tolerance=zero_tolerance,
    )


def _quantile_items(values: np.ndarray, quantiles: Sequence[float]) -> tuple[tuple[str, float], ...]:
    # NumPy can partition for all requested quantiles in one call.  Calling
    # ``np.quantile`` once per percentile dominated the small per-species
    # arrays used by DATA4.
    q = np.asarray(tuple(float(value) for value in quantiles), dtype=np.float64)
    computed = np.asarray(np.quantile(values, q), dtype=np.float64).reshape(-1)
    return tuple(
        (f"q{int(round(level * 100)):02d}", float(value))
        for level, value in zip(q.tolist(), computed.tolist(), strict=True)
    )


def _species_force_statistics(
    atomic_numbers: np.ndarray,
    forces: np.ndarray,
    quantiles: Sequence[float],
    species_indices: Mapping[int, np.ndarray] | None = None,
) -> tuple[SpeciesForceStatistics, ...]:
    output: list[SpeciesForceStatistics] = []
    active_indices = (
        {int(z): np.flatnonzero(atomic_numbers == int(z)) for z in np.unique(atomic_numbers)}
        if species_indices is None else species_indices
    )
    for atomic_number in sorted(active_indices):
        selected = forces[active_indices[atomic_number]]
        norms = np.linalg.norm(selected, axis=1)
        output.append(
            SpeciesForceStatistics(
                atomic_number=atomic_number,
                symbol=chemical_symbols[atomic_number],
                atom_count=int(selected.shape[0]),
                component_rms_ev_per_angstrom=float(np.sqrt(np.mean(selected * selected))),
                norm_mean_ev_per_angstrom=float(np.mean(norms)),
                norm_max_ev_per_angstrom=float(np.max(norms)),
                norm_quantiles_ev_per_angstrom=_quantile_items(norms, quantiles),
            )
        )
    return tuple(output)



def _build_raw_features_for_run(task: tuple[Any, ...]) -> tuple[str, tuple[RawFrameFeatureRecord, ...]]:
    run_id, data, frame_by_source_index, strain_by_uid, decision_by_uid, active = task
    atomic_numbers = np.asarray(data.atomic_numbers, dtype=np.int32)
    pbc = np.asarray(data.pbc, dtype=np.bool_)
    mass_amu = float(np.sum(atomic_masses[atomic_numbers]))
    species_indices = {int(z): np.flatnonzero(atomic_numbers == int(z)) for z in np.unique(atomic_numbers)}
    pair_rule_groups: dict[tuple[int, int], list[PairFeatureRule]] = {}
    for rule in active.pair_rules:
        pair_rule_groups.setdefault(
            (rule.center_atomic_number, rule.neighbor_atomic_number), []
        ).append(rule)
    pair_indices = {
        key: (
            np.flatnonzero(atomic_numbers == key[0]),
            np.flatnonzero(atomic_numbers == key[1]),
        )
        for key in pair_rule_groups
    }
    records: list[RawFrameFeatureRecord] = []
    for local_index, source_index_value in enumerate(data.source_frame_indices):
        source_index = int(source_index_value)
        try:
            frame = frame_by_source_index[source_index]
        except KeyError as exc:
            raise TrainingDataInputError(
                f"FrameData occurrence {run_id}:{source_index} is absent from the frame catalog."
            ) from exc
        decision = decision_by_uid[frame.frame_uid]
        strain = strain_by_uid[frame.frame_uid]
        cell = np.asarray(data.cells_angstrom[local_index], dtype=np.float64)
        volume = float(np.linalg.det(cell))
        if not np.isfinite(volume) or volume <= active.minimum_cell_volume_angstrom3:
            raise TrainingDataInputError(f"Invalid cell volume for frame {frame.frame_uid}.")
        lengths, angles = _cell_lengths_angles(cell)
        density_g_cm3 = mass_amu / volume * _AMU_PER_A3_TO_G_PER_CM3
        warnings: list[str] = []

        energy = None if data.energies_ev is None else float(data.energies_ev[local_index])
        if energy is not None and not np.isfinite(energy):
            warnings.append("nonfinite_energy")
            energy = None
        temperature = None if data.temperatures_kelvin is None else float(data.temperatures_kelvin[local_index])
        if temperature is not None and not np.isfinite(temperature):
            warnings.append("nonfinite_temperature")
            temperature = None

        force_component_rms = force_norm_mean = force_norm_max = None
        force_quantiles: tuple[tuple[str, float], ...] = ()
        species_force: tuple[SpeciesForceStatistics, ...] = ()
        if data.forces_ev_per_angstrom is None:
            warnings.append("forces_absent")
        else:
            force_array = np.asarray(data.forces_ev_per_angstrom[local_index], dtype=np.float64)
            if np.any(~np.isfinite(force_array)):
                warnings.append("nonfinite_forces")
            else:
                norms = np.linalg.norm(force_array, axis=1)
                force_component_rms = float(np.sqrt(np.mean(force_array * force_array)))
                force_norm_mean = float(np.mean(norms))
                force_norm_max = float(np.max(norms))
                force_quantiles = _quantile_items(norms, active.force_quantiles)
                species_force = _species_force_statistics(
                    atomic_numbers, force_array, active.force_quantiles, species_indices,
                )

        pressure = deviatoric_norm = von_mises = None
        if data.stresses_ev_per_angstrom3 is None:
            warnings.append("stress_absent")
        else:
            stress = np.asarray(data.stresses_ev_per_angstrom3[local_index], dtype=np.float64)
            if np.any(~np.isfinite(stress)):
                warnings.append("nonfinite_stress")
            else:
                trace = float(np.trace(stress))
                pressure = -trace / 3.0
                deviatoric = stress - (trace / 3.0) * np.eye(3)
                deviatoric_norm = float(np.linalg.norm(deviatoric))
                von_mises = float(np.sqrt(1.5 * np.sum(deviatoric * deviatoric)))

        fractional_positions = np.asarray(
            data.fractional_positions[local_index], dtype=np.float64
        )
        pair_statistics_list: list[PairGeometryStatistics] = []
        for key, rules in pair_rule_groups.items():
            center_indices, neighbor_indices = pair_indices[key]
            distances: np.ndarray | None = None
            if center_indices.size and neighbor_indices.size:
                displacement = minimum_image_displacements(
                    fractional_positions[center_indices],
                    fractional_positions[neighbor_indices],
                    cell=cell,
                    pbc=pbc,
                )
                distances = np.linalg.norm(displacement, axis=-1)
                if key[0] == key[1]:
                    same = center_indices[:, None] == neighbor_indices[None, :]
                    distances[same] = np.inf
            pair_statistics_list.extend(
                _pair_statistics_from_distances(
                    rule=rule,
                    center_indices=center_indices,
                    neighbor_indices=neighbor_indices,
                    distances=distances,
                    zero_tolerance=active.pair_distance_zero_tolerance_angstrom,
                )
                for rule in rules
            )
        by_rule = {item.rule_id: item for item in pair_statistics_list}
        pair_statistics = tuple(by_rule[rule.rule_id] for rule in active.pair_rules)
        warnings.extend(
            f"pair:{item.rule_id}:{code}"
            for item in pair_statistics
            for code in item.warning_codes
        )
        records.append(
            RawFrameFeatureRecord(
                frame_uid=frame.frame_uid,
                frame_record_digest=frame.content_digest,
                policy_digest=active.policy_digest,
                eligibility_state=decision.state.value,
                energy_total_ev=energy,
                energy_per_atom_ev=None if energy is None else energy / frame.atom_count,
                instantaneous_temperature_kelvin=temperature,
                cell_volume_angstrom3=volume,
                mass_density_g_cm3=density_g_cm3,
                cell_lengths_angstrom=lengths,
                cell_angles_degrees=angles,
                force_component_rms_ev_per_angstrom=force_component_rms,
                force_norm_mean_ev_per_angstrom=force_norm_mean,
                force_norm_max_ev_per_angstrom=force_norm_max,
                force_norm_quantiles_ev_per_angstrom=force_quantiles,
                pressure_ev_per_angstrom3=pressure,
                stress_deviatoric_norm_ev_per_angstrom3=deviatoric_norm,
                stress_von_mises_ev_per_angstrom3=von_mises,
                hydrostatic_strain=None if strain.tensor_class.value == "unresolved" else strain.hydrostatic_logarithmic_strain,
                deviatoric_strain_norm=None if strain.tensor_class.value == "unresolved" else strain.deviatoric_norm,
                engineering_shear=None if strain.tensor_class.value == "unresolved" else strain.engineering_shear,
                species_force_statistics=species_force,
                pair_geometry_statistics=pair_statistics,
                warning_codes=tuple(warnings),
            )
        )
    return run_id, tuple(records)


def build_raw_feature_catalog(
    source_catalog: Any,
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    *,
    policy: RawFeaturePolicy | None = None,
    progress_callback: Callable[[str], None] | None = None,
    parallel_workers: int = 1,
) -> RawFeatureCatalog:
    """Compute partition-independent raw features for all DATA3 frame occurrences."""

    active = RawFeaturePolicy() if policy is None else policy
    source_ids = {item.run_id for item in source_catalog.sources}
    if set(frame_data_by_run) != source_ids:
        raise TrainingDataInputError("FrameData run IDs must exactly match the source catalog.")
    if frame_catalog.source_catalog_digest != source_catalog.content_digest:
        raise TrainingDataInputError("Frame/source catalog digest mismatch.")
    frames_by_run: dict[str, dict[int, Any]] = {run_id: {} for run_id in source_ids}
    for item in frame_catalog.frames:
        frames_by_run[item.run_id][item.source_frame_index] = item
    strain_all = {item.frame_uid: item for item in frame_catalog.strain_records}
    decision_all = {item.frame_uid: item for item in frame_catalog.eligibility.decisions}
    records: list[RawFrameFeatureRecord] = []
    ordered_run_ids = sorted(source_ids)
    tasks = []
    for run_id in ordered_run_ids:
        run_frames = frames_by_run[run_id]
        run_uids = {item.frame_uid for item in run_frames.values()}
        tasks.append((
            run_id,
            frame_data_by_run[run_id],
            run_frames,
            {uid: strain_all[uid] for uid in run_uids},
            {uid: decision_all[uid] for uid in run_uids},
            active,
        ))
    workers = max(1, min(int(parallel_workers), len(tasks))) if tasks else 1
    completed = 0
    if workers == 1:
        results = map(_build_raw_features_for_run, tasks)
        for run_id, run_records in results:
            records.extend(run_records)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"raw features; status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; item={run_id}; frames={len(run_records):,}; workers=1"
                )
    else:
        for result in isolated_process_map(__name__, "_build_raw_features_for_run", tasks, workers=workers):
            run_id, run_records = result
            records.extend(run_records)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"raw features; status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; item={run_id}; frames={len(run_records):,}; workers={workers}"
                )

    if len(records) != len(frame_catalog.frames):
        raise TrainingDataInputError("Raw feature count does not match frame catalog.")
    return RawFeatureCatalog(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        policy=active,
        records=tuple(records),
    )
