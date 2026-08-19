"""Fold-local and final-domain feature metrics for MLFF-DATA7."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, MutableMapping, Sequence

import numpy as np

from .progress_timing import format_progress_fraction
from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest, validate_serialized_digest
from .difficulty import TrainingDifficultyDomainKind, build_training_difficulty_domains
from .model_features import (
    read_mace_descriptor_array,
    read_mace_descriptor_summary,
    read_mace_descriptor_summary_rows,
)
from .partition import OuterRole

FEATURE_FIT_DOMAIN_SCHEMA = "mdstats.feature-fit-domain.v1"
FEATURE_BLOCK_POLICY_SCHEMA = "mdstats.feature-block-policy.v1"
FEATURE_METRIC_POLICY_SCHEMA = "mdstats.feature-metric-policy.v1"
FITTED_FEATURE_BLOCK_SCHEMA = "mdstats.fitted-feature-block.v1"
TRANSFORMED_FRAME_FEATURE_SCHEMA = "mdstats.transformed-frame-feature.v1"
FITTED_FEATURE_METRIC_SCHEMA = "mdstats.fitted-feature-metric.v2"
FITTED_FEATURE_METRIC_LEGACY_SCHEMA = "mdstats.fitted-feature-metric.v1"
TRANSFORMED_FRAME_FEATURE_TABLE_SCHEMA = "mdstats.transformed-frame-feature-table.v1"
FEATURE_METRIC_POLICY_VERSION = "mdstats.mlff-data7.feature-metric.2026-08.v3"
MLFF_DATA7_PARSER_VERSION = "0.20.64a0"
MLFF_DATA7_LEGACY_PARSER_VERSION = "0.20.35a0"
MLFF_DATA7_V63_PARSER_VERSION = "0.20.63a0"


class FeatureFitDomainKind(str, Enum):
    FINAL_DEVELOPMENT = "final_development"
    CROSS_VALIDATION_TRAINING = "cross_validation_training"


class FeatureScalingKind(str, Enum):
    ROBUST_IQR = "robust_iqr"
    STANDARD = "standard"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class FeatureFitDomain:
    label_domain_id: str
    kind: FeatureFitDomainKind
    data5_bundle_digest: str
    unit_ids: tuple[str, ...]
    frame_uids: tuple[str, ...]
    fold_index: int | None = None
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "data5_bundle_digest", validate_digest(self.data5_bundle_digest, name="data5_bundle_digest"))
        object.__setattr__(self, "kind", FeatureFitDomainKind(self.kind))
        units = tuple(sorted(set(validate_digest(v, name="unit_id") for v in self.unit_ids)))
        frames = tuple(sorted(set(validate_digest(v, name="frame_uid") for v in self.frame_uids)))
        if not self.label_domain_id.strip() or not units or not frames:
            raise TrainingDataInputError("Feature fit domains require label domain, units, and frames.")
        if self.kind is FeatureFitDomainKind.CROSS_VALIDATION_TRAINING:
            if self.fold_index is None or self.fold_index < 0:
                raise TrainingDataInputError("Cross-validation fit domains require fold_index.")
        elif self.fold_index is not None:
            raise TrainingDataInputError("Final-development fit domains cannot have fold_index.")
        object.__setattr__(self, "unit_ids", units)
        object.__setattr__(self, "frame_uids", frames)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FEATURE_FIT_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "kind": self.kind.value,
            "data5_bundle_digest": self.data5_bundle_digest,
            "unit_ids": list(self.unit_ids),
            "frame_uids": list(self.frame_uids),
            "fold_index": self.fold_index,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "FeatureFitDomain":
        if payload.get("schema") != FEATURE_FIT_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported feature-fit-domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            kind=FeatureFitDomainKind(payload["kind"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]),
            unit_ids=tuple(str(v) for v in payload["unit_ids"]),
            frame_uids=tuple(str(v) for v in payload["frame_uids"]),
            fold_index=None if payload.get("fold_index") is None else int(payload["fold_index"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Feature-fit-domain digest mismatch.")
        return result


def _frames_for_units(data5_bundle: Any, unit_ids: Sequence[str]) -> tuple[str, ...]:
    return tuple(sorted({uid for unit_id in unit_ids for uid in data5_bundle.unit_catalog.unit(unit_id).frame_uids}))


def build_feature_fit_domains(
    data5_bundle: Any,
    *,
    cross_validation_plans: Sequence[Any] | None = None,
) -> tuple[FeatureFitDomain, ...]:
    result: list[FeatureFitDomain] = []
    for outer in data5_bundle.outer_partitions:
        units = outer.units_for(OuterRole.DEVELOPMENT)
        result.append(FeatureFitDomain(
            label_domain_id=outer.label_domain_id,
            kind=FeatureFitDomainKind.FINAL_DEVELOPMENT,
            data5_bundle_digest=data5_bundle.content_digest,
            unit_ids=units,
            frame_uids=_frames_for_units(data5_bundle, units),
        ))
    plans = (
        data5_bundle.cross_validation_plans
        if cross_validation_plans is None
        else tuple(cross_validation_plans)
    )
    for plan in plans:
        for fold in plan.folds:
            result.append(FeatureFitDomain(
                label_domain_id=plan.label_domain_id,
                kind=FeatureFitDomainKind.CROSS_VALIDATION_TRAINING,
                data5_bundle_digest=data5_bundle.content_digest,
                unit_ids=fold.training_unit_ids,
                frame_uids=_frames_for_units(data5_bundle, fold.training_unit_ids),
                fold_index=fold.fold_index,
            ))
    return tuple(sorted(result, key=lambda item: (item.label_domain_id, item.kind.value, -1 if item.fold_index is None else item.fold_index)))


@dataclass(frozen=True, slots=True)
class FeatureBlockPolicy:
    name: str
    weight: float = 1.0
    scaling: FeatureScalingKind = FeatureScalingKind.ROBUST_IQR
    include_missing_indicators: bool = True
    normalize_by_dimension: bool = True
    pca_components: int | None = None
    required: bool = False

    def __post_init__(self) -> None:
        if self.name not in {"raw_physical", "universal_structural", "profile_extensions", "lta_frame", "mace_summary", "difficulty"}:
            raise TrainingDataInputError(f"Unsupported feature block {self.name!r}.")
        weight = float(self.weight)
        if not np.isfinite(weight) or weight <= 0.0:
            raise TrainingDataInputError("Feature block weights must be positive and finite.")
        object.__setattr__(self, "weight", weight)
        object.__setattr__(self, "scaling", FeatureScalingKind(self.scaling))
        if self.pca_components is not None and self.pca_components <= 0:
            raise TrainingDataInputError("pca_components must be positive when present.")

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "schema": FEATURE_BLOCK_POLICY_SCHEMA,
            "name": self.name,
            "weight": self.weight,
            "scaling": self.scaling.value,
            "include_missing_indicators": self.include_missing_indicators,
            "normalize_by_dimension": self.normalize_by_dimension,
            "pca_components": self.pca_components,
            "required": self.required,
        }
        return {**payload, "content_digest": digest(payload)}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FeatureBlockPolicy":
        if payload.get("schema") != FEATURE_BLOCK_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported feature-block policy schema.")
        result = cls(
            name=str(payload["name"]), weight=float(payload["weight"]),
            scaling=FeatureScalingKind(payload["scaling"]),
            include_missing_indicators=bool(payload["include_missing_indicators"]),
            normalize_by_dimension=bool(payload["normalize_by_dimension"]),
            pca_components=None if payload.get("pca_components") is None else int(payload["pca_components"]),
            required=bool(payload["required"]),
        )
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("Feature-block policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class FeatureMetricPolicyTemplate:
    blocks: tuple[FeatureBlockPolicy, ...] = (
        FeatureBlockPolicy("raw_physical", weight=1.0, required=True),
        # High-dimensional aggregate catalogs are compressed before distance
        # calculations.  Without this bound, the transformed DATA7 matrix and
        # its Python frame records can consume several gigabytes.
        FeatureBlockPolicy("universal_structural", weight=1.5, pca_components=64, required=False),
        FeatureBlockPolicy("profile_extensions", weight=1.5, pca_components=32, required=False),
        FeatureBlockPolicy("mace_summary", weight=1.5, pca_components=32, required=False),
        FeatureBlockPolicy("difficulty", weight=0.5, required=False),
    )
    minimum_scale: float = 1.0e-12
    tie_tolerance: float = 1.0e-12
    randomized_projection_seed: int = 0
    policy_version: str = FEATURE_METRIC_POLICY_VERSION
    _legacy_omits_randomized_projection_seed: bool = field(
        default=False, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        blocks = tuple(self.blocks)
        if not blocks or len({item.name for item in blocks}) != len(blocks):
            raise TrainingDataInputError("Feature metric blocks must be non-empty and unique.")
        for name in ("minimum_scale", "tie_tolerance"):
            value = float(getattr(self, name))
            if not np.isfinite(value) or value <= 0.0:
                raise TrainingDataInputError(f"{name} must be positive and finite.")
            object.__setattr__(self, name, value)
        seed = int(self.randomized_projection_seed)
        if seed < 0:
            raise TrainingDataInputError(
                "randomized_projection_seed must be nonnegative."
            )
        object.__setattr__(self, "randomized_projection_seed", seed)
        if not self.policy_version.strip():
            raise TrainingDataInputError("policy_version must be non-empty.")
        object.__setattr__(self, "blocks", blocks)

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": FEATURE_METRIC_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "blocks": [item.to_dict() for item in self.blocks],
            "minimum_scale": self.minimum_scale,
            "tie_tolerance": self.tie_tolerance,
        }
        if not self._legacy_omits_randomized_projection_seed:
            payload["randomized_projection_seed"] = self.randomized_projection_seed
        return payload

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FeatureMetricPolicyTemplate":
        if payload.get("schema") != FEATURE_METRIC_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported feature-metric policy schema.")
        result = cls(
            blocks=tuple(FeatureBlockPolicy.from_dict(item) for item in payload["blocks"]),
            minimum_scale=float(payload["minimum_scale"]),
            tie_tolerance=float(payload["tie_tolerance"]),
            randomized_projection_seed=int(
                payload.get("randomized_projection_seed", 0)
            ),
            policy_version=str(payload["policy_version"]),
        )
        if "randomized_projection_seed" not in payload:
            object.__setattr__(
                result, "_legacy_omits_randomized_projection_seed", True
            )
        validate_serialized_digest(
            payload,
            digest_field="policy_digest",
            current_digest=result.policy_digest,
            error_message="Feature-metric policy digest mismatch.",
        )
        return result


@dataclass(frozen=True, slots=True, eq=False)
class FittedFeatureBlockMetric:
    block_name: str
    input_feature_names: tuple[str, ...]
    center: np.ndarray
    scale: np.ndarray
    projection: np.ndarray
    output_dimension: int
    weight_factor: float
    policy_digest: str
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "policy_digest",
            validate_digest(self.policy_digest, name="policy_digest"),
        )
        names = tuple(str(v) for v in self.input_feature_names)
        center = np.asarray(self.center, dtype=np.float64)
        scale = np.asarray(self.scale, dtype=np.float64)
        if center.ndim != 1 or scale.ndim != 1:
            raise TrainingDataInputError(
                "Fitted feature block center/scale must be one-dimensional."
            )
        center = np.ascontiguousarray(center)
        scale = np.ascontiguousarray(scale)
        if not names or len(names) != center.size or center.size != scale.size:
            raise TrainingDataInputError("Fitted feature block arrays are misaligned.")
        if (
            np.any(~np.isfinite(center))
            or np.any(~np.isfinite(scale))
            or np.any(scale <= 0.0)
        ):
            raise TrainingDataInputError(
                "Fitted feature block center/scale is invalid."
            )
        projection = np.asarray(self.projection, dtype=np.float64)
        if projection.size == 0:
            projection = np.empty((0, len(names)), dtype=np.float64)
        elif projection.ndim != 2:
            raise TrainingDataInputError("Fitted projection must be two-dimensional.")
        projection = np.ascontiguousarray(projection)
        if projection.shape[0] > 0:
            if projection.shape != (self.output_dimension, len(names)):
                raise TrainingDataInputError(
                    "Fitted projection shape is inconsistent."
                )
            if np.any(~np.isfinite(projection)):
                raise TrainingDataInputError("Fitted projection is non-finite.")
        elif self.output_dimension != len(names):
            raise TrainingDataInputError(
                "Identity feature block output dimension is inconsistent."
            )
        if (
            self.output_dimension <= 0
            or not np.isfinite(self.weight_factor)
            or self.weight_factor <= 0.0
        ):
            raise TrainingDataInputError(
                "Fitted feature block output scaling is invalid."
            )
        center.setflags(write=False)
        scale.setflags(write=False)
        projection.setflags(write=False)
        object.__setattr__(self, "input_feature_names", names)
        object.__setattr__(self, "center", center)
        object.__setattr__(self, "scale", scale)
        object.__setattr__(self, "projection", projection)

    @classmethod
    def _from_authenticated_arrays(
        cls,
        *,
        block_name: str,
        input_feature_names: Sequence[str],
        center: np.ndarray,
        scale: np.ndarray,
        projection: np.ndarray,
        output_dimension: int,
        weight_factor: float,
        policy_digest: str,
        content_digest: str,
    ) -> "FittedFeatureBlockMetric":
        names = tuple(str(value) for value in input_feature_names)
        center_array = np.asarray(center, dtype=np.float64, order="C")
        scale_array = np.asarray(scale, dtype=np.float64, order="C")
        projection_array = np.asarray(projection, dtype=np.float64, order="C")
        if projection_array.size == 0:
            projection_array = np.empty((0, len(names)), dtype=np.float64)
        if (
            center_array.shape != (len(names),)
            or scale_array.shape != (len(names),)
            or (
                projection_array.shape[0] > 0
                and projection_array.shape
                != (int(output_dimension), len(names))
            )
        ):
            raise TrainingDataInputError(
                "Authenticated fitted-feature block arrays are misaligned."
            )
        for array in (center_array, scale_array, projection_array):
            array.setflags(write=False)
        result = object.__new__(cls)
        object.__setattr__(result, "block_name", str(block_name))
        object.__setattr__(result, "input_feature_names", names)
        object.__setattr__(result, "center", center_array)
        object.__setattr__(result, "scale", scale_array)
        object.__setattr__(result, "projection", projection_array)
        object.__setattr__(result, "output_dimension", int(output_dimension))
        object.__setattr__(result, "weight_factor", float(weight_factor))
        object.__setattr__(
            result,
            "policy_digest",
            validate_digest(policy_digest, name="policy_digest"),
        )
        object.__setattr__(
            result,
            "_content_digest_cache",
            validate_digest(content_digest, name="content_digest"),
        )
        return result

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FITTED_FEATURE_BLOCK_SCHEMA,
            "block_name": self.block_name,
            "input_feature_names": list(self.input_feature_names),
            "center": self.center.tolist(),
            "scale": self.scale.tolist(),
            "projection": self.projection.tolist(),
            "output_dimension": self.output_dimension,
            "weight_factor": self.weight_factor,
            "policy_digest": self.policy_digest,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "FittedFeatureBlockMetric":
        if payload.get("schema") != FITTED_FEATURE_BLOCK_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported fitted-feature-block schema."
            )
        result = cls(
            block_name=str(payload["block_name"]),
            input_feature_names=tuple(
                str(v) for v in payload["input_feature_names"]
            ),
            center=np.asarray(payload["center"], dtype=np.float64),
            scale=np.asarray(payload["scale"], dtype=np.float64),
            projection=np.asarray(payload["projection"], dtype=np.float64),
            output_dimension=int(payload["output_dimension"]),
            weight_factor=float(payload["weight_factor"]),
            policy_digest=str(payload["policy_digest"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Fitted-feature-block digest mismatch."
            )
        return result

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, FittedFeatureBlockMetric)
            and self.block_name == other.block_name
            and self.input_feature_names == other.input_feature_names
            and np.array_equal(self.center, other.center)
            and np.array_equal(self.scale, other.scale)
            and np.array_equal(self.projection, other.projection)
            and self.output_dimension == other.output_dimension
            and self.weight_factor == other.weight_factor
            and self.policy_digest == other.policy_digest
        )


@dataclass(frozen=True, slots=True)
class TransformedFrameFeature:
    frame_uid: str
    vector: tuple[float, ...]
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "frame_uid", validate_digest(self.frame_uid, name="frame_uid"))
        vector = tuple(float(v) for v in self.vector)
        if not vector or any(not np.isfinite(v) for v in vector):
            raise TrainingDataInputError("Transformed feature vectors must be finite and non-empty.")
        object.__setattr__(self, "vector", vector)

    def to_dict(self) -> dict[str, Any]:
        payload = {"schema": TRANSFORMED_FRAME_FEATURE_SCHEMA, "frame_uid": self.frame_uid, "vector": list(self.vector)}
        value = self._content_digest_cache or digest(payload)
        object.__setattr__(self, "_content_digest_cache", value)
        return {**payload, "content_digest": value}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TransformedFrameFeature":
        if payload.get("schema") != TRANSFORMED_FRAME_FEATURE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported transformed-frame-feature schema.")
        result = cls(frame_uid=str(payload["frame_uid"]), vector=tuple(float(v) for v in payload["vector"]))
        if payload.get("content_digest") not in (None, result.to_dict()["content_digest"]):
            raise TrainingDataSerializationError("Transformed-frame-feature digest mismatch.")
        return result


def _metric_array_content_digest(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return digest({
        "dtype": contiguous.dtype.str,
        "shape": list(contiguous.shape),
        "bytes_sha256": __import__("hashlib").sha256(
            memoryview(contiguous).cast("B")
        ).hexdigest(),
    })


@dataclass(frozen=True, slots=True, eq=False)
class TransformedFrameFeatureTable(Sequence[TransformedFrameFeature]):
    """Columnar fitted frame vectors with lazy compatibility objects."""

    frame_uids: tuple[str, ...]
    values: np.ndarray
    _index_by_uid: Mapping[str, int] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        uids = tuple(validate_digest(uid, name="frame_uid") for uid in self.frame_uids)
        values = np.asarray(self.values, dtype=np.float64, order="C")
        if not values.flags.c_contiguous:
            values = np.ascontiguousarray(values)
        if not uids or len(set(uids)) != len(uids):
            raise TrainingDataInputError(
                "Transformed frame table requires unique frame UIDs."
            )
        if values.ndim != 2 or values.shape[0] != len(uids) or values.shape[1] == 0:
            raise TrainingDataInputError(
                "Transformed frame table has inconsistent dimensions."
            )
        if np.any(~np.isfinite(values)):
            raise TrainingDataInputError(
                "Transformed frame table values must be finite."
            )
        values.setflags(write=False)
        object.__setattr__(self, "frame_uids", uids)
        object.__setattr__(self, "values", values)
        object.__setattr__(
            self, "_index_by_uid", {uid: index for index, uid in enumerate(uids)}
        )

    @classmethod
    def _from_authenticated_arrays(
        cls,
        *,
        frame_uids: Sequence[str],
        values: np.ndarray,
        content_digest: str,
    ) -> "TransformedFrameFeatureTable":
        """Restore an authenticated, immutable fitted-feature matrix."""

        uids = tuple(validate_digest(uid, name="frame_uid") for uid in frame_uids)
        value_array = np.asarray(values, dtype=np.float64, order="C")
        if value_array.ndim != 2 or value_array.shape[0] != len(uids) or value_array.shape[1] == 0:
            raise TrainingDataInputError(
                "Authenticated transformed-frame table dimensions are inconsistent."
            )
        value_array.setflags(write=False)
        result = object.__new__(cls)
        object.__setattr__(result, "frame_uids", uids)
        object.__setattr__(result, "values", value_array)
        object.__setattr__(result, "_index_by_uid", {uid: index for index, uid in enumerate(uids)})
        object.__setattr__(result, "_content_digest_cache", validate_digest(content_digest, name="content_digest"))
        return result

    @classmethod
    def from_features(
        cls, features: Sequence[TransformedFrameFeature]
    ) -> "TransformedFrameFeatureTable":
        ordered = tuple(sorted(features, key=lambda item: item.frame_uid))
        if not ordered:
            raise TrainingDataInputError("Transformed frame table cannot be empty.")
        return cls(
            frame_uids=tuple(item.frame_uid for item in ordered),
            values=np.asarray([item.vector for item in ordered], dtype=np.float64),
        )

    def __len__(self) -> int:
        return len(self.frame_uids)

    def _feature(self, index: int) -> TransformedFrameFeature:
        return TransformedFrameFeature(
            frame_uid=self.frame_uids[index],
            vector=tuple(float(value) for value in self.values[index]),
        )

    def __getitem__(
        self, index: int | slice
    ) -> TransformedFrameFeature | tuple[TransformedFrameFeature, ...]:
        if isinstance(index, slice):
            return tuple(
                self._feature(value) for value in range(*index.indices(len(self)))
            )
        normalized = int(index)
        if normalized < 0:
            normalized += len(self)
        if normalized < 0 or normalized >= len(self):
            raise IndexError(index)
        return self._feature(normalized)

    def __iter__(self) -> Iterator[TransformedFrameFeature]:
        for index in range(len(self)):
            yield self._feature(index)

    def index_for_uid(self, frame_uid: str) -> int:
        try:
            return self._index_by_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def feature_for_uid(self, frame_uid: str) -> TransformedFrameFeature:
        return self._feature(self.index_for_uid(frame_uid))

    def vector_for_uid(self, frame_uid: str) -> np.ndarray:
        return self.values[self.index_for_uid(frame_uid)]

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest({
                "frame_uids": list(self.frame_uids),
                "values_digest": _metric_array_content_digest(self.values),
            })
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": TRANSFORMED_FRAME_FEATURE_TABLE_SCHEMA,
            "frame_uids": list(self.frame_uids),
            "values": self.values.tolist(),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "TransformedFrameFeatureTable":
        if payload.get("schema") != TRANSFORMED_FRAME_FEATURE_TABLE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported transformed-frame feature-table schema."
            )
        result = cls(
            frame_uids=tuple(str(value) for value in payload["frame_uids"]),
            values=np.asarray(payload["values"], dtype=np.float64),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Transformed-frame feature-table digest mismatch."
            )
        return result

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, TransformedFrameFeatureTable)
            and self.frame_uids == other.frame_uids
            and np.array_equal(self.values, other.values)
        )


@dataclass(frozen=True, slots=True)
class FittedFeatureMetric:
    domain: FeatureFitDomain
    policy: FeatureMetricPolicyTemplate
    data4_bundle_digest: str
    data6_bundle_digest: str
    block_metrics: tuple[FittedFeatureBlockMetric, ...]
    frame_features: TransformedFrameFeatureTable | Sequence[TransformedFrameFeature]
    _serialization_parser_version: str = field(
        default=MLFF_DATA7_PARSER_VERSION, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("data4_bundle_digest", "data6_bundle_digest"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        blocks = tuple(self.block_metrics)
        table = (
            self.frame_features
            if isinstance(self.frame_features, TransformedFrameFeatureTable)
            else TransformedFrameFeatureTable.from_features(self.frame_features)
        )
        if not blocks or len({item.block_name for item in blocks}) != len(blocks):
            raise TrainingDataInputError(
                "Fitted metric blocks must be non-empty and unique."
            )
        if set(table.frame_uids) != set(self.domain.frame_uids):
            raise TrainingDataInputError(
                "Fitted metric must cover exactly its training domain."
            )
        if any(item.policy_digest != self.policy.policy_digest for item in blocks):
            raise TrainingDataInputError("Fitted block policy mismatch.")
        if table.values.shape[1] != sum(
            item.output_dimension for item in blocks
        ):
            raise TrainingDataInputError(
                "Fitted metric output dimensions are inconsistent."
            )
        object.__setattr__(self, "block_metrics", blocks)
        object.__setattr__(self, "frame_features", table)

    @property
    def frame_feature_table(self) -> TransformedFrameFeatureTable:
        assert isinstance(self.frame_features, TransformedFrameFeatureTable)
        return self.frame_features

    def for_frame(self, frame_uid: str) -> TransformedFrameFeature:
        return self.frame_feature_table.feature_for_uid(frame_uid)

    def vector_for_frame(self, frame_uid: str) -> np.ndarray:
        return self.frame_feature_table.vector_for_uid(frame_uid)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FITTED_FEATURE_METRIC_SCHEMA,
            "parser_version": self._serialization_parser_version,
            "domain": self.domain.to_dict(),
            "policy": self.policy.to_dict(),
            "data4_bundle_digest": self.data4_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "block_metrics": [item.to_dict() for item in self.block_metrics],
            "frame_feature_table": self.frame_feature_table.to_dict(),
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": FITTED_FEATURE_METRIC_SCHEMA,
            "parser_version": self._serialization_parser_version,
            "domain_digest": self.domain.content_digest,
            "policy_digest": self.policy.policy_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "block_metric_digests": [
                item.content_digest for item in self.block_metrics
            ],
            "frame_feature_table_digest": self.frame_feature_table.content_digest,
        }

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._digest_payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FittedFeatureMetric":
        schema = payload.get("schema")
        if schema not in {
            FITTED_FEATURE_METRIC_SCHEMA,
            FITTED_FEATURE_METRIC_LEGACY_SCHEMA,
        }:
            raise TrainingDataSerializationError(
                "Unsupported fitted-feature-metric schema."
            )
        if payload.get("parser_version") not in (
            None,
            MLFF_DATA7_PARSER_VERSION,
            MLFF_DATA7_V63_PARSER_VERSION,
            MLFF_DATA7_LEGACY_PARSER_VERSION,
        ):
            raise TrainingDataSerializationError("Unsupported DATA7 parser version.")
        if schema == FITTED_FEATURE_METRIC_SCHEMA:
            frame_features: TransformedFrameFeatureTable | Sequence[TransformedFrameFeature] = (
                TransformedFrameFeatureTable.from_dict(
                    payload["frame_feature_table"]
                )
            )
        else:
            frame_features = tuple(
                TransformedFrameFeature.from_dict(item)
                for item in payload["frame_features"]
            )
        result = cls(
            domain=FeatureFitDomain.from_dict(payload["domain"]),
            policy=FeatureMetricPolicyTemplate.from_dict(payload["policy"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            data6_bundle_digest=str(payload["data6_bundle_digest"]),
            block_metrics=tuple(
                FittedFeatureBlockMetric.from_dict(item)
                for item in payload["block_metrics"]
            ),
            frame_features=frame_features,
        )
        if payload.get("parser_version") is not None:
            object.__setattr__(
                result,
                "_serialization_parser_version",
                str(payload["parser_version"]),
            )
        validate_serialized_digest(
            payload,
            digest_field="content_digest",
            current_digest=result.content_digest,
            error_message="Fitted-feature-metric digest mismatch.",
        )
        return result


def _value(value: Any) -> tuple[float, bool]:
    if value is None:
        return 0.0, True
    numeric = float(value)
    return (numeric, False) if np.isfinite(numeric) else (0.0, True)


def _raw_physical(record: Any, species_atomic_numbers: tuple[int, ...]) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    items: list[tuple[str, Any]] = [
        ("temperature_K", record.instantaneous_temperature_kelvin),
        ("volume_A3", record.cell_volume_angstrom3),
        ("density_g_cm3", record.mass_density_g_cm3),
        ("force_component_rms", record.force_component_rms_ev_per_angstrom),
        ("force_norm_mean", record.force_norm_mean_ev_per_angstrom),
        ("force_norm_max", record.force_norm_max_ev_per_angstrom),
        ("pressure", record.pressure_ev_per_angstrom3),
        ("stress_deviatoric", record.stress_deviatoric_norm_ev_per_angstrom3),
        ("stress_von_mises", record.stress_von_mises_ev_per_angstrom3),
        ("hydrostatic_strain", record.hydrostatic_strain),
        ("deviatoric_strain", record.deviatoric_strain_norm),
    ]
    items.extend((f"cell_length_{axis}", value) for axis, value in zip("abc", record.cell_lengths_angstrom, strict=True))
    items.extend((f"cell_angle_{axis}", value) for axis, value in zip(("alpha", "beta", "gamma"), record.cell_angles_degrees, strict=True))
    shear = record.engineering_shear if record.engineering_shear is not None else (None, None, None)
    items.extend((f"engineering_shear_{axis}", value) for axis, value in zip(("xy", "yz", "zx"), shear, strict=True))
    for atomic_number in species_atomic_numbers:
        selected = next((v for v in record.species_force_statistics if v.atomic_number == atomic_number), None)
        items.extend((
            (f"Z{atomic_number}_force_component_rms", None if selected is None else selected.component_rms_ev_per_angstrom),
            (f"Z{atomic_number}_force_norm_mean", None if selected is None else selected.norm_mean_ev_per_angstrom),
            (f"Z{atomic_number}_force_norm_max", None if selected is None else selected.norm_max_ev_per_angstrom),
        ))
    values, missing = zip(*(_value(value) for _, value in items), strict=True)
    return tuple(name for name, _ in items), np.asarray(values), np.asarray(missing, dtype=bool)


def _difficulty_features(record: Any, species_atomic_numbers: tuple[int, ...]) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    items: list[tuple[str, Any]] = [
        ("abs_energy_error_per_atom", record.absolute_energy_error_per_atom_ev),
        ("force_component_rmse", record.force_component_rmse_ev_per_angstrom),
        ("force_vector_mean", record.force_vector_error_mean_ev_per_angstrom),
        ("force_vector_max", record.force_vector_error_max_ev_per_angstrom),
        ("stress_component_rmse", record.stress_component_rmse_ev_per_angstrom3),
    ]
    for atomic_number in species_atomic_numbers:
        selected = next((v for v in record.species_force_errors if v.atomic_number == atomic_number), None)
        items.extend((
            (f"Z{atomic_number}_force_component_rmse", None if selected is None else selected.component_rmse_ev_per_angstrom),
            (f"Z{atomic_number}_force_vector_mean", None if selected is None else selected.vector_error_mean_ev_per_angstrom),
            (f"Z{atomic_number}_force_vector_max", None if selected is None else selected.vector_error_max_ev_per_angstrom),
        ))
    values, missing = zip(*(_value(value) for _, value in items), strict=True)
    return tuple(name for name, _ in items), np.asarray(values), np.asarray(missing, dtype=bool)


@lru_cache(maxsize=None)
def _mace_summary_feature_names(
    descriptor_dimension: int,
    species_atomic_numbers: tuple[int, ...],
) -> tuple[str, ...]:
    names: list[str] = []
    for prefix in ("global_mean", "global_std"):
        names.extend(f"{prefix}_{index}" for index in range(descriptor_dimension))
    for atomic_number in species_atomic_numbers:
        names.append(f"Z{atomic_number}_present")
        names.extend(
            f"Z{atomic_number}_mean_{index}"
            for index in range(descriptor_dimension)
        )
    return tuple(names)


def _mace_summary(
    frame_uid: str,
    *,
    data6_bundle: Any,
    descriptor_root: Path,
    frame_index: Mapping[str, tuple[Any, Any, int]],
    species_atomic_numbers: tuple[int, ...],
    summary_cache: MutableMapping[
        tuple[str, tuple[int, ...]], tuple[np.ndarray, np.ndarray]
    ] | None = None,
) -> tuple[tuple[str, ...], np.ndarray, np.ndarray]:
    cache_key = (frame_uid, species_atomic_numbers)
    if summary_cache is not None:
        cached = summary_cache.get(cache_key)
        if cached is not None:
            values, missing = cached
            descriptor_dimension = (
                len(values) - len(species_atomic_numbers)
            ) // (2 + len(species_atomic_numbers))
            return (
                _mace_summary_feature_names(
                    descriptor_dimension, species_atomic_numbers
                ),
                values,
                missing,
            )
    manifest = data6_bundle.mace_descriptor_manifest
    if manifest is None:
        raise TrainingDataInputError("MACE summary block requires a DATA6 descriptor manifest.")
    persisted = read_mace_descriptor_summary(
        manifest, descriptor_root, frame_uid, species_atomic_numbers
    )
    if persisted is not None:
        value_array, missing_array = persisted
        descriptor_dimension = (
            len(value_array) - len(species_atomic_numbers)
        ) // (2 + len(species_atomic_numbers))
        if summary_cache is not None:
            summary_cache[cache_key] = (value_array, missing_array)
        return (
            _mace_summary_feature_names(
                descriptor_dimension, species_atomic_numbers
            ),
            value_array,
            missing_array,
        )
    array = read_mace_descriptor_array(manifest, descriptor_root, frame_uid)
    _, frame_data, _ = frame_index[frame_uid]
    numbers = np.asarray(frame_data.atomic_numbers, dtype=np.int32)
    values: list[float] = []
    missing: list[bool] = []
    for prefix in ("global_mean", "global_std"):
        vector = np.mean(array, axis=0) if prefix.endswith("mean") else np.std(array, axis=0)
        for value in vector:
            values.append(float(value)); missing.append(False)
    for atomic_number in species_atomic_numbers:
        mask = numbers == atomic_number
        values.append(float(np.any(mask))); missing.append(False)
        vector = np.mean(array[mask], axis=0) if np.any(mask) else np.zeros(array.shape[1])
        for value in vector:
            values.append(float(value)); missing.append(not np.any(mask))
    value_array = np.asarray(values, dtype=np.float64)
    missing_array = np.asarray(missing, dtype=bool)
    if summary_cache is not None:
        summary_cache[cache_key] = (value_array, missing_array)
    return (
        _mace_summary_feature_names(array.shape[1], species_atomic_numbers),
        value_array,
        missing_array,
    )


def _iter_raw_blocks(
    domain: FeatureFitDomain, *, frame_catalog: Any, frame_data_by_run: Mapping[str, Any], data4_bundle: Any, data6_bundle: Any,
    policy: FeatureMetricPolicyTemplate, mace_descriptor_root: str | Path | None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    mace_summary_cache: MutableMapping[
        tuple[str, tuple[int, ...]], tuple[np.ndarray, np.ndarray]
    ] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> Iterable[tuple[str, tuple[str, ...], np.ndarray, np.ndarray]]:
    from ._frame_access import build_frame_array_index
    frame_index = (
        build_frame_array_index(frame_catalog, frame_data_by_run)
        if frame_array_index is None
        else frame_array_index
    )
    domain_frame_set = frozenset(domain.frame_uids)
    structural_catalog = next(
        (
            item
            for item in data6_bundle.universal_structural_features
            if domain_frame_set.issubset(
                item.frame_descriptor_table.frame_uid_set
            )
        ),
        None,
    )
    profile_extensions = tuple(getattr(data6_bundle, "profile_selection_features", ()))
    if not profile_extensions and getattr(data6_bundle, "lta_selection_features", None) is not None:
        from .profile_extensions import wrap_lta_selection_features
        profile_extensions = (wrap_lta_selection_features(
            data6_bundle.lta_selection_features, data4_bundle_digest=data6_bundle.data4_bundle_digest
        ),)
    # Chemical species are invariant within each trajectory run.  Inspect one
    # atomic-number array per participating run instead of rewalking every atom
    # in every frame (O(R*A) rather than O(N*A)).
    domain_run_ids = tuple(sorted({
        str(frame_index[uid][0].run_id) for uid in domain.frame_uids
    }))
    species_atomic_numbers = tuple(sorted({
        int(number)
        for run_id in domain_run_ids
        for number in np.asarray(frame_data_by_run[run_id].atomic_numbers, dtype=np.int32)
    }))
    difficulty_catalog = data6_bundle.training_difficulty_for_domain(domain)
    if difficulty_catalog is not None and tuple(difficulty_catalog.domain.frame_uids) != tuple(domain.frame_uids):
        raise TrainingDataInputError("DATA6 difficulty-domain identity matches but frame membership differs.")
    difficulty_by_uid = {} if difficulty_catalog is None else {item.frame_uid: item for item in difficulty_catalog.records}
    yielded = False
    for block in policy.blocks:
        if progress_callback is not None:
            progress_callback(
                f"status=phase; phase=extracting-feature-block; block={block.name}; frames={len(domain.frame_uids):,}"
            )
        # Universal structural features are stored columnarly.  Extract the
        # complete domain in one indexed NumPy operation rather than lazily
        # materializing tens of millions of Python ``(name, value)`` pairs.
        if block.name == "universal_structural" and structural_catalog is not None:
            names, values, masks = structural_catalog.frame_feature_matrix(
                domain.frame_uids
            )
            yielded = True
            yield (
                block.name,
                names,
                np.asarray(values, dtype=np.float64),
                np.asarray(masks, dtype=np.bool_),
            )
            if progress_callback is not None:
                progress_callback(
                    f"feature block {block.name!r}; progress={format_progress_fraction(len(domain.frame_uids), len(domain.frame_uids))}; "
                    "backend=columnar"
                )
            continue

        if block.name == "mace_summary" and mace_descriptor_root is not None:
            manifest = data6_bundle.mace_descriptor_manifest
            bulk = None if manifest is None else read_mace_descriptor_summary_rows(
                manifest,
                Path(mace_descriptor_root),
                domain.frame_uids,
                species_atomic_numbers,
            )
            if bulk is not None and bulk[0].shape[1] > 0:
                values_matrix, missing_matrix = bulk
                descriptor_dimension = (
                    values_matrix.shape[1] - len(species_atomic_numbers)
                ) // (2 + len(species_atomic_numbers))
                names = _mace_summary_feature_names(
                    descriptor_dimension, species_atomic_numbers
                )
                yielded = True
                yield block.name, names, values_matrix, missing_matrix
                if progress_callback is not None:
                    progress_callback(
                        f"feature block {block.name!r}; progress={format_progress_fraction(len(domain.frame_uids), len(domain.frame_uids))}; "
                        "backend=shard-batched"
                    )
                continue

        values_matrix: np.ndarray | None = None
        missing_matrix: np.ndarray | None = None
        names: tuple[str, ...] | None = None
        available = True
        frame_count = len(domain.frame_uids)
        report_interval = max(1_000, frame_count // 20)
        for frame_number, uid in enumerate(domain.frame_uids, start=1):
            try:
                if block.name == "raw_physical":
                    current_names, values, missing = _raw_physical(data4_bundle.raw_features.for_frame(uid), species_atomic_numbers)
                elif block.name == "universal_structural":
                    if structural_catalog is None: raise KeyError(uid)
                    item = structural_catalog.for_frame(uid); current_names = item.feature_names; values = np.asarray(item.vector); missing = np.asarray(item.missing_mask, dtype=bool)
                elif block.name in {"profile_extensions", "lta_frame"}:
                    extension_vectors = []
                    extension_masks = []
                    names_parts = []
                    for extension in profile_extensions:
                        try:
                            extension_names, extension_values, extension_missing = extension.frame_feature_vector(uid)
                        except TrainingDataInputError:
                            continue
                        names_parts.extend(extension_names)
                        extension_vectors.extend(extension_values)
                        extension_masks.extend(extension_missing)
                    if not names_parts:
                        raise KeyError(uid)
                    current_names = tuple(names_parts)
                    values = np.asarray(extension_vectors, dtype=np.float64)
                    missing = np.asarray(extension_masks, dtype=bool)
                elif block.name == "mace_summary":
                    if mace_descriptor_root is None: raise KeyError(uid)
                    current_names, values, missing = _mace_summary(
                        uid,
                        data6_bundle=data6_bundle,
                        descriptor_root=Path(mace_descriptor_root),
                        frame_index=frame_index,
                        species_atomic_numbers=species_atomic_numbers,
                        summary_cache=mace_summary_cache,
                    )
                else:
                    item = difficulty_by_uid[uid]
                    current_names, values, missing = _difficulty_features(item, species_atomic_numbers)
            except (KeyError, TrainingDataInputError):
                available = False; break
            current_names = tuple(current_names)
            row_values = np.asarray(values, dtype=np.float64).reshape(-1)
            row_missing = np.asarray(missing, dtype=np.bool_).reshape(-1)
            if row_values.shape != row_missing.shape:
                raise TrainingDataInputError(
                    f"Feature values and missing mask differ within block {block.name}."
                )
            if names is None:
                names = current_names
                if len(names) != row_values.size:
                    raise TrainingDataInputError(
                        f"Feature-name count differs from values within block {block.name}."
                    )
                values_matrix = np.empty(
                    (frame_count, row_values.size), dtype=np.float64
                )
                missing_matrix = np.empty(
                    (frame_count, row_values.size), dtype=np.bool_
                )
            if current_names != names:
                raise TrainingDataInputError(
                    f"Feature ordering changed within block {block.name}."
                )
            assert values_matrix is not None and missing_matrix is not None
            values_matrix[frame_number - 1] = row_values
            missing_matrix[frame_number - 1] = row_missing
            if (
                progress_callback is not None
                and len(domain.frame_uids) >= report_interval
                and (
                    frame_number % report_interval == 0
                    or frame_number == len(domain.frame_uids)
                )
            ):
                progress_callback(
                    f"feature block {block.name!r}; progress={format_progress_fraction(frame_number, len(domain.frame_uids))}"
                )
        if not available:
            if block.required: raise TrainingDataInputError(f"Required feature block {block.name!r} is unavailable.")
            continue
        assert names is not None and values_matrix is not None and missing_matrix is not None
        yielded = True
        yield block.name, names, values_matrix, missing_matrix
    if not yielded:
        raise TrainingDataInputError("No feature blocks are available for fitting.")


def _raw_blocks(
    domain: FeatureFitDomain, *, frame_catalog: Any, frame_data_by_run: Mapping[str, Any], data4_bundle: Any, data6_bundle: Any,
    policy: FeatureMetricPolicyTemplate, mace_descriptor_root: str | Path | None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    mace_summary_cache: MutableMapping[
        tuple[str, tuple[int, ...]], tuple[np.ndarray, np.ndarray]
    ] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> dict[str, tuple[tuple[str, ...], np.ndarray, np.ndarray]]:
    """Compatibility collector for callers that explicitly need all raw blocks.

    Production fitting consumes :func:`_iter_raw_blocks` directly so a large
    universal matrix is released before the next block is extracted.
    """

    return {
        name: (feature_names, values, missing)
        for name, feature_names, values, missing in _iter_raw_blocks(
            domain,
            frame_catalog=frame_catalog,
            frame_data_by_run=frame_data_by_run,
            data4_bundle=data4_bundle,
            data6_bundle=data6_bundle,
            policy=policy,
            mace_descriptor_root=mace_descriptor_root,
            frame_array_index=frame_array_index,
            mace_summary_cache=mace_summary_cache,
            progress_callback=progress_callback,
        )
    }


def _column_location_scale(
    X: np.ndarray,
    missing: np.ndarray,
    scaling: FeatureScalingKind,
    *,
    chunk_columns: int = 128,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute column statistics with bounded temporary memory."""

    center = np.zeros(X.shape[1], dtype=np.float64)
    scale = np.ones(X.shape[1], dtype=np.float64)
    if scaling is FeatureScalingKind.NONE:
        return center, scale
    import warnings

    for start in range(0, X.shape[1], chunk_columns):
        stop = min(X.shape[1], start + chunk_columns)
        block = np.asarray(X[:, start:stop], dtype=np.float64)
        block_missing = np.asarray(missing[:, start:stop], dtype=np.bool_)
        if scaling is FeatureScalingKind.ROBUST_IQR:
            # Exact robust quantiles still require an observed-value work
            # matrix. Keep it bounded by chunk_columns, but avoid this copy for
            # the much more common standard-scaling path below.
            observed = np.where(block_missing, np.nan, block)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                with np.errstate(invalid="ignore", divide="ignore"):
                    quartiles = np.nanpercentile(
                        observed, (25.0, 50.0, 75.0), axis=0
                    )
            current_center = quartiles[1]
            current_scale = quartiles[2] - quartiles[0]
        else:
            observed_mask = ~block_missing
            counts = np.count_nonzero(observed_mask, axis=0)
            sums = np.sum(
                block,
                axis=0,
                dtype=np.float64,
                where=observed_mask,
                initial=0.0,
            )
            current_center = np.zeros(stop - start, dtype=np.float64)
            nonempty = counts > 0
            np.divide(
                sums,
                counts,
                out=current_center,
                where=nonempty,
            )
            # A centered two-pass variance is more stable than E[x^2]-E[x]^2
            # and uses one bounded temporary instead of a NaN-filled matrix
            # plus nanmean/nanstd internals.
            deviations = block - current_center[None, :]
            np.copyto(deviations, 0.0, where=block_missing)
            deviations *= deviations
            variance = np.sum(deviations, axis=0, dtype=np.float64)
            np.divide(variance, counts, out=variance, where=nonempty)
            current_scale = np.sqrt(variance)
            current_center[~nonempty] = np.nan
            current_scale[~nonempty] = np.nan
        valid_center = np.isfinite(current_center)
        center[start:stop][valid_center] = current_center[valid_center]
        valid_scale = np.isfinite(current_scale)
        scale[start:stop][valid_scale] = current_scale[valid_scale]
    return center, scale


