"""Stage-11E8a-S0 raw-source bootstrap for the 300 K Na-LTA pilot.

This module converts one already-normalized trajectory into the first real,
source-bound pilot products: a C0 registration, an E0b Na sample catalog, and a
fail-closed E8a dossier.  It deliberately does not execute density estimation,
mode discovery, temporal segmentation, transition paths, or network inference.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from time import perf_counter
from typing import Any, Mapping

import numpy as np

from ..site_samples import (
    FrameworkAlignedIonSampleCatalog,
    PMFTemperatureProvenance,
    SamplingStateProvenance,
    prepare_framework_aligned_ion_sample_catalog,
)
from ...collection import AtomisticFrameCollection
from ...coordinates.registration import (
    FrameRegistrationPolicy,
    FrameRegistrationResult,
    RegistrationSpatialPolicy,
    TranslationMode,
    prepare_frame_registration,
)
from ._pilot_common import (
    array_payload_bytes as _array_payload_bytes,
    file_digest as _file_sha256,
)

from .pilot_audit import (
    NaLta300KPilotReport,
    PilotArtifactRecord,
    PilotAuditInputError,
    PilotAuditResourcePolicy,
    PilotDatasetIdentity,
    PilotEvidenceRecord,
    PilotEvidenceStatus,
    PilotPMFStatus,
    PilotRateStatus,
    PilotResourceUsage,
    PilotScientificOutcome,
    prepare_na_lta_300k_pilot_report,
)

PILOT_SOURCE_BOOTSTRAP_STAGE = "11E8a-S0"
EXPECTED_NA_LTA_SPECIES_COUNTS = {"Al": 24, "Na": 24, "O": 96, "Si": 24}
_ATOMIC_SYMBOLS = {8: "O", 11: "Na", 13: "Al", 14: "Si"}


@dataclass(frozen=True, slots=True)
class NaLta300KSourceBootstrap:
    """Runtime products from the source-bound E8a bootstrap."""

    report: NaLta300KPilotReport
    registration: FrameRegistrationResult
    na_samples: FrameworkAlignedIonSampleCatalog
    trajectory_path: str
    trajectory_sha256: str

    def __post_init__(self) -> None:
        if self.report.dataset.trajectory_digest != self.trajectory_sha256:
            raise PilotAuditInputError(
                "Bootstrap report and trajectory SHA-256 are inconsistent."
            )
        if self.report.dataset.registration_signature != self.registration.signature:
            raise PilotAuditInputError(
                "Bootstrap report and registration signature are inconsistent."
            )
        if self.na_samples.registration_signature != self.registration.signature:
            raise PilotAuditInputError(
                "Bootstrap Na sample catalog is not bound to the registration."
            )




def _source_path_match(collection: AtomisticFrameCollection, path: Path) -> str:
    """Validate that reader provenance refers to the raw path being hashed."""

    provenance = collection.provenance
    if provenance is None or not provenance.source_files:
        raise PilotAuditInputError(
            "Stage 11E8a-S0 requires reader provenance with source_files."
        )
    basename_match = False
    for source in provenance.source_files:
        candidate = Path(source).expanduser()
        if candidate.is_absolute():
            if candidate.resolve() == path:
                return "exact_path"
        elif candidate.name == path.name:
            basename_match = True
    if basename_match:
        return "basename_only"
    raise PilotAuditInputError(
        "collection provenance does not reference the trajectory_path being hashed."
    )


def _species_counts(collection: AtomisticFrameCollection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for atomic_number in np.unique(collection.atomic_numbers):
        number = int(atomic_number)
        symbol = _ATOMIC_SYMBOLS.get(number, f"Z{number}")
        counts[symbol] = int(np.count_nonzero(collection.atomic_numbers == number))
    return dict(sorted(counts.items()))




def _default_registration_policy(collection: AtomisticFrameCollection) -> FrameRegistrationPolicy:
    # S0 certifies the source coordinate measure without choosing the later
    # density/site-discovery gauge.  Analysis-specific framework registration
    # belongs to S1 and may be supplied explicitly through registration_policy.
    return FrameRegistrationPolicy(
        spatial_policy=RegistrationSpatialPolicy.PHYSICAL,
        translation_mode=TranslationMode.NONE,
        require_fixed_registered_cell=True,
    )


def prepare_na_lta_300k_source_bootstrap(
    collection: AtomisticFrameCollection,
    trajectory_path: str | Path,
    *,
    temperature_kelvin: float = 300.0,
    registration_policy: FrameRegistrationPolicy | None = None,
    metadata: Mapping[str, Any] | None = None,
    audit_policy: PilotAuditResourcePolicy | None = None,
) -> NaLta300KSourceBootstrap:
    """Create source-bound C0/E0b products and a fail-closed E8a dossier.

    The input collection must already be normalized by an mdstats reader.  The
    raw file is hashed independently so every pilot evidence record is bound to
    the exact source bytes rather than only to an in-memory coordinate digest.
    """

    if not isinstance(collection, AtomisticFrameCollection):
        raise TypeError("collection must be an AtomisticFrameCollection.")
    path = Path(trajectory_path).resolve()
    if not path.is_file():
        raise PilotAuditInputError(f"Trajectory file does not exist: {path}")
    if not collection.is_trajectory:
        raise PilotAuditInputError("Stage 11E8a requires trajectory semantics.")
    if collection.times is None:
        raise PilotAuditInputError("Stage 11E8a requires a physical trajectory time axis.")
    if not all(bool(value) for value in collection.pbc):
        raise PilotAuditInputError("The 300 K Na-LTA pilot requires full periodicity.")
    if not np.isfinite(float(temperature_kelvin)) or abs(float(temperature_kelvin) - 300.0) > 1.0e-8:
        raise PilotAuditInputError("Stage 11E8a requires the declared temperature 300 K.")

    counts = _species_counts(collection)
    if collection.n_atoms != 168 or counts != EXPECTED_NA_LTA_SPECIES_COUNTS:
        raise PilotAuditInputError(
            "The source is not the required 168-atom Na-LTA composition: "
            f"received {counts}."
        )

    source_path_match = _source_path_match(collection, path)
    started = perf_counter()
    trajectory_sha256 = _file_sha256(path)
    active_registration_policy = registration_policy or _default_registration_policy(collection)
    registration = prepare_frame_registration(
        collection,
        policy=active_registration_policy,
    )
    sampling_state = SamplingStateProvenance(
        declaration_source="Stage 11E8a source bootstrap",
        notes=(
            "Equilibrium and stationarity are intentionally unresolved until the "
            "dedicated pilot diagnostics are executed.",
        ),
    )
    pmf_temperature = PMFTemperatureProvenance.from_collection(collection)
    na_samples = prepare_framework_aligned_ion_sample_catalog(
        collection,
        registration,
        species_atomic_number=11,
        species_label="Na",
        sampling_state=sampling_state,
        pmf_temperature=pmf_temperature,
        metadata={"pilot_stage": PILOT_SOURCE_BOOTSTRAP_STAGE},
    )
    elapsed = perf_counter() - started

    force_available = collection.forces is not None and registration.transformed_forces is not None
    position_fraction = float(np.mean(na_samples.evidence_masks.position_mask))
    force_fraction = float(np.mean(na_samples.evidence_masks.force_mask))
    joint_fraction = float(np.mean(na_samples.evidence_masks.joint_mask))
    unresolved_fraction = 1.0 - position_fraction
    resident_bytes = _array_payload_bytes(collection, registration, na_samples)

    artifact = PilotArtifactRecord(
        artifact_id="raw_trajectory",
        role="raw 300 K Na-LTA trajectory",
        relative_path=path.name,
        byte_count=path.stat().st_size,
        sha256=trajectory_sha256,
        source_kind="raw",
        metadata={
            "absolute_path_recorded": False,
            "source_format": (
                None if collection.provenance is None else collection.provenance.source_format
            ),
            "collection_source_path_match": source_path_match,
        },
    )
    evidence = (
        PilotEvidenceRecord(
            "registration", "C0A1-C0A3", PilotEvidenceStatus.RESOLVED,
            source_digest=trajectory_sha256,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={
                "registration_signature": registration.signature,
                "collection_source_path_match": source_path_match,
                "source_contract_signature": registration.source_contract_signature,
                "registration_policy_signature": registration.policy.signature,
                "spatial_policy": registration.policy.spatial_policy.value,
                "translation_mode": registration.policy.translation_mode.value,
                "reference_atom_count": len(registration.policy.reference_atom_indices),
                "maximum_cell_identity_error": registration.maximum_cell_identity_error,
                "maximum_position_round_trip_error": registration.maximum_position_round_trip_error,
                "maximum_force_work_error": registration.maximum_force_work_error,
                "registered_cell_fixed": registration.policy.require_fixed_registered_cell,
                "na_sample_catalog_signature": na_samples.signature,
                "na_compact_sample_count": na_samples.n_samples,
            },
            artifact_ids=("raw_trajectory",),
        ),
        PilotEvidenceRecord(
            "stationarity", "11E0b/E8a", PilotEvidenceStatus.PARTIAL,
            source_digest=trajectory_sha256,
            accepted_fraction=0.0,
            unresolved_fraction=1.0,
            metrics={
                "equilibrium_status": sampling_state.equilibrium_status.value,
                "stationarity_status": sampling_state.stationarity_status.value,
                "temporal_weight_units": na_samples.temporal_weighting.weight_units,
            },
            messages=("Stationarity has not yet been tested on the real trajectory.",),
        ),
        PilotEvidenceRecord(
            "force_availability", "11E0b/11E3", (
                PilotEvidenceStatus.RESOLVED if force_available else PilotEvidenceStatus.UNAVAILABLE
            ),
            source_digest=trajectory_sha256,
            accepted_fraction=force_fraction,
            unresolved_fraction=1.0 - force_fraction,
            metrics={
                "source_forces_present": collection.forces is not None,
                "registered_forces_present": registration.transformed_forces is not None,
                "force_fraction": force_fraction,
                "joint_position_force_fraction": joint_fraction,
                "force_transform_status": na_samples.force_provenance.geometric_status.value,
                "pmf_force_status": na_samples.force_provenance.pmf_status.value,
            },
            artifact_ids=("raw_trajectory",),
        ),
        PilotEvidenceRecord(
            "unresolved_fraction", "11E8a-S0", PilotEvidenceStatus.PARTIAL,
            source_digest=trajectory_sha256,
            accepted_fraction=position_fraction,
            unresolved_fraction=unresolved_fraction,
            metrics={
                "source_position_fraction": position_fraction,
                "source_force_fraction": force_fraction,
                "source_joint_fraction": joint_fraction,
                "downstream_site_evidence_executed": False,
            },
        ),
        PilotEvidenceRecord(
            "cost", "11E8a-S0", PilotEvidenceStatus.RESOLVED,
            source_digest=trajectory_sha256,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={"source_bootstrap_wall_seconds": elapsed},
        ),
        PilotEvidenceRecord(
            "memory", "11E8a-S0", PilotEvidenceStatus.RESOLVED,
            source_digest=trajectory_sha256,
            accepted_fraction=1.0,
            unresolved_fraction=0.0,
            metrics={
                "resident_numerical_payload_bytes": resident_bytes,
                "measurement_kind": "deduplicated ndarray payload estimate",
            },
        ),
    )

    duration_ps = float(collection.times[-1] - collection.times[0])
    dataset = PilotDatasetIdentity(
        material="Na-LTA",
        mobile_species="Na",
        temperature_kelvin=300.0,
        atom_count=collection.n_atoms,
        species_counts=counts,
        frame_count=collection.n_frames,
        duration_ps=duration_ps,
        trajectory_available=True,
        trajectory_digest=trajectory_sha256,
        frame_semantics=collection.frame_semantics.value,
        registration_signature=registration.signature,
        metadata={
            "trajectory_filename": path.name,
            "source_format": (
                None if collection.provenance is None else collection.provenance.source_format
            ),
            "collection_source_path_match": source_path_match,
            "force_available": force_available,
            "velocity_available": collection.velocities is not None,
            "fixed_source_cell": bool(np.allclose(collection.cells, collection.cells[0])),
            "source_bootstrap_stage": PILOT_SOURCE_BOOTSTRAP_STAGE,
        },
    )
    report = prepare_na_lta_300k_pilot_report(
        dataset,
        evidence,
        artifacts=(artifact,),
        resources=PilotResourceUsage(
            wall_seconds=elapsed,
            peak_memory_bytes=resident_bytes,
            worker_count=1,
            output_bytes=artifact.byte_count,
            metadata={
                "memory_measurement_kind": "deduplicated ndarray payload estimate",
                "scope": "C0 registration plus E0b Na sample catalog",
            },
        ),
        outcome=PilotScientificOutcome(
            rate_status=PilotRateStatus.NOT_EVALUATED,
            global_pmf_status=(
                PilotPMFStatus.SUPPORT_LIMITED
                if na_samples.evidence_masks.pmf_force_mask.any()
                else PilotPMFStatus.UNSUPPORTED
            ),
            conclusions=(
                "The raw trajectory bytes, C0 registration, and E0b Na position/force samples are source-bound.",
                "Density, attractor, temporal, transition-path, and observed-network evidence has not yet been executed.",
            ),
        ),
        metadata={
            **dict(metadata or {}),
            "audit_kind": "real_trajectory_source_bootstrap",
            "source_bootstrap_complete": True,
            "next_execution_boundary": "11E8a-S1 density and attractor pilot gauge",
        },
        policy=audit_policy,
    )
    return NaLta300KSourceBootstrap(
        report=report,
        registration=registration,
        na_samples=na_samples,
        trajectory_path=str(path),
        trajectory_sha256=trajectory_sha256,
    )


__all__ = [
    "PILOT_SOURCE_BOOTSTRAP_STAGE",
    "EXPECTED_NA_LTA_SPECIES_COUNTS",
    "NaLta300KSourceBootstrap",
    "prepare_na_lta_300k_source_bootstrap",
]
