"""VASP source audits and immutable source catalogs for MLFF-DATA2."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from math import gcd
from functools import reduce
from pathlib import Path
from typing import Any, Callable, Mapping
import xml.etree.ElementTree as ET

from mdstats.io.xml_recovery import classify_xml_parse_error
from mdstats.io import (
    certify_vasp_simulation_controls,
    read_vasp_run_controls,
)

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .atomic_references import (
    AtomicReferenceIdentifiabilityCatalog,
    AtomicReferenceIdentifiabilityPolicy,
    AtomicReferenceIdentifiabilityReport,
    analyze_atomic_reference_identifiability,
)
from .energy import (
    SelectedEnergyChannel,
    VaspEnergyLabelPolicy,
    select_vasp_energy_channel,
)
from .labels import (
    DerivativeConvention,
    ElectronicStructureFingerprint,
    EnergyReferenceIdentity,
    LabelCompatibilityPolicy,
    LabelDomainCatalog,
    NumericalQualityProfile,
    SoftwareProvenance,
    TheoryIdentity,
    build_label_domain_catalog,
)
from .manifest import TrainingDataManifest, TrainingDataRunSpec

SOURCE_COMPOSITION_SCHEMA = "mdstats.training-source-composition.v1"
VASP_STATIC_SOURCE_METADATA_SCHEMA = "mdstats.vasp-static-source-metadata.v1"
SOURCE_AUDIT_POLICY_SCHEMA = "mdstats.training-source-audit-policy.v1"
TRAINING_DATA_SOURCE_SCHEMA = "mdstats.training-data-source.v1"
TRAINING_DATA_SOURCE_CATALOG_SCHEMA = "mdstats.training-data-source-catalog.v1"
SOURCE_AUDIT_POLICY_VERSION = "mdstats.mlff-data2.source-audit.2026-07.v1"
MLFF_DATA2_PARSER_VERSION = "0.20.63a0"


class SourceTrajectoryAssessmentMode(str, Enum):
    CONTROLS_ONLY = "controls_only"
    FULL_IF_AVAILABLE = "full_if_available"
    FULL_REQUIRED = "full_required"


class SourceAssessmentStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    COMPLETED = "completed"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SourceComposition:
    element_counts: tuple[tuple[str, int], ...]
    reduced_formula: str
    atom_count: int

    def __post_init__(self) -> None:
        counts = tuple(sorted((str(symbol), int(count)) for symbol, count in self.element_counts))
        if not counts or any(count <= 0 for _, count in counts):
            raise TrainingDataInputError("Source composition requires positive element counts.")
        if len({symbol for symbol, _ in counts}) != len(counts):
            raise TrainingDataInputError("Source composition contains duplicate elements.")
        if sum(count for _, count in counts) != self.atom_count:
            raise TrainingDataInputError("Source atom count does not match element counts.")
        object.__setattr__(self, "element_counts", counts)

    @classmethod
    def from_symbols(cls, symbols: tuple[str, ...]) -> "SourceComposition":
        counts: dict[str, int] = {}
        for symbol in symbols:
            normalized = str(symbol).strip()
            if not normalized:
                raise TrainingDataInputError("Empty element symbol in source atom list.")
            counts[normalized] = counts.get(normalized, 0) + 1
        if not counts:
            raise TrainingDataInputError("Source atom list is empty.")
        divisor = reduce(gcd, counts.values())
        formula = "".join(
            symbol + ("" if count // divisor == 1 else str(count // divisor))
            for symbol, count in sorted(counts.items())
        )
        return cls(tuple(counts.items()), formula, len(symbols))

    def as_dict(self) -> dict[str, int]:
        return dict(self.element_counts)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_COMPOSITION_SCHEMA,
            "element_counts": dict(self.element_counts),
            "reduced_formula": self.reduced_formula,
            "atom_count": self.atom_count,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceComposition":
        if payload.get("schema") != SOURCE_COMPOSITION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported source-composition schema.")
        result = cls(
            element_counts=tuple((str(k), int(v)) for k, v in payload["element_counts"].items()),
            reduced_formula=str(payload["reduced_formula"]),
            atom_count=int(payload["atom_count"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Source-composition digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class VaspStaticSourceMetadata:
    atom_symbols: tuple[str, ...]
    paw_datasets: tuple[tuple[str, str], ...]
    kpoint_count: int | None
    kpoint_payload_sha256: str | None
    kpoint_generation: tuple[tuple[str, Any], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "atom_symbols", tuple(str(item) for item in self.atom_symbols))
        object.__setattr__(self, "paw_datasets", tuple(sorted((str(a), str(b)) for a, b in self.paw_datasets)))
        object.__setattr__(self, "kpoint_generation", tuple(sorted((str(a), b) for a, b in self.kpoint_generation)))
        if self.kpoint_count is not None and self.kpoint_count < 0:
            raise TrainingDataInputError("kpoint_count must be nonnegative.")
        if self.kpoint_payload_sha256 is not None:
            object.__setattr__(self, "kpoint_payload_sha256", validate_digest(self.kpoint_payload_sha256, name="kpoint_payload_sha256"))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": VASP_STATIC_SOURCE_METADATA_SCHEMA,
            "atom_symbols": list(self.atom_symbols),
            "paw_datasets": dict(self.paw_datasets),
            "kpoint_count": self.kpoint_count,
            "kpoint_payload_sha256": self.kpoint_payload_sha256,
            "kpoint_generation": dict(self.kpoint_generation),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "VaspStaticSourceMetadata":
        if payload.get("schema") != VASP_STATIC_SOURCE_METADATA_SCHEMA:
            raise TrainingDataSerializationError("Unsupported VASP static metadata schema.")
        result = cls(
            atom_symbols=tuple(str(item) for item in payload.get("atom_symbols", ())),
            paw_datasets=tuple((str(k), str(v)) for k, v in payload.get("paw_datasets", {}).items()),
            kpoint_count=None if payload.get("kpoint_count") is None else int(payload["kpoint_count"]),
            kpoint_payload_sha256=None if payload.get("kpoint_payload_sha256") is None else str(payload["kpoint_payload_sha256"]),
            kpoint_generation=tuple((str(k), v) for k, v in payload.get("kpoint_generation", {}).items()),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("VASP static metadata digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class SourceAuditPolicy:
    trajectory_assessment_mode: SourceTrajectoryAssessmentMode = SourceTrajectoryAssessmentMode.CONTROLS_ONLY
    fail_on_unresolved_label_domain: bool = True
    policy_version: str = SOURCE_AUDIT_POLICY_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "trajectory_assessment_mode", SourceTrajectoryAssessmentMode(self.trajectory_assessment_mode))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": SOURCE_AUDIT_POLICY_SCHEMA,
            "policy_version": self.policy_version,
            "trajectory_assessment_mode": self.trajectory_assessment_mode.value,
            "fail_on_unresolved_label_domain": self.fail_on_unresolved_label_domain,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "SourceAuditPolicy":
        if payload.get("schema") != SOURCE_AUDIT_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported source-audit-policy schema.")
        result = cls(
            trajectory_assessment_mode=SourceTrajectoryAssessmentMode(payload["trajectory_assessment_mode"]),
            fail_on_unresolved_label_domain=bool(payload["fail_on_unresolved_label_domain"]),
            policy_version=str(payload["policy_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("Source-audit-policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingDataSource:
    run_id: str
    source_locator: str
    source_identity_signature: str
    source_control_bundle_signature: str
    source_sha256: str
    frame_count: int
    timestep_fs: float | None
    composition: SourceComposition
    ensemble_certificate_signature: str
    ensemble_status: str
    ensemble: str
    selected_energy: SelectedEnergyChannel
    electronic_structure: ElectronicStructureFingerprint
    label_domain_id: str | None
    reference_group: str | None
    replica_id: str | None
    reference_run_id: str | None
    assertions: tuple[tuple[str, Any], ...]
    quality_assessment_status: SourceAssessmentStatus
    quality_signature: str | None
    quality_outcome: str | None
    production_assessment_status: SourceAssessmentStatus
    production_regime_signature: str | None
    production_status: str | None
    assessment_notes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in (
            "source_identity_signature", "source_control_bundle_signature",
            "source_sha256", "ensemble_certificate_signature",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("quality_signature", "production_regime_signature"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        if self.frame_count < 0:
            raise TrainingDataInputError("frame_count must be nonnegative.")
        object.__setattr__(self, "quality_assessment_status", SourceAssessmentStatus(self.quality_assessment_status))
        object.__setattr__(self, "production_assessment_status", SourceAssessmentStatus(self.production_assessment_status))
        object.__setattr__(self, "assertions", tuple(sorted((str(a), b) for a, b in self.assertions)))
        object.__setattr__(self, "assessment_notes", tuple(str(item) for item in self.assessment_notes))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DATA_SOURCE_SCHEMA,
            "run_id": self.run_id,
            "source_locator": self.source_locator,
            "source_identity_signature": self.source_identity_signature,
            "source_control_bundle_signature": self.source_control_bundle_signature,
            "source_sha256": self.source_sha256,
            "frame_count": self.frame_count,
            "timestep_fs": self.timestep_fs,
            "composition": self.composition.to_dict(),
            "ensemble_certificate_signature": self.ensemble_certificate_signature,
            "ensemble_status": self.ensemble_status,
            "ensemble": self.ensemble,
            "selected_energy": self.selected_energy.to_dict(),
            "electronic_structure": self.electronic_structure.to_dict(),
            "label_domain_id": self.label_domain_id,
            "reference_group": self.reference_group,
            "replica_id": self.replica_id,
            "reference_run_id": self.reference_run_id,
            "assertions": dict(self.assertions),
            "quality_assessment_status": self.quality_assessment_status.value,
            "quality_signature": self.quality_signature,
            "quality_outcome": self.quality_outcome,
            "production_assessment_status": self.production_assessment_status.value,
            "production_regime_signature": self.production_regime_signature,
            "production_status": self.production_status,
            "assessment_notes": list(self.assessment_notes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingDataSource":
        if payload.get("schema") != TRAINING_DATA_SOURCE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported training-data-source schema.")
        result = cls(
            run_id=str(payload["run_id"]),
            source_locator=str(payload["source_locator"]),
            source_identity_signature=str(payload["source_identity_signature"]),
            source_control_bundle_signature=str(payload["source_control_bundle_signature"]),
            source_sha256=str(payload["source_sha256"]),
            frame_count=int(payload["frame_count"]),
            timestep_fs=None if payload.get("timestep_fs") is None else float(payload["timestep_fs"]),
            composition=SourceComposition.from_dict(payload["composition"]),
            ensemble_certificate_signature=str(payload["ensemble_certificate_signature"]),
            ensemble_status=str(payload["ensemble_status"]),
            ensemble=str(payload["ensemble"]),
            selected_energy=SelectedEnergyChannel.from_dict(payload["selected_energy"]),
            electronic_structure=ElectronicStructureFingerprint.from_dict(payload["electronic_structure"]),
            label_domain_id=None if payload.get("label_domain_id") is None else str(payload["label_domain_id"]),
            reference_group=None if payload.get("reference_group") is None else str(payload["reference_group"]),
            replica_id=None if payload.get("replica_id") is None else str(payload["replica_id"]),
            reference_run_id=None if payload.get("reference_run_id") is None else str(payload["reference_run_id"]),
            assertions=tuple((str(k), v) for k, v in payload.get("assertions", {}).items()),
            quality_assessment_status=SourceAssessmentStatus(payload["quality_assessment_status"]),
            quality_signature=None if payload.get("quality_signature") is None else str(payload["quality_signature"]),
            quality_outcome=None if payload.get("quality_outcome") is None else str(payload["quality_outcome"]),
            production_assessment_status=SourceAssessmentStatus(payload["production_assessment_status"]),
            production_regime_signature=None if payload.get("production_regime_signature") is None else str(payload["production_regime_signature"]),
            production_status=None if payload.get("production_status") is None else str(payload["production_status"]),
            assessment_notes=tuple(str(item) for item in payload.get("assessment_notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Training-data-source digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TrainingDataSourceCatalog:
    dataset_id: str
    manifest_digest: str
    source_audit_policy_digest: str
    energy_policy_digest: str
    label_compatibility_policy_digest: str
    sources: tuple[TrainingDataSource, ...]
    label_domains: LabelDomainCatalog
    atomic_reference_identifiability: AtomicReferenceIdentifiabilityCatalog
    notes: tuple[str, ...] = ()
    _by_run_id: dict[str, TrainingDataSource] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _content_digest_cache: str | None = field(
        default=None, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "manifest_digest", "source_audit_policy_digest", "energy_policy_digest",
            "label_compatibility_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        sources = tuple(sorted(self.sources, key=lambda item: item.run_id))
        if len({item.run_id for item in sources}) != len(sources):
            raise TrainingDataInputError("Source catalog run IDs must be unique.")
        object.__setattr__(self, "sources", sources)
        object.__setattr__(self, "notes", tuple(str(item) for item in self.notes))
        object.__setattr__(self, "_by_run_id", {item.run_id: item for item in sources})

    def source(self, run_id: str) -> TrainingDataSource:
        try:
            return self._by_run_id[run_id]
        except KeyError:
            raise KeyError(run_id) from None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TRAINING_DATA_SOURCE_CATALOG_SCHEMA,
            "dataset_id": self.dataset_id,
            "manifest_digest": self.manifest_digest,
            "source_audit_policy_digest": self.source_audit_policy_digest,
            "energy_policy_digest": self.energy_policy_digest,
            "label_compatibility_policy_digest": self.label_compatibility_policy_digest,
            "sources": [item.to_dict() for item in self.sources],
            "label_domains": self.label_domains.to_dict(),
            "atomic_reference_identifiability": self.atomic_reference_identifiability.to_dict(),
            "notes": list(self.notes),
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
    def from_dict(cls, payload: Mapping[str, Any]) -> "TrainingDataSourceCatalog":
        if payload.get("schema") != TRAINING_DATA_SOURCE_CATALOG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported source-catalog schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            manifest_digest=str(payload["manifest_digest"]),
            source_audit_policy_digest=str(payload["source_audit_policy_digest"]),
            energy_policy_digest=str(payload["energy_policy_digest"]),
            label_compatibility_policy_digest=str(payload["label_compatibility_policy_digest"]),
            sources=tuple(TrainingDataSource.from_dict(item) for item in payload.get("sources", ())),
            label_domains=LabelDomainCatalog.from_dict(payload["label_domains"]),
            atomic_reference_identifiability=AtomicReferenceIdentifiabilityCatalog.from_dict(payload["atomic_reference_identifiability"]),
            notes=tuple(str(item) for item in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Source-catalog digest mismatch.")
        return result


def _parse_scalar(text: str, kind: str | None) -> Any:
    raw = text.strip()
    if kind == "logical":
        return raw.upper() in {"T", ".TRUE.", "TRUE"}
    if kind == "string":
        return raw
    try:
        if any(marker in raw.lower() for marker in (".", "e", "d")):
            return float(raw.replace("D", "E").replace("d", "e"))
        return int(raw)
    except ValueError:
        return raw


def _extract_static_metadata(path: Path) -> VaspStaticSourceMetadata:
    symbols: list[str] = []
    paw: list[tuple[str, str]] = []
    kpoint_vectors: list[tuple[float, ...]] = []
    kpoint_weights: list[tuple[float, ...]] = []
    generation: dict[str, Any] = {}
    try:
        # ``atominfo`` and ``kpoints`` are VASP header records.  Stop at the
        # first ionic calculation instead of walking the entire trajectory.
        # This preserves identical metadata while avoiding an O(n_frames)
        # second XML pass for every source.
        # Own the stream explicitly.  ``ElementTree.iterparse(path)`` keeps its
        # internally opened file alive when iteration stops early; across many
        # large sources that deferred cleanup can stall garbage collection.
        with path.open("rb") as xml_stream:
            parser = ET.iterparse(xml_stream, events=("start", "end"))
            for event, element in parser:
                if event == "start" and element.tag == "calculation":
                    break
                if event == "end" and element.tag == "atominfo":
                    atom_set = element.find("array[@name='atoms']/set")
                    if atom_set is not None:
                        for row in list(atom_set):
                            cells = [(cell.text or "").strip() for cell in row.findall("c")]
                            if cells:
                                symbols.append(cells[0])
                    type_set = element.find("array[@name='atomtypes']/set")
                    if type_set is not None:
                        for row in list(type_set):
                            cells = [(cell.text or "").strip() for cell in row.findall("c")]
                            if len(cells) >= 5:
                                paw.append((cells[1], cells[4]))
                    element.clear()
                elif event == "end" and element.tag == "kpoints":
                    gen = element.find("generation")
                    if gen is not None:
                        for item in list(gen):
                            name = item.attrib.get("name", item.tag)
                            generation[name] = _parse_scalar((item.text or ""), item.attrib.get("type"))
                    for varray, target in (
                        (element.find("varray[@name='kpointlist']"), kpoint_vectors),
                        (element.find("varray[@name='weights']"), kpoint_weights),
                    ):
                        if varray is not None:
                            for vector in varray.findall("v"):
                                target.append(tuple(float(v) for v in (vector.text or "").split()))
                    element.clear()
            del parser
    except ET.ParseError as exc:
        diagnostic = classify_xml_parse_error(path, exc)
        if not diagnostic.recoverable_trailing_interruption:
            raise TrainingDataInputError(
                f"Could not parse VASP XML metadata: {path!s}: {exc}."
            ) from exc
        if not symbols:
            raise TrainingDataInputError(
                f"Interrupted VASP XML metadata is ambiguous for {path!s}: "
                "atom identities were not recovered."
            ) from exc
    kpoint_payload = None
    if kpoint_vectors or kpoint_weights or generation:
        kpoint_payload = digest({
            "generation": generation,
            "kpoints": kpoint_vectors,
            "weights": kpoint_weights,
        })
    return VaspStaticSourceMetadata(
        atom_symbols=tuple(symbols),
        paw_datasets=tuple(paw),
        kpoint_count=None if not kpoint_vectors else len(kpoint_vectors),
        kpoint_payload_sha256=kpoint_payload,
        kpoint_generation=tuple(generation.items()),
    )


def _control(run_controls: Any, name: str) -> Any:
    value = run_controls.effective_value(name)
    return run_controls.explicit_value(name) if value is None else value


def _settings(run_controls: Any, names: tuple[str, ...]) -> tuple[tuple[str, Any], ...]:
    result = []
    for name in names:
        value = _control(run_controls, name)
        if value is not None:
            result.append((name, value))
    return tuple(result)


def _fingerprint(bundle: Any, static: VaspStaticSourceMetadata, selected: SelectedEnergyChannel) -> ElectronicStructureFingerprint:
    controls = bundle.run_controls
    xc = _settings(controls, ("GGA", "METAGGA", "LEXCH"))
    dft_u = _settings(controls, ("LDAU", "LDAUTYPE", "LDAUL", "LDAUU", "LDAUJ"))
    spin = _settings(controls, ("ISPIN", "LNONCOLLINEAR", "LSORBIT", "SAXIS"))
    dispersion = _settings(controls, ("IVDW", "LUSE_VDW", "VDW_S6", "VDW_S8", "VDW_SR"))
    hybrid = _settings(controls, ("LHFCALC", "AEXX", "HFSCREEN", "ALDAC", "AGGAX", "AGGAC"))
    theory_notes: list[str] = []
    if not xc:
        theory_notes.append("No explicit/effective XC identifier was reconstructed.")
    if not static.paw_datasets:
        theory_notes.append("No PAW dataset descriptors were reconstructed.")
    theory_status = "resolved" if xc and static.paw_datasets else "partial"

    smearing = _settings(controls, ("ISMEAR", "SIGMA"))
    energy_status = "resolved" if {name for name, _ in smearing} >= {"ISMEAR", "SIGMA"} else "partial"
    quality = bundle.numerical_quality_controls
    limit_values = [value for value in quality.scf_iteration_limit_reached if value is not None]
    limit_fraction = None if not limit_values else sum(bool(v) for v in limit_values) / len(limit_values)
    numerical_settings = {
        "ENCUT_eV": quality.encut_ev,
        "EDIFF_eV": quality.ediff_ev,
        "NELM": quality.nelm,
        "NELMIN": quality.nelmin,
        "ALGO": quality.algo,
        "IALGO": quality.ialgo,
        "PREC_explicit": quality.prec_explicit,
        "PREC_effective": quality.prec_effective,
        "LREAL_explicit": quality.lreal_explicit,
        "LREAL_effective": quality.lreal_effective,
        "LASPH": _control(controls, "LASPH"),
        "ISYM": quality.isym,
    }
    numerical_settings = {key: value for key, value in numerical_settings.items() if value is not None}
    return ElectronicStructureFingerprint(
        theory=TheoryIdentity(
            xc_settings=xc,
            dft_u_settings=dft_u,
            paw_datasets=static.paw_datasets,
            spin_settings=spin,
            dispersion_settings=dispersion,
            hybrid_settings=hybrid,
            resolution_status=theory_status,
            notes=tuple(theory_notes),
        ),
        energy_reference=EnergyReferenceIdentity(
            source_name=selected.source_name,
            semantic_role=selected.semantic_role,
            units=selected.units,
            normalization=selected.normalization,
            smearing_settings=smearing,
            entropy_convention="finite_smearing_electronic_free_energy",
            resolution_status=energy_status,
        ),
        derivative_convention=DerivativeConvention(),
        numerical_quality=NumericalQualityProfile(
            settings=tuple(numerical_settings.items()),
            kpoint_count=static.kpoint_count,
            kpoint_payload_sha256=static.kpoint_payload_sha256,
            scf_limit_fraction=limit_fraction,
        ),
        software_provenance=SoftwareProvenance(
            source_program=controls.source_program,
            source_program_version=controls.source_program_version,
            source_program_subversion=controls.source_program_subversion,
            control_semantics_version=controls.control_semantics_version,
            parser_package="mdstats",
            parser_version=MLFF_DATA2_PARSER_VERSION,
        ),
    )


@dataclass(frozen=True, slots=True)
class LoadedVaspTrainingSource:
    """One-pass VASP evidence reused by DATA2, DATA3, and DATA4.

    The object is intentionally process-local and is never serialized into the
    scientific campaign record.  Immutable ``FrameData`` arrays are retained
    so downstream stages do not reopen ``vasprun.xml`` during the same run.
    """

    source: TrainingDataSource
    frame_data: Any
    temperature_target: Any
    controls_seconds: float
    frames_seconds: float
    assessment_seconds: float


def load_vasp_training_source(
    run: TrainingDataRunSpec,
    *,
    base_directory: str | Path = ".",
    source_policy: SourceAuditPolicy | None = None,
    energy_policy: VaspEnergyLabelPolicy | None = None,
    strict: bool = True,
) -> LoadedVaspTrainingSource:
    """Read one VASP source once and reuse its evidence across MLFF stages."""

    import time
    import numpy as np
    from mdstats.io import read_vasp_frames
    from mdstats.io.vasp_controls import _parse_vasp_xml
    from mdstats.io.production_regimes import assess_production_regimes
    from mdstats.io.trajectory_quality import assess_trajectory_quality
    from .conditions import TemperatureTargetEvidence
    from .frame_catalog import FrameData

    source_active = SourceAuditPolicy(
        trajectory_assessment_mode=SourceTrajectoryAssessmentMode.FULL_REQUIRED,
        fail_on_unresolved_label_domain=True,
    ) if source_policy is None else source_policy
    energy_active = VaspEnergyLabelPolicy() if energy_policy is None else energy_policy
    path, companion_paths = run.resolve(Path(base_directory))

    start = time.monotonic()
    parsed_vasp_xml = _parse_vasp_xml(
        path, companion_files=companion_paths
    )
    bundle = parsed_vasp_xml.bundle
    certificate = certify_vasp_simulation_controls(bundle, companion_files=companion_paths)
    selected = select_vasp_energy_channel(
        bundle.energy_catalog,
        source_control_bundle_signature=bundle.signature,
        policy=energy_active,
    )
    static = VaspStaticSourceMetadata(
        atom_symbols=parsed_vasp_xml.atom_symbols,
        paw_datasets=parsed_vasp_xml.paw_datasets,
        kpoint_count=parsed_vasp_xml.kpoint_count,
        kpoint_payload_sha256=parsed_vasp_xml.kpoint_payload_sha256,
        kpoint_generation=parsed_vasp_xml.kpoint_generation,
    )
    controls_seconds = time.monotonic() - start

    start = time.monotonic()
    collection = read_vasp_frames(
        path,
        strict=strict,
        assess_quality=False,
        assess_stationarity=False,
        assess_admissibility=False,
        _parsed_vasp_xml=parsed_vasp_xml,
    )
    frames_seconds = time.monotonic() - start

    quality = None
    production = None
    assessment_notes: list[str] = []
    start = time.monotonic()
    if source_active.trajectory_assessment_mode is not SourceTrajectoryAssessmentMode.CONTROLS_ONLY:
        quality = assess_trajectory_quality(
            collection,
            energy_catalog=bundle.energy_catalog,
            numerical_quality_controls=bundle.numerical_quality_controls,
            simulation_control_certificate=certificate,
            source_identity_signature=bundle.source_identity.signature,
            emit_warning=False,
            raise_on_unqualified=False,
        )
        production = assess_production_regimes(
            collection,
            energy_catalog=bundle.energy_catalog,
            simulation_control_certificate=certificate,
            trajectory_quality_verdict=quality,
            source_identity_signature=bundle.source_identity.signature,
        )
    assessment_seconds = time.monotonic() - start

    composition = SourceComposition.from_symbols(static.atom_symbols)
    if bundle.source_identity.atom_count not in (None, composition.atom_count):
        raise TrainingDataInputError(f"Source atom count mismatch for {run.run_id!r}.")
    channel = bundle.energy_catalog.channel(selected.source_name)
    if channel is None:
        raise TrainingDataInputError(f"Selected energy channel is absent for {run.run_id!r}.")
    energies = channel.as_array()
    if len(energies) != collection.n_frames:
        raise TrainingDataInputError(
            f"Energy/frame count mismatch for {run.run_id!r}: {len(energies)} != {collection.n_frames}."
        )
    scf_flags = bundle.numerical_quality_controls.scf_iteration_limit_reached
    if len(scf_flags) != collection.n_frames:
        raise TrainingDataInputError(
            f"SCF-quality/frame count mismatch for {run.run_id!r}: {len(scf_flags)} != {collection.n_frames}."
        )
    frame_data = FrameData.from_collection(
        collection,
        source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
        energies_ev=energies,
        scf_iteration_limit_reached=scf_flags,
    )
    tebeg = _control(bundle.run_controls, "TEBEG")
    teend = _control(bundle.run_controls, "TEEND")
    target = TemperatureTargetEvidence(
        target_start_kelvin=None if tebeg is None else float(tebeg),
        target_end_kelvin=None if teend is None else float(teend),
        evidence="VASP effective/explicit TEBEG and TEEND",
    )
    if quality is None:
        quality_status = SourceAssessmentStatus.NOT_REQUESTED
        quality_signature = quality_outcome = None
        production_status = SourceAssessmentStatus.NOT_REQUESTED
        production_signature = production_outcome = None
    else:
        quality_status = SourceAssessmentStatus.COMPLETED
        quality_signature = quality.signature
        quality_outcome = quality.outcome.value
        production_status = SourceAssessmentStatus.COMPLETED
        production_signature = production.signature
        production_outcome = production.overall_status.value
    if not bundle.numerical_quality_controls.source_parse_complete:
        assessment_notes.append(
            "Interrupted vasprun.xml was recovered from complete ionic records; "
            + str(bundle.numerical_quality_controls.source_parse_warning)
        )
    source = TrainingDataSource(
        run_id=run.run_id,
        source_locator=run.vasprun,
        source_identity_signature=bundle.source_identity.signature,
        source_control_bundle_signature=bundle.signature,
        source_sha256=bundle.source_identity.primary_sha256,
        frame_count=collection.n_frames,
        timestep_fs=bundle.numerical_quality_controls.potim_fs,
        composition=composition,
        ensemble_certificate_signature=certificate.signature,
        ensemble_status=certificate.ensemble_status.value,
        ensemble=certificate.ensemble.value,
        selected_energy=selected,
        electronic_structure=_fingerprint(bundle, static, selected),
        label_domain_id=None,
        reference_group=run.reference_group,
        replica_id=run.replica_id,
        reference_run_id=run.reference_run_id,
        assertions=run.assertions,
        quality_assessment_status=quality_status,
        quality_signature=quality_signature,
        quality_outcome=quality_outcome,
        production_assessment_status=production_status,
        production_regime_signature=production_signature,
        production_status=production_outcome,
        assessment_notes=tuple(assessment_notes),
    )
    return LoadedVaspTrainingSource(
        source=source,
        frame_data=frame_data,
        temperature_target=target,
        controls_seconds=controls_seconds,
        frames_seconds=frames_seconds,
        assessment_seconds=assessment_seconds,
    )


def _finalize_source_catalog(
    manifest: TrainingDataManifest,
    sources: tuple[TrainingDataSource, ...],
    *,
    source_active: SourceAuditPolicy,
    energy_active: VaspEnergyLabelPolicy,
    label_active: LabelCompatibilityPolicy,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None,
) -> TrainingDataSourceCatalog:
    domains = build_label_domain_catalog(
        {item.run_id: item.electronic_structure for item in sources},
        policy=label_active,
    )
    if source_active.fail_on_unresolved_label_domain and domains.unresolved_source_ids:
        raise TrainingDataInputError(
            "Unresolved label domains for sources: " + ", ".join(domains.unresolved_source_ids)
        )
    assigned = tuple(replace(item, label_domain_id=domains.domain_for_source(item.run_id)) for item in sources)
    atomic_active = AtomicReferenceIdentifiabilityPolicy() if atomic_reference_policy is None else atomic_reference_policy
    assigned_by_run = {item.run_id: item for item in assigned}
    atomic_reports = tuple(
        (
            domain.domain_id,
            analyze_atomic_reference_identifiability(
                {
                    run_id: assigned_by_run[run_id].composition.as_dict()
                    for run_id in domain.source_ids
                },
                policy=atomic_active,
            ),
        )
        for domain in domains.domains
    )
    return TrainingDataSourceCatalog(
        dataset_id=manifest.dataset_id,
        manifest_digest=manifest.content_digest,
        source_audit_policy_digest=source_active.policy_digest,
        energy_policy_digest=energy_active.policy_digest,
        label_compatibility_policy_digest=label_active.policy_digest,
        sources=assigned,
        label_domains=domains,
        atomic_reference_identifiability=AtomicReferenceIdentifiabilityCatalog(
            policy_digest=atomic_active.policy_digest, domain_reports=atomic_reports
        ),
        notes=("DATA2 catalog contains source-level facts only; frame identities and eligibility begin in DATA3.",),
    )


def _optional_assessments(path: Path, companions: Mapping[str, Path], mode: SourceTrajectoryAssessmentMode) -> tuple[SourceAssessmentStatus, str | None, str | None, SourceAssessmentStatus, str | None, str | None, tuple[str, ...]]:
    if mode is SourceTrajectoryAssessmentMode.CONTROLS_ONLY:
        return (SourceAssessmentStatus.NOT_REQUESTED, None, None, SourceAssessmentStatus.NOT_REQUESTED, None, None, ())
    try:
        from mdstats.io import assess_vasp_production_regimes, assess_vasp_trajectory_quality
        quality = assess_vasp_trajectory_quality(
            path, companion_files=companions, emit_warning=False, raise_on_unqualified=False
        )
        production = assess_vasp_production_regimes(
            path, companion_files=companions, emit_quality_warning=False, raise_on_unqualified=False
        )
        return (
            SourceAssessmentStatus.COMPLETED,
            quality.signature,
            quality.outcome.value,
            SourceAssessmentStatus.COMPLETED,
            production.signature,
            production.overall_status.value,
            (),
        )
    except (ImportError, ModuleNotFoundError) as exc:
        if mode is SourceTrajectoryAssessmentMode.FULL_REQUIRED:
            raise
        return (
            SourceAssessmentStatus.UNAVAILABLE, None, None,
            SourceAssessmentStatus.UNAVAILABLE, None, None,
            (f"Full trajectory assessment unavailable: {type(exc).__name__}: {exc}",),
        )
    except Exception as exc:
        if mode is SourceTrajectoryAssessmentMode.FULL_REQUIRED:
            raise
        return (
            SourceAssessmentStatus.FAILED, None, None,
            SourceAssessmentStatus.FAILED, None, None,
            (f"Full trajectory assessment failed: {type(exc).__name__}: {exc}",),
        )


def _audit_one(
    run: TrainingDataRunSpec,
    *,
    base_directory: Path,
    source_policy: SourceAuditPolicy,
    energy_policy: VaspEnergyLabelPolicy,
) -> TrainingDataSource:
    """Audit one source through the shared one-parse ingestion path."""

    return load_vasp_training_source(
        run,
        base_directory=base_directory,
        source_policy=source_policy,
        energy_policy=energy_policy,
        strict=True,
    ).source


def build_training_data_source_catalog(
    manifest: TrainingDataManifest,
    *,
    base_directory: str | Path = ".",
    source_policy: SourceAuditPolicy | None = None,
    energy_policy: VaspEnergyLabelPolicy | None = None,
    label_compatibility_policy: LabelCompatibilityPolicy | None = None,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
) -> TrainingDataSourceCatalog:
    """Build a deterministic DATA2 catalog from manifest-declared VASP sources."""

    source_active = SourceAuditPolicy() if source_policy is None else source_policy
    energy_active = VaspEnergyLabelPolicy() if energy_policy is None else energy_policy
    label_active = LabelCompatibilityPolicy() if label_compatibility_policy is None else label_compatibility_policy
    sources = tuple(
        _audit_one(
            run,
            base_directory=Path(base_directory),
            source_policy=source_active,
            energy_policy=energy_active,
        )
        for run in manifest.runs
    )
    return _finalize_source_catalog(
        manifest,
        sources,
        source_active=source_active,
        energy_active=energy_active,
        label_active=label_active,
        atomic_reference_policy=atomic_reference_policy,
    )


def build_training_data_source_catalog_from_sources(
    manifest: TrainingDataManifest,
    sources_by_run: Mapping[str, TrainingDataSource],
    *,
    source_policy: SourceAuditPolicy | None = None,
    energy_policy: VaspEnergyLabelPolicy | None = None,
    label_compatibility_policy: LabelCompatibilityPolicy | None = None,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
) -> TrainingDataSourceCatalog:
    """Finalize DATA2 from already audited immutable source records."""

    source_active = SourceAuditPolicy() if source_policy is None else source_policy
    energy_active = VaspEnergyLabelPolicy() if energy_policy is None else energy_policy
    label_active = LabelCompatibilityPolicy() if label_compatibility_policy is None else label_compatibility_policy
    expected = tuple(run.run_id for run in manifest.runs)
    if set(expected) != set(sources_by_run):
        raise TrainingDataInputError("Audited VASP source IDs must exactly match the manifest.")
    sources = tuple(sources_by_run[run_id] for run_id in expected)
    return _finalize_source_catalog(
        manifest,
        sources,
        source_active=source_active,
        energy_active=energy_active,
        label_active=label_active,
        atomic_reference_policy=atomic_reference_policy,
    )


def build_training_data_source_catalog_from_loaded(
    manifest: TrainingDataManifest,
    loaded_sources: Mapping[str, LoadedVaspTrainingSource],
    *,
    source_policy: SourceAuditPolicy | None = None,
    energy_policy: VaspEnergyLabelPolicy | None = None,
    label_compatibility_policy: LabelCompatibilityPolicy | None = None,
    atomic_reference_policy: AtomicReferenceIdentifiabilityPolicy | None = None,
) -> TrainingDataSourceCatalog:
    """Finalize DATA2 from sources already parsed by ``load_vasp_training_source``."""

    return build_training_data_source_catalog_from_sources(
        manifest,
        {run_id: item.source for run_id, item in loaded_sources.items()},
        source_policy=source_policy,
        energy_policy=energy_policy,
        label_compatibility_policy=label_compatibility_policy,
        atomic_reference_policy=atomic_reference_policy,
    )
