"""Fail-closed production-corpus qualification for MLFF-DATA9A9c.

The qualification gate is bound to an immutable :class:`ProductionCorpusPlan`.
It derives foundation-model, residual-E0, replay, extension, and DATA8 status
from verified artifacts; callers cannot assert those states with booleans.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .reference_fit import AtomicReferenceFitMode
from .foundation import foundation_identity_matches_lineage

PRODUCTION_STAGE_RESOURCE_SCHEMA = "mdstats.production-stage-resource.v1"
PRODUCTION_EXPECTED_RUN_SCHEMA = "mdstats.production-expected-run.v1"
PROFILE_EXTENSION_REQUIREMENT_SCHEMA = "mdstats.profile-extension-evidence-requirement.v1"
PRODUCTION_CORPUS_PLAN_SCHEMA = "mdstats.production-corpus-plan.v1"
PRODUCTION_CORPUS_QUALIFICATION_SCHEMA = "mdstats.production-corpus-qualification.v3"
MLFF_DATA9A3_PARSER_VERSION = "0.20.55a0"


class ProductionGateStatus(str, Enum):
    BLOCKED = "blocked"
    CONDITIONALLY_READY = "conditionally_ready"
    PASSED = "passed"


@dataclass(frozen=True, slots=True)
class ProductionStageResourceRecord:
    stage: str
    wall_seconds: float
    peak_rss_mib: float
    output_size_bytes: int
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.stage.strip():
            raise TrainingDataInputError("Production resource stage must be non-empty.")
        if self.wall_seconds < 0 or self.peak_rss_mib < 0 or self.output_size_bytes < 0:
            raise TrainingDataInputError("Production resource measurements must be nonnegative.")
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_STAGE_RESOURCE_SCHEMA, "stage": self.stage,
                "wall_seconds": float(self.wall_seconds), "peak_rss_mib": float(self.peak_rss_mib),
                "output_size_bytes": int(self.output_size_bytes), "notes": list(self.notes)}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionStageResourceRecord":
        if payload.get("schema") != PRODUCTION_STAGE_RESOURCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production resource schema.")
        result = cls(stage=str(payload["stage"]), wall_seconds=float(payload["wall_seconds"]),
                     peak_rss_mib=float(payload["peak_rss_mib"]), output_size_bytes=int(payload["output_size_bytes"]),
                     notes=tuple(str(v) for v in payload.get("notes", ())))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production resource digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionExpectedRun:
    run_id: str
    frame_count: int
    reduced_formula: str
    ensemble: str
    target_start_kelvin: float | None = None
    target_end_kelvin: float | None = None

    def __post_init__(self) -> None:
        if not self.run_id.strip() or self.frame_count < 1 or not self.reduced_formula.strip() or not self.ensemble.strip():
            raise TrainingDataInputError("Invalid expected production run.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_EXPECTED_RUN_SCHEMA, "run_id": self.run_id, "frame_count": self.frame_count,
                "reduced_formula": self.reduced_formula, "ensemble": self.ensemble,
                "target_start_kelvin": self.target_start_kelvin, "target_end_kelvin": self.target_end_kelvin}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionExpectedRun":
        if payload.get("schema") != PRODUCTION_EXPECTED_RUN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported expected-run schema.")
        result = cls(run_id=str(payload["run_id"]), frame_count=int(payload["frame_count"]),
                     reduced_formula=str(payload["reduced_formula"]), ensemble=str(payload["ensemble"]),
                     target_start_kelvin=None if payload.get("target_start_kelvin") is None else float(payload["target_start_kelvin"]),
                     target_end_kelvin=None if payload.get("target_end_kelvin") is None else float(payload["target_end_kelvin"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Expected-run digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProfileExtensionEvidenceRequirement:
    extension_id: str
    require_partition_features: bool = True
    require_selection_features: bool = True
    require_selection_coverage: bool = True

    def __post_init__(self) -> None:
        if not self.extension_id.strip():
            raise TrainingDataInputError("Profile extension requirement must have an ID.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": PROFILE_EXTENSION_REQUIREMENT_SCHEMA, "extension_id": self.extension_id,
                "require_partition_features": self.require_partition_features,
                "require_selection_features": self.require_selection_features,
                "require_selection_coverage": self.require_selection_coverage}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProfileExtensionEvidenceRequirement":
        if payload.get("schema") != PROFILE_EXTENSION_REQUIREMENT_SCHEMA:
            raise TrainingDataSerializationError("Unsupported extension-requirement schema.")
        result = cls(extension_id=str(payload["extension_id"]),
                     require_partition_features=bool(payload["require_partition_features"]),
                     require_selection_features=bool(payload["require_selection_features"]),
                     require_selection_coverage=bool(payload["require_selection_coverage"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Extension-requirement digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionCorpusPlan:
    plan_id: str
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    normalization_manifest_digest: str
    reference_manifest_digest: str
    expected_runs: tuple[ProductionExpectedRun, ...]
    expected_cross_validation_fold_count: int
    required_profile_extensions: tuple[ProfileExtensionEvidenceRequirement, ...] = ()
    require_foundation_features: bool = True
    require_foundation_residual_e0: bool = True
    require_data8_artifacts: bool = True
    require_replay_corpus: bool = True

    def __post_init__(self) -> None:
        if not self.plan_id.strip() or not self.dataset_id.strip():
            raise TrainingDataInputError("Production corpus plan identifiers must be non-empty.")
        for name in ("source_catalog_digest", "frame_catalog_digest", "normalization_manifest_digest", "reference_manifest_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        runs = tuple(sorted(self.expected_runs, key=lambda item: item.run_id))
        if not runs or len({item.run_id for item in runs}) != len(runs):
            raise TrainingDataInputError("Production corpus plan requires unique expected runs.")
        object.__setattr__(self, "expected_runs", runs)
        requirements = tuple(sorted(self.required_profile_extensions, key=lambda item: item.extension_id))
        if len({item.extension_id for item in requirements}) != len(requirements):
            raise TrainingDataInputError("Production extension requirements must be unique.")
        object.__setattr__(self, "required_profile_extensions", requirements)
        if self.expected_cross_validation_fold_count < 0:
            raise TrainingDataInputError("Expected cross-validation fold count cannot be negative.")

    @property
    def expected_source_count(self) -> int:
        return len(self.expected_runs)

    @property
    def expected_total_frame_count(self) -> int:
        return sum(item.frame_count for item in self.expected_runs)

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_CORPUS_PLAN_SCHEMA, "plan_id": self.plan_id, "dataset_id": self.dataset_id,
                "source_catalog_digest": self.source_catalog_digest, "frame_catalog_digest": self.frame_catalog_digest,
                "normalization_manifest_digest": self.normalization_manifest_digest,
                "reference_manifest_digest": self.reference_manifest_digest,
                "expected_runs": [item.to_dict() for item in self.expected_runs],
                "expected_cross_validation_fold_count": self.expected_cross_validation_fold_count,
                "required_profile_extensions": [item.to_dict() for item in self.required_profile_extensions],
                "require_foundation_features": self.require_foundation_features,
                "require_foundation_residual_e0": self.require_foundation_residual_e0,
                "require_data8_artifacts": self.require_data8_artifacts,
                "require_replay_corpus": self.require_replay_corpus}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionCorpusPlan":
        if payload.get("schema") != PRODUCTION_CORPUS_PLAN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production-corpus-plan schema.")
        result = cls(plan_id=str(payload["plan_id"]), dataset_id=str(payload["dataset_id"]),
                     source_catalog_digest=str(payload["source_catalog_digest"]),
                     frame_catalog_digest=str(payload["frame_catalog_digest"]),
                     normalization_manifest_digest=str(payload["normalization_manifest_digest"]),
                     reference_manifest_digest=str(payload["reference_manifest_digest"]),
                     expected_runs=tuple(ProductionExpectedRun.from_dict(item) for item in payload["expected_runs"]),
                     expected_cross_validation_fold_count=int(payload["expected_cross_validation_fold_count"]),
                     required_profile_extensions=tuple(ProfileExtensionEvidenceRequirement.from_dict(item) for item in payload.get("required_profile_extensions", ())),
                     require_foundation_features=bool(payload["require_foundation_features"]),
                     require_foundation_residual_e0=bool(payload["require_foundation_residual_e0"]),
                     require_data8_artifacts=bool(payload["require_data8_artifacts"]),
                     require_replay_corpus=bool(payload["require_replay_corpus"]))
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production-corpus-plan digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class ProductionCorpusQualificationRecord:
    production_plan_digest: str
    dataset_id: str
    expected_source_count: int
    source_count: int
    total_frame_count: int
    normalization_manifest_digest: str
    reference_manifest_digest: str
    run_evidence_digest: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str | None
    data5_bundle_digest: str | None
    data6_bundle_digest: str | None
    data7_bundle_digests: tuple[str, ...]
    data8_bundle_digest: str | None
    eligible_frame_count: int
    degraded_frame_count: int
    rejected_frame_count: int
    unresolved_strain_frame_count: int
    duplicate_geometry_group_count: int
    duplicate_labeled_group_count: int
    composition_formulas: tuple[str, ...]
    target_temperatures_kelvin: tuple[float, ...]
    ensembles: tuple[str, ...]
    strain_class_counts: tuple[tuple[str, int], ...]
    feasibility_outcomes: tuple[tuple[str, int], ...]
    independence_grade_counts: tuple[tuple[str, int], ...]
    event_type_counts: tuple[tuple[str, int], ...]
    partition_unit_count: int
    condition_count: int
    cross_validation_fold_count: int
    leakage_audit_passed: bool
    profile_extension_coverage_materialized: bool
    foundation_features_materialized: bool
    foundation_residual_e0_materialized: bool
    data8_artifacts_materialized: bool
    replay_corpus_bound: bool
    target_corpus_qualified: bool
    full_data9a_passed: bool
    status: ProductionGateStatus
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]
    resource_records: tuple[ProductionStageResourceRecord, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "production_plan_digest", validate_digest(self.production_plan_digest, name="production_plan_digest"))
        for name in ("normalization_manifest_digest", "reference_manifest_digest", "run_evidence_digest", "source_catalog_digest", "frame_catalog_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("data4_bundle_digest", "data5_bundle_digest", "data6_bundle_digest", "data8_bundle_digest"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        object.__setattr__(self, "data7_bundle_digests", tuple(validate_digest(v, name="data7_bundle_digest") for v in self.data7_bundle_digests))
        object.__setattr__(self, "status", ProductionGateStatus(self.status))
        object.__setattr__(self, "composition_formulas", tuple(sorted(set(self.composition_formulas))))
        object.__setattr__(self, "target_temperatures_kelvin", tuple(sorted(set(float(v) for v in self.target_temperatures_kelvin))))
        object.__setattr__(self, "ensembles", tuple(sorted(set(self.ensembles))))
        for name in ("strain_class_counts", "feasibility_outcomes", "independence_grade_counts", "event_type_counts"):
            object.__setattr__(self, name, tuple(sorted((str(k), int(v)) for k, v in getattr(self, name))))
        object.__setattr__(self, "blockers", tuple(sorted(set(str(v) for v in self.blockers))))
        object.__setattr__(self, "warnings", tuple(sorted(set(str(v) for v in self.warnings))))
        object.__setattr__(self, "resource_records", tuple(self.resource_records))
        if self.full_data9a_passed and not self.target_corpus_qualified:
            raise TrainingDataInputError("Full DATA9A cannot pass when the target corpus fails.")
        if self.status is ProductionGateStatus.PASSED and not self.full_data9a_passed:
            raise TrainingDataInputError("Passed status requires full DATA9A completion.")

    def _payload(self) -> dict[str, Any]:
        return {"schema": PRODUCTION_CORPUS_QUALIFICATION_SCHEMA, "parser_version": MLFF_DATA9A3_PARSER_VERSION,
                **{name: getattr(self, name) for name in (
                    "production_plan_digest", "dataset_id", "expected_source_count", "source_count", "total_frame_count",
                    "normalization_manifest_digest", "reference_manifest_digest", "run_evidence_digest", "source_catalog_digest",
                    "frame_catalog_digest", "data4_bundle_digest", "data5_bundle_digest", "data6_bundle_digest",
                    "data8_bundle_digest", "eligible_frame_count", "degraded_frame_count", "rejected_frame_count",
                    "unresolved_strain_frame_count", "duplicate_geometry_group_count", "duplicate_labeled_group_count",
                    "partition_unit_count", "condition_count", "cross_validation_fold_count", "leakage_audit_passed",
                    "profile_extension_coverage_materialized", "foundation_features_materialized",
                    "foundation_residual_e0_materialized", "data8_artifacts_materialized", "replay_corpus_bound",
                    "target_corpus_qualified", "full_data9a_passed")},
                "data7_bundle_digests": list(self.data7_bundle_digests),
                "composition_formulas": list(self.composition_formulas),
                "target_temperatures_kelvin": list(self.target_temperatures_kelvin), "ensembles": list(self.ensembles),
                "strain_class_counts": dict(self.strain_class_counts), "feasibility_outcomes": dict(self.feasibility_outcomes),
                "independence_grade_counts": dict(self.independence_grade_counts), "event_type_counts": dict(self.event_type_counts),
                "status": self.status.value, "blockers": list(self.blockers), "warnings": list(self.warnings),
                "resource_records": [item.to_dict() for item in self.resource_records]}

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProductionCorpusQualificationRecord":
        if payload.get("schema") != PRODUCTION_CORPUS_QUALIFICATION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported production qualification schema.")
        kwargs = dict(payload)
        for key in ("schema", "parser_version", "content_digest"):
            kwargs.pop(key, None)
        for key in ("data7_bundle_digests", "composition_formulas", "target_temperatures_kelvin", "ensembles", "blockers", "warnings"):
            kwargs[key] = tuple(payload.get(key, ()))
        for key in ("strain_class_counts", "feasibility_outcomes", "independence_grade_counts", "event_type_counts"):
            kwargs[key] = tuple(payload.get(key, {}).items())
        kwargs["resource_records"] = tuple(ProductionStageResourceRecord.from_dict(v) for v in payload.get("resource_records", ()))
        result = cls(**kwargs)
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Production qualification digest mismatch.")
        return result


def _artifact_digest(artifact: Any | None, verified: str | None, *, name: str) -> str | None:
    if artifact is None:
        if verified is not None:
            raise TrainingDataInputError(f"{name} was supplied without its artifact.")
        return None
    if verified is not None:
        return validate_digest(verified, name=name)
    return artifact.content_digest


def _run_signature(run: Mapping[str, Any]) -> tuple[Any, ...]:
    return (str(run.get("run_id", "")), int(run["frame_count"]), str(run["reduced_formula"]), str(run["ensemble"]),
            None if run.get("target_start_kelvin") is None else float(run["target_start_kelvin"]),
            None if run.get("target_end_kelvin") is None else float(run["target_end_kelvin"]))


def _expected_run_signature(run: ProductionExpectedRun) -> tuple[Any, ...]:
    return (run.run_id, run.frame_count, run.reduced_formula, run.ensemble, run.target_start_kelvin, run.target_end_kelvin)


def _foundation_features_complete(data6_bundle: Any | None) -> bool:
    return bool(data6_bundle is not None and data6_bundle.model_sweep_plan is not None
                and data6_bundle.model_sweep_checkpoint_digest is not None
                and data6_bundle.mace_descriptor_manifest is not None
                and data6_bundle.prediction_manifest is not None
                and len(data6_bundle.mace_descriptor_manifest.records) == len(data6_bundle.model_sweep_plan.descriptor_frame_uids)
                and len(data6_bundle.prediction_manifest.records) == len(data6_bundle.model_sweep_plan.prediction_frame_uids))


def _foundation_residual_complete(data7_bundles: Sequence[Any], foundation_identity: Any | None) -> bool:
    if not data7_bundles or foundation_identity is None:
        return False
    return all(
        bundle.atomic_reference_fit.policy.fit_mode is AtomicReferenceFitMode.FOUNDATION_RESIDUAL
        and bundle.atomic_reference_fit.is_foundation_residual_fit
        and foundation_identity_matches_lineage(
            foundation_identity,
            foundation_identity_digest=bundle.atomic_reference_fit.foundation_identity_digest,
            legacy_checkpoint_digest=bundle.atomic_reference_fit.foundation_checkpoint_digest,
        )
        and tuple(z for z, _ in bundle.atomic_reference_fit.foundation_reference_energies_ev) == bundle.atomic_reference_fit.element_order
        for bundle in data7_bundles
    )


def _extension_coverage(plan: ProductionCorpusPlan, data4_bundle: Any | None, data6_bundle: Any | None,
                        data7_bundles: Sequence[Any]) -> bool:
    partition = set() if data4_bundle is None else {item.extension_id for item in data4_bundle.profile_partition_features}
    selection = set() if data6_bundle is None else {item.extension_id for item in data6_bundle.profile_selection_features}
    coverage_classes = {label for bundle in data7_bundles for level in bundle.coverage_report.levels
                        for label in level.represented_environment_classes}
    for requirement in plan.required_profile_extensions:
        if requirement.require_partition_features and requirement.extension_id not in partition:
            return False
        if requirement.require_selection_features and requirement.extension_id not in selection:
            return False
        if requirement.require_selection_coverage and not any(label.startswith(requirement.extension_id + ":") for label in coverage_classes):
            return False
    return True


def build_production_corpus_qualification_record(*, production_plan: ProductionCorpusPlan,
    normalization_manifest: Mapping[str, Any], reference_manifest: Mapping[str, Any],
    run_evidence_manifest: Mapping[str, Any], source_catalog: Any, frame_catalog: Any,
    data4_bundle: Any | None, data5_bundle: Any | None, data6_bundle: Any | None = None,
    data7_bundles: Sequence[Any] = (), data8_bundle: Any | None = None,
    resource_records: Sequence[ProductionStageResourceRecord] = (), production_materialization: Any | None = None,
    verified_data4_bundle_digest: str | None = None, verified_data5_bundle_digest: str | None = None,
    verified_data6_bundle_digest: str | None = None) -> ProductionCorpusQualificationRecord:
    if source_catalog.content_digest != production_plan.source_catalog_digest or frame_catalog.content_digest != production_plan.frame_catalog_digest:
        raise TrainingDataInputError("Live source/frame catalogs do not match the frozen production corpus plan.")
    if frame_catalog.dataset_id != production_plan.dataset_id:
        raise TrainingDataInputError("Production corpus plan/dataset mismatch.")
    if digest(normalization_manifest) != production_plan.normalization_manifest_digest or digest(reference_manifest) != production_plan.reference_manifest_digest:
        raise TrainingDataInputError("Production manifests do not match the frozen production corpus plan.")
    materialized_data7_digests: tuple[str, ...] | None = None
    if production_materialization is not None:
        if not bool(getattr(production_materialization, "complete", False)):
            raise TrainingDataInputError("Production qualification requires complete DATA9A9b materialization.")
        materialized_d7 = tuple(production_materialization.load_data7_bundles())
        materialized_d8 = production_materialization.load_data8_bundle()
        if data6_bundle is None or data6_bundle.content_digest != production_materialization.checkpoint.plan.data6_bundle_digest:
            raise TrainingDataInputError("Production materialization/DATA6 qualification lineage mismatch.")
        if data7_bundles and tuple(v.content_digest for v in data7_bundles) != tuple(v.content_digest for v in materialized_d7):
            raise TrainingDataInputError("Explicit DATA7 bundles disagree with production materialization.")
        if data8_bundle is not None and data8_bundle.content_digest != materialized_d8.content_digest:
            raise TrainingDataInputError("Explicit DATA8 bundle disagrees with production materialization.")
        data7_bundles, data8_bundle = materialized_d7, materialized_d8
        materialized_data7_digests = tuple(production_materialization.data7_bundle_digests)

    runs = tuple(run_evidence_manifest.get("runs", ()))
    expected = tuple(_expected_run_signature(item) for item in production_plan.expected_runs)
    observed = tuple(sorted((_run_signature(item) for item in runs), key=lambda item: item[0]))
    corpus_exact = observed == expected
    frame_digest = frame_catalog.content_digest
    d4_digest = _artifact_digest(data4_bundle, verified_data4_bundle_digest, name="verified_data4_bundle_digest")
    d5_digest = _artifact_digest(data5_bundle, verified_data5_bundle_digest, name="verified_data5_bundle_digest")
    d6_digest = _artifact_digest(data6_bundle, verified_data6_bundle_digest, name="verified_data6_bundle_digest")
    d7_digests = materialized_data7_digests if materialized_data7_digests is not None else tuple(v.content_digest for v in data7_bundles)
    d8_digest = None if data8_bundle is None else data8_bundle.content_digest

    eligibility = {"eligible": 0, "degraded": 0, "rejected": 0}
    for decision in frame_catalog.eligibility.decisions:
        if decision.state.value == "eligible": eligibility["degraded" if decision.warning_codes else "eligible"] += 1
        elif decision.state.value == "unresolved": eligibility["degraded"] += 1
        else: eligibility["rejected"] += 1
    strain_counts: dict[str, int] = {}
    for item in frame_catalog.strain_records: strain_counts[item.tensor_class.value] = strain_counts.get(item.tensor_class.value, 0) + 1
    unresolved = strain_counts.get("unresolved", 0)
    event_counts: dict[str, int] = {}
    if data4_bundle is not None:
        for event in data4_bundle.events.events: event_counts[event.event_type.value] = event_counts.get(event.event_type.value, 0) + 1
    feasibility_counts: dict[str, int] = {}; independence_counts: dict[str, int] = {}
    d5_usable = leakage_passed = False; unit_count = condition_count = fold_count = 0
    if data5_bundle is not None:
        d5_usable = all(v.is_usable for v in data5_bundle.feasibility_reports); leakage_passed = bool(data5_bundle.leakage_audit.passed)
        for v in data5_bundle.feasibility_reports: feasibility_counts[v.outcome.value] = feasibility_counts.get(v.outcome.value, 0) + 1
        for v in data5_bundle.independence_reports: independence_counts[v.weakest_grade.value] = independence_counts.get(v.weakest_grade.value, 0) + 1
        unit_count = len(data5_bundle.unit_catalog.units); condition_count = len({v.condition.condition_id for v in data5_bundle.unit_catalog.units})
        fold_count = sum(len(v.folds) for v in data5_bundle.cross_validation_plans)

    source_integrity = corpus_exact and len(runs) == production_plan.expected_source_count and all(
        bool(v.get("energy_complete")) and bool(v.get("forces_complete")) and bool(v.get("stress_complete"))
        and v.get("ensemble_status") == "resolved" and v.get("quality_outcome") != "unqualified"
        and v.get("production_status") != "rejected" for v in runs)
    frame_integrity = len(frame_catalog.frames) == production_plan.expected_total_frame_count and unresolved == 0 and eligibility["rejected"] == 0
    target_qualified = bool(source_integrity and frame_integrity and data4_bundle is not None and data5_bundle is not None
                            and d5_usable and leakage_passed and fold_count == production_plan.expected_cross_validation_fold_count)
    extension_ok = _extension_coverage(production_plan, data4_bundle, data6_bundle, data7_bundles)
    foundation_features = _foundation_features_complete(data6_bundle)
    foundation_identity = None
    if production_materialization is not None:
        foundation_identity = production_materialization.checkpoint.plan.foundation_checkpoint
    residual_e0 = _foundation_residual_complete(data7_bundles, foundation_identity)
    data8_ready = data8_bundle is not None
    replay_bound = bool(data8_bundle is not None and data8_bundle.replay_plan.mode.value != "none")

    blockers: list[str] = []; warnings: list[str] = []
    if data5_bundle is not None:
        non_full = sorted({v.outcome.value for v in data5_bundle.feasibility_reports if v.outcome.value != "fully_supported"})
        if non_full:
            warnings.append("data5_non_full_feasibility:" + ",".join(non_full))
        weak = sorted({v.weakest_grade.value for v in data5_bundle.independence_reports
                       if v.weakest_grade.value in {"slow_state_not_decorrelated", "insufficient_independence"}})
        if weak:
            warnings.append("data5_weak_independence_evidence:" + ",".join(weak))
    recovered = sorted(str(v.get("run_id", "")) for v in runs if v.get("recovered_xml"))
    if recovered:
        warnings.append("interrupted_xml_sources_recovered_from_complete_calculations:" + ",".join(recovered))
    degraded_runs = sorted(str(v.get("run_id", "")) for v in runs if v.get("quality_outcome") != "qualified")
    if degraded_runs:
        warnings.append("non_strict_quality_outcomes_present:" + ",".join(degraded_runs))
    if not corpus_exact: blockers.append("production_corpus_does_not_match_frozen_plan")
    if not source_integrity: blockers.append("target_source_or_property_integrity_incomplete")
    if unresolved: blockers.append("unresolved_frame_strain")
    if eligibility["rejected"]: blockers.append("rejected_training_frames_present")
    if data4_bundle is None: blockers.append("data4_not_materialized")
    if data5_bundle is None: blockers.append("data5_not_materialized")
    elif not d5_usable: blockers.append("data5_role_feasibility_insufficient")
    if fold_count != production_plan.expected_cross_validation_fold_count: blockers.append("cross_validation_fold_count_mismatch")
    if not extension_ok: blockers.append("profile_extension_coverage_not_materialized")
    if production_plan.require_foundation_features and not foundation_features: blockers.append("foundation_features_not_materialized")
    if production_plan.require_foundation_residual_e0 and not residual_e0: blockers.append("foundation_residual_e0_not_materialized")
    if production_plan.require_data8_artifacts and not data8_ready: blockers.append("data8_artifacts_not_materialized")
    if production_plan.require_replay_corpus and not replay_bound: blockers.append("production_replay_corpus_not_bound")
    full = bool(target_qualified and extension_ok
                and (foundation_features or not production_plan.require_foundation_features)
                and (residual_e0 or not production_plan.require_foundation_residual_e0)
                and (data8_ready or not production_plan.require_data8_artifacts)
                and (replay_bound or not production_plan.require_replay_corpus))
    status = ProductionGateStatus.PASSED if full else ProductionGateStatus.CONDITIONALLY_READY if target_qualified else ProductionGateStatus.BLOCKED
    return ProductionCorpusQualificationRecord(
        production_plan_digest=production_plan.content_digest, dataset_id=frame_catalog.dataset_id,
        expected_source_count=production_plan.expected_source_count, source_count=len(runs),
        total_frame_count=sum(int(v["frame_count"]) for v in runs),
        normalization_manifest_digest=digest(normalization_manifest), reference_manifest_digest=digest(reference_manifest),
        run_evidence_digest=digest(run_evidence_manifest), source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_digest, data4_bundle_digest=d4_digest, data5_bundle_digest=d5_digest,
        data6_bundle_digest=d6_digest, data7_bundle_digests=d7_digests, data8_bundle_digest=d8_digest,
        eligible_frame_count=eligibility["eligible"], degraded_frame_count=eligibility["degraded"],
        rejected_frame_count=eligibility["rejected"], unresolved_strain_frame_count=unresolved,
        duplicate_geometry_group_count=len(frame_catalog.duplicates.geometry_groups),
        duplicate_labeled_group_count=len(frame_catalog.duplicates.labeled_groups),
        composition_formulas=tuple(str(v["reduced_formula"]) for v in runs),
        target_temperatures_kelvin=tuple(float(x) for v in runs for x in (v.get("target_start_kelvin"), v.get("target_end_kelvin")) if x is not None),
        ensembles=tuple(str(v["ensemble"]) for v in runs), strain_class_counts=tuple(strain_counts.items()),
        feasibility_outcomes=tuple(feasibility_counts.items()), independence_grade_counts=tuple(independence_counts.items()),
        event_type_counts=tuple(event_counts.items()), partition_unit_count=unit_count, condition_count=condition_count,
        cross_validation_fold_count=fold_count, leakage_audit_passed=leakage_passed,
        profile_extension_coverage_materialized=extension_ok, foundation_features_materialized=foundation_features,
        foundation_residual_e0_materialized=residual_e0, data8_artifacts_materialized=data8_ready,
        replay_corpus_bound=replay_bound, target_corpus_qualified=target_qualified, full_data9a_passed=full,
        status=status, blockers=tuple(blockers), warnings=tuple(warnings), resource_records=tuple(resource_records))
