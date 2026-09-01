"""DATA5 orchestration bundle for feasibility, roles, folds, blinding, and leakage."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest, validate_serialized_digest
from .blinding import BlindingBoundaryCatalog, BlindingPolicy, build_blinding_boundary_catalog
from .leakage import LeakageAuditPolicy, LeakageAuditReport, audit_partition_leakage
from .partition import (
    CrossValidationPlan,
    OuterPartition,
    PartitionFeasibilityReport,
    PartitionIndependenceReport,
    PartitionPolicy,
    PartitionUnitCatalog,
    assess_partition_feasibility,
    build_cross_validation_plans,
    build_independence_reports,
    build_outer_partitions,
    build_partition_unit_catalog,
)

DATA5_PARTITION_BUNDLE_SCHEMA = "mdstats.data5-partition-bundle.v2"
LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA = "mdstats.data5-partition-bundle.v1"
MLFF_DATA5_PARSER_VERSION = "0.20.33a0"


@dataclass(frozen=True, slots=True)
class Data5PartitionBundle:
    dataset_id: str
    source_catalog_digest: str
    frame_catalog_digest: str
    data4_bundle_digest: str
    partition_policy: PartitionPolicy
    unit_catalog: PartitionUnitCatalog
    feasibility_reports: tuple[PartitionFeasibilityReport, ...]
    outer_partitions: tuple[OuterPartition, ...]
    independence_reports: tuple[PartitionIndependenceReport, ...]
    cross_validation_plans: tuple[CrossValidationPlan, ...] = ()
    blinding_boundaries: BlindingBoundaryCatalog = field(default_factory=lambda: BlindingBoundaryCatalog(boundaries=()))
    leakage_audit: LeakageAuditReport = field(default_factory=lambda: None)  # type: ignore[assignment]
    schema: str = DATA5_PARTITION_BUNDLE_SCHEMA
    notes: tuple[str, ...] = ()
    _content_digest_cache: str = field(
        default="", init=False, repr=False, compare=False
    )
    _feasibility_by_label_domain: dict[str, PartitionFeasibilityReport] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _outer_by_label_domain: dict[str, OuterPartition] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _independence_by_label_domain: dict[str, PartitionIndependenceReport] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _cross_validation_by_label_domain: dict[str, CrossValidationPlan] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("source_catalog_digest", "frame_catalog_digest", "data4_bundle_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if self.schema not in (DATA5_PARTITION_BUNDLE_SCHEMA, LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA):
            raise TrainingDataInputError("Unsupported DATA5 partition-bundle schema.")
        if self.unit_catalog.dataset_id != self.dataset_id:
            raise TrainingDataInputError("DATA5 unit catalog dataset mismatch.")
        if self.unit_catalog.source_catalog_digest != self.source_catalog_digest:
            raise TrainingDataInputError("DATA5 source lineage mismatch.")
        if self.unit_catalog.frame_catalog_digest != self.frame_catalog_digest:
            raise TrainingDataInputError("DATA5 frame lineage mismatch.")
        if self.unit_catalog.data4_bundle_digest != self.data4_bundle_digest:
            raise TrainingDataInputError("DATA5 feature lineage mismatch.")
        if self.unit_catalog.policy_digest != self.partition_policy.policy_digest:
            raise TrainingDataInputError("DATA5 partition policy mismatch.")
        domains = {item.label_domain_id for item in self.unit_catalog.units}
        for name, records in (
            ("feasibility_reports", self.feasibility_reports),
            ("outer_partitions", self.outer_partitions),
            ("independence_reports", self.independence_reports),
        ):
            if {item.label_domain_id for item in records} != domains:
                raise TrainingDataInputError(f"{name} does not cover every label domain exactly.")
        if self.schema == LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA:
            if {item.label_domain_id for item in self.cross_validation_plans} != domains:
                raise TrainingDataInputError("cross_validation_plans does not cover every label domain exactly.")
        if self.leakage_audit is not None:
            if self.leakage_audit.unit_catalog_digest != self.unit_catalog.content_digest:
                raise TrainingDataInputError("DATA5 leakage audit lineage mismatch.")
            if not self.leakage_audit.passed:
                raise TrainingDataInputError("DATA5 bundle cannot be created with leakage errors.")
        feasibility = tuple(sorted(self.feasibility_reports, key=lambda item: item.label_domain_id))
        outer = tuple(sorted(self.outer_partitions, key=lambda item: item.label_domain_id))
        independence = tuple(sorted(self.independence_reports, key=lambda item: item.label_domain_id))
        cross_validation = tuple(sorted(self.cross_validation_plans, key=lambda item: item.label_domain_id))
        object.__setattr__(self, "feasibility_reports", feasibility)
        object.__setattr__(self, "outer_partitions", outer)
        object.__setattr__(self, "independence_reports", independence)
        object.__setattr__(self, "cross_validation_plans", cross_validation)
        object.__setattr__(self, "_feasibility_by_label_domain", {item.label_domain_id: item for item in feasibility})
        object.__setattr__(self, "_outer_by_label_domain", {item.label_domain_id: item for item in outer})
        object.__setattr__(self, "_independence_by_label_domain", {item.label_domain_id: item for item in independence})
        object.__setattr__(self, "_cross_validation_by_label_domain", {item.label_domain_id: item for item in cross_validation})
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))

    def feasibility_for_domain(self, label_domain_id: str) -> PartitionFeasibilityReport:
        try:
            return self._feasibility_by_label_domain[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def outer_partition_for_domain(self, label_domain_id: str) -> OuterPartition:
        try:
            return self._outer_by_label_domain[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def independence_for_domain(self, label_domain_id: str) -> PartitionIndependenceReport:
        try:
            return self._independence_by_label_domain[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def cross_validation_for_domain(self, label_domain_id: str) -> CrossValidationPlan:
        if self.schema != LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA:
            raise AttributeError("Current DATA5 partition bundles do not construct cross-validation plans.")
        try:
            return self._cross_validation_by_label_domain[label_domain_id]
        except KeyError:
            raise KeyError(label_domain_id) from None

    def _payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": self.schema,
            "parser_version": MLFF_DATA5_PARSER_VERSION,
            "dataset_id": self.dataset_id,
            "source_catalog_digest": self.source_catalog_digest,
            "frame_catalog_digest": self.frame_catalog_digest,
            "data4_bundle_digest": self.data4_bundle_digest,
            "partition_policy": self.partition_policy.to_dict(),
            "unit_catalog": self.unit_catalog.to_dict(),
            "feasibility_reports": [item.to_dict() for item in self.feasibility_reports],
            "outer_partitions": [item.to_dict() for item in self.outer_partitions],
            "independence_reports": [item.to_dict() for item in self.independence_reports],
            "blinding_boundaries": self.blinding_boundaries.to_dict(),
            "leakage_audit": self.leakage_audit.to_dict(),
            "notes": list(self.notes),
        }
        if self.schema == LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA:
            payload["cross_validation_plans"] = [item.to_dict() for item in self.cross_validation_plans]
        return payload

    @property
    def content_digest(self) -> str:
        cached = self._content_digest_cache
        if not cached:
            cached = digest(self._payload())
            object.__setattr__(self, "_content_digest_cache", cached)
        return cached

    def to_dict(self) -> dict[str, Any]:
        payload = self._payload()
        cached = self._content_digest_cache
        if not cached:
            cached = digest(payload)
            object.__setattr__(self, "_content_digest_cache", cached)
        return {**payload, "content_digest": cached}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Data5PartitionBundle":
        schema = payload.get("schema")
        if schema not in (DATA5_PARTITION_BUNDLE_SCHEMA, LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA):
            raise TrainingDataSerializationError("Unsupported DATA5 partition-bundle schema.")
        if payload.get("parser_version") not in (None, MLFF_DATA5_PARSER_VERSION):
            raise TrainingDataSerializationError("Unsupported DATA5 parser version.")
        cv_plans = ()
        if schema == LEGACY_DATA5_PARTITION_BUNDLE_SCHEMA:
            cv_plans = tuple(CrossValidationPlan.from_dict(item) for item in payload.get("cross_validation_plans", ()))
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_catalog_digest=str(payload["source_catalog_digest"]),
            frame_catalog_digest=str(payload["frame_catalog_digest"]),
            data4_bundle_digest=str(payload["data4_bundle_digest"]),
            partition_policy=PartitionPolicy.from_dict(payload["partition_policy"]),
            unit_catalog=PartitionUnitCatalog.from_dict(payload["unit_catalog"]),
            feasibility_reports=tuple(PartitionFeasibilityReport.from_dict(item) for item in payload["feasibility_reports"]),
            outer_partitions=tuple(OuterPartition.from_dict(item) for item in payload["outer_partitions"]),
            independence_reports=tuple(PartitionIndependenceReport.from_dict(item) for item in payload["independence_reports"]),
            cross_validation_plans=cv_plans,
            blinding_boundaries=BlindingBoundaryCatalog.from_dict(payload["blinding_boundaries"]),
            leakage_audit=LeakageAuditReport.from_dict(payload["leakage_audit"]),
            schema=schema,
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        validate_serialized_digest(
            payload,
            digest_field="content_digest",
            current_digest=result.content_digest,
            error_message="DATA5 partition-bundle digest mismatch.",
        )
        return result


def build_data5_partition_bundle(
    source_catalog: Any,
    frame_catalog: Any,
    data4_bundle: Any,
    *,
    partition_policy: PartitionPolicy | None = None,
    blinding_policy: BlindingPolicy | None = None,
    leakage_policy: LeakageAuditPolicy | None = None,
    regime_by_frame_uid: Mapping[str, str] | None = None,
    user_labels_by_frame_uid: Mapping[str, Mapping[str, str]] | None = None,
) -> Data5PartitionBundle:
    active = PartitionPolicy() if partition_policy is None else partition_policy
    units = build_partition_unit_catalog(
        source_catalog,
        frame_catalog,
        data4_bundle,
        policy=active,
        regime_by_frame_uid=regime_by_frame_uid,
        user_labels_by_frame_uid=user_labels_by_frame_uid,
    )
    feasibility = assess_partition_feasibility(units, policy=active)
    outer = build_outer_partitions(units, feasibility, policy=active)
    independence = build_independence_reports(units)
    blinding = build_blinding_boundary_catalog(outer, policy=blinding_policy)
    leakage = audit_partition_leakage(
        units,
        outer,
        (),
        frame_catalog,
        data4_bundle,
        policy=leakage_policy,
        partition_policy=active,
    )
    return Data5PartitionBundle(
        dataset_id=frame_catalog.dataset_id,
        source_catalog_digest=source_catalog.content_digest,
        frame_catalog_digest=frame_catalog.content_digest,
        data4_bundle_digest=data4_bundle.content_digest,
        partition_policy=active,
        unit_catalog=units,
        feasibility_reports=feasibility,
        outer_partitions=outer,
        independence_reports=independence,
        cross_validation_plans=(),
        blinding_boundaries=blinding,
        leakage_audit=leakage,
        schema=DATA5_PARTITION_BUNDLE_SCHEMA,
        notes=(
            "DATA5 assigns statistical roles only; fitted transforms, selection, model residuals, E0 fits, and MACE artifacts remain downstream.",
        ),
    )