def _principal_projection(
    Z: np.ndarray,
    components: int,
    *,
    random_seed: int = 0,
) -> np.ndarray:
    """Return deterministic leading right-singular vectors.

    Small matrices retain exact SVD semantics.  Large campaign matrices use a
    deterministic randomized range finder, reducing work from a full
    ``O(min(N,P)^2 max(N,P))`` decomposition to roughly ``O(N P K)`` where
    ``K`` is the requested output dimension.
    """

    retained = min(int(components), Z.shape[0], Z.shape[1])
    if retained <= 0:
        raise TrainingDataInputError("PCA retained dimension must be positive.")
    if Z.size <= 2_000_000 or retained >= min(Z.shape) // 2:
        _, _, vh = np.linalg.svd(Z, full_matrices=False)
        return np.asarray(vh[:retained], dtype=np.float64)

    oversampling = min(16, max(4, Z.shape[1] - retained))
    sketch_size = min(Z.shape[1], retained + oversampling)
    generator = np.random.default_rng(int(random_seed))
    omega = generator.standard_normal((Z.shape[1], sketch_size))
    sample = Z @ omega
    basis, _ = np.linalg.qr(sample, mode="reduced")
    compressed = basis.T @ Z
    _, _, vh = np.linalg.svd(compressed, full_matrices=False)
    return np.asarray(vh[:retained], dtype=np.float64)


