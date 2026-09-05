"""Canonical frame authority without compatibility-domain lineage."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

import numpy as np
from numpy.typing import ArrayLike

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..conditions import (
    TemperatureConditionCatalog,
    TemperatureTargetEvidence,
    build_temperature_condition,
)
from ..eligibility import (
    FrameEligibilityCatalog,
    FrameEligibilityDecision,
    FrameEligibilityPolicy,
    StressRequirement,
    assess_frame_eligibility,
    evaluate_required_label_contract,
)
from ..frame_catalog import FrameData
from ..identity import (
    DuplicateDetectionCatalog,
    FrameIdentity,
    GeometryFingerprintPolicy,
    LabelFingerprintPolicy,
    build_duplicate_detection_catalog,
    frame_uid,
    geometry_fingerprint,
    labeled_configuration_fingerprint,
    source_occurrence_signature,
)
from ..progress_timing import format_progress_fraction
from ..resources import isolated_process_map
from ..strain import (
    FrameStrainRecord,
    ReferenceCellCatalog,
    ReferenceCellPolicy,
    StrainPolicy,
    build_reference_cell_catalog,
    compute_frame_strain,
)
from .identity import (
    CanonicalFrameIdentity,
    canonical_training_label_payload_digest,
)
from .sources import SourceAuthority


def _composition_counts(numbers: np.ndarray) -> dict[str, int]:
    try:
        from ase.data import chemical_symbols  # type: ignore
    except ModuleNotFoundError:
        return {}
    result: dict[str, int] = {}
    for number in numbers:
        symbol = chemical_symbols[int(number)]
        result[symbol] = result.get(symbol, 0) + 1
    return result


def _label_at(array: np.ndarray | None, index: int) -> Any:
    if array is None:
        return None
    value = array[index]
    if np.isscalar(value):
        return float(value)
    return value


def _build_canonical_frame_records_for_run(
    task: tuple[Any, ...],
) -> tuple[str, list[CanonicalFrameRecord], list[FrameEligibilityDecision], list[FrameStrainRecord]]:
    (
        run_id,
        source,
        data,
        temperature_condition,
        reference,
        geometry_active,
        label_active,
        eligibility_active,
        strain_active,
        energy_normalization,
        entropy_convention,
    ) = task

    derivative_digest = (
        source.electronic_structure.derivative_convention.content_digest
    )
    occurrence_signature = source_occurrence_signature(
        run_id=source.run_id,
        source_locator=source.source_locator,
        source_identity_signature=source.source_identity_signature,
    )
    atomic_digest = digest(data.atomic_numbers.tolist())
    assertions = dict(source.assertions)

    canonical_frames: list[CanonicalFrameRecord] = []
    eligibility_decisions: list[FrameEligibilityDecision] = []
    strain_records: list[FrameStrainRecord] = []

    for local_index in range(data.n_frames):
        source_index = int(data.source_frame_indices[local_index])
        uid = frame_uid(occurrence_signature, source_index)
        energy = _label_at(data.energies_ev, local_index)
        forces = _label_at(data.forces_ev_per_angstrom, local_index)
        stress = _label_at(data.stresses_ev_per_angstrom3, local_index)
        cell = np.asarray(data.cells_angstrom[local_index], dtype=np.float64)

        geometry_digest = geometry_fingerprint(
            data.atomic_numbers,
            data.pbc,
            cell,
            data.fractional_positions[local_index],
            policy=geometry_active,
        )

        label_eval = evaluate_required_label_contract(
            atom_count=data.n_atoms,
            energy_ev=energy,
            forces_ev_per_angstrom=forces,
            stress_ev_per_angstrom3=stress,
            policy=eligibility_active,
        )

        if label_eval.is_satisfied:
            canonical_label_digest = canonical_training_label_payload_digest(
                selected_energy_channel=source.selected_energy_channel,
                energy_semantic_role=source.selected_energy_semantic_role,
                energy_units=source.selected_energy_units,
                energy_normalization=energy_normalization,
                entropy_convention=entropy_convention,
                energy_ev=energy,
                forces_ev_per_angstrom=forces,
                stress_ev_per_angstrom3=stress,
                derivative_convention_digest=derivative_digest,
                policy=label_active,
            )
            labeled_geom = labeled_configuration_fingerprint(
                geometry_digest, canonical_label_digest
            )
        else:
            canonical_label_digest = None
            labeled_geom = None

        temperature = _label_at(data.temperatures_kelvin, local_index)
        if temperature is not None and not np.isfinite(float(temperature)):
            temperature = None

        c_record = CanonicalFrameRecord(
            frame_uid=uid,
            run_id=run_id,
            source_identity_signature=source.source_identity_signature,
            source_occurrence_signature=occurrence_signature,
            source_frame_index=source_index,
            source_frame_id=int(data.frame_ids[local_index]),
            step=None if data.steps is None else int(data.steps[local_index]),
            time_ps=(
                None
                if data.times_ps is None
                else float(data.times_ps[local_index])
            ),
            atom_count=data.n_atoms,
            atomic_numbers_digest=atomic_digest,
            pbc=tuple(bool(v) for v in data.pbc),
            cell_matrix_angstrom=tuple(
                tuple(float(v) for v in row) for row in cell
            ),
            cell_volume_angstrom3=float(np.linalg.det(cell)),
            selected_energy_channel=source.selected_energy_channel,
            energy_present=energy is not None,
            forces_present=forces is not None,
            stress_present=stress is not None,
            instantaneous_temperature_kelvin=temperature,
            temperature_condition_digest=temperature_condition.content_digest,
            geometry_fingerprint=geometry_digest,
            canonical_label_payload_digest=canonical_label_digest,
            labeled_configuration_fingerprint=labeled_geom,
            electronic_structure_fingerprint_digest=source.electronic_structure.content_digest,
        )
        canonical_frames.append(c_record)

        decision = assess_frame_eligibility(
            frame_record=c_record,
            atomic_numbers=data.atomic_numbers,
            fractional_positions=data.fractional_positions[local_index],
            cell=cell,
            energy_ev=energy,
            forces_ev_per_angstrom=forces,
            stress_ev_per_angstrom3=stress,
            scf_iteration_limit_reached=data.scf_iteration_limit_reached[
                local_index
            ],
            source_quality_status=source.quality_assessment_status,
            source_quality_outcome=source.quality_outcome,
            policy=eligibility_active,
        )
        eligibility_decisions.append(decision)

        strain_records.append(
            compute_frame_strain(
                frame_uid=uid,
                current_cell_angstrom=cell,
                reference=reference,
                ensemble=source.ensemble,
                assertions=assertions,
                policy=strain_active,
            )
        )

    return run_id, canonical_frames, eligibility_decisions, strain_records


def build_canonical_frame_authority(
    source_authority: SourceAuthority,
    frame_data_by_run: Mapping[str, FrameData],
    *,
    temperature_targets_by_run: Mapping[str, TemperatureTargetEvidence] | None = None,
    explicit_reference_cells_by_group: Mapping[str, ArrayLike] | None = None,
    geometry_policy: GeometryFingerprintPolicy | None = None,
    label_policy: LabelFingerprintPolicy | None = None,
    eligibility_policy: FrameEligibilityPolicy | None = None,
    reference_cell_policy: ReferenceCellPolicy | None = None,
    strain_policy: StrainPolicy | None = None,
    energy_normalization: str = "extensive",
    entropy_convention: str = "electronic_entropy_included",
    parallel_workers: int = 1,
    progress_callback: Callable[[str], None] | None = None,
) -> CanonicalFrameAuthority:
    """Build current-generation CanonicalFrameAuthority from normalized frame arrays."""
    if not isinstance(source_authority, SourceAuthority):
        raise TrainingDataInputError(
            "CanonicalFrameAuthority requires a current-generation SourceAuthority."
        )
    geometry_active = (
        GeometryFingerprintPolicy() if geometry_policy is None else geometry_policy
    )
    label_active = (
        LabelFingerprintPolicy() if label_policy is None else label_policy
    )
    eligibility_active = (
        FrameEligibilityPolicy() if eligibility_policy is None else eligibility_policy
    )
    reference_active = (
        ReferenceCellPolicy() if reference_cell_policy is None else reference_cell_policy
    )
    strain_active = StrainPolicy() if strain_policy is None else strain_policy

    source_map = {item.run_id: item for item in source_authority.sources}
    if set(source_map) != set(frame_data_by_run):
        raise TrainingDataInputError(
            "frame_data_by_run keys must exactly match source-authority run IDs."
        )
    targets = {} if temperature_targets_by_run is None else dict(temperature_targets_by_run)

    for run_id, source in source_map.items():
        data = frame_data_by_run[run_id]
        if data.n_frames != source.frame_count:
            raise TrainingDataInputError(
                f"Frame count mismatch for {run_id!r}: {data.n_frames} != {source.frame_count}."
            )
        if data.n_atoms != source.composition.atom_count:
            raise TrainingDataInputError(
                f"Atom count mismatch for {run_id!r}: {data.n_atoms} != {source.composition.atom_count}."
            )
        counts = _composition_counts(data.atomic_numbers)
        if counts and counts != source.composition.as_dict():
            raise TrainingDataInputError(f"Composition mismatch for {run_id!r}.")
        if np.any(data.source_frame_indices >= source.frame_count):
            raise TrainingDataInputError(
                f"Source-frame index exceeds source count for {run_id!r}."
            )

    temperature_records = []
    for run_id, source in source_map.items():
        data = frame_data_by_run[run_id]
        target = targets.get(run_id, TemperatureTargetEvidence())
        temperature_records.append(
            build_temperature_condition(
                run_id=run_id,
                source_identity_signature=source.source_identity_signature,
                ensemble=source.ensemble,
                instantaneous_temperatures_kelvin=data.temperatures_kelvin,
                target_start_kelvin=target.target_start_kelvin,
                target_end_kelvin=target.target_end_kelvin,
                target_evidence=target.evidence,
            )
        )
    temperature_catalog = TemperatureConditionCatalog(tuple(temperature_records))

    reference_catalog = build_reference_cell_catalog(
        source_authority.sources,
        cells_by_run={
            run_id: data.cells_angstrom for run_id, data in frame_data_by_run.items()
        },
        explicit_cells_by_group=explicit_reference_cells_by_group,
        policy=reference_active,
    )

    ordered_run_ids = sorted(source_map)
    tasks: list[tuple[Any, ...]] = []
    for run_id in ordered_run_ids:
        source = source_map[run_id]
        data = frame_data_by_run[run_id]
        temperature_condition = temperature_catalog.for_run(run_id)
        resolution = reference_catalog.resolution_for_run(run_id)
        reference = (
            None
            if resolution.reference_cell_id is None
            else reference_catalog.record(resolution.reference_cell_id)
        )
        tasks.append((
            run_id,
            source,
            data,
            temperature_condition,
            reference,
            geometry_active,
            label_active,
            eligibility_active,
            strain_active,
            energy_normalization,
            entropy_convention,
        ))

    workers = max(1, min(int(parallel_workers), len(tasks))) if tasks else 1
    completed = 0
    canonical_frames: list[CanonicalFrameRecord] = []
    eligibility_decisions: list[FrameEligibilityDecision] = []
    strain_records: list[FrameStrainRecord] = []

    if workers == 1:
        results = map(_build_canonical_frame_records_for_run, tasks)
        for run_id, run_records, run_decisions, run_strains in results:
            canonical_frames.extend(run_records)
            eligibility_decisions.extend(run_decisions)
            strain_records.extend(run_strains)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"canonical frames; status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; "
                    f"item={run_id}; frames={len(run_records):,}; workers=1"
                )
    else:
        for result in isolated_process_map(
            __name__, "_build_canonical_frame_records_for_run", tasks, workers=workers
        ):
            run_id, run_records, run_decisions, run_strains = result
            canonical_frames.extend(run_records)
            eligibility_decisions.extend(run_decisions)
            strain_records.extend(run_strains)
            completed += 1
            if progress_callback is not None:
                progress_callback(
                    f"canonical frames; status=item-complete; progress={format_progress_fraction(completed, len(tasks))}; "
                    f"item={run_id}; frames={len(run_records):,}; workers={workers}"
                )

    duplicates = build_duplicate_detection_catalog(
        canonical_frames,
        source_frame_counts={s.run_id: s.frame_count for s in source_authority.sources},
    )

    return CanonicalFrameAuthority(
        dataset_id=source_authority.dataset_id,
        source_authority_digest=source_authority.content_digest,
        geometry_policy_digest=geometry_active.policy_digest,
        label_policy_digest=label_active.policy_digest,
        eligibility_policy_digest=eligibility_active.policy_digest,
        reference_cell_catalog=reference_catalog,
        temperature_conditions=temperature_catalog,
        frames=tuple(canonical_frames),
        eligibility=FrameEligibilityCatalog(
            policy_digest=eligibility_active.policy_digest,
            decisions=tuple(eligibility_decisions),
        ),
        strain_records=tuple(strain_records),
        duplicates=duplicates,
        notes=(
            "Canonical frame authority built from normalized frame arrays and source authority.",
        ),
    )


def _control_value(run_controls: Any, name: str) -> Any:
    value = run_controls.effective_value(name)
    return run_controls.explicit_value(name) if value is None else value


@dataclass(frozen=True, slots=True)
class AuthenticatedVaspSource:
    """One freshly authenticated P1 VASP source, without any frame payload.

    Authentication and normalized frame-payload acquisition are two different
    operations.  Every consumer that needs the eight P1 source/control/
    ensemble/energy facts re-established against the real files obtains them
    here; how the normalized arrays themselves are acquired (a direct
    ``vasprun.xml`` read or the authenticated normalized frame cache) is a
    separate decision that this record deliberately does not make.
    """

    run_id: str
    source_path: Path
    companion_paths: Mapping[str, Path]
    controls: Any
    energy_channel: Any
    temperature_target: TemperatureTargetEvidence


def _resolved_source_paths(source: Any, base: Path) -> tuple[Path, dict[str, Path]]:
    """Resolve one P1 source locator and its companions against ``base``."""

    path = Path(source.source_locator)
    if not path.is_absolute():
        path = base / path
    companion_paths = {
        role: (base / locator if not Path(locator).is_absolute() else Path(locator))
        for role, locator in source.companion_files
    }
    return path, companion_paths


def changed_vasp_source_identities(
    source_authority: SourceAuthority,
    *,
    base_directory: str | Path = ".",
) -> tuple[str, ...]:
    """Run IDs whose live source/companion bytes no longer match P1 record.

    This answers one question and decides nothing: *are the inputs this
    campaign was prepared from still the inputs on disk?*  It reads exactly
    the identity facts :func:`authenticate_vasp_source_authority` proves, and
    compares only the two byte-level signatures -- source identity and control
    interpretation -- so a source whose bytes are unchanged can never be
    reported as changed.

    A source that cannot be read at all is *not* reported here.  "Unreadable"
    is not "changed": it is a failure that belongs to full authentication,
    which produces the accurate message.
    """

    from mdstats.io import read_vasp_run_controls

    base = Path(base_directory)
    changed: list[str] = []
    for source in source_authority.sources:
        path, companion_paths = _resolved_source_paths(source, base)
        try:
            bundle = read_vasp_run_controls(path, companion_files=companion_paths)
        except Exception:  # noqa: BLE001 - the authenticator owns this diagnosis
            continue
        if (
            bundle.source_identity.signature != source.source_identity_signature
            or bundle.signature != source.source_control_digest
        ):
            changed.append(str(source.run_id))
    return tuple(sorted(changed))


def authenticate_vasp_source_authority(
    source_authority: SourceAuthority,
    *,
    base_directory: str | Path = ".",
) -> dict[str, AuthenticatedVaspSource]:
    """Re-establish the eight P1 source facts against the actual VASP files.

    This is the single implementation of fresh P1 authentication.  It reads
    only the source/control metadata required to prove identity, control
    interpretation, companion bindings, the ensemble certificate and its
    reconstructed value, and the selected energy channel name/units/semantic
    role.  It never reads the frame payload, and it never accepts cache
    metadata, a timestamp, or a previously validated object in place of a
    check.
    """

    from mdstats.io import read_vasp_run_controls
    from mdstats.io.vasp_ensemble import certify_vasp_simulation_controls

    base = Path(base_directory)
    authenticated: dict[str, AuthenticatedVaspSource] = {}
    for source in source_authority.sources:
        path, companion_paths = _resolved_source_paths(source, base)
        bundle = read_vasp_run_controls(path, companion_files=companion_paths)
        if bundle.source_identity.signature != source.source_identity_signature:
            raise TrainingDataInputError(
                f"Source identity changed for {source.run_id!r}."
            )
        if bundle.signature != source.source_control_digest:
            raise TrainingDataInputError(
                f"Source control interpretation mismatch for {source.run_id!r}."
            )
        certificate = certify_vasp_simulation_controls(bundle, companion_files=companion_paths)
        if certificate.signature != source.ensemble_certificate_digest:
            raise TrainingDataInputError(
                f"Ensemble certificate interpretation mismatch for {source.run_id!r}."
            )
        if certificate.ensemble.value != source.ensemble:
            raise TrainingDataInputError(
                f"Ensemble interpretation mismatch for {source.run_id!r}: "
                f"reparsed={certificate.ensemble.value!r} != persisted={source.ensemble!r}"
            )
        channel = bundle.energy_catalog.channel(source.selected_energy_channel)
        if channel is None:
            raise TrainingDataInputError(
                f"Selected energy channel {source.selected_energy_channel!r} is absent for {source.run_id!r}."
            )
        if channel.source_name != source.selected_energy_channel:
            raise TrainingDataInputError(
                f"Selected energy channel source_name mismatch for {source.run_id!r}: "
                f"reparsed={channel.source_name!r} != persisted={source.selected_energy_channel!r}"
            )
        if channel.units != source.selected_energy_units:
            raise TrainingDataInputError(
                f"Selected energy channel units mismatch for {source.run_id!r}: "
                f"reparsed={channel.units!r} != persisted={source.selected_energy_units!r}"
            )
        if channel.semantic_role != source.selected_energy_semantic_role:
            raise TrainingDataInputError(
                f"Selected energy channel semantic_role mismatch for {source.run_id!r}: "
                f"reparsed={channel.semantic_role!r} != persisted={source.selected_energy_semantic_role!r}"
            )
        tebeg = _control_value(bundle.run_controls, "TEBEG")
        teend = _control_value(bundle.run_controls, "TEEND")
        authenticated[source.run_id] = AuthenticatedVaspSource(
            run_id=source.run_id,
            source_path=path,
            companion_paths=dict(companion_paths),
            controls=bundle,
            energy_channel=channel,
            temperature_target=TemperatureTargetEvidence(
                target_start_kelvin=None if tebeg is None else float(tebeg),
                target_end_kelvin=None if teend is None else float(teend),
                evidence="VASP effective/explicit TEBEG and TEEND",
            ),
        )
    return authenticated


def authenticated_vasp_temperature_targets(
    authenticated: Mapping[str, AuthenticatedVaspSource],
) -> dict[str, TemperatureTargetEvidence]:
    """Project the temperature-target evidence canonical construction needs."""

    return {
        run_id: record.temperature_target
        for run_id, record in authenticated.items()
    }


def read_authenticated_vasp_frame_data(
    authenticated: Mapping[str, AuthenticatedVaspSource],
    *,
    strict: bool = True,
) -> dict[str, FrameData]:
    """Read the normalized frame payload of already authenticated sources."""

    from mdstats.io import read_vasp_frames

    frame_data: dict[str, FrameData] = {}
    for run_id, record in authenticated.items():
        collection = read_vasp_frames(
            record.source_path,
            strict=strict,
            assess_quality=False,
            assess_stationarity=False,
            assess_admissibility=False,
        )
        frame_data[run_id] = FrameData.from_collection(
            collection,
            source_frame_indices=np.arange(collection.n_frames, dtype=np.int64),
            energies_ev=record.energy_channel.as_array(),
            scf_iteration_limit_reached=(
                record.controls.numerical_quality_controls.scf_iteration_limit_reached
            ),
        )
    return frame_data


def build_vasp_canonical_frame_authority(
    source_authority: SourceAuthority,
    *,
    base_directory: str | Path = ".",
    strict: bool = True,
    **kwargs: Any,
) -> CanonicalFrameAuthority:
    """Build CanonicalFrameAuthority directly from VASP sources bound by SourceAuthority.

    This composes the same three owners the current runtime composes -- fresh
    P1 authentication, normalized frame acquisition, and canonical-frame
    construction -- and differs only in acquiring the payload straight from the
    sources instead of from the authenticated normalized frame cache.
    """

    if "temperature_targets_by_run" in kwargs:
        raise TrainingDataInputError(
            "build_vasp_canonical_frame_authority derives temperature targets from VASP controls."
        )
    authenticated = authenticate_vasp_source_authority(
        source_authority, base_directory=base_directory
    )
    frame_data = read_authenticated_vasp_frame_data(authenticated, strict=strict)
    return build_canonical_frame_authority(
        source_authority,
        frame_data,
        temperature_targets_by_run=authenticated_vasp_temperature_targets(
            authenticated
        ),
        **kwargs,
    )


CANONICAL_FRAME_RECORD_SCHEMA = "mdstats.canonical-frame-record.v1"
CANONICAL_FRAME_AUTHORITY_SCHEMA = "mdstats.canonical-frame-authority.v1"


@dataclass(frozen=True, slots=True)
class CanonicalFrameRecord:
    frame_uid: str
    run_id: str
    source_identity_signature: str
    source_occurrence_signature: str
    source_frame_index: int
    source_frame_id: int
    step: int | None
    time_ps: float | None
    atom_count: int
    atomic_numbers_digest: str
    pbc: tuple[bool, bool, bool]
    cell_matrix_angstrom: tuple[tuple[float, float, float], ...]
    cell_volume_angstrom3: float
    selected_energy_channel: str
    energy_present: bool
    forces_present: bool
    stress_present: bool
    instantaneous_temperature_kelvin: float | None
    temperature_condition_digest: str
    geometry_fingerprint: str
    canonical_label_payload_digest: str | None = None
    labeled_configuration_fingerprint: str | None = None
    electronic_structure_fingerprint_digest: str = ""
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        for name in (
            "frame_uid",
            "source_identity_signature",
            "source_occurrence_signature",
            "atomic_numbers_digest",
            "temperature_condition_digest",
            "geometry_fingerprint",
            "electronic_structure_fingerprint_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in (
            "canonical_label_payload_digest",
            "labeled_configuration_fingerprint",
        ):
            val = getattr(self, name)
            if val is not None:
                object.__setattr__(self, name, validate_digest(val, name=name))
        if (self.canonical_label_payload_digest is None) != (self.labeled_configuration_fingerprint is None):
            raise TrainingDataInputError(
                "canonical_label_payload_digest and labeled_configuration_fingerprint must be either both present or both None."
            )
        if self.canonical_label_payload_digest is not None:
            expected_fingerprint = labeled_configuration_fingerprint(
                self.geometry_fingerprint, self.canonical_label_payload_digest
            )
            if self.labeled_configuration_fingerprint != expected_fingerprint:
                raise TrainingDataInputError(
                    f"labeled_configuration_fingerprint mismatch: expected {expected_fingerprint}, got {self.labeled_configuration_fingerprint}"
                )
        if self.source_frame_index < 0 or self.atom_count <= 0:
            raise TrainingDataInputError("Frame indices and atom count are invalid.")
        if not self.run_id.strip() or not self.selected_energy_channel.strip():
            raise TrainingDataInputError("Frame record identifiers must be non-empty.")
        cell = np.asarray(self.cell_matrix_angstrom, dtype=np.float64)
        if cell.shape != (3, 3) or np.any(~np.isfinite(cell)):
            raise TrainingDataInputError("Frame cell must be a finite 3 x 3 matrix.")
        volume = float(np.linalg.det(cell))
        if not np.isclose(volume, self.cell_volume_angstrom3, rtol=1e-12, atol=1e-12):
            raise TrainingDataInputError("Frame cell volume is inconsistent.")
        object.__setattr__(self, "cell_volume_angstrom3", volume)
        if self.time_ps is not None and not np.isfinite(float(self.time_ps)):
            raise TrainingDataInputError("Frame time must be finite when present.")
        if self.instantaneous_temperature_kelvin is not None:
            value = float(self.instantaneous_temperature_kelvin)
            if not np.isfinite(value) or value < 0.0:
                raise TrainingDataInputError(
                    "Instantaneous temperature must be finite and nonnegative."
                )
            object.__setattr__(self, "instantaneous_temperature_kelvin", value)

    @property
    def has_authoritative_label(self) -> bool:
        return self.canonical_label_payload_digest is not None

    @property
    def label_payload_digest(self) -> str | None:
        return self.canonical_label_payload_digest

    @property
    def identity(self) -> CanonicalFrameIdentity:
        return CanonicalFrameIdentity(
            frame_uid=self.frame_uid,
            run_id=self.run_id,
            source_frame_index=self.source_frame_index,
            geometry_fingerprint=self.geometry_fingerprint,
            canonical_label_payload_digest=self.canonical_label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
            electronic_structure_fingerprint_digest=self.electronic_structure_fingerprint_digest,
        )

    def as_duplicate_frame_identity(self) -> FrameIdentity:
        if self.canonical_label_payload_digest is None or self.labeled_configuration_fingerprint is None:
            raise TrainingDataInputError("Cannot construct FrameIdentity without authoritative label identity.")
        return FrameIdentity(
            frame_uid=self.frame_uid,
            geometry_fingerprint=self.geometry_fingerprint,
            label_payload_digest=self.canonical_label_payload_digest,
            labeled_configuration_fingerprint=self.labeled_configuration_fingerprint,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CANONICAL_FRAME_RECORD_SCHEMA,
            "frame_uid": self.frame_uid,
            "run_id": self.run_id,
            "source_identity_signature": self.source_identity_signature,
            "source_occurrence_signature": self.source_occurrence_signature,
            "source_frame_index": self.source_frame_index,
            "source_frame_id": self.source_frame_id,
            "step": self.step,
            "time_ps": self.time_ps,
            "atom_count": self.atom_count,
            "atomic_numbers_digest": self.atomic_numbers_digest,
            "pbc": list(self.pbc),
            "cell_matrix_angstrom": [list(row) for row in self.cell_matrix_angstrom],
            "cell_volume_angstrom3": self.cell_volume_angstrom3,
            "selected_energy_channel": self.selected_energy_channel,
            "energy_present": self.energy_present,
            "forces_present": self.forces_present,
            "stress_present": self.stress_present,
            "instantaneous_temperature_kelvin": self.instantaneous_temperature_kelvin,
            "temperature_condition_digest": self.temperature_condition_digest,
            "geometry_fingerprint": self.geometry_fingerprint,
            "canonical_label_payload_digest": self.canonical_label_payload_digest,
            "labeled_configuration_fingerprint": self.labeled_configuration_fingerprint,
            "electronic_structure_fingerprint_digest": self.electronic_structure_fingerprint_digest,
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
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalFrameRecord":
        if payload.get("schema") != CANONICAL_FRAME_RECORD_SCHEMA:
            raise TrainingDataSerializationError("Unsupported canonical-frame-record schema.")
        label_digest = (
            None
            if payload.get("canonical_label_payload_digest") is None
            else str(payload["canonical_label_payload_digest"])
        )
        labeled_fingerprint = (
            None
            if payload.get("labeled_configuration_fingerprint") is None
            else str(payload["labeled_configuration_fingerprint"])
        )
        geom_fingerprint = str(payload["geometry_fingerprint"])
        if (label_digest is None) != (labeled_fingerprint is None):
            raise TrainingDataSerializationError(
                "canonical_label_payload_digest and labeled_configuration_fingerprint must be either both present or both None."
            )
        if label_digest is not None:
            expected = labeled_configuration_fingerprint(geom_fingerprint, label_digest)
            if labeled_fingerprint != expected:
                raise TrainingDataSerializationError(
                    f"labeled_configuration_fingerprint mismatch: expected {expected}, got {labeled_fingerprint}"
                )

        result = cls(
            frame_uid=str(payload["frame_uid"]),
            run_id=str(payload["run_id"]),
            source_identity_signature=str(payload["source_identity_signature"]),
            source_occurrence_signature=str(payload["source_occurrence_signature"]),
            source_frame_index=int(payload["source_frame_index"]),
            source_frame_id=int(payload["source_frame_id"]),
            step=None if payload.get("step") is None else int(payload["step"]),
            time_ps=None if payload.get("time_ps") is None else float(payload["time_ps"]),
            atom_count=int(payload["atom_count"]),
            atomic_numbers_digest=str(payload["atomic_numbers_digest"]),
            pbc=tuple(bool(v) for v in payload["pbc"]),
            cell_matrix_angstrom=tuple(
                tuple(float(v) for v in row) for row in payload["cell_matrix_angstrom"]
            ),
            cell_volume_angstrom3=float(payload["cell_volume_angstrom3"]),
            selected_energy_channel=str(payload["selected_energy_channel"]),
            energy_present=bool(payload["energy_present"]),
            forces_present=bool(payload["forces_present"]),
            stress_present=bool(payload["stress_present"]),
            instantaneous_temperature_kelvin=(
                None
                if payload.get("instantaneous_temperature_kelvin") is None
                else float(payload["instantaneous_temperature_kelvin"])
            ),
            temperature_condition_digest=str(payload["temperature_condition_digest"]),
            geometry_fingerprint=geom_fingerprint,
            canonical_label_payload_digest=label_digest,
            labeled_configuration_fingerprint=labeled_fingerprint,
            electronic_structure_fingerprint_digest=str(
                payload["electronic_structure_fingerprint_digest"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Canonical-frame-record digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CanonicalFrameAuthority:
    dataset_id: str
    source_authority_digest: str
    geometry_policy_digest: str
    label_policy_digest: str
    eligibility_policy_digest: str
    reference_cell_catalog: ReferenceCellCatalog
    temperature_conditions: TemperatureConditionCatalog
    frames: tuple[CanonicalFrameRecord, ...]
    eligibility: FrameEligibilityCatalog
    strain_records: tuple[FrameStrainRecord, ...]
    duplicates: DuplicateDetectionCatalog
    notes: tuple[str, ...] = ()
    _content_digest_cache: str | None = field(default=None, init=False, repr=False, compare=False)
    _by_frame_uid: dict[str, CanonicalFrameRecord] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )
    _by_run_id: dict[str, tuple[CanonicalFrameRecord, ...]] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in (
            "source_authority_digest",
            "geometry_policy_digest",
            "label_policy_digest",
            "eligibility_policy_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        frames = tuple(sorted(self.frames, key=lambda item: (item.run_id, item.source_frame_index)))
        if len({item.frame_uid for item in frames}) != len(frames):
            raise TrainingDataInputError("Duplicate frame UIDs in canonical frame authority.")
        strain = tuple(sorted(self.strain_records, key=lambda item: item.frame_uid))
        known = {item.frame_uid for item in frames}
        if {item.frame_uid for item in self.eligibility.decisions} != known:
            raise TrainingDataInputError("Eligibility decisions do not cover every frame exactly.")
        if {item.frame_uid for item in strain} != known:
            raise TrainingDataInputError("Strain records do not cover every frame exactly.")
        object.__setattr__(self, "frames", frames)
        object.__setattr__(self, "strain_records", strain)
        object.__setattr__(self, "notes", tuple(str(v) for v in self.notes))
        object.__setattr__(self, "_by_frame_uid", {item.frame_uid: item for item in frames})
        by_run: dict[str, list[CanonicalFrameRecord]] = {}
        for item in frames:
            by_run.setdefault(item.run_id, []).append(item)
        object.__setattr__(self, "_by_run_id", {k: tuple(v) for k, v in by_run.items()})

    def frame(self, frame_uid: str) -> CanonicalFrameRecord:
        try:
            return self._by_frame_uid[frame_uid]
        except KeyError:
            raise KeyError(frame_uid) from None

    def frames_for_run(self, run_id: str) -> tuple[CanonicalFrameRecord, ...]:
        return self._by_run_id.get(run_id, ())

    @property
    def source_catalog_digest(self) -> str:
        return self.source_authority_digest

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CANONICAL_FRAME_AUTHORITY_SCHEMA,
            "dataset_id": self.dataset_id,
            "source_authority_digest": self.source_authority_digest,
            "geometry_policy_digest": self.geometry_policy_digest,
            "label_policy_digest": self.label_policy_digest,
            "eligibility_policy_digest": self.eligibility_policy_digest,
            "reference_cell_catalog": self.reference_cell_catalog.to_dict(),
            "temperature_conditions": self.temperature_conditions.to_dict(),
            "frames": [item.to_dict() for item in self.frames],
            "eligibility": self.eligibility.to_dict(),
            "strain_records": [item.to_dict() for item in self.strain_records],
            "duplicates": self.duplicates.to_dict(),
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
        return {**payload, "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CanonicalFrameAuthority":
        if payload.get("schema") != CANONICAL_FRAME_AUTHORITY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported canonical-frame-authority schema.")
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            source_authority_digest=str(payload["source_authority_digest"]),
            geometry_policy_digest=str(payload["geometry_policy_digest"]),
            label_policy_digest=str(payload["label_policy_digest"]),
            eligibility_policy_digest=str(payload["eligibility_policy_digest"]),
            reference_cell_catalog=ReferenceCellCatalog.from_dict(
                payload["reference_cell_catalog"]
            ),
            temperature_conditions=TemperatureConditionCatalog.from_dict(
                payload["temperature_conditions"]
            ),
            frames=tuple(CanonicalFrameRecord.from_dict(item) for item in payload.get("frames", ())),
            eligibility=FrameEligibilityCatalog.from_dict(payload["eligibility"]),
            strain_records=tuple(
                FrameStrainRecord.from_dict(item) for item in payload.get("strain_records", ())
            ),
            duplicates=DuplicateDetectionCatalog.from_dict(payload["duplicates"]),
            notes=tuple(str(v) for v in payload.get("notes", ())),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Canonical-frame-authority digest mismatch.")
        return result
