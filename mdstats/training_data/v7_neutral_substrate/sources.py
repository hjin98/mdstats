"""V7 source authority: precise provenance without compatibility eligibility."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..atomic_references import (
    AtomicReferenceIdentifiabilityPolicy,
    AtomicReferenceIdentifiabilityReport,
    analyze_atomic_reference_identifiability,
)
from ..labels import (
    ElectronicStructureFingerprint,
    LabelCompatibilityPolicy,
    build_label_domain_catalog,
)
from ..sources import TrainingDataSource, TrainingDataSourceCatalog

V7_SOURCE_RECORD_SCHEMA = "mdstats.v7-source-record.v1"
V7_PROVENANCE_DIAGNOSTICS_SCHEMA = "mdstats.v7-provenance-diagnostics.v1"
V7_ADVISORY_COMPATIBILITY_REPORT_SCHEMA = "mdstats.v7-advisory-compatibility-report.v1"
V7_SOURCE_AUTHORITY_SCHEMA = "mdstats.v7-source-authority.v1"


def _source_is_mechanically_usable(source: TrainingDataSource) -> tuple[bool, tuple[str, ...]]:
    reasons: list[str] = []
    selected = source.selected_energy
    if selected.present_count < 1:
        reasons.append("missing_required_energy_labels")
    if not str(selected.units).strip() or not str(selected.source_name).strip():
        reasons.append("unconvertible_energy_channel")
    if source.frame_count < 1:
        reasons.append("empty_source")
    return (not reasons, tuple(reasons))


def _fingerprint_dimension_values(
    fingerprint: ElectronicStructureFingerprint,
) -> dict[str, str]:
    return {
        "theory": fingerprint.theory.content_digest,
        "theory_resolution": fingerprint.theory.resolution_status,
        "energy_reference": fingerprint.energy_reference.content_digest,
        "energy_reference_resolution": fingerprint.energy_reference.resolution_status,
        "derivative_convention": fingerprint.derivative_convention.content_digest,
        "numerical_quality": fingerprint.numerical_quality.content_digest,
        "software_provenance": fingerprint.software_provenance.content_digest,
        "xc": digest(dict(fingerprint.theory.xc_settings)),
        "dft_u": digest(dict(fingerprint.theory.dft_u_settings)),
        "hybrid": digest(dict(fingerprint.theory.hybrid_settings)),
        "smearing": digest(dict(fingerprint.energy_reference.smearing_settings)),
    }


@dataclass(frozen=True, slots=True)
class V7SourceRecord:
    run_id: str
    source_locator: str
    source_identity_signature: str
    frame_count: int
    composition_digest: str
    reduced_formula: str
    selected_energy_channel: str
    selected_energy_units: str
    selected_energy_semantic_role: str
    electronic_structure: ElectronicStructureFingerprint
    replica_id: str | None
    reference_group: str | None
    reference_run_id: str | None
    assertions: tuple[tuple[str, Any], ...]
    target_usable: bool
    mechanical_rejection_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.source_locator.strip():
            raise TrainingDataInputError("V7 source run_id and source_locator must be non-empty.")
        object.__setattr__(
            self,
            "source_identity_signature",
            validate_digest(self.source_identity_signature, name="source_identity_signature"),
        )
        object.__setattr__(
            self,
            "composition_digest",
            validate_digest(self.composition_digest, name="composition_digest"),
        )
        object.__setattr__(self, "assertions", tuple(sorted((str(k), v) for k, v in self.assertions)))
        object.__setattr__(
            self,
            "mechanical_rejection_codes",
            tuple(str(code) for code in self.mechanical_rejection_codes),
        )
        if self.target_usable and self.mechanical_rejection_codes:
            raise TrainingDataInputError("Usable V7 sources cannot carry mechanical rejection codes.")
        if not self.target_usable and not self.mechanical_rejection_codes:
            raise TrainingDataInputError("Unusable V7 sources require mechanical rejection codes.")

    @property
    def composition(self) -> Any:
        """Duck-typed composition surface used by the neutral partition builder."""

        from types import SimpleNamespace

        return SimpleNamespace(reduced_formula=self.reduced_formula)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_SOURCE_RECORD_SCHEMA,
            "run_id": self.run_id,
            "source_locator": self.source_locator,
            "source_identity_signature": self.source_identity_signature,
            "frame_count": self.frame_count,
            "composition_digest": self.composition_digest,
            "reduced_formula": self.reduced_formula,
            "selected_energy_channel": self.selected_energy_channel,
            "selected_energy_units": self.selected_energy_units,
            "selected_energy_semantic_role": self.selected_energy_semantic_role,
            "electronic_structure": self.electronic_structure.to_dict(),
            "replica_id": self.replica_id,
            "reference_group": self.reference_group,
            "reference_run_id": self.reference_run_id,
            "assertions": dict(self.assertions),
            "target_usable": self.target_usable,
            "mechanical_rejection_codes": list(self.mechanical_rejection_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7SourceRecord":
        if payload.get("schema") != V7_SOURCE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 source-record schema.")
        result = cls(
            run_id=str(payload["run_id"]),
            source_locator=str(payload["source_locator"]),
            source_identity_signature=str(payload["source_identity_signature"]),
            frame_count=int(payload["frame_count"]),
            composition_digest=str(payload["composition_digest"]),
            reduced_formula=str(payload["reduced_formula"]),
            selected_energy_channel=str(payload["selected_energy_channel"]),
            selected_energy_units=str(payload["selected_energy_units"]),
            selected_energy_semantic_role=str(payload["selected_energy_semantic_role"]),
            electronic_structure=ElectronicStructureFingerprint.from_dict(
                payload["electronic_structure"]
            ),
            replica_id=None if payload.get("replica_id") is None else str(payload["replica_id"]),
            reference_group=(
                None if payload.get("reference_group") is None else str(payload["reference_group"])
            ),
            reference_run_id=(
                None if payload.get("reference_run_id") is None else str(payload["reference_run_id"])
            ),
            assertions=tuple((str(k), v) for k, v in payload.get("assertions", {}).items()),
            target_usable=bool(payload["target_usable"]),
            mechanical_rejection_codes=tuple(
                str(code) for code in payload.get("mechanical_rejection_codes", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 source-record digest mismatch.")
        return result


def v7_source_record_from_data2(source: TrainingDataSource) -> V7SourceRecord:
    usable, reasons = _source_is_mechanically_usable(source)
    return V7SourceRecord(
        run_id=source.run_id,
        source_locator=source.source_locator,
        source_identity_signature=source.source_identity_signature,
        frame_count=source.frame_count,
        composition_digest=source.composition.content_digest,
        reduced_formula=source.composition.reduced_formula,
        selected_energy_channel=source.selected_energy.source_name,
        selected_energy_units=source.selected_energy.units,
        selected_energy_semantic_role=source.selected_energy.semantic_role,
        electronic_structure=source.electronic_structure,
        replica_id=source.replica_id,
        reference_group=source.reference_group,
        reference_run_id=source.reference_run_id,
        assertions=source.assertions,
        target_usable=usable,
        mechanical_rejection_codes=reasons,
    )


@dataclass(frozen=True, slots=True)
class V7ProvenanceDiagnostics:
    fingerprint_counts: tuple[tuple[str, int], ...]
    unresolved_or_partial_source_ids: tuple[str, ...]
    varying_dimensions: tuple[str, ...]
    selected_energy_channel_counts: tuple[tuple[str, int], ...]
    notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "fingerprint_counts",
            tuple(sorted((str(k), int(v)) for k, v in self.fingerprint_counts)),
        )
        object.__setattr__(
            self,
            "unresolved_or_partial_source_ids",
            tuple(sorted(str(item) for item in self.unresolved_or_partial_source_ids)),
        )
        object.__setattr__(
            self, "varying_dimensions", tuple(sorted(str(item) for item in self.varying_dimensions))
        )
        object.__setattr__(
            self,
            "selected_energy_channel_counts",
            tuple(sorted((str(k), int(v)) for k, v in self.selected_energy_channel_counts)),
        )
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_PROVENANCE_DIAGNOSTICS_SCHEMA,
            "fingerprint_counts": dict(self.fingerprint_counts),
            "unresolved_or_partial_source_ids": list(self.unresolved_or_partial_source_ids),
            "varying_dimensions": list(self.varying_dimensions),
            "selected_energy_channel_counts": dict(self.selected_energy_channel_counts),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7ProvenanceDiagnostics":
        if payload.get("schema") != V7_PROVENANCE_DIAGNOSTICS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 provenance-diagnostics schema.")
        result = cls(
            fingerprint_counts=tuple(
                (str(k), int(v)) for k, v in payload.get("fingerprint_counts", {}).items()
            ),
            unresolved_or_partial_source_ids=tuple(
                str(item) for item in payload.get("unresolved_or_partial_source_ids", ())
            ),
            varying_dimensions=tuple(str(item) for item in payload.get("varying_dimensions", ())),
            selected_energy_channel_counts=tuple(
                (str(k), int(v)) for k, v in payload.get("selected_energy_channel_counts", {}).items()
            ),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 provenance-diagnostics digest mismatch.")
        return result


def build_v7_provenance_diagnostics(records: Sequence[V7SourceRecord]) -> V7ProvenanceDiagnostics:
    fingerprint_counts: dict[str, int] = {}
    channel_counts: dict[str, int] = {}
    unresolved: list[str] = []
    dimension_values: dict[str, set[str]] = {}
    for record in records:
        fingerprint = record.electronic_structure
        fingerprint_counts[fingerprint.content_digest] = (
            fingerprint_counts.get(fingerprint.content_digest, 0) + 1
        )
        channel_counts[record.selected_energy_channel] = (
            channel_counts.get(record.selected_energy_channel, 0) + 1
        )
        if fingerprint.theory.resolution_status != "resolved" or (
            fingerprint.energy_reference.resolution_status != "resolved"
        ):
            unresolved.append(record.run_id)
        for name, value in _fingerprint_dimension_values(fingerprint).items():
            dimension_values.setdefault(name, set()).add(value)
    varying = tuple(name for name, values in dimension_values.items() if len(values) > 1)
    notes = ()
    if unresolved:
        notes = (
            "Unresolved or partial electronic-structure provenance is reported and does not "
            "block target-usable membership.",
        )
    return V7ProvenanceDiagnostics(
        fingerprint_counts=tuple(fingerprint_counts.items()),
        unresolved_or_partial_source_ids=tuple(unresolved),
        varying_dimensions=varying,
        selected_energy_channel_counts=tuple(channel_counts.items()),
        notes=notes,
    )


@dataclass(frozen=True, slots=True)
class V7AdvisoryCompatibilityReport:
    """Non-authoritative compatibility grouping used only for diagnostics."""

    policy_digest: str
    source_group_ids: tuple[tuple[str, str | None], ...]
    unresolved_source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "policy_digest", validate_digest(self.policy_digest, name="policy_digest"))
        groups = tuple(sorted((str(run_id), group_id) for run_id, group_id in self.source_group_ids))
        if len({run_id for run_id, _ in groups}) != len(groups):
            raise TrainingDataInputError("Advisory compatibility groups require unique source IDs.")
        object.__setattr__(self, "source_group_ids", groups)
        object.__setattr__(
            self,
            "unresolved_source_ids",
            tuple(sorted(str(item) for item in self.unresolved_source_ids)),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_ADVISORY_COMPATIBILITY_REPORT_SCHEMA,
            "policy_digest": self.policy_digest,
            "source_group_ids": [[run_id, group_id] for run_id, group_id in self.source_group_ids],
            "unresolved_source_ids": list(self.unresolved_source_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7AdvisoryCompatibilityReport":
        if payload.get("schema") != V7_ADVISORY_COMPATIBILITY_REPORT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported V7 advisory-compatibility-report schema."
            )
        result = cls(
            policy_digest=str(payload["policy_digest"]),
            source_group_ids=tuple(
                (str(run_id), None if group_id is None else str(group_id))
                for run_id, group_id in payload.get("source_group_ids", ())
            ),
            unresolved_source_ids=tuple(str(item) for item in payload.get("unresolved_source_ids", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "V7 advisory-compatibility-report digest mismatch."
            )
        return result


def build_v7_advisory_compatibility_report(
    records: Sequence[V7SourceRecord],
    *,
    policy: LabelCompatibilityPolicy | None = None,
) -> V7AdvisoryCompatibilityReport:
    active = LabelCompatibilityPolicy() if policy is None else policy
    catalog = build_label_domain_catalog(
        {item.run_id: item.electronic_structure for item in records},
        policy=active,
    )
    groups: list[tuple[str, str | None]] = []
    for record in records:
        groups.append((record.run_id, catalog.domain_for_source(record.run_id)))
    return V7AdvisoryCompatibilityReport(
        policy_digest=active.policy_digest,
        source_group_ids=tuple(groups),
        unresolved_source_ids=tuple(catalog.unresolved_source_ids),
    )


@dataclass(frozen=True, slots=True)
class V7SourceAuthority:
    dataset_id: str
    manifest_digest: str
    energy_policy_digest: str
    sources: tuple[V7SourceRecord, ...]
    provenance_diagnostics: V7ProvenanceDiagnostics
    advisory_compatibility: V7AdvisoryCompatibilityReport
    atomic_reference_identifiability: AtomicReferenceIdentifiabilityReport
    notes: tuple[str, ...] = ()
    _by_run_id: dict[str, V7SourceRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("manifest_digest", "energy_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        sources = tuple(sorted(self.sources, key=lambda item: item.run_id))
        if len({item.run_id for item in sources}) != len(sources):
            raise TrainingDataInputError("V7 source run IDs must be unique.")
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))
        object.__setattr__(self, "_by_run_id", {item.run_id: item for item in sources})

    def source(self, run_id: str) -> V7SourceRecord:
        try:
            return self._by_run_id[run_id]
        except KeyError:
            raise KeyError(run_id) from None

    @property
    def target_usable_run_ids(self) -> tuple[str, ...]:
        return tuple(item.run_id for item in self.sources if item.target_usable)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": V7_SOURCE_AUTHORITY_SCHEMA,
            "dataset_id": self.dataset_id,
            "manifest_digest": self.manifest_digest,
            "energy_policy_digest": self.energy_policy_digest,
            "sources": [item.to_dict() for item in self.sources],
            "provenance_diagnostics": self.provenance_diagnostics.to_dict(),
            "atomic_reference_identifiability": self.atomic_reference_identifiability.to_dict(),
            "notes": list(self.notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "advisory_compatibility": self.advisory_compatibility.to_dict(),
            "content_digest": self.content_digest,
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "V7SourceAuthority":
        if payload.get("schema") != V7_SOURCE_AUTHORITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported V7 source-authority schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            manifest_digest=str(payload["manifest_digest"]),
            energy_policy_digest=str(payload["energy_policy_digest"]),
            sources=tuple(V7SourceRecord.from_dict(item) for item in payload["sources"]),
            provenance_diagnostics=V7ProvenanceDiagnostics.from_dict(
                payload["provenance_diagnostics"]
            ),
            advisory_compatibility=V7AdvisoryCompatibilityReport.from_dict(
                payload["advisory_compatibility"]
            ),
            atomic_reference_identifiability=AtomicReferenceIdentifiabilityReport.from_dict(
                payload["atomic_reference_identifiability"]
            ),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("V7 source-authority digest mismatch.")
        return result


def build_v7_source_authority(
    sources: Sequence[TrainingDataSource],
    *,
    dataset_id: str,
    manifest_digest: str,
    energy_policy_digest: str,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
    advisory_compatibility_policy: LabelCompatibilityPolicy | None = None,
) -> V7SourceAuthority:
    records = tuple(v7_source_record_from_data2(item) for item in sources)
    if not records:
        raise TrainingDataInputError("V7 source authority requires at least one source.")
    source_by_id = {item.run_id: item for item in sources}
    usable = [item for item in records if item.target_usable]
    compositions = {
        item.run_id: source_by_id[item.run_id].composition.as_dict()
        for item in (usable or records)
    }
    atomic_active = (
        AtomicReferenceIdentifiabilityPolicy()
        if atomic_reference_policy is None
        else atomic_reference_policy
    )
    atomic_report = analyze_atomic_reference_identifiability(
        compositions, policy=atomic_active
    )
    return V7SourceAuthority(
        dataset_id=dataset_id,
        manifest_digest=manifest_digest,
        energy_policy_digest=energy_policy_digest,
        sources=records,
        provenance_diagnostics=build_v7_provenance_diagnostics(records),
        advisory_compatibility=build_v7_advisory_compatibility_report(
            records, policy=advisory_compatibility_policy
        ),
        atomic_reference_identifiability=atomic_report,
        notes=(
            "V7 source authority records precise provenance and corpus-level atomic-reference "
            "identifiability. Compatibility grouping is advisory only and is not a training "
            "eligibility or identity axis.",
        ),
    )


def build_v7_source_authority_from_data2_catalog(
    catalog: TrainingDataSourceCatalog,
    *,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
    advisory_compatibility_policy: LabelCompatibilityPolicy | None = None,
) -> V7SourceAuthority:
    return build_v7_source_authority(
        catalog.sources,
        dataset_id=catalog.dataset_id,
        manifest_digest=catalog.manifest_digest,
        energy_policy_digest=catalog.energy_policy_digest,
        atomic_reference_policy=atomic_reference_policy,
        advisory_compatibility_policy=advisory_compatibility_policy,
    )
