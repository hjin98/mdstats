"""Neutral source authority: precise provenance without compatibility eligibility."""

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
from ..manifest import TrainingDataManifest
from ..sources import SourceComposition, TrainingDataSource, TrainingDataSourceCatalog

SOURCE_RECORD_SCHEMA = "mdstats.source-record.v2"
PROVENANCE_DIAGNOSTICS_SCHEMA = "mdstats.provenance-diagnostics.v1"
ADVISORY_COMPATIBILITY_REPORT_SCHEMA = "mdstats.advisory-compatibility-report.v1"
SOURCE_AUTHORITY_SCHEMA = "mdstats.source-authority.v1"


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
class SourceRecord:
    run_id: str
    source_locator: str
    source_identity_signature: str
    source_control_digest: str
    ensemble_certificate_digest: str
    frame_count: int
    composition: SourceComposition
    selected_energy_channel: str
    selected_energy_units: str
    selected_energy_semantic_role: str
    electronic_structure: ElectronicStructureFingerprint
    ensemble: str
    quality_assessment_status: str
    quality_outcome: str | None
    timestep_fs: float | None
    replica_id: str | None
    reference_group: str | None
    reference_run_id: str | None
    assertions: tuple[tuple[str, Any], ...]
    target_usable: bool
    mechanical_rejection_codes: tuple[str, ...]
    companion_files: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.run_id.strip() or not self.source_locator.strip():
            raise TrainingDataInputError("Source run_id and source_locator must be non-empty.")
        for name in (
            "source_identity_signature",
            "source_control_digest",
            "ensemble_certificate_digest",
        ):
            object.__setattr__(
                self,
                name,
                validate_digest(getattr(self, name), name=name),
            )
        if not isinstance(self.composition, SourceComposition):
            raise TrainingDataInputError("Source composition must be an instance of SourceComposition.")
        object.__setattr__(self, "assertions", tuple(sorted((str(k), v) for k, v in self.assertions)))
        object.__setattr__(
            self,
            "companion_files",
            tuple(sorted((str(k), str(v)) for k, v in self.companion_files)),
        )
        object.__setattr__(
            self,
            "mechanical_rejection_codes",
            tuple(str(code) for code in self.mechanical_rejection_codes),
        )
        if self.target_usable and self.mechanical_rejection_codes:
            raise TrainingDataInputError("Usable sources cannot carry mechanical rejection codes.")
        if not self.target_usable and not self.mechanical_rejection_codes:
            raise TrainingDataInputError("Unusable sources require mechanical rejection codes.")

        status = str(self.quality_assessment_status).lower()
        if status not in {"not_requested", "completed", "unavailable", "failed"}:
            raise TrainingDataInputError(f"Invalid quality_assessment_status: {self.quality_assessment_status!r}")
        outcome = None if self.quality_outcome is None else str(self.quality_outcome).lower()
        if status == "completed":
            if outcome not in {"strictly_qualified", "degraded_quality", "unqualified"}:
                raise TrainingDataInputError(
                    f"Completed quality assessment requires valid quality_outcome, got {self.quality_outcome!r}"
                )
        else:
            if outcome is not None:
                raise TrainingDataInputError(
                    f"quality_outcome must be None when quality_assessment_status is {status!r}, got {self.quality_outcome!r}"
                )
        object.__setattr__(self, "quality_assessment_status", status)
        object.__setattr__(self, "quality_outcome", outcome)

    @property
    def composition_digest(self) -> str:
        return self.composition.content_digest

    @property
    def reduced_formula(self) -> str:
        return self.composition.reduced_formula

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_RECORD_SCHEMA,
            "run_id": self.run_id,
            "source_locator": self.source_locator,
            "source_identity_signature": self.source_identity_signature,
            "source_control_digest": self.source_control_digest,
            "ensemble_certificate_digest": self.ensemble_certificate_digest,
            "frame_count": self.frame_count,
            "composition": self.composition.to_dict(),
            "selected_energy_channel": self.selected_energy_channel,
            "selected_energy_units": self.selected_energy_units,
            "selected_energy_semantic_role": self.selected_energy_semantic_role,
            "electronic_structure": self.electronic_structure.to_dict(),
            "ensemble": self.ensemble,
            "quality_assessment_status": self.quality_assessment_status,
            "quality_outcome": self.quality_outcome,
            "timestep_fs": self.timestep_fs,
            "replica_id": self.replica_id,
            "reference_group": self.reference_group,
            "reference_run_id": self.reference_run_id,
            "assertions": dict(self.assertions),
            "companion_files": dict(self.companion_files),
            "target_usable": self.target_usable,
            "mechanical_rejection_codes": list(self.mechanical_rejection_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceRecord":
        if payload.get("schema") != SOURCE_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported source-record schema.")
        required_keys = (
            "run_id",
            "source_locator",
            "source_identity_signature",
            "source_control_digest",
            "ensemble_certificate_digest",
            "frame_count",
            "composition",
            "selected_energy_channel",
            "selected_energy_units",
            "selected_energy_semantic_role",
            "electronic_structure",
            "ensemble",
            "quality_assessment_status",
            "quality_outcome",
            "timestep_fs",
            "replica_id",
            "reference_group",
            "reference_run_id",
            "assertions",
            "companion_files",
            "target_usable",
            "mechanical_rejection_codes",
        )
        for key in required_keys:
            if key not in payload:
                raise TrainingDataSerializationError(
                    f"Source-record missing required field: {key!r}"
                )

        comp_payload = payload["composition"]
        if not isinstance(comp_payload, Mapping):
            raise TrainingDataSerializationError("Source-record composition must be a mapping.")
        comp = SourceComposition.from_dict(comp_payload)

        status = str(payload["quality_assessment_status"]).lower()
        outcome_raw = payload["quality_outcome"]
        outcome = None if outcome_raw is None else str(outcome_raw).lower()
        if status not in {"not_requested", "completed", "unavailable", "failed"}:
            raise TrainingDataSerializationError(f"Invalid quality_assessment_status: {status!r}")
        if status == "completed":
            if outcome not in {"strictly_qualified", "degraded_quality", "unqualified"}:
                raise TrainingDataSerializationError(
                    f"Completed quality assessment requires valid quality_outcome, got {outcome!r}"
                )
        else:
            if outcome is not None:
                raise TrainingDataSerializationError(
                    f"quality_outcome must be None when quality_assessment_status is {status!r}"
                )

        elec_payload = payload["electronic_structure"]
        if not isinstance(elec_payload, Mapping):
            raise TrainingDataSerializationError("Source-record electronic_structure must be a mapping.")
        electronic_structure = ElectronicStructureFingerprint.from_dict(elec_payload)

        assertions_raw = payload["assertions"]
        if not isinstance(assertions_raw, Mapping):
            raise TrainingDataSerializationError("Source-record assertions must be a mapping.")
        assertions = tuple(sorted((str(k), v) for k, v in assertions_raw.items()))

        companions_raw = payload["companion_files"]
        if not isinstance(companions_raw, Mapping):
            raise TrainingDataSerializationError("Source-record companion_files must be a mapping.")
        companions = tuple(sorted((str(k), str(v)) for k, v in companions_raw.items()))

        rejections_raw = payload["mechanical_rejection_codes"]
        if not isinstance(rejections_raw, Sequence) or isinstance(rejections_raw, (str, bytes)):
            raise TrainingDataSerializationError("Source-record mechanical_rejection_codes must be a sequence.")
        mechanical_rejection_codes = tuple(str(code) for code in rejections_raw)

        result = cls(
            run_id=str(payload["run_id"]),
            source_locator=str(payload["source_locator"]),
            source_identity_signature=str(payload["source_identity_signature"]),
            source_control_digest=str(payload["source_control_digest"]),
            ensemble_certificate_digest=str(payload["ensemble_certificate_digest"]),
            frame_count=int(payload["frame_count"]),
            composition=comp,
            selected_energy_channel=str(payload["selected_energy_channel"]),
            selected_energy_units=str(payload["selected_energy_units"]),
            selected_energy_semantic_role=str(payload["selected_energy_semantic_role"]),
            electronic_structure=electronic_structure,
            ensemble=str(payload["ensemble"]),
            quality_assessment_status=status,
            quality_outcome=outcome,
            timestep_fs=None if payload["timestep_fs"] is None else float(payload["timestep_fs"]),
            replica_id=None if payload["replica_id"] is None else str(payload["replica_id"]),
            reference_group=(
                None if payload["reference_group"] is None else str(payload["reference_group"])
            ),
            reference_run_id=(
                None if payload["reference_run_id"] is None else str(payload["reference_run_id"])
            ),
            assertions=assertions,
            companion_files=companions,
            target_usable=bool(payload["target_usable"]),
            mechanical_rejection_codes=mechanical_rejection_codes,
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Source-record digest mismatch.")
        return result


def source_record_from_data2(
    source: TrainingDataSource,
    companion_files: Sequence[tuple[str, str]] | Mapping[str, str] | None = None,
) -> SourceRecord:
    usable, reasons = _source_is_mechanically_usable(source)
    quality_status = (
        source.quality_assessment_status.value
        if hasattr(source.quality_assessment_status, "value")
        else str(source.quality_assessment_status)
    )
    if companion_files is None:
        companions: tuple[tuple[str, str], ...] = ()
    elif isinstance(companion_files, Mapping):
        companions = tuple(sorted((str(k), str(v)) for k, v in companion_files.items()))
    else:
        companions = tuple(sorted((str(k), str(v)) for k, v in companion_files))

    return SourceRecord(
        run_id=source.run_id,
        source_locator=source.source_locator,
        source_identity_signature=source.source_identity_signature,
        source_control_digest=source.source_control_bundle_signature,
        ensemble_certificate_digest=source.ensemble_certificate_signature,
        frame_count=source.frame_count,
        composition=source.composition,
        selected_energy_channel=source.selected_energy.source_name,
        selected_energy_units=source.selected_energy.units,
        selected_energy_semantic_role=source.selected_energy.semantic_role,
        electronic_structure=source.electronic_structure,
        ensemble=source.ensemble,
        quality_assessment_status=quality_status,
        quality_outcome=source.quality_outcome,
        timestep_fs=source.timestep_fs,
        replica_id=source.replica_id,
        reference_group=source.reference_group,
        reference_run_id=source.reference_run_id,
        assertions=source.assertions,
        companion_files=companions,
        target_usable=usable,
        mechanical_rejection_codes=reasons,
    )


@dataclass(frozen=True, slots=True)
class ProvenanceDiagnostics:
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
            "schema": PROVENANCE_DIAGNOSTICS_SCHEMA,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "ProvenanceDiagnostics":
        if payload.get("schema") != PROVENANCE_DIAGNOSTICS_SCHEMA:
            raise TrainingDataSerializationError("Unsupported provenance-diagnostics schema.")
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
            raise TrainingDataSerializationError("Provenance-diagnostics digest mismatch.")
        return result


def build_provenance_diagnostics(records: Sequence[SourceRecord]) -> ProvenanceDiagnostics:
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
    return ProvenanceDiagnostics(
        fingerprint_counts=tuple(fingerprint_counts.items()),
        unresolved_or_partial_source_ids=tuple(unresolved),
        varying_dimensions=varying,
        selected_energy_channel_counts=tuple(channel_counts.items()),
        notes=notes,
    )


@dataclass(frozen=True, slots=True)
class AdvisoryCompatibilityReport:
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
            "schema": ADVISORY_COMPATIBILITY_REPORT_SCHEMA,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "AdvisoryCompatibilityReport":
        if payload.get("schema") != ADVISORY_COMPATIBILITY_REPORT_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported advisory-compatibility-report schema."
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
                "Advisory-compatibility-report digest mismatch."
            )
        return result


def build_advisory_compatibility_report(
    records: Sequence[SourceRecord],
    *,
    policy: LabelCompatibilityPolicy | None = None,
) -> AdvisoryCompatibilityReport:
    active = LabelCompatibilityPolicy() if policy is None else policy
    catalog = build_label_domain_catalog(
        {item.run_id: item.electronic_structure for item in records},
        policy=active,
    )
    groups: list[tuple[str, str | None]] = []
    for record in records:
        groups.append((record.run_id, catalog.domain_for_source(record.run_id)))
    return AdvisoryCompatibilityReport(
        policy_digest=active.policy_digest,
        source_group_ids=tuple(groups),
        unresolved_source_ids=tuple(catalog.unresolved_source_ids),
    )


@dataclass(frozen=True, slots=True)
class SourceAuthority:
    dataset_id: str
    manifest_digest: str
    energy_policy_digest: str
    sources: tuple[SourceRecord, ...]
    provenance_diagnostics: ProvenanceDiagnostics
    advisory_compatibility: AdvisoryCompatibilityReport
    atomic_reference_identifiability: AtomicReferenceIdentifiabilityReport
    notes: tuple[str, ...] = ()
    _by_run_id: dict[str, SourceRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("manifest_digest", "energy_policy_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        sources = tuple(sorted(self.sources, key=lambda item: item.run_id))
        if len({item.run_id for item in sources}) != len(sources):
            raise TrainingDataInputError("Source run IDs must be unique.")
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))
        object.__setattr__(self, "_by_run_id", {item.run_id: item for item in sources})

    def source(self, run_id: str) -> SourceRecord:
        try:
            return self._by_run_id[run_id]
        except KeyError:
            raise KeyError(run_id) from None

    @property
    def target_usable_run_ids(self) -> tuple[str, ...]:
        return tuple(item.run_id for item in self.sources if item.target_usable)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_AUTHORITY_SCHEMA,
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceAuthority":
        if payload.get("schema") != SOURCE_AUTHORITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported source-authority schema.")
        for key in (
            "dataset_id",
            "manifest_digest",
            "energy_policy_digest",
            "sources",
            "provenance_diagnostics",
            "atomic_reference_identifiability",
        ):
            if key not in payload:
                raise TrainingDataSerializationError(f"Source-authority missing required field: {key!r}")
        sources = tuple(SourceRecord.from_dict(item) for item in payload["sources"])
        advisory_payload = payload.get("advisory_compatibility")
        if advisory_payload is None:
            advisory = build_advisory_compatibility_report(sources)
        else:
            advisory = AdvisoryCompatibilityReport.from_dict(advisory_payload)
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            manifest_digest=str(payload["manifest_digest"]),
            energy_policy_digest=str(payload["energy_policy_digest"]),
            sources=sources,
            provenance_diagnostics=ProvenanceDiagnostics.from_dict(
                payload["provenance_diagnostics"]
            ),
            advisory_compatibility=advisory,
            atomic_reference_identifiability=AtomicReferenceIdentifiabilityReport.from_dict(
                payload["atomic_reference_identifiability"]
            ),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Source-authority digest mismatch.")
        return result


def build_source_authority(
    sources: Sequence[TrainingDataSource],
    *,
    dataset_id: str,
    manifest_digest: str,
    energy_policy_digest: str,
    companion_files_by_run: Mapping[str, Sequence[tuple[str, str]]] | None = None,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
    advisory_compatibility_policy: LabelCompatibilityPolicy | None = None,
) -> SourceAuthority:
    companions_map = companion_files_by_run or {}
    records = tuple(
        source_record_from_data2(item, companion_files=companions_map.get(item.run_id))
        for item in sources
    )
    if not records:
        raise TrainingDataInputError("Source authority requires at least one source.")
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
    return SourceAuthority(
        dataset_id=dataset_id,
        manifest_digest=manifest_digest,
        energy_policy_digest=energy_policy_digest,
        sources=records,
        provenance_diagnostics=build_provenance_diagnostics(records),
        advisory_compatibility=build_advisory_compatibility_report(
            records, policy=advisory_compatibility_policy
        ),
        atomic_reference_identifiability=atomic_report,
        notes=(
            "Source authority records precise provenance and corpus-level atomic-reference "
            "identifiability. Compatibility grouping is advisory only and is not a training "
            "eligibility or identity axis.",
        ),
    )


def build_source_authority_from_data2_catalog(
    catalog: TrainingDataSourceCatalog,
    *,
    manifest: TrainingDataManifest,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
    advisory_compatibility_policy: LabelCompatibilityPolicy | None = None,
) -> SourceAuthority:
    """Build current-generation SourceAuthority from DATA2 catalog with verified originating manifest."""
    if not isinstance(catalog, TrainingDataSourceCatalog):
        raise TrainingDataInputError("catalog must be an instance of TrainingDataSourceCatalog.")
    if manifest is None or not isinstance(manifest, TrainingDataManifest):
        raise TrainingDataInputError("Originating TrainingDataManifest is required for SourceAuthority conversion.")
    if manifest.content_digest != catalog.manifest_digest:
        raise TrainingDataInputError(
            f"Manifest content digest mismatch: manifest={manifest.content_digest!r} != catalog={catalog.manifest_digest!r}"
        )
    if manifest.dataset_id != catalog.dataset_id:
        raise TrainingDataInputError(
            f"Manifest dataset ID mismatch: manifest={manifest.dataset_id!r} != catalog={catalog.dataset_id!r}"
        )
    manifest_runs = {run.run_id: run for run in manifest.runs}
    catalog_runs = {source.run_id: source for source in catalog.sources}
    if set(manifest_runs) != set(catalog_runs):
        raise TrainingDataInputError(
            f"Manifest run IDs do not match catalog source run IDs: manifest={sorted(manifest_runs)} != catalog={sorted(catalog_runs)}"
        )
    for run_id, run_spec in manifest_runs.items():
        source = catalog_runs[run_id]
        if run_spec.vasprun != source.source_locator:
            raise TrainingDataInputError(
                f"Source locator mismatch for run {run_id!r}: manifest={run_spec.vasprun!r} != catalog={source.source_locator!r}"
            )

    companions_by_run = {
        run.run_id: run.companion_files
        for run in manifest.runs
    }

    return build_source_authority(
        catalog.sources,
        dataset_id=catalog.dataset_id,
        manifest_digest=catalog.manifest_digest,
        energy_policy_digest=catalog.energy_policy_digest,
        companion_files_by_run=companions_by_run,
        atomic_reference_policy=atomic_reference_policy,
        advisory_compatibility_policy=advisory_compatibility_policy,
    )