def _orient_projection_rows(projection: np.ndarray) -> None:
    """Apply the deterministic sign convention used by fitted metrics."""

    for row in projection:
        pivot = int(np.flatnonzero(np.abs(row) == np.max(np.abs(row)))[0])
        if row[pivot] < 0.0:
            row *= -1.0


def _implicit_missing_indicator_projection(
    standardized: np.ndarray,
    missing: np.ndarray,
    components: int,
    *,
    random_seed: int = 0,
    row_chunk: int = 2_048,
) -> tuple[np.ndarray, np.ndarray]:
    """PCA of ``[standardized, missing.astype(float)]`` without materializing it.

    The production universal block can contain roughly 1,400 columns.  An
    explicit missing-indicator concatenation therefore allocates another
    ``N x P`` float64 matrix (about 394 MiB for 36,759 x 1,404) before PCA.
    This routine performs the same deterministic randomized range finder using
    block matrix products and bounded row temporaries.
    """

    n_rows, n_features = standardized.shape
    total_features = 2 * n_features
    retained = min(int(components), n_rows, total_features)
    if retained <= 0:
        raise TrainingDataInputError("PCA retained dimension must be positive.")

    # Preserve exact-SVD behavior for genuinely small matrices.  The large
    # campaign path below is selected under the same criterion as
    # _principal_projection applied to the explicit concatenated matrix.
    if n_rows * total_features <= 2_000_000 or retained >= min(n_rows, total_features) // 2:
        explicit = np.concatenate(
            (standardized, missing.astype(np.float64)), axis=1
        )
        projection = _principal_projection(
            explicit, retained, random_seed=random_seed
        )
        _orient_projection_rows(projection)
        output = explicit @ projection.T
        return projection, output

    oversampling = min(16, max(4, total_features - retained))
    sketch_size = min(total_features, retained + oversampling)
    generator = np.random.default_rng(int(random_seed))
    omega = generator.standard_normal((total_features, sketch_size))
    omega_values = omega[:n_features]
    omega_missing = omega[n_features:]

    sample = standardized @ omega_values
    for start in range(0, n_rows, row_chunk):
        stop = min(n_rows, start + row_chunk)
        sample[start:stop] += (
            missing[start:stop] @ omega_missing
        )
    basis, _ = np.linalg.qr(sample, mode="reduced")
    del sample

    compressed_values = basis.T @ standardized
    compressed_missing = np.zeros(
        (basis.shape[1], n_features), dtype=np.float64
    )
    for start in range(0, n_rows, row_chunk):
        stop = min(n_rows, start + row_chunk)
        compressed_missing += (
            basis[start:stop].T
            @ missing[start:stop]
        )
    compressed = np.concatenate(
        (compressed_values, compressed_missing), axis=1
    )
    del compressed_values, compressed_missing, basis
    _, _, vh = np.linalg.svd(compressed, full_matrices=False)
    projection = np.asarray(vh[:retained], dtype=np.float64)
    _orient_projection_rows(projection)

    output = standardized @ projection[:, :n_features].T
    missing_projection = projection[:, n_features:].T
    for start in range(0, n_rows, row_chunk):
        stop = min(n_rows, start + row_chunk)
        output[start:stop] += (
            missing[start:stop] @ missing_projection
        )
    return projection, output


