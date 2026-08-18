"""DATA7 orchestration for fitted metrics, objectives, E0 fits, and selection."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, MutableMapping

import numpy as np

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .feature_metric import FeatureFitDomain, FeatureMetricPolicyTemplate, FittedFeatureMetric, build_feature_fit_domains, fit_feature_metric
from .objectives import (
    CheckpointMetricPolicy, ConfigurationWeightPolicy, TrainingObjectivePolicy,
    TrainingWeightCatalog, build_training_weight_catalog,
)
from .reference_fit import (
    AtomicReferenceFitPolicy,
    AtomicReferenceFitRecord,
    fit_atomic_reference_energies,
)
from .selection import (
    SelectionBudgetPolicy, SelectionCoverageReport, TrainingSelectionPlan,
    build_selection_coverage_report, build_training_selection_plan,
)

DATA7_PREPARATION_BUNDLE_SCHEMA = "mdstats.data7-preparation-bundle.v1"
MLFF_DATA7_PARSER_VERSION = "0.20.64a0"
MLFF_DATA7_LEGACY_PARSER_VERSION = "0.20.35a0"
MLFF_DATA7_V63_PARSER_VERSION = "0.20.63a0"


@dataclass(frozen=True, slots=True)
class Data7PreparationBundle:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    data5_bundle_digest: str
    data6_bundle_digest: str
    domain: FeatureFitDomain
    fitted_metric: FittedFeatureMetric
    atomic_reference_fit: AtomicReferenceFitRecord
    training_weights: TrainingWeightCatalog
    checkpoint_metric_policy: CheckpointMetricPolicy
    selection_plan: TrainingSelectionPlan
    coverage_report: SelectionCoverageReport
    notes: tuple[str, ...] = ()
    _serialization_parser_version: str = field(
        default=MLFF_DATA7_PARSER_VERSION, init=False, repr=False, compare=False
    )
    _content_digest_cache: str = field(default="", init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in ("source_catalog_digest", "frame_catalog_digest", "data4_bundle_digest", "data5_bundle_digest", "data6_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.fitted_metric.domain.content_digest != self.domain.content_digest:
            raise TrainingDataInputError("DATA7 fitted metric/domain mismatch.")
        if self.fitted_metric.data4_bundle_digest != self.data4_bundle_digest or self.fitted_metric.data6_bundle_digest != self.data6_bundle_digest:
            raise TrainingDataInputError("DATA7 fitted metric lineage mismatch.")
        if self.atomic_reference_fit.domain.content_digest != self.domain.content_digest:
            raise TrainingDataInputError("DATA7 E0/domain mismatch.")
        if self.atomic_reference_fit.frame_catalog_digest != self.frame_catalog_digest:
            raise TrainingDataInputError("DATA7 E0/frame lineage mismatch.")
        if self.training_weights.domain.content_digest != self.domain.content_digest:
            raise TrainingDataInputError("DATA7 weight/domain mismatch.")
        if self.training_weights.data4_bundle_digest != self.data4_bundle_digest or self.training_weights.data5_bundle_digest != self.data5_bundle_digest:
            raise TrainingDataInputError("DATA7 weight lineage mismatch.")
        if self.selection_plan.domain.content_digest != self.domain.content_digest:
            raise TrainingDataInputError("DATA7 selection/domain mismatch.")
        if self.selection_plan.data4_bundle_digest != self.data4_bundle_digest or self.selection_plan.data6_bundle_digest != self.data6_bundle_digest:
            raise TrainingDataInputError("DATA7 selection lineage mismatch.")
        if self.selection_plan.metric_digest != self.fitted_metric.content_digest:
            raise TrainingDataInputError("DATA7 selection/metric mismatch.")
        if self.coverage_report.selection_plan_digest != self.selection_plan.content_digest:
            raise TrainingDataInputError("DATA7 coverage/selection mismatch.")
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": DATA7_PREPARATION_BUNDLE_SCHEMA, "parser_version": self._serialization_parser_version,
            "dataset_id": self.dataset_id, "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest, "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest, "data6_bundle_digest": self.data6_bundle_digest,
            "domain": self.domain.to_dict(), "fitted_metric": self.fitted_metric.to_dict(),
            "atomic_reference_fit": self.atomic_reference_fit.to_dict(), "training_weights": self.training_weights.to_dict(),
            "checkpoint_metric_policy": self.checkpoint_metric_policy.to_dict(), "selection_plan": self.selection_plan.to_dict(),
            "coverage_report": self.coverage_report.to_dict(), "notes": list(self.notes),
        }

    def _digest_payload(self) -> dict[str, Any]:
        return {
            "schema": DATA7_PREPARATION_BUNDLE_SCHEMA,
            "parser_version": self._serialization_parser_version,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "data5_bundle_digest": self.data5_bundle_digest,
            "data6_bundle_digest": self.data6_bundle_digest,
            "domain_digest": self.domain.content_digest,
            "fitted_metric_digest": self.fitted_metric.content_digest,
            "atomic_reference_fit_digest": self.atomic_reference_fit.content_digest,
            "training_weights_digest": self.training_weights.content_digest,
            "checkpoint_metric_policy_digest": self.checkpoint_metric_policy.policy_digest,
            "selection_plan_digest": self.selection_plan.content_digest,
            "coverage_report_digest": self.coverage_report.content_digest,
            "notes": list(self.notes),
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data7PreparationBundle":
        if payload.get("schema") != DATA7_PREPARATION_BUNDLE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported DATA7 preparation-bundle schema.")
        if payload.get("parser_version") not in (
            None,
            MLFF_DATA7_PARSER_VERSION,
            MLFF_DATA7_V63_PARSER_VERSION,
            MLFF_DATA7_LEGACY_PARSER_VERSION,
        ):
            raise TrainingDataSerializationError("Unsupported DATA7 parser version.")
        result = cls(
            dataset_id=str(payload["dataset_id"]), source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]), data4_bundle_digest=str(payload["data4_bundle_digest"]),
            data5_bundle_digest=str(payload["data5_bundle_digest"]), data6_bundle_digest=str(payload["data6_bundle_digest"]),
            domain=FeatureFitDomain.from_dict(payload["domain"]), fitted_metric=FittedFeatureMetric.from_dict(payload["fitted_metric"]),
            atomic_reference_fit=AtomicReferenceFitRecord.from_dict(payload["atomic_reference_fit"]),
            training_weights=TrainingWeightCatalog.from_dict(payload["training_weights"]),
            checkpoint_metric_policy=CheckpointMetricPolicy.from_dict(payload["checkpoint_metric_policy"]),
            selection_plan=TrainingSelectionPlan.from_dict(payload["selection_plan"]),
            coverage_report=SelectionCoverageReport.from_dict(payload["coverage_report"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("parser_version") is not None:
            object.__setattr__(
                result,
                "_serialization_parser_version",
                str(payload["parser_version"]),
            )
        expected = payload.get("content_digest")
        if expected is not None and expected != result.content_digest:
            legacy_payload = {
                key: value for key, value in payload.items() if key != "content_digest"
            }
            if expected != digest(legacy_payload):
                raise TrainingDataSerializationError(
                    "DATA7 preparation-bundle digest mismatch."
                )
        return result


def build_data7_preparation_bundle(
    source_catalog: Any, frame_catalog: Any, frame_data_by_run: Mapping[str, Any], data4_bundle: Any, data5_bundle: Any, data6_bundle: Any,
    domain: FeatureFitDomain, *, feature_metric_policy: FeatureMetricPolicyTemplate | None = None,
    atomic_reference_policy: AtomicReferenceFitPolicy | None = None,
    objective_policy: TrainingObjectivePolicy | None = None,
    configuration_weight_policy: ConfigurationWeightPolicy | None = None,
    checkpoint_metric_policy: CheckpointMetricPolicy | None = None,
    selection_budget_policy: SelectionBudgetPolicy,
    mace_descriptor_root: str | Path | None = None,
    foundation_prediction_energy_by_frame: Mapping[str, float] | None = None,
    foundation_reference_energies: Mapping[int, float] | None = None,
    foundation_checkpoint_digest: str | None = None,
    foundation_identity_digest: str | None = None,
    frame_array_index: Mapping[str, tuple[Any, Any, int]] | None = None,
    mace_summary_cache: MutableMapping[
        tuple[str, tuple[int, ...]], tuple[np.ndarray, np.ndarray]
    ] | None = None,
    composition_count_cache: MutableMapping[str, Mapping[int, int]] | None = None,
    canonical_domain_digests: set[str] | frozenset[str] | None = None,
    frame_record_by_uid: Mapping[str, Any] | None = None,
    event_anchor_frame_uids: set[str] | frozenset[str] | None = None,
    protected_event_frame_uids: set[str] | frozenset[str] | None = None,
    progress_callback: Callable[[str], None] | None = None,
) -> Data7PreparationBundle:
    canonical = (
        {item.content_digest for item in build_feature_fit_domains(data5_bundle)}
        if canonical_domain_digests is None
        else canonical_domain_digests
    )
    if domain.content_digest not in canonical:
        raise TrainingDataInputError("DATA7 requires a canonical DATA5 training domain.")
    if data6_bundle.data5_bundle_digest != data5_bundle.content_digest or data6_bundle.data4_bundle_digest != data4_bundle.content_digest:
        raise TrainingDataInputError("DATA7 input lineage mismatch.")
    if progress_callback is not None:
        progress_callback("status=phase; phase=fitting-domain-local-feature-metric")
    metric = fit_feature_metric(
        frame_catalog, frame_data_by_run, data4_bundle, data5_bundle, data6_bundle, domain,
        policy=feature_metric_policy,
        mace_descriptor_root=mace_descriptor_root,
        frame_array_index=frame_array_index,
        mace_summary_cache=mace_summary_cache,
        canonical_domain_digests=canonical,
        progress_callback=progress_callback,
    )
    if progress_callback is not None:
        progress_callback("status=phase; phase=fitting-atomic-reference-energies")
    e0 = fit_atomic_reference_energies(
        frame_catalog,
        frame_data_by_run,
        data5_bundle,
        domain,
        policy=atomic_reference_policy,
        foundation_prediction_energy_by_frame=foundation_prediction_energy_by_frame,
        foundation_reference_energies=foundation_reference_energies,
        foundation_checkpoint_digest=foundation_checkpoint_digest,
        foundation_identity_digest=foundation_identity_digest,
        frame_array_index=frame_array_index,
        composition_count_cache=composition_count_cache,
        canonical_domain_digests=canonical,
    )
    if progress_callback is not None:
        progress_callback("status=phase; phase=building-training-objective-weights")
    weights = build_training_weight_catalog(
        frame_catalog, data4_bundle, data5_bundle, domain,
        objective_policy=objective_policy, configuration_policy=configuration_weight_policy,
        canonical_domain_digests=canonical,
        frame_record_by_uid=frame_record_by_uid,
        event_anchor_frame_uids=event_anchor_frame_uids,
        protected_event_frame_uids=protected_event_frame_uids,
    )
    checkpoint = CheckpointMetricPolicy() if checkpoint_metric_policy is None else checkpoint_metric_policy
    if progress_callback is not None:
        progress_callback("status=phase; phase=building-bounded-selection-ladder")
    selection = build_training_selection_plan(data4_bundle, data5_bundle, data6_bundle, metric, policy=selection_budget_policy)
    if progress_callback is not None:
        progress_callback("status=phase; phase=computing-vectorized-selection-coverage")
    coverage = build_selection_coverage_report(data4_bundle, data5_bundle, data6_bundle, metric, selection)
    return Data7PreparationBundle(
        dataset_id=frame_catalog.dataset_id, source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest, data4_bundle_digest=data4_bundle.content_digest,
        data5_bundle_digest=data5_bundle.content_digest, data6_bundle_digest=data6_bundle.content_digest,
        domain=domain, fitted_metric=metric, atomic_reference_fit=e0, training_weights=weights,
        checkpoint_metric_policy=checkpoint, selection_plan=selection, coverage_report=coverage,
        notes=(
            "DATA7 fitted products and selections are local to one canonical training domain; held-out evidence remains untouched.",
            "Coverage reports are descriptive and require DATA9 learning-curve validation.",
        ),
    )
