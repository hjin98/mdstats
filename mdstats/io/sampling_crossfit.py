"""Stage 11E-SAMP0 complete-system cross-fit sampling foundation.

The partition is constructed from one accepted STAT1 production regime and one or
more immutable E0b species sample catalogs.  Blocks are frame-owned: every mobile
ion represented by the supplied catalogs at one frame stays in the same block and
cross-fit domain.  Ion multiplicity therefore never inflates the complete-system
effective sample count.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from ..analysis.site_samples import FrameworkAlignedIonSampleCatalog
from ..sampling import (
    CompleteFrameBlockPolicy,
    PurgedKFoldPolicy,
    assign_balanced_round_robin,
    build_complete_frame_block_plan,
    build_purged_kfold_plan,
    effective_sample_count,
    integrated_autocorrelation_time,
)
from .production_regimes import (
    ProductionIntervalStatus,
    ProductionRegime,
    ProductionRegimeCatalog,
)
from .source_controls import SourceControlError, SourceControlSerializationError

EVIDENCE_CROSSFIT_POLICY_SCHEMA = "mdstats.evidence-crossfit-policy.v1"
SAMPLING_ADEQUACY_POLICY_SCHEMA = "mdstats.sampling-adequacy-policy.v1"
FEATURE_CORRESPONDENCE_POLICY_SCHEMA = "mdstats.feature-correspondence-policy.v1"
COMPLETE_SYSTEM_BLOCK_SCHEMA = "mdstats.complete-system-block.v1"
LOCAL_DECORRELATION_DIAGNOSTIC_SCHEMA = (
    "mdstats.local-decorrelation-diagnostic.v1"
)
DOMAIN_SAMPLING_DIAGNOSTIC_SCHEMA = "mdstats.domain-sampling-diagnostic.v1"
NESTED_SELECTION_FOLD_SCHEMA = "mdstats.nested-selection-fold.v1"
NESTED_SELECTION_PLAN_SCHEMA = "mdstats.nested-selection-plan.v1"
EVIDENCE_CROSSFIT_PARTITION_SCHEMA = "mdstats.evidence-crossfit-partition.v1"

EVIDENCE_CROSSFIT_POLICY_VERSION = "mdstats.evidence-crossfit-policy.2026-07.v1"
SAMPLING_ADEQUACY_POLICY_VERSION = "mdstats.sampling-adequacy-policy.2026-07.v1"
FEATURE_CORRESPONDENCE_POLICY_VERSION = "stage11_feature_correspondence_v1"


class CrossfitDomain(str, Enum):
    DISCOVERY = "discovery"
    MODEL_SELECTION = "model_selection"
    BASIN_VALIDATION = "basin_validation"
    CORRIDOR_VALIDATION = "corridor_validation"
    THERMODYNAMIC_ESTIMATION = "thermodynamic_estimation"
    THERMODYNAMIC_VALIDATION = "thermodynamic_validation"
    FINAL_REFIT = "final_refit"


PRIMARY_DOMAINS = (
    CrossfitDomain.DISCOVERY,
    CrossfitDomain.MODEL_SELECTION,
    CrossfitDomain.BASIN_VALIDATION,
    CrossfitDomain.CORRIDOR_VALIDATION,
    CrossfitDomain.THERMODYNAMIC_ESTIMATION,
    CrossfitDomain.THERMODYNAMIC_VALIDATION,
)


class CrossfitPartitionMode(str, Enum):
    EXPLICIT_HOLDOUT = "explicit_holdout"
    NESTED_DISCOVERY_SELECTION = "nested_discovery_selection"


class SamplingAdequacyStatus(str, Enum):
    ADEQUATE = "adequate"
    INSUFFICIENT = "insufficient"
    UNAVAILABLE = "unavailable"


class CrossfitPartitionStatus(str, Enum):
    ACCEPTED = "accepted"
    INSUFFICIENT = "insufficient"


class FeatureType(str, Enum):
    POINT = "point"
    RIDGE = "ridge"


class FeatureCorrespondenceOutcome(str, Enum):
    MATCHED = "matched"
    AMBIGUOUS = "ambiguous"
    UNMATCHED_LEFT = "unmatched_left"
    UNMATCHED_RIGHT = "unmatched_right"
    SPLIT = "split"
    MERGE = "merge"


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_digest(value: str, *, name: str) -> None:
    if not isinstance(value, str) or len(value) != 64:
        raise SourceControlError(f"{name} must be a SHA-256 digest.")


def _finite(value: Any, *, name: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise SourceControlError(f"{name} must be finite.")
    return result



@dataclass(frozen=True, slots=True)
class EvidenceCrossfitPolicy:
    policy_version: str = EVIDENCE_CROSSFIT_POLICY_VERSION
    mode: CrossfitPartitionMode = CrossfitPartitionMode.EXPLICIT_HOLDOUT
    minimum_block_frames: int = 32
    autocorrelation_block_multiplier: float = 2.0
    explicit_block_length_frames: int | None = None
    nested_selection_folds: int = 3
    nested_selection_purge_blocks: int = 0
    include_final_refit: bool = False
    assignment_strategy: str = "deterministic_balanced_round_robin"
    replica_metadata_key: str = "replica_id"

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SourceControlError("Crossfit policy version is required.")
        object.__setattr__(self, "mode", CrossfitPartitionMode(self.mode))
        if self.minimum_block_frames < 2:
            raise SourceControlError("minimum_block_frames must be at least two.")
        if self.autocorrelation_block_multiplier < 1.0:
            raise SourceControlError(
                "autocorrelation_block_multiplier must be at least one."
            )
        if (
            self.explicit_block_length_frames is not None
            and self.explicit_block_length_frames < 2
        ):
            raise SourceControlError(
                "explicit_block_length_frames must be at least two."
            )
        if self.nested_selection_folds < 2:
            raise SourceControlError("nested_selection_folds must be at least two.")
        if self.nested_selection_purge_blocks < 0:
            raise SourceControlError(
                "nested_selection_purge_blocks must be nonnegative."
            )
        if self.assignment_strategy != "deterministic_balanced_round_robin":
            raise SourceControlError("Unsupported crossfit assignment strategy.")
        if not self.replica_metadata_key:
            raise SourceControlError("replica_metadata_key must be nonempty.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVIDENCE_CROSSFIT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "mode": self.mode.value,
            "minimum_block_frames": self.minimum_block_frames,
            "autocorrelation_block_multiplier": self.autocorrelation_block_multiplier,
            "explicit_block_length_frames": self.explicit_block_length_frames,
            "nested_selection_folds": self.nested_selection_folds,
            "nested_selection_purge_blocks": self.nested_selection_purge_blocks,
            "include_final_refit": self.include_final_refit,
            "assignment_strategy": self.assignment_strategy,
            "replica_metadata_key": self.replica_metadata_key,
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceCrossfitPolicy":
        if payload.get("schema") != EVIDENCE_CROSSFIT_POLICY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported evidence-crossfit-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            mode=CrossfitPartitionMode(payload["mode"]),
            minimum_block_frames=int(payload["minimum_block_frames"]),
            autocorrelation_block_multiplier=float(
                payload["autocorrelation_block_multiplier"]
            ),
            explicit_block_length_frames=(
                None
                if payload.get("explicit_block_length_frames") is None
                else int(payload["explicit_block_length_frames"])
            ),
            nested_selection_folds=int(payload["nested_selection_folds"]),
            nested_selection_purge_blocks=int(
                payload["nested_selection_purge_blocks"]
            ),
            include_final_refit=bool(payload["include_final_refit"]),
            assignment_strategy=str(payload["assignment_strategy"]),
            replica_metadata_key=str(payload["replica_metadata_key"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Evidence-crossfit-policy signature mismatch."
            )
        return result


_DEFAULT_MINIMUM_BLOCKS = tuple((item.value, 2) for item in PRIMARY_DOMAINS)


@dataclass(frozen=True, slots=True)
class SamplingAdequacyPolicy:
    policy_version: str = SAMPLING_ADEQUACY_POLICY_VERSION
    minimum_blocks_per_domain: tuple[tuple[str, int], ...] = _DEFAULT_MINIMUM_BLOCKS
    minimum_effective_samples_per_domain: float = 2.0
    minimum_replica_support_per_domain: int = 1
    require_positive_represented_time: bool = True
    maximum_tau_to_block_length_ratio: float = 0.5

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SourceControlError("Sampling-adequacy policy version is required.")
        entries = tuple(
            sorted(
                (
                    CrossfitDomain(name).value,
                    int(count),
                )
                for name, count in self.minimum_blocks_per_domain
            )
        )
        if (
            len(entries) != len(PRIMARY_DOMAINS)
            or {name for name, _ in entries} != {item.value for item in PRIMARY_DOMAINS}
        ):
            raise SourceControlError(
                "minimum_blocks_per_domain must define every primary domain exactly once."
            )
        if any(count < 1 for _, count in entries):
            raise SourceControlError("Minimum domain block counts must be positive.")
        if self.minimum_effective_samples_per_domain <= 0.0:
            raise SourceControlError(
                "minimum_effective_samples_per_domain must be positive."
            )
        if self.minimum_replica_support_per_domain < 1:
            raise SourceControlError(
                "minimum_replica_support_per_domain must be positive."
            )
        if not 0.0 < self.maximum_tau_to_block_length_ratio <= 1.0:
            raise SourceControlError(
                "maximum_tau_to_block_length_ratio must lie in (0, 1]."
            )
        object.__setattr__(self, "minimum_blocks_per_domain", entries)

    def minimum_blocks(self, domain: CrossfitDomain | str) -> int:
        target = CrossfitDomain(domain).value
        return dict(self.minimum_blocks_per_domain)[target]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SAMPLING_ADEQUACY_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "minimum_blocks_per_domain": [
                [name, count] for name, count in self.minimum_blocks_per_domain
            ],
            "minimum_effective_samples_per_domain": (
                self.minimum_effective_samples_per_domain
            ),
            "minimum_replica_support_per_domain": (
                self.minimum_replica_support_per_domain
            ),
            "require_positive_represented_time": self.require_positive_represented_time,
            "maximum_tau_to_block_length_ratio": (
                self.maximum_tau_to_block_length_ratio
            ),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SamplingAdequacyPolicy":
        if payload.get("schema") != SAMPLING_ADEQUACY_POLICY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported sampling-adequacy-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            minimum_blocks_per_domain=tuple(
                (str(item[0]), int(item[1]))
                for item in payload["minimum_blocks_per_domain"]
            ),
            minimum_effective_samples_per_domain=float(
                payload["minimum_effective_samples_per_domain"]
            ),
            minimum_replica_support_per_domain=int(
                payload["minimum_replica_support_per_domain"]
            ),
            require_positive_represented_time=bool(
                payload["require_positive_represented_time"]
            ),
            maximum_tau_to_block_length_ratio=float(
                payload["maximum_tau_to_block_length_ratio"]
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Sampling-adequacy-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class FeatureCorrespondencePolicy:
    policy_version: str = FEATURE_CORRESPONDENCE_POLICY_VERSION
    distance_weight: float = 1.0
    overlap_weight: float = 2.0
    probability_weight: float = 1.0
    maximum_assignment_cost: float = 3.0
    ambiguity_margin: float = 0.10
    admissible_type_pairs: tuple[tuple[str, str], ...] = (
        (FeatureType.POINT.value, FeatureType.POINT.value),
        (FeatureType.RIDGE.value, FeatureType.RIDGE.value),
    )
    deterministic_tie_breaking: str = "lexicographic_feature_id"
    explicit_outcomes: tuple[str, ...] = tuple(
        item.value for item in FeatureCorrespondenceOutcome
    )

    def __post_init__(self) -> None:
        if not self.policy_version:
            raise SourceControlError("Feature-correspondence policy version is required.")
        for name in (
            "distance_weight",
            "overlap_weight",
            "probability_weight",
            "maximum_assignment_cost",
            "ambiguity_margin",
        ):
            if _finite(getattr(self, name), name=name) < 0.0:
                raise SourceControlError(f"{name} must be nonnegative.")
        pairs = tuple(
            sorted(
                (FeatureType(left).value, FeatureType(right).value)
                for left, right in self.admissible_type_pairs
            )
        )
        if not pairs:
            raise SourceControlError("At least one feature-type pair is required.")
        outcomes = tuple(str(item) for item in self.explicit_outcomes)
        if set(outcomes) != {item.value for item in FeatureCorrespondenceOutcome}:
            raise SourceControlError(
                "explicit_outcomes must enumerate matched, ambiguous, unmatched, split, and merge."
            )
        if self.deterministic_tie_breaking != "lexicographic_feature_id":
            raise SourceControlError("Unsupported correspondence tie-breaking policy.")
        object.__setattr__(self, "admissible_type_pairs", pairs)
        object.__setattr__(self, "explicit_outcomes", outcomes)

    def type_pair_is_admissible(
        self, left: FeatureType | str, right: FeatureType | str
    ) -> bool:
        pair = (FeatureType(left).value, FeatureType(right).value)
        return pair in self.admissible_type_pairs

    def normalized_cost(
        self,
        *,
        distance: float,
        overlap: float,
        probability_left: float,
        probability_right: float,
        sigma_min: float,
        probability_scale: float,
        left_type: FeatureType | str,
        right_type: FeatureType | str,
    ) -> float:
        if not self.type_pair_is_admissible(left_type, right_type):
            return math.inf
        distance = _finite(distance, name="distance")
        overlap = _finite(overlap, name="overlap")
        probability_left = _finite(probability_left, name="probability_left")
        probability_right = _finite(probability_right, name="probability_right")
        sigma_min = _finite(sigma_min, name="sigma_min")
        probability_scale = _finite(
            probability_scale, name="probability_scale"
        )
        if distance < 0.0 or not 0.0 <= overlap <= 1.0:
            raise SourceControlError("Distance/overlap arguments are outside their domain.")
        if sigma_min <= 0.0 or probability_scale <= 0.0:
            raise SourceControlError("Correspondence scales must be positive.")
        return float(
            self.distance_weight * (distance / sigma_min) ** 2
            + self.overlap_weight * (1.0 - overlap)
            + self.probability_weight
            * abs(probability_left - probability_right)
            / probability_scale
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FEATURE_CORRESPONDENCE_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "distance_weight": self.distance_weight,
            "overlap_weight": self.overlap_weight,
            "probability_weight": self.probability_weight,
            "maximum_assignment_cost": self.maximum_assignment_cost,
            "ambiguity_margin": self.ambiguity_margin,
            "admissible_type_pairs": [list(item) for item in self.admissible_type_pairs],
            "deterministic_tie_breaking": self.deterministic_tie_breaking,
            "explicit_outcomes": list(self.explicit_outcomes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FeatureCorrespondencePolicy":
        if payload.get("schema") != FEATURE_CORRESPONDENCE_POLICY_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported feature-correspondence-policy schema."
            )
        result = cls(
            policy_version=str(payload["policy_version"]),
            distance_weight=float(payload["distance_weight"]),
            overlap_weight=float(payload["overlap_weight"]),
            probability_weight=float(payload["probability_weight"]),
            maximum_assignment_cost=float(payload["maximum_assignment_cost"]),
            ambiguity_margin=float(payload["ambiguity_margin"]),
            admissible_type_pairs=tuple(
                (str(item[0]), str(item[1]))
                for item in payload["admissible_type_pairs"]
            ),
            deterministic_tie_breaking=str(
                payload["deterministic_tie_breaking"]
            ),
            explicit_outcomes=tuple(str(item) for item in payload["explicit_outcomes"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Feature-correspondence-policy signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class CompleteSystemBlock:
    block_id: str
    regime_id: str
    frame_start: int
    frame_stop: int
    frame_ids: tuple[int, ...]
    represented_time: float
    weight_units: str
    catalog_sample_spans: tuple[tuple[str, int, int], ...]
    selected_atom_count: int
    sample_count: int
    replica_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.block_id or not self.regime_id:
            raise SourceControlError("Complete-system block identities are required.")
        if self.frame_start < 0 or self.frame_stop <= self.frame_start:
            raise SourceControlError("Complete-system block frame interval is invalid.")
        frame_ids = tuple(int(value) for value in self.frame_ids)
        if len(frame_ids) != self.frame_stop - self.frame_start:
            raise SourceControlError("Complete-system block frame IDs are not complete.")
        represented_time = _finite(self.represented_time, name="represented_time")
        if represented_time < 0.0:
            raise SourceControlError("represented_time must be nonnegative.")
        spans = tuple(
            sorted((str(sig), int(start), int(stop)) for sig, start, stop in self.catalog_sample_spans)
        )
        for signature, start, stop in spans:
            _require_digest(signature, name="catalog sample-span signature")
            if start < 0 or stop <= start:
                raise SourceControlError("Catalog sample span is invalid.")
        if self.selected_atom_count < 1 or self.sample_count < 1:
            raise SourceControlError("Complete-system block must contain mobile-ion samples.")
        if self.sample_count != sum(stop - start for _, start, stop in spans):
            raise SourceControlError("Complete-system block sample count disagrees with spans.")
        replicas = tuple(sorted({str(value) for value in self.replica_ids}))
        if not replicas:
            raise SourceControlError("Complete-system block requires replica support.")
        object.__setattr__(self, "frame_ids", frame_ids)
        object.__setattr__(self, "represented_time", represented_time)
        object.__setattr__(self, "catalog_sample_spans", spans)
        object.__setattr__(self, "replica_ids", replicas)

    @property
    def frame_count(self) -> int:
        return self.frame_stop - self.frame_start

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": COMPLETE_SYSTEM_BLOCK_SCHEMA,
            "block_id": self.block_id,
            "regime_id": self.regime_id,
            "frame_start": self.frame_start,
            "frame_stop": self.frame_stop,
            "frame_ids": list(self.frame_ids),
            "represented_time": self.represented_time,
            "weight_units": self.weight_units,
            "catalog_sample_spans": [list(item) for item in self.catalog_sample_spans],
            "selected_atom_count": self.selected_atom_count,
            "sample_count": self.sample_count,
            "replica_ids": list(self.replica_ids),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CompleteSystemBlock":
        if payload.get("schema") != COMPLETE_SYSTEM_BLOCK_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported complete-system-block schema."
            )
        result = cls(
            block_id=str(payload["block_id"]),
            regime_id=str(payload["regime_id"]),
            frame_start=int(payload["frame_start"]),
            frame_stop=int(payload["frame_stop"]),
            frame_ids=tuple(int(value) for value in payload["frame_ids"]),
            represented_time=float(payload["represented_time"]),
            weight_units=str(payload["weight_units"]),
            catalog_sample_spans=tuple(
                (str(item[0]), int(item[1]), int(item[2]))
                for item in payload["catalog_sample_spans"]
            ),
            selected_atom_count=int(payload["selected_atom_count"]),
            sample_count=int(payload["sample_count"]),
            replica_ids=tuple(str(value) for value in payload["replica_ids"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Complete-system-block signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class LocalDecorrelationDiagnostic:
    block_id: str
    observable_name: str
    frame_count: int
    autocorrelation_time_frames: float
    effective_sample_count: float

    def __post_init__(self) -> None:
        if not self.block_id or not self.observable_name or self.frame_count < 1:
            raise SourceControlError("Local decorrelation diagnostic identity is invalid.")
        tau = _finite(
            self.autocorrelation_time_frames,
            name="autocorrelation_time_frames",
        )
        ess = _finite(self.effective_sample_count, name="effective_sample_count")
        if tau < 0.5 or ess < 0.0 or ess > self.frame_count + 1.0e-9:
            raise SourceControlError("Local decorrelation diagnostic is out of bounds.")
        object.__setattr__(self, "autocorrelation_time_frames", tau)
        object.__setattr__(self, "effective_sample_count", ess)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": LOCAL_DECORRELATION_DIAGNOSTIC_SCHEMA,
            "block_id": self.block_id,
            "observable_name": self.observable_name,
            "frame_count": self.frame_count,
            "autocorrelation_time_frames": self.autocorrelation_time_frames,
            "effective_sample_count": self.effective_sample_count,
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "LocalDecorrelationDiagnostic":
        if payload.get("schema") != LOCAL_DECORRELATION_DIAGNOSTIC_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported local-decorrelation-diagnostic schema."
            )
        result = cls(
            block_id=str(payload["block_id"]),
            observable_name=str(payload["observable_name"]),
            frame_count=int(payload["frame_count"]),
            autocorrelation_time_frames=float(
                payload["autocorrelation_time_frames"]
            ),
            effective_sample_count=float(payload["effective_sample_count"]),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Local-decorrelation-diagnostic signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class DomainSamplingDiagnostic:
    domain: CrossfitDomain
    block_ids: tuple[str, ...]
    frame_count: int
    represented_time: float
    weight_units: str
    replica_ids: tuple[str, ...]
    local_diagnostics: tuple[LocalDecorrelationDiagnostic, ...]
    maximum_autocorrelation_time_frames: float | None
    complete_system_effective_sample_count: float | None
    status: SamplingAdequacyStatus
    reasons: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "domain", CrossfitDomain(self.domain))
        blocks = tuple(str(value) for value in self.block_ids)
        replicas = tuple(sorted({str(value) for value in self.replica_ids}))
        diagnostics = tuple(self.local_diagnostics)
        represented = _finite(self.represented_time, name="represented_time")
        if self.frame_count < 0 or represented < 0.0:
            raise SourceControlError("Domain sampling totals must be nonnegative.")
        maximum_tau = (
            None
            if self.maximum_autocorrelation_time_frames is None
            else _finite(
                self.maximum_autocorrelation_time_frames,
                name="maximum_autocorrelation_time_frames",
            )
        )
        ess = (
            None
            if self.complete_system_effective_sample_count is None
            else _finite(
                self.complete_system_effective_sample_count,
                name="complete_system_effective_sample_count",
            )
        )
        object.__setattr__(self, "block_ids", blocks)
        object.__setattr__(self, "replica_ids", replicas)
        object.__setattr__(self, "local_diagnostics", diagnostics)
        object.__setattr__(self, "represented_time", represented)
        object.__setattr__(self, "maximum_autocorrelation_time_frames", maximum_tau)
        object.__setattr__(self, "complete_system_effective_sample_count", ess)
        object.__setattr__(self, "status", SamplingAdequacyStatus(self.status))
        object.__setattr__(self, "reasons", tuple(str(value) for value in self.reasons))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DOMAIN_SAMPLING_DIAGNOSTIC_SCHEMA,
            "domain": self.domain.value,
            "block_ids": list(self.block_ids),
            "frame_count": self.frame_count,
            "represented_time": self.represented_time,
            "weight_units": self.weight_units,
            "replica_ids": list(self.replica_ids),
            "local_diagnostics": [item.to_dict() for item in self.local_diagnostics],
            "maximum_autocorrelation_time_frames": (
                self.maximum_autocorrelation_time_frames
            ),
            "complete_system_effective_sample_count": (
                self.complete_system_effective_sample_count
            ),
            "status": self.status.value,
            "reasons": list(self.reasons),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "DomainSamplingDiagnostic":
        if payload.get("schema") != DOMAIN_SAMPLING_DIAGNOSTIC_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported domain-sampling-diagnostic schema."
            )
        result = cls(
            domain=CrossfitDomain(payload["domain"]),
            block_ids=tuple(str(value) for value in payload["block_ids"]),
            frame_count=int(payload["frame_count"]),
            represented_time=float(payload["represented_time"]),
            weight_units=str(payload["weight_units"]),
            replica_ids=tuple(str(value) for value in payload["replica_ids"]),
            local_diagnostics=tuple(
                LocalDecorrelationDiagnostic.from_dict(item)
                for item in payload["local_diagnostics"]
            ),
            maximum_autocorrelation_time_frames=payload.get(
                "maximum_autocorrelation_time_frames"
            ),
            complete_system_effective_sample_count=payload.get(
                "complete_system_effective_sample_count"
            ),
            status=SamplingAdequacyStatus(payload["status"]),
            reasons=tuple(str(value) for value in payload.get("reasons", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Domain-sampling-diagnostic signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class NestedSelectionFold:
    fold_index: int
    training_block_ids: tuple[str, ...]
    model_selection_block_ids: tuple[str, ...]
    purged_block_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.fold_index < 0:
            raise SourceControlError("Nested-selection fold index must be nonnegative.")
        train = tuple(str(value) for value in self.training_block_ids)
        validate = tuple(str(value) for value in self.model_selection_block_ids)
        purged = tuple(str(value) for value in self.purged_block_ids)
        if set(train) & set(validate) or set(train) & set(purged) or set(validate) & set(purged):
            raise SourceControlError("Nested-selection fold sets must be disjoint.")
        if not train or not validate:
            raise SourceControlError(
                "Nested-selection folds require training and model-selection blocks."
            )
        object.__setattr__(self, "training_block_ids", train)
        object.__setattr__(self, "model_selection_block_ids", validate)
        object.__setattr__(self, "purged_block_ids", purged)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NESTED_SELECTION_FOLD_SCHEMA,
            "fold_index": self.fold_index,
            "training_block_ids": list(self.training_block_ids),
            "model_selection_block_ids": list(self.model_selection_block_ids),
            "purged_block_ids": list(self.purged_block_ids),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NestedSelectionFold":
        if payload.get("schema") != NESTED_SELECTION_FOLD_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported nested-selection-fold schema."
            )
        result = cls(
            fold_index=int(payload["fold_index"]),
            training_block_ids=tuple(payload["training_block_ids"]),
            model_selection_block_ids=tuple(payload["model_selection_block_ids"]),
            purged_block_ids=tuple(payload.get("purged_block_ids", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Nested-selection-fold signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class NestedSelectionPlan:
    policy_signature: str
    discovery_model_selection_pool_block_ids: tuple[str, ...]
    folds: tuple[NestedSelectionFold, ...]

    def __post_init__(self) -> None:
        _require_digest(self.policy_signature, name="nested-selection policy signature")
        pool = tuple(str(value) for value in self.discovery_model_selection_pool_block_ids)
        folds = tuple(self.folds)
        if not pool or not folds:
            raise SourceControlError("Nested-selection plan cannot be empty.")
        pool_set = set(pool)
        for fold in folds:
            if (
                set(fold.training_block_ids)
                | set(fold.model_selection_block_ids)
                | set(fold.purged_block_ids)
            ) != pool_set:
                raise SourceControlError(
                    "Every nested-selection fold must partition the complete discovery/model-selection pool."
                )
        object.__setattr__(self, "discovery_model_selection_pool_block_ids", pool)
        object.__setattr__(self, "folds", folds)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": NESTED_SELECTION_PLAN_SCHEMA,
            "policy_signature": self.policy_signature,
            "discovery_model_selection_pool_block_ids": list(
                self.discovery_model_selection_pool_block_ids
            ),
            "folds": [item.to_dict() for item in self.folds],
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "NestedSelectionPlan":
        if payload.get("schema") != NESTED_SELECTION_PLAN_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported nested-selection-plan schema."
            )
        result = cls(
            policy_signature=str(payload["policy_signature"]),
            discovery_model_selection_pool_block_ids=tuple(
                payload["discovery_model_selection_pool_block_ids"]
            ),
            folds=tuple(
                NestedSelectionFold.from_dict(item) for item in payload["folds"]
            ),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Nested-selection-plan signature mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class EvidenceCrossfitPartition:
    source_identity_signature: str
    production_regime_catalog_signature: str
    production_regime_id: str
    production_regime_signature: str
    sample_catalog_signatures: tuple[str, ...]
    temporal_weighting_signatures: tuple[str, ...]
    policy: EvidenceCrossfitPolicy
    adequacy_policy: SamplingAdequacyPolicy
    correspondence_policy: FeatureCorrespondencePolicy
    resolved_block_length_frames: int
    blocks: tuple[CompleteSystemBlock, ...]
    domain_block_ids: tuple[tuple[str, tuple[str, ...]], ...]
    nested_selection_plan: NestedSelectionPlan | None
    domain_diagnostics: tuple[DomainSamplingDiagnostic, ...]
    status: CrossfitPartitionStatus
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_identity_signature",
            "production_regime_catalog_signature",
            "production_regime_signature",
        ):
            _require_digest(getattr(self, name), name=name)
        catalogs = tuple(sorted(str(value) for value in self.sample_catalog_signatures))
        temporal = tuple(sorted(str(value) for value in self.temporal_weighting_signatures))
        for value in catalogs + temporal:
            _require_digest(value, name="partition dependency signature")
        if not self.production_regime_id or self.resolved_block_length_frames < 2:
            raise SourceControlError("Crossfit partition regime/block identity is invalid.")
        blocks = tuple(self.blocks)
        block_ids = [item.block_id for item in blocks]
        if len(block_ids) != len(set(block_ids)):
            raise SourceControlError("Complete-system block IDs must be unique.")
        assignments = tuple(
            sorted(
                (
                    CrossfitDomain(name).value,
                    tuple(str(value) for value in ids),
                )
                for name, ids in self.domain_block_ids
            )
        )
        assignment_map = dict(assignments)
        required_names = {item.value for item in PRIMARY_DOMAINS}
        if not required_names.issubset(assignment_map):
            raise SourceControlError("Every primary crossfit domain must be present.")
        known = set(block_ids)
        if any(not set(ids).issubset(known) for ids in assignment_map.values()):
            raise SourceControlError("Crossfit domain references an unknown block.")
        primary_sets = {name: set(assignment_map[name]) for name in required_names}
        if self.policy.mode is CrossfitPartitionMode.EXPLICIT_HOLDOUT:
            seen: set[str] = set()
            for domain in PRIMARY_DOMAINS:
                values = primary_sets[domain.value]
                if seen & values:
                    raise SourceControlError(
                        "Explicit crossfit primary domains must be disjoint."
                    )
                seen |= values
            if seen != known:
                raise SourceControlError(
                    "Explicit crossfit primary domains must cover every block."
                )
            if self.nested_selection_plan is not None:
                raise SourceControlError(
                    "Explicit crossfit mode cannot carry a nested-selection plan."
                )
        else:
            if primary_sets[CrossfitDomain.DISCOVERY.value] != primary_sets[
                CrossfitDomain.MODEL_SELECTION.value
            ]:
                raise SourceControlError(
                    "Nested mode requires one shared discovery/model-selection pool."
                )
            heldout = (
                primary_sets[CrossfitDomain.BASIN_VALIDATION.value]
                | primary_sets[CrossfitDomain.CORRIDOR_VALIDATION.value]
                | primary_sets[CrossfitDomain.THERMODYNAMIC_ESTIMATION.value]
                | primary_sets[CrossfitDomain.THERMODYNAMIC_VALIDATION.value]
            )
            if heldout & primary_sets[CrossfitDomain.DISCOVERY.value]:
                raise SourceControlError(
                    "Nested selection may not inspect held-out validation domains."
                )
            if heldout | primary_sets[CrossfitDomain.DISCOVERY.value] != known:
                raise SourceControlError("Nested crossfit domains must cover every block.")
            if (
                self.nested_selection_plan is None
                and CrossfitPartitionStatus(self.status)
                is not CrossfitPartitionStatus.INSUFFICIENT
            ):
                raise SourceControlError("Accepted nested mode requires a nested-selection plan.")
        if CrossfitDomain.FINAL_REFIT.value in assignment_map:
            if set(assignment_map[CrossfitDomain.FINAL_REFIT.value]) != known:
                raise SourceControlError("final_refit must explicitly use all blocks.")
        diagnostics = tuple(self.domain_diagnostics)
        if {item.domain.value for item in diagnostics} != required_names:
            raise SourceControlError(
                "Crossfit partition requires one diagnostic per primary domain."
            )
        object.__setattr__(self, "sample_catalog_signatures", catalogs)
        object.__setattr__(self, "temporal_weighting_signatures", temporal)
        object.__setattr__(self, "blocks", blocks)
        object.__setattr__(self, "domain_block_ids", assignments)
        object.__setattr__(self, "domain_diagnostics", diagnostics)
        object.__setattr__(self, "status", CrossfitPartitionStatus(self.status))
        object.__setattr__(self, "notes", tuple(str(value) for value in self.notes))

    def block_ids_for(self, domain: CrossfitDomain | str) -> tuple[str, ...]:
        return dict(self.domain_block_ids)[CrossfitDomain(domain).value]

    def frame_indices_for(self, domain: CrossfitDomain | str) -> np.ndarray:
        wanted = set(self.block_ids_for(domain))
        frames: list[int] = []
        for block in self.blocks:
            if block.block_id in wanted:
                frames.extend(range(block.frame_start, block.frame_stop))
        return np.asarray(sorted(frames), dtype=np.int64)

    def sample_mask_for(
        self,
        catalog: FrameworkAlignedIonSampleCatalog,
        domain: CrossfitDomain | str,
    ) -> np.ndarray:
        if catalog.signature not in self.sample_catalog_signatures:
            raise SourceControlError("Sample catalog is not bound to this partition.")
        mask = np.zeros(catalog.n_samples, dtype=np.bool_)
        wanted = set(self.block_ids_for(domain))
        for block in self.blocks:
            if block.block_id not in wanted:
                continue
            for signature, start, stop in block.catalog_sample_spans:
                if signature == catalog.signature:
                    mask[start:stop] = True
        mask.setflags(write=False)
        return mask

    def domain_signature(self, domain: CrossfitDomain | str) -> str:
        target = CrossfitDomain(domain)
        return _digest(
            {
                "partition_signature": self.signature,
                "domain": target.value,
                "block_ids": list(self.block_ids_for(target)),
                "final_refit_is_new_lineage": target is CrossfitDomain.FINAL_REFIT,
            }
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": EVIDENCE_CROSSFIT_PARTITION_SCHEMA,
            "source_identity_signature": self.source_identity_signature,
            "production_regime_catalog_signature": self.production_regime_catalog_signature,
            "production_regime_id": self.production_regime_id,
            "production_regime_signature": self.production_regime_signature,
            "sample_catalog_signatures": list(self.sample_catalog_signatures),
            "temporal_weighting_signatures": list(
                self.temporal_weighting_signatures
            ),
            "policy": self.policy.to_dict(),
            "adequacy_policy": self.adequacy_policy.to_dict(),
            "correspondence_policy": self.correspondence_policy.to_dict(),
            "resolved_block_length_frames": self.resolved_block_length_frames,
            "blocks": [item.to_dict() for item in self.blocks],
            "domain_block_ids": [
                [name, list(ids)] for name, ids in self.domain_block_ids
            ],
            "nested_selection_plan": (
                None
                if self.nested_selection_plan is None
                else self.nested_selection_plan.to_dict()
            ),
            "domain_diagnostics": [
                item.to_dict() for item in self.domain_diagnostics
            ],
            "status": self.status.value,
            "notes": list(self.notes),
        }

    @property
    def signature(self) -> str:
        return _digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "signature": self.signature}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "EvidenceCrossfitPartition":
        if payload.get("schema") != EVIDENCE_CROSSFIT_PARTITION_SCHEMA:
            raise SourceControlSerializationError(
                "Unsupported evidence-crossfit-partition schema."
            )
        result = cls(
            source_identity_signature=str(payload["source_identity_signature"]),
            production_regime_catalog_signature=str(
                payload["production_regime_catalog_signature"]
            ),
            production_regime_id=str(payload["production_regime_id"]),
            production_regime_signature=str(payload["production_regime_signature"]),
            sample_catalog_signatures=tuple(payload["sample_catalog_signatures"]),
            temporal_weighting_signatures=tuple(
                payload["temporal_weighting_signatures"]
            ),
            policy=EvidenceCrossfitPolicy.from_dict(payload["policy"]),
            adequacy_policy=SamplingAdequacyPolicy.from_dict(
                payload["adequacy_policy"]
            ),
            correspondence_policy=FeatureCorrespondencePolicy.from_dict(
                payload["correspondence_policy"]
            ),
            resolved_block_length_frames=int(payload["resolved_block_length_frames"]),
            blocks=tuple(CompleteSystemBlock.from_dict(item) for item in payload["blocks"]),
            domain_block_ids=tuple(
                (str(item[0]), tuple(str(value) for value in item[1]))
                for item in payload["domain_block_ids"]
            ),
            nested_selection_plan=(
                None
                if payload.get("nested_selection_plan") is None
                else NestedSelectionPlan.from_dict(payload["nested_selection_plan"])
            ),
            domain_diagnostics=tuple(
                DomainSamplingDiagnostic.from_dict(item)
                for item in payload["domain_diagnostics"]
            ),
            status=CrossfitPartitionStatus(payload["status"]),
            notes=tuple(str(value) for value in payload.get("notes", ())),
        )
        if payload.get("signature") not in (None, result.signature):
            raise SourceControlSerializationError(
                "Evidence-crossfit-partition signature mismatch."
            )
        return result


def _resolve_regime(
    catalog: ProductionRegimeCatalog, regime_id: str | None
) -> ProductionRegime:
    if regime_id is None:
        selected = tuple(catalog.selected_regime_ids)
        if len(selected) != 1:
            raise SourceControlError(
                "SAMP0 requires one explicit accepted production regime; regimes are never pooled implicitly."
            )
        regime_id = selected[0]
    matches = [item for item in catalog.regimes if item.regime_id == regime_id]
    if len(matches) != 1:
        raise SourceControlError("Requested production regime is not unique in STAT1.")
    regime = matches[0]
    if (
        not regime.scientific_use_permitted
        or regime.production_interval_status
        is not ProductionIntervalStatus.SCIENTIFIC_CANDIDATE
    ):
        raise SourceControlError(
            "SAMP0 can be built only inside a STAT1 scientific-candidate regime."
        )
    return regime


def _catalog_source_signature(catalog: FrameworkAlignedIonSampleCatalog) -> str:
    value = catalog.metadata.get("source_identity_signature")
    if not isinstance(value, str) or len(value) != 64:
        raise SourceControlError(
            "E0b sample catalog lacks a signed source_identity_signature binding."
        )
    return value


def _validate_catalogs(
    catalogs: Sequence[FrameworkAlignedIonSampleCatalog],
    *,
    source_identity_signature: str,
    replica_metadata_key: str,
) -> tuple[FrameworkAlignedIonSampleCatalog, ...]:
    result = tuple(catalogs)
    if not result:
        raise SourceControlError("SAMP0 requires at least one E0b sample catalog.")
    if len({item.signature for item in result}) != len(result):
        raise SourceControlError("Duplicate E0b sample catalogs are not permitted.")
    reference = result[0].temporal_weighting
    selected_atoms: set[int] = set()
    replica_ids: set[str] = set()
    for catalog in result:
        if _catalog_source_signature(catalog) != source_identity_signature:
            raise SourceControlError("E0b/STAT1 source identity mismatch.")
        weighting = catalog.temporal_weighting
        if not np.array_equal(weighting.frame_indices, reference.frame_indices):
            raise SourceControlError("E0b frame-index catalogs are not aligned.")
        if not np.array_equal(weighting.frame_ids, reference.frame_ids):
            raise SourceControlError("E0b frame identities are not aligned.")
        if not np.array_equal(weighting.temporal_mask, reference.temporal_mask):
            raise SourceControlError("E0b temporal masks are not aligned.")
        if not np.allclose(
            weighting.represented_time_weights,
            reference.represented_time_weights,
            rtol=0.0,
            atol=0.0,
        ):
            raise SourceControlError("E0b represented-time weights are not aligned.")
        if weighting.weight_units != reference.weight_units:
            raise SourceControlError("E0b represented-time units are not aligned.")
        overlap = selected_atoms & set(catalog.selected_atom_indices)
        if overlap:
            raise SourceControlError(
                "E0b species catalogs overlap mobile atom identities: "
                + ",".join(str(value) for value in sorted(overlap))
            )
        selected_atoms.update(catalog.selected_atom_indices)
        replica_ids.add(
            str(catalog.metadata.get(replica_metadata_key, "replica-0"))
        )
    if len(replica_ids) != 1:
        raise SourceControlError(
            "One source-bound SAMP0 partition cannot manufacture multiple replica identities."
        )
    return result


def _derived_observables(
    catalogs: Sequence[FrameworkAlignedIonSampleCatalog],
    frame_count: int,
    eligible_frames: np.ndarray,
) -> dict[str, np.ndarray]:
    observables: dict[str, np.ndarray] = {}
    for catalog in catalogs:
        counts = np.bincount(catalog.frame_indices, minlength=frame_count).astype(float)
        if np.any(counts == 0.0):
            raise SourceControlError("E0b catalog does not represent every source frame.")
        eligible_sample_mask = np.isin(catalog.frame_indices, eligible_frames)
        if not np.all(catalog.evidence_masks.position_source_mask[eligible_sample_mask]):
            continue
        for component, axis in enumerate("xyz"):
            sums = np.bincount(
                catalog.frame_indices,
                weights=catalog.registered_positions[:, component],
                minlength=frame_count,
            )
            observables[f"{catalog.species_label}:centroid_{axis}"] = sums / counts
    return observables



def _sample_span(
    catalog: FrameworkAlignedIonSampleCatalog, start: int, stop: int
) -> tuple[int, int]:
    indices = np.flatnonzero(
        (catalog.frame_indices >= start) & (catalog.frame_indices < stop)
    )
    if indices.size != (stop - start) * len(catalog.selected_atom_indices):
        raise SourceControlError(
            "E0b catalog cannot form a complete-system block for the requested frames."
        )
    if indices[-1] - indices[0] + 1 != indices.size:
        raise SourceControlError("E0b frame-major sample span is not contiguous.")
    return int(indices[0]), int(indices[-1]) + 1


def _assign_domains(
    block_ids: Sequence[str], mode: CrossfitPartitionMode
) -> tuple[dict[CrossfitDomain, tuple[str, ...]], tuple[str, ...] | None]:
    if mode is CrossfitPartitionMode.EXPLICIT_HOLDOUT:
        plan = assign_balanced_round_robin(
            block_ids, tuple(domain.value for domain in PRIMARY_DOMAINS)
        )
        return (
            {domain: plan.items_for(domain.value) for domain in PRIMARY_DOMAINS},
            None,
        )
    heldout_domains = (
        CrossfitDomain.BASIN_VALIDATION,
        CrossfitDomain.CORRIDOR_VALIDATION,
        CrossfitDomain.THERMODYNAMIC_ESTIMATION,
        CrossfitDomain.THERMODYNAMIC_VALIDATION,
    )
    labels = ("pool", *(domain.value for domain in heldout_domains))
    plan = assign_balanced_round_robin(block_ids, labels)
    pool = plan.items_for("pool")
    groups = {
        CrossfitDomain.DISCOVERY: pool,
        CrossfitDomain.MODEL_SELECTION: pool,
        **{domain: plan.items_for(domain.value) for domain in heldout_domains},
    }
    return groups, pool


def _nested_plan(
    pool: tuple[str, ...], policy: EvidenceCrossfitPolicy
) -> NestedSelectionPlan | None:
    if policy.mode is CrossfitPartitionMode.EXPLICIT_HOLDOUT:
        return None
    if len(pool) < 2:
        return None
    generic = build_purged_kfold_plan(
        pool,
        policy=PurgedKFoldPolicy(
            requested_fold_count=policy.nested_selection_folds,
            purge_radius_items=policy.nested_selection_purge_blocks,
        ),
    )
    folds = tuple(
        NestedSelectionFold(
            fold_index=fold.fold_index,
            training_block_ids=fold.training_item_ids,
            model_selection_block_ids=fold.evaluation_item_ids,
            purged_block_ids=fold.purged_item_ids,
        )
        for fold in generic.folds
    )
    if not folds:
        return None
    return NestedSelectionPlan(
        policy_signature=policy.signature,
        discovery_model_selection_pool_block_ids=pool,
        folds=folds,
    )


def build_evidence_crossfit_partition(
    *,
    production_regime_catalog: ProductionRegimeCatalog,
    sample_catalogs: Sequence[FrameworkAlignedIonSampleCatalog],
    regime_id: str | None = None,
    frame_observables: Mapping[str, Sequence[float] | np.ndarray] | None = None,
    policy: EvidenceCrossfitPolicy | None = None,
    adequacy_policy: SamplingAdequacyPolicy | None = None,
    correspondence_policy: FeatureCorrespondencePolicy | None = None,
) -> EvidenceCrossfitPartition:
    """Build one source-bound SAMP0 partition inside one accepted STAT1 regime."""

    if not isinstance(production_regime_catalog, ProductionRegimeCatalog):
        raise TypeError("production_regime_catalog must be ProductionRegimeCatalog.")
    policy = EvidenceCrossfitPolicy() if policy is None else policy
    adequacy_policy = (
        SamplingAdequacyPolicy() if adequacy_policy is None else adequacy_policy
    )
    correspondence_policy = (
        FeatureCorrespondencePolicy()
        if correspondence_policy is None
        else correspondence_policy
    )
    source_signature = production_regime_catalog.source_identity_signature
    catalogs = _validate_catalogs(
        sample_catalogs,
        source_identity_signature=source_signature,
        replica_metadata_key=policy.replica_metadata_key,
    )
    regime = _resolve_regime(production_regime_catalog, regime_id)
    weighting = catalogs[0].temporal_weighting
    frame_count = int(weighting.frame_indices.size)
    if regime.frame_stop > frame_count:
        raise SourceControlError("STAT1 regime extends beyond the E0b frame catalog.")
    eligible = np.arange(regime.frame_start, regime.frame_stop, dtype=np.int64)
    eligible = eligible[weighting.temporal_mask[eligible]]
    if eligible.size == 0:
        raise SourceControlError("No E0b temporal evidence lies inside the STAT1 regime.")

    observables = _derived_observables(catalogs, frame_count, eligible)
    if frame_observables is not None:
        for name, values in frame_observables.items():
            vector = np.asarray(values, dtype=np.float64)
            if vector.shape != (frame_count,) or np.any(~np.isfinite(vector)):
                raise SourceControlError(
                    f"Frame observable {name!r} must be finite and frame-aligned."
                )
            observables[str(name)] = vector
    block_plan = build_complete_frame_block_plan(
        eligible_frame_indices=eligible,
        frame_observables=observables,
        policy=CompleteFrameBlockPolicy(
            minimum_block_frames=policy.minimum_block_frames,
            autocorrelation_block_multiplier=policy.autocorrelation_block_multiplier,
            explicit_block_length_frames=policy.explicit_block_length_frames,
        ),
    )
    maximum_tau = block_plan.maximum_autocorrelation_time_frames
    decorrelation_length = block_plan.decorrelation_target_length_frames
    resolved_block_length = block_plan.resolved_block_length_frames
    intervals = tuple(
        (interval.frame_start, interval.frame_stop)
        for interval in block_plan.block_intervals
    )
    replica_ids = tuple(
        sorted(
            {
                str(catalog.metadata.get(policy.replica_metadata_key, "replica-0"))
                for catalog in catalogs
            }
        )
    )
    blocks: list[CompleteSystemBlock] = []
    for index, (start, stop) in enumerate(intervals):
        spans = []
        selected_atoms = 0
        sample_count = 0
        for catalog in catalogs:
            sample_start, sample_stop = _sample_span(catalog, start, stop)
            spans.append((catalog.signature, sample_start, sample_stop))
            selected_atoms += len(catalog.selected_atom_indices)
            sample_count += sample_stop - sample_start
        represented_time = float(
            np.sum(weighting.represented_time_weights[start:stop])
        )
        blocks.append(
            CompleteSystemBlock(
                block_id=f"{regime.regime_id}:block-{index:04d}",
                regime_id=regime.regime_id,
                frame_start=start,
                frame_stop=stop,
                frame_ids=tuple(int(value) for value in weighting.frame_ids[start:stop]),
                represented_time=represented_time,
                weight_units=weighting.weight_units,
                catalog_sample_spans=tuple(spans),
                selected_atom_count=selected_atoms,
                sample_count=sample_count,
                replica_ids=replica_ids,
            )
        )
    block_by_id = {item.block_id: item for item in blocks}
    groups, pool = _assign_domains(
        tuple(item.block_id for item in blocks), policy.mode
    )
    nested = None if pool is None else _nested_plan(pool, policy)

    diagnostics: list[DomainSamplingDiagnostic] = []
    for domain in PRIMARY_DOMAINS:
        ids = groups[domain]
        local: list[LocalDecorrelationDiagnostic] = []
        ess_by_observable = {name: 0.0 for name in observables}
        maximum_local_tau: float | None = None
        for block_id in ids:
            block = block_by_id[block_id]
            for name, values in observables.items():
                tau = integrated_autocorrelation_time(
                    values[block.frame_start : block.frame_stop]
                )
                ess = effective_sample_count(block.frame_count, tau)
                local.append(
                    LocalDecorrelationDiagnostic(
                        block_id=block_id,
                        observable_name=name,
                        frame_count=block.frame_count,
                        autocorrelation_time_frames=tau,
                        effective_sample_count=ess,
                    )
                )
                ess_by_observable[name] += ess
                maximum_local_tau = (
                    tau if maximum_local_tau is None else max(maximum_local_tau, tau)
                )
        complete_ess = (
            None
            if not ids or not observables
            else min(ess_by_observable.values())
        )
        domain_blocks = [block_by_id[value] for value in ids]
        represented = float(sum(item.represented_time for item in domain_blocks))
        domain_replicas = tuple(
            sorted({replica for item in domain_blocks for replica in item.replica_ids})
        )
        reasons: list[str] = []
        if len(ids) < adequacy_policy.minimum_blocks(domain):
            reasons.append(
                f"block_support={len(ids)}<{adequacy_policy.minimum_blocks(domain)}"
            )
        if complete_ess is None or complete_ess < adequacy_policy.minimum_effective_samples_per_domain:
            reasons.append(
                "complete_system_effective_sample_count_below_policy"
            )
        if len(domain_replicas) < adequacy_policy.minimum_replica_support_per_domain:
            reasons.append("replica_support_below_policy")
        if adequacy_policy.require_positive_represented_time and represented <= 0.0:
            reasons.append("represented_time_not_positive")
        if maximum_local_tau is not None and ids:
            shortest = min(block_by_id[value].frame_count for value in ids)
            if maximum_local_tau / shortest > adequacy_policy.maximum_tau_to_block_length_ratio:
                reasons.append("local_decorrelation_time_too_large_for_block")
        domain_status = (
            SamplingAdequacyStatus.UNAVAILABLE
            if ids and not observables
            else (
                SamplingAdequacyStatus.ADEQUATE
                if not reasons
                else SamplingAdequacyStatus.INSUFFICIENT
            )
        )
        diagnostics.append(
            DomainSamplingDiagnostic(
                domain=domain,
                block_ids=ids,
                frame_count=sum(item.frame_count for item in domain_blocks),
                represented_time=represented,
                weight_units=weighting.weight_units,
                replica_ids=domain_replicas,
                local_diagnostics=tuple(local),
                maximum_autocorrelation_time_frames=maximum_local_tau,
                complete_system_effective_sample_count=complete_ess,
                status=domain_status,
                reasons=tuple(reasons),
            )
        )
    status = (
        CrossfitPartitionStatus.ACCEPTED
        if all(item.status is SamplingAdequacyStatus.ADEQUATE for item in diagnostics)
        and (policy.mode is CrossfitPartitionMode.EXPLICIT_HOLDOUT or nested is not None)
        else CrossfitPartitionStatus.INSUFFICIENT
    )
    domain_map: dict[CrossfitDomain, tuple[str, ...]] = dict(groups)
    if policy.include_final_refit:
        domain_map[CrossfitDomain.FINAL_REFIT] = tuple(item.block_id for item in blocks)
    notes = [
        "Blocks are complete-system frame blocks; ion count does not multiply effective sample size.",
        "One accepted STAT1 regime is used and multiple regimes are never pooled implicitly.",
        "Held-out validation domains cannot alter discovery/model-selection hypotheses.",
        "Any final_refit domain is an all-block new lineage and inherits no held-out certificate.",
        f"maximum_discovery_observable_tau_frames={maximum_tau:.12g}",
    ]
    if policy.explicit_block_length_frames is not None and resolved_block_length < decorrelation_length:
        notes.append(
            "Explicit block length is shorter than the decorrelation-derived target; adequacy remains fail-closed."
        )
    return EvidenceCrossfitPartition(
        source_identity_signature=source_signature,
        production_regime_catalog_signature=production_regime_catalog.signature,
        production_regime_id=regime.regime_id,
        production_regime_signature=regime.signature,
        sample_catalog_signatures=tuple(item.signature for item in catalogs),
        temporal_weighting_signatures=tuple(
            item.temporal_weighting.signature for item in catalogs
        ),
        policy=policy,
        adequacy_policy=adequacy_policy,
        correspondence_policy=correspondence_policy,
        resolved_block_length_frames=resolved_block_length,
        blocks=tuple(blocks),
        domain_block_ids=tuple(
            (domain.value, ids) for domain, ids in domain_map.items()
        ),
        nested_selection_plan=nested,
        domain_diagnostics=tuple(diagnostics),
        status=status,
        notes=tuple(notes),
    )


__all__ = [
    "EVIDENCE_CROSSFIT_POLICY_SCHEMA",
    "SAMPLING_ADEQUACY_POLICY_SCHEMA",
    "FEATURE_CORRESPONDENCE_POLICY_SCHEMA",
    "COMPLETE_SYSTEM_BLOCK_SCHEMA",
    "LOCAL_DECORRELATION_DIAGNOSTIC_SCHEMA",
    "DOMAIN_SAMPLING_DIAGNOSTIC_SCHEMA",
    "NESTED_SELECTION_FOLD_SCHEMA",
    "NESTED_SELECTION_PLAN_SCHEMA",
    "EVIDENCE_CROSSFIT_PARTITION_SCHEMA",
    "EVIDENCE_CROSSFIT_POLICY_VERSION",
    "SAMPLING_ADEQUACY_POLICY_VERSION",
    "FEATURE_CORRESPONDENCE_POLICY_VERSION",
    "CrossfitDomain",
    "CrossfitPartitionMode",
    "SamplingAdequacyStatus",
    "CrossfitPartitionStatus",
    "FeatureType",
    "FeatureCorrespondenceOutcome",
    "EvidenceCrossfitPolicy",
    "SamplingAdequacyPolicy",
    "FeatureCorrespondencePolicy",
    "CompleteSystemBlock",
    "LocalDecorrelationDiagnostic",
    "DomainSamplingDiagnostic",
    "NestedSelectionFold",
    "NestedSelectionPlan",
    "EvidenceCrossfitPartition",
    "build_evidence_crossfit_partition",
]