def _fit_block(
    names: tuple[str, ...],
    X: np.ndarray,
    missing: np.ndarray,
    block: FeatureBlockPolicy,
    policy: FeatureMetricPolicyTemplate,
    *,
    progress_callback: Callable[[str], None] | None = None,
) -> tuple[FittedFeatureBlockMetric, np.ndarray]:
    X = np.asarray(X, dtype=np.float64)
    missing = np.asarray(missing, dtype=np.bool_)
    if X.ndim != 2 or missing.shape != X.shape:
        raise TrainingDataInputError("Feature values and missing mask are misaligned.")
    if progress_callback is not None:
        progress_callback(
            f"status=phase; phase=feature-location-scale; block={block.name}"
        )
    center, scale = _column_location_scale(X, missing, block.scaling)
    scale = np.where(
        np.isfinite(scale) & (scale >= policy.minimum_scale), scale, 1.0
    )

    if progress_callback is not None:
        progress_callback(
            f"status=phase; phase=feature-impute-standardize; block={block.name}"
        )
    # One writable matrix is sufficient for imputation and standardization.
    Z = np.array(X, dtype=np.float64, copy=True, order="C")
    np.copyto(Z, np.broadcast_to(center, Z.shape), where=missing)
    Z -= center[None, :]
    Z /= scale[None, :]
    feature_names = list(names)
    input_feature_count = X.shape[1]
    if block.include_missing_indicators:
        center = np.concatenate((center, np.zeros(input_feature_count)))
        scale = np.concatenate((scale, np.ones(input_feature_count)))
        feature_names.extend(f"missing:{name}" for name in names)

    projection: np.ndarray | None = None
    logical_dimension = (
        2 * input_feature_count
        if block.include_missing_indicators
        else input_feature_count
    )
    use_pca = (
        block.pca_components is not None
        and block.pca_components < logical_dimension
        and Z.shape[0] >= 2
    )
    if use_pca and block.include_missing_indicators:
        if progress_callback is not None:
            progress_callback(
                f"status=phase; phase=feature-PCA; block={block.name}; dimensions={logical_dimension:,}->{block.pca_components:,}; missing_indicators=implicit"
            )
        projection, output = _implicit_missing_indicator_projection(
            Z,
            missing,
            block.pca_components,
            random_seed=policy.randomized_projection_seed,
        )
        del Z
    else:
        if block.include_missing_indicators:
            Z = np.concatenate((Z, missing.astype(np.float64)), axis=1)
        output = Z
        if use_pca:
            if progress_callback is not None:
                progress_callback(
                    f"status=phase; phase=feature-PCA; block={block.name}; dimensions={logical_dimension:,}->{block.pca_components:,}"
                )
            projection = _principal_projection(
                Z,
                block.pca_components,
                random_seed=policy.randomized_projection_seed,
            )
            _orient_projection_rows(projection)
            output = Z @ projection.T
            del Z

    dimension = output.shape[1]
    factor = (
        float(np.sqrt(block.weight / dimension))
        if block.normalize_by_dimension
        else float(np.sqrt(block.weight))
    )
    output *= factor
    metric = FittedFeatureBlockMetric(
        block_name=block.name,
        input_feature_names=tuple(feature_names),
        center=center,
        scale=scale,
        projection=(
            np.empty((0, len(feature_names)), dtype=np.float64)
            if projection is None
            else projection
        ),
        output_dimension=dimension,
        weight_factor=factor,
        policy_digest=policy.policy_digest,
    )
    if progress_callback is not None:
        progress_callback(
            f"status=complete; phase=feature-transform; block={block.name}; output_dimension={dimension:,}"
        )
    return metric, output


