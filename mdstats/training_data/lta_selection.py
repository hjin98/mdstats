"""Selection-grade LTA descriptors for MLFF-DATA6.

These are raw, named physical descriptors. DATA7 owns every fitted transform,
metric, and selection algorithm.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from ase.data import chemical_symbols

from .progress_timing import format_progress_fraction
from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._frame_access import build_frame_array_index
from .raw_features import minimum_image_displacements

LTA_SELECTION_POLICY_SCHEMA = "mdstats.lta-selection-policy.v2"
LTA_SELECTION_POLICY_LEGACY_SCHEMA = "mdstats.lta-selection-policy.v1"
LTA_ATOMIC_ENVIRONMENT_DESCRIPTOR_SCHEMA = (
    "mdstats.lta-atomic-environment-descriptor.v1"
)
LTA_FRAME_SELECTION_DESCRIPTOR_SCHEMA = "mdstats.lta-frame-selection-descriptor.v1"
LTA_SELECTION_FEATURE_CATALOG_SCHEMA = "mdstats.lta-selection-feature-catalog.v1"
LTA_SELECTION_POLICY_VERSION = "mdstats.mlff-data6.lta-selection.2026-08.v2"
MLFF_DATA6_PARSER_VERSION = "0.20.34a0"

_BASE_ENVIRONMENT_FEATURES = (
    "oxygen_coordination",
    "oxygen_distance_min_angstrom",
    "oxygen_distance_mean_angstrom",
    "oxygen_distance_std_angstrom",
    "oxygen_distance_median_angstrom",
    "oxygen_distance_max_angstrom",
    "ring_center_distance_angstrom",
    "signed_plane_distance_angstrom",
    "absolute_plane_distance_angstrom",
    "radial_distance_angstrom",
    "ring_size_4",
    "ring_size_6",
    "ring_size_8",
    "ring_size_unresolved",
    "site_ring_4_on_center",
    "site_ring_4_off_center",
    "site_ring_6_on_center",
    "site_ring_6_off_center",
    "site_ring_8_on_center",
    "site_ring_8_off_center",
    "site_unresolved",
    "coordination_changed",
    "site_changed",
    "ring_crossing",
)


def _finite_or_none(value: Any, *, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not np.isfinite(result):
        raise TrainingDataInputError(f"{name} must be finite when present.")
    return result


def _named_vector(
    names: Sequence[str], values: Sequence[float | None], *, fill: float
) -> tuple[tuple[str, float], tuple[bool, ...]]:
    if len(names) != len(values):
        raise TrainingDataInputError("Feature names and values are misaligned.")
    result: list[tuple[str, float]] = []
    missing: list[bool] = []
    for name, value in zip(names, values, strict=True):
        if not str(name).strip():
            raise TrainingDataInputError("Feature names must be non-empty.")
        if value is None:
            result.append((str(name), float(fill)))
            missing.append(True)
        else:
            numeric = float(value)
            if not np.isfinite(numeric):
                raise TrainingDataInputError("Feature vectors must be finite.")
            result.append((str(name), numeric))
            missing.append(False)
    return tuple(result), tuple(missing)


@dataclass(frozen=True, slots=True)
class LtaSelectionPolicy:
    mobile_atomic_numbers: tuple[int, ...] = (3, 11, 19)
    oxygen_atomic_number: int = 8
    missing_value_fill: float = 0.0
    aggregate_statistics: tuple[str, ...] = ("mean", "std", "min", "max")
    materialize_atomic_environments: bool = True
    policy_version: str = LTA_SELECTION_POLICY_VERSION

    def __post_init__(self) -> None:
        mobile = tuple(sorted(set(int(v) for v in self.mobile_atomic_numbers)))
        if not mobile or any(v <= 0 for v in mobile):
            raise TrainingDataInputError("mobile_atomic_numbers must be positive.")
        if self.oxygen_atomic_number <= 0:
            raise TrainingDataInputError("oxygen_atomic_number must be positive.")
        fill = float(self.missing_value_fill)
        if not np.isfinite(fill):
            raise TrainingDataInputError("missing_value_fill must be finite.")
        allowed = {"mean", "std", "min", "max"}
        statistics = tuple(str(v) for v in self.aggregate_statistics)
        if not statistics or len(set(statistics)) != len(statistics):
            raise TrainingDataInputError("aggregate_statistics must be non-empty and unique.")
        if any(v not in allowed for v in statistics):
            raise TrainingDataInputError("Unsupported aggregate statistic.")
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        object.__setattr__(self, "mobile_atomic_numbers", mobile)
        object.__setattr__(self, "missing_value_fill", fill)
        object.__setattr__(self, "aggregate_statistics", statistics)

    @property
    def environment_feature_names(self) -> tuple[str, ...]:
        return _BASE_ENVIRONMENT_FEATURES

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_SELECTION_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "mobile_atomic_numbers": list(self.mobile_atomic_numbers),
            "oxygen_atomic_number": self.oxygen_atomic_number,
            "missing_value_fill": self.missing_value_fill,
            "aggregate_statistics": list(self.aggregate_statistics),
            "materialize_atomic_environments": self.materialize_atomic_environments,
            "environment_feature_names": list(self.environment_feature_names),
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaSelectionPolicy":
        schema = payload.get("schema")
        if schema not in {LTA_SELECTION_POLICY_SCHEMA, LTA_SELECTION_POLICY_LEGACY_SCHEMA}:
            raise TrainingDataSerializationError("Unsupported LTA selection-policy schema.")
        result = cls(
            mobile_atomic_numbers=tuple(int(v) for v in payload["mobile_atomic_numbers"]),
            oxygen_atomic_number=int(payload["oxygen_atomic_number"]),
            missing_value_fill=float(payload["missing_value_fill"]),
            aggregate_statistics=tuple(str(v) for v in payload["aggregate_statistics"]),
            materialize_atomic_environments=bool(payload.get("materialize_atomic_environments", True)),
            policy_version=(LTA_SELECTION_POLICY_VERSION if schema == LTA_SELECTION_POLICY_LEGACY_SCHEMA else str(payload["policy_version"])),
        )
        if tuple(payload.get("environment_feature_names", ())) not in (
            (),
            result.environment_feature_names,
        ):
            raise TrainingDataSerializationError("LTA environment feature ordering changed.")
        if schema == LTA_SELECTION_POLICY_SCHEMA and payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("LTA selection-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaAtomicEnvironmentDescriptor:
    frame_uid: str
    atom_index: int
    atomic_number: int
    symbol: str
    ring_id: str | None
    ring_size: int | None
    site_class: str
    named_features: tuple[tuple[str, float], ...]
    missing_mask: tuple[bool, ...]
    policy_digest: str
    source_state_digest: str

    def __post_init__(self) -> None:
        for name in ("frame_uid", "policy_digest", "source_state_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.atom_index < 0 or self.atomic_number <= 0 or not self.symbol.strip():
            raise TrainingDataInputError("Invalid LTA environment identity.")
        if self.ring_size is not None and self.ring_size not in {4, 6, 8}:
            raise TrainingDataInputError("ring_size must be 4, 6, 8, or absent.")
        features = tuple((str(k), float(v)) for k, v in self.named_features)
        if not features or len({k for k, _ in features}) != len(features):
            raise TrainingDataInputError("Named environment features must be unique.")
        if any(not np.isfinite(v) for _, v in features):
            raise TrainingDataInputError("Environment features must be finite.")
        mask = tuple(bool(v) for v in self.missing_mask)
        if len(mask) != len(features):
            raise TrainingDataInputError("Environment missing mask is misaligned.")
        object.__setattr__(self, "named_features", features)
        object.__setattr__(self, "missing_mask", mask)

    @property
    def vector(self) -> tuple[float, ...]:
        return tuple(value for _, value in self.named_features)

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.named_features)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_ATOMIC_ENVIRONMENT_DESCRIPTOR_SCHEMA,
            "frame_uid": self.frame_uid,
            "atom_index": self.atom_index,
            "atomic_number": self.atomic_number,
            "symbol": self.symbol,
            "ring_id": self.ring_id,
            "ring_size": self.ring_size,
            "site_class": self.site_class,
            "named_features": dict(self.named_features),
            "feature_order": list(self.feature_names),
            "missing_mask": list(self.missing_mask),
            "policy_digest": self.policy_digest,
            "source_state_digest": self.source_state_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaAtomicEnvironmentDescriptor":
        if payload.get("schema") != LTA_ATOMIC_ENVIRONMENT_DESCRIPTOR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA atomic descriptor schema.")
        order = tuple(str(v) for v in payload["feature_order"])
        mapping = payload["named_features"]
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            atom_index=int(payload["atom_index"]),
            atomic_number=int(payload["atomic_number"]),
            symbol=str(payload["symbol"]),
            ring_id=None if payload.get("ring_id") is None else str(payload["ring_id"]),
            ring_size=None if payload.get("ring_size") is None else int(payload["ring_size"]),
            site_class=str(payload["site_class"]),
            named_features=tuple((name, float(mapping[name])) for name in order),
            missing_mask=tuple(bool(v) for v in payload["missing_mask"]),
            policy_digest=str(payload["policy_digest"]),
            source_state_digest=str(payload["source_state_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("LTA atomic descriptor digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaFrameSelectionDescriptor:
    frame_uid: str
    frame_record_digest: str
    policy_digest: str
    named_features: tuple[tuple[str, float], ...]
    missing_mask: tuple[bool, ...]
    environment_count: int
    warning_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("frame_uid", "frame_record_digest", "policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        features = tuple((str(k), float(v)) for k, v in self.named_features)
        if not features or len({k for k, _ in features}) != len(features):
            raise TrainingDataInputError("Frame selection features must be unique.")
        if any(not np.isfinite(v) for _, v in features):
            raise TrainingDataInputError("Frame selection features must be finite.")
        mask = tuple(bool(v) for v in self.missing_mask)
        if len(mask) != len(features) or self.environment_count < 0:
            raise TrainingDataInputError("Frame selection descriptor is inconsistent.")
        object.__setattr__(self, "named_features", features)
        object.__setattr__(self, "missing_mask", mask)
        object.__setattr__(self, "warning_codes", tuple(sorted(set(str(v) for v in self.warning_codes))))

    @property
    def vector(self) -> tuple[float, ...]:
        return tuple(value for _, value in self.named_features)

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.named_features)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_FRAME_SELECTION_DESCRIPTOR_SCHEMA,
            "frame_uid": self.frame_uid,
            "frame_record_digest": self.frame_record_digest,
            "policy_digest": self.policy_digest,
            "named_features": dict(self.named_features),
            "feature_order": list(self.feature_names),
            "missing_mask": list(self.missing_mask),
            "environment_count": self.environment_count,
            "warning_codes": list(self.warning_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaFrameSelectionDescriptor":
        if payload.get("schema") != LTA_FRAME_SELECTION_DESCRIPTOR_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA frame descriptor schema.")
        order = tuple(str(v) for v in payload["feature_order"])
        mapping = payload["named_features"]
        result = cls(
            frame_uid=str(payload["frame_uid"]),
            frame_record_digest=str(payload["frame_record_digest"]),
            policy_digest=str(payload["policy_digest"]),
            named_features=tuple((name, float(mapping[name])) for name in order),
            missing_mask=tuple(bool(v) for v in payload["missing_mask"]),
            environment_count=int(payload["environment_count"]),
            warning_codes=tuple(str(v) for v in payload.get("warning_codes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("LTA frame descriptor digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class LtaSelectionFeatureCatalog:
    dataset_id: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    policy: LtaSelectionPolicy
    frame_descriptors: tuple[LtaFrameSelectionDescriptor, ...]
    atomic_environment_descriptors: tuple[LtaAtomicEnvironmentDescriptor, ...]
    _by_frame_uid: Mapping[str, LtaFrameSelectionDescriptor] = field(default_factory=dict, init=False, repr=False, compare=False)
    _environments_by_frame_uid: Mapping[str, tuple[LtaAtomicEnvironmentDescriptor, ...]] = field(default_factory=dict, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("frame_catalog_digest", "data4_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(sorted(self.frame_descriptors, key=lambda item: item.frame_uid))
        atoms = tuple(sorted(self.atomic_environment_descriptors, key=lambda item: (item.frame_uid, item.atom_index)))
        if len({item.frame_uid for item in frames}) != len(frames):
            raise TrainingDataInputError("LTA frame descriptor UIDs must be unique.")
        frame_uids = {item.frame_uid for item in frames}
        if any(item.frame_uid not in frame_uids for item in atoms):
            raise TrainingDataInputError("LTA atomic descriptor references an unknown frame.")
        if any(item.policy_digest != self.policy.policy_digest for item in (*frames, *atoms)):
            raise TrainingDataInputError("LTA selection policy mismatch.")
        if self.policy.materialize_atomic_environments and frames and not atoms:
            raise TrainingDataInputError(
                "LTA policy requested atomic environments but the catalog is empty."
            )
        object.__setattr__(self, "frame_descriptors", frames)
        object.__setattr__(self, "atomic_environment_descriptors", atoms)
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in frames})
        grouped: dict[str, list[LtaAtomicEnvironmentDescriptor]] = {}
        for item in atoms:
            grouped.setdefault(item.frame_uid, []).append(item)
        object.__setattr__(self, "_environments_by_frame_uid", {key: tuple(value) for key, value in grouped.items()})

    def for_frame(self, frame_uid: str) -> LtaFrameSelectionDescriptor:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def environments_for_frame(self, frame_uid: str) -> tuple[LtaAtomicEnvironmentDescriptor, ...]:
        return self._environments_by_frame_uid.get(frame_uid, ())

    def environment_class_labels_for_frame(self, frame_uid: str) -> tuple[str, ...]:
        """Return exact represented LTA classes from full or compact evidence.

        Production campaigns intentionally omit per-atom Python environment
        records to bound memory.  The immutable frame aggregate table retains
        exact species/site counts, so DATA7 coverage labels can be recovered
        without rematerializing those per-atom objects.
        """
        materialized = self.environments_for_frame(frame_uid)
        if materialized:
            return tuple(sorted({
                f"lta:{item.symbol}:{item.site_class}"
                for item in materialized
            }))

        frame_record = self._by_frame_uid.get(frame_uid)
        if frame_record is None:
            return ()
        features = dict(frame_record.named_features)
        sites = (
            "ring_4_on_center", "ring_4_off_center",
            "ring_6_on_center", "ring_6_off_center",
            "ring_8_on_center", "ring_8_off_center", "unresolved",
        )
        labels: set[str] = set()
        for atomic_number in self.policy.mobile_atomic_numbers:
            symbol = chemical_symbols[atomic_number]
            prefix = symbol.lower()
            for site in sites:
                if float(features.get(f"{prefix}.site_{site}.count", 0.0)) > 0.0:
                    labels.add(f"lta:{symbol}:{site}")
        return tuple(sorted(labels))

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_SELECTION_FEATURE_CATALOG_SCHEMA,
            "parser_version": MLFF_DATA6_PARSER_VERSION,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "policy_digest": self.policy.policy_digest,
            "frame_descriptor_digests": [item.content_digest for item in self.frame_descriptors],
            "atomic_environment_digests": [item.content_digest for item in self.atomic_environment_descriptors],
        }

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LTA_SELECTION_FEATURE_CATALOG_SCHEMA,
            "parser_version": MLFF_DATA6_PARSER_VERSION,
            "dataset_id": self.dataset_id,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "policy": self.policy.to_dict(),
            "frame_descriptors": [item.to_dict() for item in self.frame_descriptors],
            "atomic_environment_descriptors": [item.to_dict() for item in self.atomic_environment_descriptors],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._digest_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LtaSelectionFeatureCatalog":
        if payload.get("schema") != LTA_SELECTION_FEATURE_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported LTA selection-feature schema.")
        if payload.get("parser_version") not in (None, MLFF_DATA6_PARSER_VERSION):
            raise TrainingDataSerializationError("Unsupported DATA6 parser version.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            policy=LtaSelectionPolicy.from_dict(payload["policy"]),
            frame_descriptors=tuple(LtaFrameSelectionDescriptor.from_dict(item) for item in payload["frame_descriptors"]),
            atomic_environment_descriptors=tuple(LtaAtomicEnvironmentDescriptor.from_dict(item) for item in payload["atomic_environment_descriptors"]),
        )
        supplied = payload.get("content_digest")
        legacy_digest = digest({key: value for key, value in payload.items() if key != "content_digest"})
        if supplied not in (None, result.content_digest, legacy_digest):
            raise TrainingDataSerializationError("LTA selection-feature digest mismatch.")
        return result


def _oxygen_distance_rows(
    atom_indices: np.ndarray,
    *,
    frame_data: Any,
    local_index: int,
    oxygen_atomic_number: int,
) -> np.ndarray:
    """Return sorted mobile-to-oxygen distances for all centers in one MIC call."""

    centers = np.asarray(atom_indices, dtype=np.int64)
    numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
    oxygen_indices = np.flatnonzero(numbers == oxygen_atomic_number)
    if centers.size == 0 or oxygen_indices.size == 0:
        return np.empty((centers.size, 0), dtype=np.float64)
    fractional = np.asarray(frame_data.fractional_positions[local_index], dtype=np.float64)
    cell = np.asarray(frame_data.cells_angstrom[local_index], dtype=np.float64)
    displacement = minimum_image_displacements(
        fractional[centers],
        fractional[oxygen_indices],
        cell=cell,
        pbc=np.asarray(frame_data.pbc, dtype=np.bool_),
    )
    return np.sort(np.linalg.norm(displacement, axis=2), axis=1)


def _site_one_hot(site_class: str) -> dict[str, float]:
    names = (
        "ring_4_on_center",
        "ring_4_off_center",
        "ring_6_on_center",
        "ring_6_off_center",
        "ring_8_on_center",
        "ring_8_off_center",
        "unresolved",
    )
    return {name: float(site_class == name) for name in names}


def _build_environment_descriptor(
    state: Any,
    *,
    oxygen_distances: np.ndarray,
    policy: LtaSelectionPolicy,
) -> LtaAtomicEnvironmentDescriptor:
    distances = np.asarray(oxygen_distances, dtype=np.float64)
    distance_values: tuple[float | None, ...]
    if distances.size:
        distance_values = (
            float(distances[0]),
            float(np.mean(distances)),
            float(np.std(distances)),
            float(np.median(distances)),
            float(distances[-1]),
        )
    else:
        distance_values = (None, None, None, None, None)
    ring = state.ring_size
    site_hot = _site_one_hot(state.site_class.value)
    values: tuple[float | None, ...] = (
        None if state.oxygen_coordination is None else float(state.oxygen_coordination),
        *distance_values,
        _finite_or_none(state.ring_center_distance_angstrom, name="ring_center_distance_angstrom"),
        _finite_or_none(state.signed_plane_distance_angstrom, name="signed_plane_distance_angstrom"),
        None if state.signed_plane_distance_angstrom is None else abs(float(state.signed_plane_distance_angstrom)),
        _finite_or_none(state.radial_distance_angstrom, name="radial_distance_angstrom"),
        float(ring == 4),
        float(ring == 6),
        float(ring == 8),
        float(ring is None),
        site_hot["ring_4_on_center"],
        site_hot["ring_4_off_center"],
        site_hot["ring_6_on_center"],
        site_hot["ring_6_off_center"],
        site_hot["ring_8_on_center"],
        site_hot["ring_8_off_center"],
        site_hot["unresolved"],
        float(state.coordination_changed),
        float(state.site_changed),
        float(state.ring_crossing),
    )
    named, missing = _named_vector(policy.environment_feature_names, values, fill=policy.missing_value_fill)
    return LtaAtomicEnvironmentDescriptor(
        frame_uid=state.frame_uid,
        atom_index=state.atom_index,
        atomic_number=state.atomic_number,
        symbol=state.symbol,
        ring_id=state.ring_id,
        ring_size=state.ring_size,
        site_class=state.site_class.value,
        named_features=named,
        missing_mask=missing,
        policy_digest=policy.policy_digest,
        source_state_digest=state.content_digest,
    )


def _aggregate(values: np.ndarray, statistic: str) -> float:
    if statistic == "mean":
        return float(np.mean(values))
    if statistic == "std":
        return float(np.std(values))
    if statistic == "min":
        return float(np.min(values))
    if statistic == "max":
        return float(np.max(values))
    raise TrainingDataInputError(f"Unsupported aggregate statistic {statistic!r}.")


def _frame_named_features(
    frame_uid: str,
    environments: tuple[LtaAtomicEnvironmentDescriptor, ...],
    *,
    data4_bundle: Any,
    policy: LtaSelectionPolicy,
) -> tuple[tuple[tuple[str, float], ...], tuple[bool, ...], tuple[str, ...]]:
    lta_record = data4_bundle.lta_partition_features.for_frame(frame_uid)
    raw_record = data4_bundle.raw_features.for_frame(frame_uid)
    pairs: list[tuple[str, float | None]] = [
        ("framework_integrity", None if lta_record.framework_integrity is None else float(lta_record.framework_integrity)),
        ("coordination_change", float(lta_record.coordination_change)),
        ("site_change", float(lta_record.site_change)),
        ("ring_crossing", float(lta_record.ring_crossing)),
        ("mobile_environment_count", float(len(environments))),
        ("unresolved_environment_count", float(sum(item.ring_size is None for item in environments))),
    ]
    for atomic_number in policy.mobile_atomic_numbers:
        symbol = chemical_symbols[atomic_number].lower()
        selected = tuple(item for item in environments if item.atomic_number == atomic_number)
        pairs.append((f"{symbol}.count", float(len(selected))))
        for ring_size in (4, 6, 8):
            pairs.append((f"{symbol}.ring_{ring_size}.count", float(sum(item.ring_size == ring_size for item in selected))))
        for site in (
            "ring_4_on_center", "ring_4_off_center", "ring_6_on_center",
            "ring_6_off_center", "ring_8_on_center", "ring_8_off_center", "unresolved",
        ):
            pairs.append((f"{symbol}.site_{site}.count", float(sum(item.site_class == site for item in selected))))
        for feature_index, feature_name in enumerate(policy.environment_feature_names[:10]):
            observed = np.asarray(
                [item.vector[feature_index] for item in selected if not item.missing_mask[feature_index]],
                dtype=np.float64,
            )
            for statistic in policy.aggregate_statistics:
                pairs.append((f"{symbol}.{feature_name}.{statistic}", None if observed.size == 0 else _aggregate(observed, statistic)))
    for pair_stat in raw_record.pair_geometry_statistics:
        prefix = f"pair.{pair_stat.rule_id}"
        for output_name, field_name in (
            ("minimum_pair_distance_angstrom", "minimum_pair_distance_angstrom"),
            ("mean_nearest_neighbor_distance_angstrom", "mean_nearest_neighbor_distance_angstrom"),
            ("maximum_nearest_neighbor_distance_angstrom", "maximum_nearest_neighbor_distance_angstrom"),
            ("coordination_mean", "coordination_mean"),
            ("coordination_maximum", "coordination_maximum"),
        ):
            pairs.append((f"{prefix}.{output_name}", getattr(pair_stat, field_name)))
    names = tuple(name for name, _ in pairs)
    values = tuple(value for _, value in pairs)
    named, missing = _named_vector(names, values, fill=policy.missing_value_fill)
    warnings = tuple(sorted(set((*lta_record.warning_codes, *raw_record.warning_codes))))
    return named, missing, warnings


def build_lta_selection_feature_catalog(
    frame_catalog: Any,
    frame_data_by_run: Mapping[str, Any],
    data4_bundle: Any,
    *,
    policy: LtaSelectionPolicy | None = None,
    frame_uids: tuple[str, ...] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> LtaSelectionFeatureCatalog:
    """Build raw selection-grade LTA descriptors on an explicit frame domain.

    Mobile-ion oxygen geometry is evaluated once per frame as a dense
    ``n_mobile x n_oxygen`` block.  The production campaign may retain only the
    frame aggregate table; per-ion Python records remain available as an
    explicit opt-in for API users.
    """

    if data4_bundle.lta_partition_features is None:
        raise TrainingDataInputError("DATA6 LTA selection requires DATA4 LTA features.")
    if data4_bundle.frame_catalog_digest != frame_catalog.content_digest:
        raise TrainingDataInputError("DATA4/frame lineage mismatch.")
    active = LtaSelectionPolicy() if policy is None else policy
    index = build_frame_array_index(frame_catalog, frame_data_by_run)
    included = None if frame_uids is None else frozenset(
        validate_digest(uid, name="frame_uid") for uid in frame_uids
    )
    states_by_frame: dict[str, list[Any]] = {}
    for state in data4_bundle.lta_partition_features.mobile_states:
        if included is not None and state.frame_uid not in included:
            continue
        if state.atomic_number in active.mobile_atomic_numbers:
            states_by_frame.setdefault(state.frame_uid, []).append(state)

    frame_records = {item.frame_uid: item for item in frame_catalog.frames}
    lta_records = tuple(
        item
        for item in data4_bundle.lta_partition_features.frame_records
        if included is None or item.frame_uid in included
    )
    environments: list[LtaAtomicEnvironmentDescriptor] = []
    frames: list[LtaFrameSelectionDescriptor] = []
    report_interval = max(100, min(1_000, len(lta_records) // 100 or 1))
    if progress_callback is not None:
        progress_callback(
            f"LTA structure; status=start; progress={format_progress_fraction(0, len(lta_records))}; "
            f"atomic-environment-materialization={'on' if active.materialize_atomic_environments else 'off'}"
        )

    for completed, lta_record in enumerate(lta_records, start=1):
        uid = lta_record.frame_uid
        states = tuple(sorted(states_by_frame.get(uid, ()), key=lambda item: item.atom_index))
        local_environments: list[LtaAtomicEnvironmentDescriptor] = []
        if states:
            _, frame_data, local_index = index[uid]
            distance_rows = _oxygen_distance_rows(
                np.asarray([state.atom_index for state in states], dtype=np.int64),
                frame_data=frame_data,
                local_index=local_index,
                oxygen_atomic_number=active.oxygen_atomic_number,
            )
            for row, state in enumerate(states):
                descriptor = _build_environment_descriptor(
                    state,
                    oxygen_distances=distance_rows[row],
                    policy=active,
                )
                local_environments.append(descriptor)
            if active.materialize_atomic_environments:
                environments.extend(local_environments)

        selected = tuple(local_environments)
        named, missing, warnings = _frame_named_features(
            uid,
            selected,
            data4_bundle=data4_bundle,
            policy=active,
        )
        frames.append(
            LtaFrameSelectionDescriptor(
                frame_uid=uid,
                frame_record_digest=frame_records[uid].content_digest,
                policy_digest=active.policy_digest,
                named_features=named,
                missing_mask=missing,
                environment_count=len(selected),
                warning_codes=warnings,
            )
        )
        if progress_callback is not None and (
            completed == len(lta_records) or completed % report_interval == 0
        ):
            progress_callback(
                f"LTA structure; status=progress; progress={format_progress_fraction(completed, len(lta_records))}"
            )

    return LtaSelectionFeatureCatalog(
        dataset_id=frame_catalog.dataset_id,
        frame_catalog_digest=frame_catalog.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        policy=active,
        frame_descriptors=tuple(frames),
        atomic_environment_descriptors=tuple(environments),
    )

