"""Stage-11E8a real-dataset pilot dossier and execution preflight.

The pilot layer does not discover states or reinterpret lower-stage results.  It
collects source-bound E0--E7 evidence, accepted-frame fractions, unresolved
fractions, resource use, and explicit scientific outcomes into one immutable
report.  Missing raw coordinates or missing required stage products are
reported as blockers rather than replaced by legacy summaries.

The exact dossier schema, evidence taxonomy, and fail-closed preflight are
mdstats-specific constructions.  General provenance and reproducibility
bookkeeping are standard scientific practice.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

import numpy as np

from ._pilot_common import (
    canonical_json as _canonical_json,
    digest as _digest,
    file_digest as _file_digest,
    freeze as _freeze,
    json_value as _json_value,
    positive_int as _positive_int,
)

PILOT_AUDIT_STAGE = "11E8a"
PILOT_DATASET_SCHEMA = "mdstats.na-lta-300k-pilot-dataset.v1"
PILOT_ARTIFACT_SCHEMA = "mdstats.pilot-artifact-record.v1"
PILOT_EVIDENCE_SCHEMA = "mdstats.pilot-evidence-record.v1"
PILOT_RESOURCE_SCHEMA = "mdstats.pilot-resource-usage.v1"
PILOT_OUTCOME_SCHEMA = "mdstats.pilot-scientific-outcome.v1"
PILOT_REPORT_SCHEMA = "mdstats.na-lta-300k-pilot-report.v1"

REQUIRED_PILOT_EVIDENCE_IDS = (
    "registration",
    "structural_mapping",
    "stationarity",
    "kernel_metric_periodization",
    "reference_cell_sensitivity",
    "field_certificate",
    "topology_certificate",
    "attractor_lineage",
    "provisional_cores",
    "temporal_support",
    "force_availability",
    "force_density_agreement",
    "transition_paths",
    "unresolved_fraction",
    "cost",
    "memory",
)


class PilotAuditError(ValueError):
    """Base Stage-11E8a error."""


class PilotAuditInputError(PilotAuditError):
    """Raised when pilot evidence is malformed or source-inconsistent."""


class PilotAuditSerializationError(PilotAuditError):
    """Raised when serialized pilot evidence is malformed or tampered with."""


class PilotAuditResourceError(PilotAuditError):
    """Raised before declared dossier resource limits are exceeded."""


class PilotEvidenceStatus(str, Enum):
    RESOLVED = "resolved"
    PARTIAL = "partial"
    LEGACY_SUMMARY_ONLY = "legacy_summary_only"
    UNAVAILABLE = "unavailable"
    NOT_APPLICABLE = "not_applicable"
    BLOCKED = "blocked"


class PilotOverallStatus(str, Enum):
    COMPLETE = "complete"
    SCIENTIFICALLY_PARTIAL = "scientifically_partial"
    BLOCKED_MISSING_TRAJECTORY = "blocked_missing_trajectory"
    BLOCKED_MISSING_REQUIRED_EVIDENCE = "blocked_missing_required_evidence"
    BLOCKED_SOURCE_MISMATCH = "blocked_source_mismatch"


class PilotRateStatus(str, Enum):
    NOT_EVALUATED = "not_evaluated"
    UNIDENTIFIED = "unidentified"
    IDENTIFIED = "identified"


class PilotPMFStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    UNSUPPORTED = "unsupported"
    SUPPORT_LIMITED = "support_limited"
    RESOLVED = "resolved"








def _sha(value: str | None, name: str, *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PilotAuditInputError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _finite_nonnegative(value: Any, name: str) -> float:
    result = float(value)
    if not np.isfinite(result) or result < 0.0:
        raise PilotAuditInputError(f"{name} must be finite and nonnegative.")
    return result


def _fraction(value: Any | None, name: str) -> float | None:
    if value is None:
        return None
    result = float(value)
    if not np.isfinite(result) or not (0.0 <= result <= 1.0):
        raise PilotAuditInputError(f"{name} must lie in [0, 1].")
    return result








@dataclass(frozen=True, slots=True)
class PilotAuditResourcePolicy:
    max_artifacts: int = 256
    max_evidence_records: int = 128
    max_metadata_entries: int = 4096

    def __post_init__(self) -> None:
        for name in ("max_artifacts", "max_evidence_records", "max_metadata_entries"):
            object.__setattr__(self, name, _positive_int(getattr(self, name), name))


@dataclass(frozen=True, slots=True)
class PilotDatasetIdentity:
    material: str
    mobile_species: str
    temperature_kelvin: float
    atom_count: int
    species_counts: Mapping[str, int]
    frame_count: int | None = None
    duration_ps: float | None = None
    trajectory_available: bool = False
    trajectory_digest: str | None = None
    frame_semantics: str = "trajectory"
    registration_signature: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.material.strip() or not self.mobile_species.strip():
            raise PilotAuditInputError("material and mobile_species must be non-empty.")
        temperature = _finite_nonnegative(self.temperature_kelvin, "temperature_kelvin")
        atom_count = _positive_int(self.atom_count, "atom_count")
        counts = {str(k): int(v) for k, v in self.species_counts.items()}
        if any(v < 0 for v in counts.values()) or sum(counts.values()) != atom_count:
            raise PilotAuditInputError("species_counts must be nonnegative and sum to atom_count.")
        frame_count = None if self.frame_count is None else _positive_int(self.frame_count, "frame_count")
        duration = None if self.duration_ps is None else _finite_nonnegative(self.duration_ps, "duration_ps")
        trajectory_digest = _sha(self.trajectory_digest, "trajectory_digest", optional=True)
        registration = _sha(self.registration_signature, "registration_signature", optional=True)
        if self.trajectory_available and trajectory_digest is None:
            raise PilotAuditInputError("An available trajectory requires trajectory_digest.")
        if self.frame_semantics not in {"trajectory", "ensemble"}:
            raise PilotAuditInputError("frame_semantics must be trajectory or ensemble.")
        metadata = _freeze(dict(self.metadata))
        payload = {
            "schema": PILOT_DATASET_SCHEMA,
            "material": self.material,
            "mobile_species": self.mobile_species,
            "temperature_kelvin": temperature,
            "atom_count": atom_count,
            "species_counts": counts,
            "frame_count": frame_count,
            "duration_ps": duration,
            "trajectory_available": bool(self.trajectory_available),
            "trajectory_digest": trajectory_digest,
            "frame_semantics": self.frame_semantics,
            "registration_signature": registration,
            "metadata": _json_value(metadata),
        }
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Pilot dataset signature is inconsistent.")
        object.__setattr__(self, "temperature_kelvin", temperature)
        object.__setattr__(self, "atom_count", atom_count)
        object.__setattr__(self, "species_counts", MappingProxyType(dict(sorted(counts.items()))))
        object.__setattr__(self, "frame_count", frame_count)
        object.__setattr__(self, "duration_ps", duration)
        object.__setattr__(self, "trajectory_digest", trajectory_digest)
        object.__setattr__(self, "registration_signature", registration)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": PILOT_DATASET_SCHEMA, "material": self.material,
            "mobile_species": self.mobile_species, "temperature_kelvin": self.temperature_kelvin,
            "atom_count": self.atom_count, "species_counts": dict(self.species_counts),
            "frame_count": self.frame_count, "duration_ps": self.duration_ps,
            "trajectory_available": self.trajectory_available, "trajectory_digest": self.trajectory_digest,
            "frame_semantics": self.frame_semantics, "registration_signature": self.registration_signature,
            "metadata": _json_value(self.metadata), "signature": self.signature,
        }

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PilotDatasetIdentity":
        if p.get("schema") != PILOT_DATASET_SCHEMA:
            raise PilotAuditSerializationError("Unsupported pilot dataset schema.")
        return cls(
            material=str(p["material"]), mobile_species=str(p["mobile_species"]),
            temperature_kelvin=float(p["temperature_kelvin"]), atom_count=int(p["atom_count"]),
            species_counts=dict(p["species_counts"]), frame_count=p.get("frame_count"),
            duration_ps=p.get("duration_ps"), trajectory_available=bool(p["trajectory_available"]),
            trajectory_digest=p.get("trajectory_digest"), frame_semantics=str(p["frame_semantics"]),
            registration_signature=p.get("registration_signature"), metadata=dict(p.get("metadata", {})),
            signature=str(p.get("signature", "")),
        )


@dataclass(frozen=True, slots=True)
class PilotArtifactRecord:
    artifact_id: str
    role: str
    relative_path: str
    byte_count: int
    sha256: str
    source_kind: str = "derived"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.artifact_id or not self.role or not self.relative_path:
            raise PilotAuditInputError("artifact_id, role, and relative_path must be non-empty.")
        byte_count = int(self.byte_count)
        if byte_count < 0:
            raise PilotAuditInputError("byte_count must be nonnegative.")
        sha = _sha(self.sha256, "sha256")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": PILOT_ARTIFACT_SCHEMA, "artifact_id": self.artifact_id, "role": self.role,
                   "relative_path": self.relative_path, "byte_count": byte_count, "sha256": sha,
                   "source_kind": self.source_kind, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Pilot artifact signature is inconsistent.")
        object.__setattr__(self, "byte_count", byte_count)
        object.__setattr__(self, "sha256", sha)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PILOT_ARTIFACT_SCHEMA, "artifact_id": self.artifact_id, "role": self.role,
                "relative_path": self.relative_path, "byte_count": self.byte_count, "sha256": self.sha256,
                "source_kind": self.source_kind, "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PilotArtifactRecord":
        if p.get("schema") != PILOT_ARTIFACT_SCHEMA:
            raise PilotAuditSerializationError("Unsupported pilot artifact schema.")
        return cls(str(p["artifact_id"]), str(p["role"]), str(p["relative_path"]), int(p["byte_count"]),
                   str(p["sha256"]), str(p.get("source_kind", "derived")), dict(p.get("metadata", {})),
                   str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class PilotEvidenceRecord:
    evidence_id: str
    stage_id: str
    status: PilotEvidenceStatus
    source_digest: str | None = None
    accepted_fraction: float | None = None
    unresolved_fraction: float | None = None
    metrics: Mapping[str, Any] = field(default_factory=dict)
    artifact_ids: tuple[str, ...] = ()
    messages: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        if not self.evidence_id or not self.stage_id:
            raise PilotAuditInputError("evidence_id and stage_id must be non-empty.")
        status = PilotEvidenceStatus(self.status)
        source = _sha(self.source_digest, "source_digest", optional=True)
        accepted = _fraction(self.accepted_fraction, "accepted_fraction")
        unresolved = _fraction(self.unresolved_fraction, "unresolved_fraction")
        metrics = _freeze(dict(self.metrics))
        artifacts = tuple(str(v) for v in self.artifact_ids)
        messages = tuple(str(v) for v in self.messages)
        payload = {"schema": PILOT_EVIDENCE_SCHEMA, "evidence_id": self.evidence_id, "stage_id": self.stage_id,
                   "status": status.value, "source_digest": source, "accepted_fraction": accepted,
                   "unresolved_fraction": unresolved, "metrics": _json_value(metrics),
                   "artifact_ids": list(artifacts), "messages": list(messages)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Pilot evidence signature is inconsistent.")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "source_digest", source)
        object.__setattr__(self, "accepted_fraction", accepted)
        object.__setattr__(self, "unresolved_fraction", unresolved)
        object.__setattr__(self, "metrics", metrics)
        object.__setattr__(self, "artifact_ids", artifacts)
        object.__setattr__(self, "messages", messages)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PILOT_EVIDENCE_SCHEMA, "evidence_id": self.evidence_id, "stage_id": self.stage_id,
                "status": self.status.value, "source_digest": self.source_digest,
                "accepted_fraction": self.accepted_fraction, "unresolved_fraction": self.unresolved_fraction,
                "metrics": _json_value(self.metrics), "artifact_ids": list(self.artifact_ids),
                "messages": list(self.messages), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PilotEvidenceRecord":
        if p.get("schema") != PILOT_EVIDENCE_SCHEMA:
            raise PilotAuditSerializationError("Unsupported pilot evidence schema.")
        return cls(str(p["evidence_id"]), str(p["stage_id"]), PilotEvidenceStatus(p["status"]),
                   p.get("source_digest"), p.get("accepted_fraction"), p.get("unresolved_fraction"),
                   dict(p.get("metrics", {})), tuple(p.get("artifact_ids", ())), tuple(p.get("messages", ())),
                   str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class PilotResourceUsage:
    wall_seconds: float | None = None
    peak_memory_bytes: int | None = None
    worker_count: int | None = None
    output_bytes: int = 0
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        wall = None if self.wall_seconds is None else _finite_nonnegative(self.wall_seconds, "wall_seconds")
        memory = None if self.peak_memory_bytes is None else int(self.peak_memory_bytes)
        workers = None if self.worker_count is None else _positive_int(self.worker_count, "worker_count")
        output = int(self.output_bytes)
        if memory is not None and memory < 0 or output < 0:
            raise PilotAuditInputError("Resource byte counts must be nonnegative.")
        metadata = _freeze(dict(self.metadata))
        payload = {"schema": PILOT_RESOURCE_SCHEMA, "wall_seconds": wall, "peak_memory_bytes": memory,
                   "worker_count": workers, "output_bytes": output, "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Pilot resource signature is inconsistent.")
        object.__setattr__(self, "wall_seconds", wall)
        object.__setattr__(self, "peak_memory_bytes", memory)
        object.__setattr__(self, "worker_count", workers)
        object.__setattr__(self, "output_bytes", output)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PILOT_RESOURCE_SCHEMA, "wall_seconds": self.wall_seconds,
                "peak_memory_bytes": self.peak_memory_bytes, "worker_count": self.worker_count,
                "output_bytes": self.output_bytes, "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PilotResourceUsage":
        if p.get("schema") != PILOT_RESOURCE_SCHEMA:
            raise PilotAuditSerializationError("Unsupported pilot resource schema.")
        return cls(p.get("wall_seconds"), p.get("peak_memory_bytes"), p.get("worker_count"),
                   int(p.get("output_bytes", 0)), dict(p.get("metadata", {})), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class PilotScientificOutcome:
    site_center_count: int | None = None
    supported_basin_count: int | None = None
    observed_connection_count: int | None = None
    transition_path_ensemble_count: int | None = None
    undersampled_path_ensemble_count: int | None = None
    rate_status: PilotRateStatus = PilotRateStatus.NOT_EVALUATED
    global_pmf_status: PilotPMFStatus = PilotPMFStatus.NOT_REQUESTED
    conclusions: tuple[str, ...] = ()
    signature: str = ""

    def __post_init__(self) -> None:
        values = []
        for name in ("site_center_count", "supported_basin_count", "observed_connection_count",
                     "transition_path_ensemble_count", "undersampled_path_ensemble_count"):
            value = getattr(self, name)
            if value is not None and int(value) < 0:
                raise PilotAuditInputError(f"{name} must be nonnegative.")
            values.append(None if value is None else int(value))
        rate = PilotRateStatus(self.rate_status)
        pmf = PilotPMFStatus(self.global_pmf_status)
        conclusions = tuple(str(v) for v in self.conclusions)
        payload = {"schema": PILOT_OUTCOME_SCHEMA,
                   **dict(zip(("site_center_count", "supported_basin_count", "observed_connection_count",
                              "transition_path_ensemble_count", "undersampled_path_ensemble_count"), values)),
                   "rate_status": rate.value, "global_pmf_status": pmf.value, "conclusions": list(conclusions)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Pilot outcome signature is inconsistent.")
        for name, value in zip(("site_center_count", "supported_basin_count", "observed_connection_count",
                                "transition_path_ensemble_count", "undersampled_path_ensemble_count"), values):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "rate_status", rate)
        object.__setattr__(self, "global_pmf_status", pmf)
        object.__setattr__(self, "conclusions", conclusions)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PILOT_OUTCOME_SCHEMA, "site_center_count": self.site_center_count,
                "supported_basin_count": self.supported_basin_count,
                "observed_connection_count": self.observed_connection_count,
                "transition_path_ensemble_count": self.transition_path_ensemble_count,
                "undersampled_path_ensemble_count": self.undersampled_path_ensemble_count,
                "rate_status": self.rate_status.value, "global_pmf_status": self.global_pmf_status.value,
                "conclusions": list(self.conclusions), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "PilotScientificOutcome":
        if p.get("schema") != PILOT_OUTCOME_SCHEMA:
            raise PilotAuditSerializationError("Unsupported pilot outcome schema.")
        return cls(p.get("site_center_count"), p.get("supported_basin_count"), p.get("observed_connection_count"),
                   p.get("transition_path_ensemble_count"), p.get("undersampled_path_ensemble_count"),
                   PilotRateStatus(p["rate_status"]), PilotPMFStatus(p["global_pmf_status"]),
                   tuple(p.get("conclusions", ())), str(p.get("signature", "")))


@dataclass(frozen=True, slots=True)
class NaLta300KPilotReport:
    dataset: PilotDatasetIdentity
    evidence: tuple[PilotEvidenceRecord, ...]
    artifacts: tuple[PilotArtifactRecord, ...]
    resources: PilotResourceUsage
    outcome: PilotScientificOutcome
    overall_status: PilotOverallStatus
    missing_required_evidence: tuple[str, ...]
    blockers: tuple[str, ...]
    metadata: Mapping[str, Any] = field(default_factory=dict)
    signature: str = ""

    def __post_init__(self) -> None:
        evidence = tuple(self.evidence)
        artifacts = tuple(self.artifacts)
        status = PilotOverallStatus(self.overall_status)
        missing = tuple(str(v) for v in self.missing_required_evidence)
        blockers = tuple(str(v) for v in self.blockers)
        metadata = _freeze(dict(self.metadata))
        ids = [item.evidence_id for item in evidence]
        artifact_ids = [item.artifact_id for item in artifacts]
        if len(ids) != len(set(ids)) or len(artifact_ids) != len(set(artifact_ids)):
            raise PilotAuditInputError("Pilot evidence and artifact IDs must be unique.")
        known_artifacts = set(artifact_ids)
        for record in evidence:
            unknown = set(record.artifact_ids) - known_artifacts
            if unknown:
                raise PilotAuditInputError(f"Evidence {record.evidence_id!r} references unknown artifacts {sorted(unknown)}.")
        payload = {"schema": PILOT_REPORT_SCHEMA, "dataset": self.dataset.to_dict(),
                   "evidence": [v.to_dict() for v in evidence], "artifacts": [v.to_dict() for v in artifacts],
                   "resources": self.resources.to_dict(), "outcome": self.outcome.to_dict(),
                   "overall_status": status.value, "missing_required_evidence": list(missing),
                   "blockers": list(blockers), "metadata": _json_value(metadata)}
        expected = _digest(payload)
        if self.signature and self.signature != expected:
            raise PilotAuditInputError("Pilot report signature is inconsistent.")
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(self, "artifacts", artifacts)
        object.__setattr__(self, "overall_status", status)
        object.__setattr__(self, "missing_required_evidence", missing)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "metadata", metadata)
        object.__setattr__(self, "signature", expected)

    def to_dict(self) -> dict[str, Any]:
        return {"schema": PILOT_REPORT_SCHEMA, "dataset": self.dataset.to_dict(),
                "evidence": [v.to_dict() for v in self.evidence], "artifacts": [v.to_dict() for v in self.artifacts],
                "resources": self.resources.to_dict(), "outcome": self.outcome.to_dict(),
                "overall_status": self.overall_status.value,
                "missing_required_evidence": list(self.missing_required_evidence), "blockers": list(self.blockers),
                "metadata": _json_value(self.metadata), "signature": self.signature}

    @classmethod
    def from_dict(cls, p: Mapping[str, Any]) -> "NaLta300KPilotReport":
        if p.get("schema") != PILOT_REPORT_SCHEMA:
            raise PilotAuditSerializationError("Unsupported pilot report schema.")
        return cls(PilotDatasetIdentity.from_dict(p["dataset"]),
                   tuple(PilotEvidenceRecord.from_dict(v) for v in p.get("evidence", ())),
                   tuple(PilotArtifactRecord.from_dict(v) for v in p.get("artifacts", ())),
                   PilotResourceUsage.from_dict(p["resources"]), PilotScientificOutcome.from_dict(p["outcome"]),
                   PilotOverallStatus(p["overall_status"]), tuple(p.get("missing_required_evidence", ())),
                   tuple(p.get("blockers", ())), dict(p.get("metadata", {})), str(p.get("signature", "")))


def prepare_na_lta_300k_pilot_report(
    dataset: PilotDatasetIdentity,
    evidence: Sequence[PilotEvidenceRecord],
    *,
    artifacts: Sequence[PilotArtifactRecord] = (),
    resources: PilotResourceUsage | None = None,
    outcome: PilotScientificOutcome | None = None,
    metadata: Mapping[str, Any] | None = None,
    policy: PilotAuditResourcePolicy | None = None,
) -> NaLta300KPilotReport:
    """Prepare one fail-closed Stage-11E8a dossier from source-bound evidence."""

    policy = policy or PilotAuditResourcePolicy()
    evidence_tuple = tuple(evidence)
    artifact_tuple = tuple(artifacts)
    if len(evidence_tuple) > policy.max_evidence_records:
        raise PilotAuditResourceError("Pilot evidence-record limit exceeded.")
    if len(artifact_tuple) > policy.max_artifacts:
        raise PilotAuditResourceError("Pilot artifact limit exceeded.")
    metadata_dict = dict(metadata or {})
    if len(metadata_dict) > policy.max_metadata_entries:
        raise PilotAuditResourceError("Pilot metadata-entry limit exceeded.")
    if dataset.material.strip().lower().replace("_", "-") not in {"na-lta", "sodium-lta"}:
        raise PilotAuditInputError("Stage 11E8a is the 300 K Na-LTA pilot.")
    if dataset.mobile_species != "Na" or abs(dataset.temperature_kelvin - 300.0) > 1.0e-8:
        raise PilotAuditInputError("Stage 11E8a requires mobile species Na at 300 K.")
    by_id = {item.evidence_id: item for item in evidence_tuple}
    if len(by_id) != len(evidence_tuple):
        raise PilotAuditInputError("Pilot evidence IDs must be unique.")
    missing = tuple(item for item in REQUIRED_PILOT_EVIDENCE_IDS if item not in by_id)
    source_digests = {item.source_digest for item in evidence_tuple if item.source_digest is not None}
    source_mismatch = dataset.trajectory_digest is not None and any(v != dataset.trajectory_digest for v in source_digests)
    blockers: list[str] = []
    if not dataset.trajectory_available:
        status = PilotOverallStatus.BLOCKED_MISSING_TRAJECTORY
        blockers.append("Raw 300 K Na-LTA trajectory coordinates are unavailable.")
    elif source_mismatch:
        status = PilotOverallStatus.BLOCKED_SOURCE_MISMATCH
        blockers.append("One or more evidence records are bound to another trajectory digest.")
    elif missing:
        status = PilotOverallStatus.BLOCKED_MISSING_REQUIRED_EVIDENCE
        blockers.append("Required Stage-11E8a evidence records are missing.")
    else:
        statuses = {item.status for item in evidence_tuple if item.evidence_id in REQUIRED_PILOT_EVIDENCE_IDS}
        if statuses <= {PilotEvidenceStatus.RESOLVED, PilotEvidenceStatus.NOT_APPLICABLE}:
            status = PilotOverallStatus.COMPLETE
        else:
            status = PilotOverallStatus.SCIENTIFICALLY_PARTIAL
            blockers.extend(item.evidence_id for item in evidence_tuple
                            if item.evidence_id in REQUIRED_PILOT_EVIDENCE_IDS
                            and item.status in {PilotEvidenceStatus.BLOCKED, PilotEvidenceStatus.UNAVAILABLE})
    return NaLta300KPilotReport(
        dataset=dataset, evidence=evidence_tuple, artifacts=artifact_tuple,
        resources=resources or PilotResourceUsage(), outcome=outcome or PilotScientificOutcome(),
        overall_status=status, missing_required_evidence=missing, blockers=tuple(blockers),
        metadata={**metadata_dict, "required_evidence_ids": REQUIRED_PILOT_EVIDENCE_IDS,
                  "source_mismatch": source_mismatch, "rates_inferred": False,
                  "legacy_summaries_replace_raw_trajectory": False},
    )


def _artifact(root: Path, relative_path: str, artifact_id: str, role: str, *, source_kind: str,
              metadata: Mapping[str, Any] | None = None) -> PilotArtifactRecord:
    path = root / relative_path
    if not path.is_file():
        raise PilotAuditInputError(f"Required bundled pilot artifact is missing: {relative_path}")
    return PilotArtifactRecord(artifact_id, role, relative_path, path.stat().st_size, _file_digest(path),
                               source_kind, dict(metadata or {}))


def audit_bundled_na_lta_300k_legacy_evidence(
    package_root: str | Path,
    *,
    policy: PilotAuditResourcePolicy | None = None,
) -> NaLta300KPilotReport:
    """Audit the real derived Na-LTA artifacts bundled with the source tree.

    The bundled package does not contain the raw trajectory.  This function
    therefore returns a source-certified *blocked* E8a dossier; it never upgrades
    legacy topology or plotting summaries into E0b--E7 scientific evidence.
    """

    root = Path(package_root).resolve()
    poscar_rel = "tests/data/Na_LTA_relaxed.POSCAR"
    topology_rel = "examples/topology_statistics/na_lta_300K/generated/tables/na_lta_300K.json"
    topology_summary_rel = "examples/topology_statistics/na_lta_300K/generated/na_lta_300K_ts5_summary.json"
    rings_rel = "examples/primitive_ring/na_lta_300K/generated/primitive_ring_catalog.json"
    density_rel = "benchmarks/density_full_trajectory_ld7_benchmark.json"
    plot_rel = "benchmarks/na_lta_300K_all_species_plot_summary.json"

    try:
        from ase.io import read as ase_read
    except Exception as exc:  # pragma: no cover - exercised by environment failure only
        raise PilotAuditInputError("Real ASE is required to audit the bundled Na-LTA structure.") from exc

    atoms = ase_read(root / poscar_rel)
    symbols = atoms.get_chemical_symbols()
    counts = {name: symbols.count(name) for name in sorted(set(symbols))}
    if len(atoms) != 168 or counts != {"Al": 24, "Na": 24, "O": 96, "Si": 24}:
        raise PilotAuditInputError("Bundled Na-LTA reference composition is inconsistent.")

    with (root / topology_rel).open("r", encoding="utf-8") as handle:
        topology = json.load(handle)
    with (root / topology_summary_rel).open("r", encoding="utf-8") as handle:
        topology_summary = json.load(handle)
    with (root / rings_rel).open("r", encoding="utf-8") as handle:
        rings = json.load(handle)
    with (root / density_rel).open("r", encoding="utf-8") as handle:
        density = json.load(handle)
    with (root / plot_rel).open("r", encoding="utf-8") as handle:
        plot = json.load(handle)

    if topology_summary.get("n_frames") != 2000 or topology_summary.get("framework_classes") != 1:
        raise PilotAuditInputError("Bundled 300 K topology summary failed its standing acceptance facts.")
    if not rings.get("search_completed_without_resource_truncation") or rings.get("complete_for_ring_sizes_up_to") != 8:
        raise PilotAuditInputError("Bundled primitive-ring catalog is not certified complete through size eight.")
    if density.get("frame_count") != 1300 or set(density.get("species", {})) != {"Na", "Si", "Al", "O"}:
        raise PilotAuditInputError("Bundled all-species density benchmark is inconsistent.")

    artifacts = (
        _artifact(root, poscar_rel, "reference_structure", "Na-LTA reference structure", source_kind="reference"),
        _artifact(root, topology_rel, "topology_statistics", "legacy 300 K topology statistics", source_kind="legacy_real_trajectory_summary"),
        _artifact(root, topology_summary_rel, "topology_summary", "legacy 300 K topology summary", source_kind="legacy_real_trajectory_summary"),
        _artifact(root, rings_rel, "primitive_ring_catalog", "Na-LTA primitive-ring catalog", source_kind="derived_reference"),
        _artifact(root, density_rel, "density_benchmark", "1,300-frame all-species density benchmark", source_kind="legacy_real_trajectory_summary"),
        _artifact(root, plot_rel, "plot_summary", "all-species browser artifact summary", source_kind="legacy_real_trajectory_summary"),
    )
    dataset = PilotDatasetIdentity(
        material="Na-LTA", mobile_species="Na", temperature_kelvin=300.0,
        atom_count=len(atoms), species_counts=counts, frame_count=2000,
        duration_ps=float(topology_summary.get("duration_ps_assigned", 0.0)),
        trajectory_available=False, frame_semantics="trajectory",
        metadata={"reference_cell_volume_angstrom3": float(atoms.get_volume()),
                  "legacy_topology_frame_count": 2000, "legacy_density_frame_count": 1300,
                  "raw_trajectory_packaged": False},
    )
    legacy_metrics = {
        "atomic_states": int(topology_summary["atomic_states"]),
        "framework_classes": int(topology_summary["framework_classes"]),
        "atomic_changed_boundaries": int(topology_summary["atomic_changed_boundaries"]),
        "framework_changed_boundaries": int(topology_summary["framework_changed_boundaries"]),
        "framework_edge_count": int(topology_summary["framework_edge_count"]),
        "primitive_ring_count": len(rings["rings"]),
        "primitive_ring_size_counts": {str(v["ring_size"]): int(v["ring_count"]) for v in rings["ring_size_counts"]},
    }
    evidence = (
        PilotEvidenceRecord("structural_mapping", "legacy-S4/C1-C3", PilotEvidenceStatus.LEGACY_SUMMARY_ONLY,
                            metrics={**legacy_metrics, "topology_digest": rings["topology_digest"]},
                            artifact_ids=("reference_structure", "topology_statistics", "primitive_ring_catalog"),
                            messages=("Real topology and ring evidence is available, but not source-bound E0b-E7 pilot output.",)),
        PilotEvidenceRecord("topology_certificate", "legacy-TS2/S4", PilotEvidenceStatus.LEGACY_SUMMARY_ONLY,
                            accepted_fraction=1.0, unresolved_fraction=0.0,
                            metrics={"framework_uniform": True, "ring_complete_through_size": 8,
                                     "ring_search_truncated": False},
                            artifact_ids=("topology_statistics", "primitive_ring_catalog")),
        PilotEvidenceRecord("kernel_metric_periodization", "legacy-LD7", PilotEvidenceStatus.LEGACY_SUMMARY_ONLY,
                            metrics={"density_frame_count": int(density["frame_count"]),
                                     "species": tuple(sorted(density["species"])),
                                     "total_seconds": float(density["total_seconds"]),
                                     "backend_by_species": {k: v["storage"]["storage_backend"] for k, v in density["species"].items()}},
                            artifact_ids=("density_benchmark", "plot_summary"),
                            messages=("This predates the Stage-11E1 source-bound periodic species-density result.",)),
        PilotEvidenceRecord("cost", "legacy-LD7", PilotEvidenceStatus.PARTIAL,
                            metrics={"density_wall_seconds": float(density["total_seconds"]),
                                     "plot_html_bytes": int(plot["html_bytes"])},
                            artifact_ids=("density_benchmark", "plot_summary")),
        PilotEvidenceRecord("memory", "legacy-LD7", PilotEvidenceStatus.PARTIAL,
                            metrics={"max_realized_density_bytes": max(int(v["storage"]["realized_bytes"])
                                                                        for v in density["species"].values()),
                                     "max_scatter_workspace_bytes": max(int(v["scatter_workspace_peak_bytes"])
                                                                         for v in density["species"].values())},
                            artifact_ids=("density_benchmark",)),
    )
    outcome = PilotScientificOutcome(
        rate_status=PilotRateStatus.NOT_EVALUATED, global_pmf_status=PilotPMFStatus.NOT_REQUESTED,
        conclusions=(
            "The archived real trajectory summaries show variable Na-inclusive atomic connectivity and one uniform framework topology.",
            "The primitive-ring reference is certified complete through ring size eight under its declared definition.",
            "No Stage-11E0b-E7 site, force, residence, path, or network conclusion can be reconstructed without raw coordinates or serialized stage products.",
        ),
    )
    return prepare_na_lta_300k_pilot_report(
        dataset, evidence, artifacts=artifacts,
        resources=PilotResourceUsage(wall_seconds=float(density["total_seconds"]),
                                     peak_memory_bytes=max(int(v["storage"]["realized_bytes"])
                                                           for v in density["species"].values()),
                                     output_bytes=sum(v.byte_count for v in artifacts),
                                     metadata={"resource_scope": "legacy_density_benchmark_only"}),
        outcome=outcome, metadata={"audit_kind": "bundled_legacy_real_evidence_preflight",
                                   "raw_trajectory_required_to_complete_e8a": True}, policy=policy,
    )


def render_na_lta_300k_pilot_markdown(report: NaLta300KPilotReport) -> str:
    """Render a deterministic human-readable dossier without changing evidence."""
    lines = ["# Stage 11E8a — 300 K Na-LTA pilot dossier", "",
             f"- Status: `{report.overall_status.value}`",
             f"- Dataset signature: `{report.dataset.signature}`",
             f"- Report signature: `{report.signature}`",
             f"- Atoms: {report.dataset.atom_count}",
             f"- Frames represented: {report.dataset.frame_count if report.dataset.frame_count is not None else 'unknown'}",
             f"- Raw trajectory available: {str(report.dataset.trajectory_available).lower()}", ""]
    if report.blockers:
        lines.extend(["## Blockers", ""] + [f"- {v}" for v in report.blockers] + [""])
    lines.extend(["## Evidence", "", "| Evidence | Stage | Status | Accepted | Unresolved |", "|---|---:|---|---:|---:|"])
    for item in report.evidence:
        accepted = "—" if item.accepted_fraction is None else f"{item.accepted_fraction:.6f}"
        unresolved = "—" if item.unresolved_fraction is None else f"{item.unresolved_fraction:.6f}"
        lines.append(f"| {item.evidence_id} | {item.stage_id} | {item.status.value} | {accepted} | {unresolved} |")
    lines.extend(["", "## Scientific outcome", ""])
    for conclusion in report.outcome.conclusions:
        lines.append(f"- {conclusion}")
    lines.extend(["", f"Rates: `{report.outcome.rate_status.value}`  ",
                  f"Global PMF: `{report.outcome.global_pmf_status.value}`", ""])
    return "\n".join(lines)


__all__ = [
    "PILOT_AUDIT_STAGE", "PILOT_DATASET_SCHEMA", "PILOT_ARTIFACT_SCHEMA", "PILOT_EVIDENCE_SCHEMA",
    "PILOT_RESOURCE_SCHEMA", "PILOT_OUTCOME_SCHEMA", "PILOT_REPORT_SCHEMA", "REQUIRED_PILOT_EVIDENCE_IDS",
    "PilotAuditError", "PilotAuditInputError", "PilotAuditSerializationError", "PilotAuditResourceError",
    "PilotEvidenceStatus", "PilotOverallStatus", "PilotRateStatus", "PilotPMFStatus", "PilotAuditResourcePolicy",
    "PilotDatasetIdentity", "PilotArtifactRecord", "PilotEvidenceRecord", "PilotResourceUsage",
    "PilotScientificOutcome", "NaLta300KPilotReport", "prepare_na_lta_300k_pilot_report",
    "audit_bundled_na_lta_300k_legacy_evidence", "render_na_lta_300k_pilot_markdown",
]