def fit_feature_metric(
    frame_catalog: Any, frame_data_by_run: Mapping[str, Any], data4_bundle: Any, data5_bundle: Any, data6_bundle: Any,
    domain: FeatureFitDomain, *, policy: FeatureMetricPolicyTemplate | None = None, mace_descriptor_root: str | Path | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    mace_summary_cache: MutableMapping[
        tuple[str, tuple[int, ...]], tuple[np.ndarray, np.ndarray]
    ] | None = None,
    canonical_domain_digests: set[str] | frozenset[str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> FittedFeatureMetric:
    canonical = (
        {item.content_digest for item in build_feature_fit_domains(data5_bundle)}
        if canonical_domain_digests is None
        else canonical_domain_digests
    )
    if domain.content_digest not in canonical:
        raise TrainingDataInputError("Feature metrics require a canonical DATA5 training domain.")
    if data6_bundle.data5_bundle_digest != data5_bundle.content_digest or data6_bundle.data4_bundle_digest != data4_bundle.content_digest:
        raise TrainingDataInputError("DATA7 feature lineage mismatch.")
    active = FeatureMetricPolicyTemplate() if policy is None else policy
    metrics: list[FittedFeatureBlockMetric] = []
    outputs: list[np.ndarray | None] = []
    policy_by_name = {item.name: item for item in active.blocks}
    for name, feature_names, X, missing in _iter_raw_blocks(
        domain,
        frame_catalog=frame_catalog,
        frame_data_by_run=frame_data_by_run,
        data4_bundle=data4_bundle,
        data6_bundle=data6_bundle,
        policy=active,
        mace_descriptor_root=mace_descriptor_root,
        frame_array_index=frame_array_index,
        mace_summary_cache=mace_summary_cache,
        progress_callback=progress_callback,
    ):
        if progress_callback is not None:
            progress_callback(
                f"status=phase; phase=fitting-feature-transform; block={name}; shape={X.shape[0]:,}x{X.shape[1]:,}"
            )
        metric, output = _fit_block(
            feature_names,
            X,
            missing,
            policy_by_name[name],
            active,
            progress_callback=progress_callback,
        )
        metrics.append(metric)
        outputs.append(output)
        # Raw block arrays can be hundreds of MiB; release each before the next
        # block is extracted instead of retaining a complete raw-block dict.
        del X, missing
    if not outputs:
        raise TrainingDataInputError("No fitted feature blocks were produced.")
    materialized_outputs = [
        output for output in outputs if output is not None
    ]
    row_count = materialized_outputs[0].shape[0]
    if any(output.shape[0] != row_count for output in materialized_outputs):
        raise TrainingDataInputError("Fitted feature blocks have inconsistent frame counts.")
    total_dimension = sum(output.shape[1] for output in materialized_outputs)
    combined = np.empty((row_count, total_dimension), dtype=np.float64)
    column_start = 0
    for index, output in enumerate(outputs):
        assert output is not None
        column_stop = column_start + output.shape[1]
        combined[:, column_start:column_stop] = output
        outputs[index] = None
        column_start = column_stop
    del materialized_outputs
    frame_table = TransformedFrameFeatureTable(
        frame_uids=tuple(domain.frame_uids),
        values=np.asarray(combined, dtype=np.float64),
    )
    return FittedFeatureMetric(
        domain=domain, policy=active, data4_bundle_digest=data4_bundle.content_digest,
        data6_bundle_digest=data6_bundle.content_digest, block_metrics=tuple(metrics), frame_features=frame_table,
    )
