"""Deployment parity: does the deployed artifact still compute the frozen model?

Static evaluation accuracy says nothing about whether target-head extraction,
dtype conversion, serialization, and ML-IAP/LAMMPS execution preserve the frozen
model's energies and forces.  This component qualifies exactly that path, on a
deterministic bounded development cohort - the claim is representation and
runtime equivalence, not independent generalization, so a development cohort is
the scientifically correct probe and an independent role would be wasted here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np

from .._common import TrainingDataInputError, digest
from .components import (
    COMPONENT_DEPLOYMENT_PARITY,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .errors import (
    QualificationError,
    QualificationLineageError,
    QualificationUnavailableError,
)
from .geometry import atoms_for_frame
from .providers import energy_of, forces_of, member_provider, predict_all, stress_of
from .publication import PublishedProductionMember, checkpoint_path_for_member
from .runtime_capability import deployed_static_evaluation


def probe_cohort(context: Any, *, count: int) -> tuple[str, ...]:
    """A deterministic bounded M3 development cohort, frozen before prediction."""

    from ..post_selection_production import frozen_m3_development_evidence

    _size, membership, _digest = frozen_m3_development_evidence(context.selected)
    if not membership:
        raise QualificationError(
            "The frozen M3 development reserve is empty, so no deterministic "
            "deployment-parity probe cohort exists."
        )
    wanted = max(1, min(int(count), len(membership)))
    stride = len(membership) / wanted
    indices = sorted({min(len(membership) - 1, int(index * stride)) for index in range(wanted)})
    return tuple(membership[index] for index in indices)


def default_deployment_exporter(
    source_model_path: Path, output_directory: Path, *, deployment_dtype: str, target_head: str | None
) -> Any:
    """Export through the real mdstats MACE deployment owner."""

    from ..mace_deployment import (
        MaceDeploymentExportPolicy,
        export_mace_deployment_artifact,
    )

    policy = MaceDeploymentExportPolicy(
        deployment_dtype=deployment_dtype, require_inference_probe=False
    )
    if target_head is None or not str(target_head).strip():
        raise QualificationError(
            "Deployment export requires the canonical published target head."
        )
    try:
        return export_mace_deployment_artifact(
            source_model_path,
            output_directory,
            deployment_dtype=deployment_dtype,
            target_head=str(target_head),
            policy=policy,
            overwrite=True,
        )
    except TrainingDataInputError as exc:
        # A bounded fixture or a target environment without a valid MACE
        # production artifact cannot establish the real product path.  Keep
        # that operational/product-runtime absence distinct from a scientific
        # rejection; the parent reports it as unavailable/blocking.
        raise QualificationUnavailableError(
            "The real MACE deployment exporter is unavailable/blocking and could not construct the "
            f"authenticated product artifact: {exc}"
        ) from exc


def default_mliap_artifact_builder(deployment_path: Path, output_path: Path, *, head: str | None) -> Path:
    """Build the exact ML-IAP artifact LAMMPS will execute, through MACE.

    The head is mandatory for a multihead-capable product: MACE would otherwise
    select a head interactively or fall back to the last one, and the deployed
    artifact would silently be a different product from the published member.
    """

    try:
        import torch
        from mace.calculators.lammps_mliap_mace import LAMMPS_MLIAP_MACE
    except Exception as exc:  # noqa: BLE001 - absence is unavailability, not failure
        raise QualificationUnavailableError(
            "The supported MACE ML-IAP export path is unavailable in this "
            f"environment: {exc}"
        ) from exc
    if head is None or not str(head).strip():
        raise QualificationError(
            "The ML-IAP builder requires the canonical published target head; "
            "building without one cannot prove product identity."
        )
    model = torch.load(deployment_path, map_location="cpu", weights_only=False)
    model = model.double().to("cpu")
    model.lammps_mliap = True
    available = tuple(str(v) for v in getattr(model, "heads", ()) or ())
    if not available or str(head) not in available:
        raise QualificationLineageError(
            f"The published target head {head!r} is not authenticated by the deployed "
            f"model, whose declared heads are {list(available)}."
        )
    lammps_model = LAMMPS_MLIAP_MACE(model, head=str(head))
    selected_head = getattr(getattr(lammps_model, "model", None), "head", None)
    if selected_head is None:
        raise QualificationLineageError(
            "The MACE ML-IAP builder did not expose an authenticated selected head."
        )
    try:
        selected_head_value = int(np.asarray(selected_head).reshape(-1)[0])
    except Exception as exc:  # noqa: BLE001 - builder output is unauthenticated
        raise QualificationLineageError(
            "The MACE ML-IAP builder returned an invalid selected-head marker."
        ) from exc
    if selected_head_value != 1:
        raise QualificationLineageError(
            "The ML-IAP artifact does not bind the canonical target head at index 1."
        )
    torch.save(lammps_model, output_path)
    return output_path


@dataclass(frozen=True, slots=True)
class DeployedEvaluation:
    energies_ev: tuple[float, ...]
    forces_ev_per_angstrom: tuple[np.ndarray, ...]
    artifact_sha256: str
    runtime_identity: str
    stresses_ev_per_angstrom3: tuple[np.ndarray | None, ...] = ()
    # These are observations from the deployed runtime, not copies of the
    # request.  The real runtime owner fills them from its post-build box;
    # bounded evaluators may omit them only for legacy in-process fixtures.
    cells_angstrom: tuple[np.ndarray, ...] = ()
    pbc: tuple[tuple[bool, bool, bool], ...] = ()
    runtime_evidence: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "energies_ev",
            tuple(float(value) for value in self.energies_ev),
        )
        object.__setattr__(
            self,
            "forces_ev_per_angstrom",
            tuple(np.asarray(value, dtype=np.float64) for value in self.forces_ev_per_angstrom),
        )
        object.__setattr__(
            self,
            "stresses_ev_per_angstrom3",
            tuple(
                None if value is None else np.asarray(value, dtype=np.float64)
                for value in self.stresses_ev_per_angstrom3
            ),
        )
        object.__setattr__(
            self,
            "cells_angstrom",
            tuple(np.asarray(value, dtype=np.float64) for value in self.cells_angstrom),
        )
        normalized_pbc: list[tuple[bool, bool, bool]] = []
        for value in self.pbc:
            if (
                not isinstance(value, (list, tuple))
                or len(value) != 3
                or any(type(axis) is not bool for axis in value)
            ):
                raise QualificationLineageError(
                    "Deployed evaluation PBC observations must be exact three-axis "
                    "boolean vectors."
                )
            normalized_pbc.append(tuple(value))
        object.__setattr__(self, "pbc", tuple(normalized_pbc))
        if any(not isinstance(value, Mapping) for value in self.runtime_evidence):
            raise QualificationLineageError(
                "Deployed evaluation runtime evidence must be a mapping per probe."
            )
        evidence = tuple(dict(value) for value in self.runtime_evidence)
        object.__setattr__(self, "runtime_evidence", evidence)


def qualify_deployment_parity(session: Any) -> QualificationComponentEvidence:
    """Compare every frozen member's in-framework and deployed predictions."""

    binding = session.binding
    policy = binding.specification.component_policy(COMPONENT_DEPLOYMENT_PARITY)
    cohort = probe_cohort(session.context, count=int(policy["probe_configuration_count"]))
    cohort_digest = digest({"deployment_probe_cohort": list(cohort)})
    atoms_list = [atoms_for_frame(session.context, uid) for uid in cohort]
    probe_geometry_digest = digest(
        {
            "schema": "mdstats.qualification-deployment-stress-cohort.v1",
            "frame_uids": list(cohort),
            "geometries": [
                {
                    "numbers": [int(value) for value in atoms.get_atomic_numbers()],
                    "cell": np.asarray(atoms.get_cell(), dtype=np.float64).tolist(),
                    "pbc": [bool(value) for value in atoms.get_pbc()],
                    "positions": np.asarray(
                        atoms.get_positions(), dtype=np.float64
                    ).tolist(),
                }
                for atoms in atoms_list
            ],
        }
    )

    member_results: list[dict[str, Any]] = []
    failures: list[str] = []
    for member in session.publication.members:
        capability = session.stress_capability(
            atoms_list,
            probe=cohort,
            member=member,
            component=COMPONENT_DEPLOYMENT_PARITY,
            claim_kind="deployment",
            geometry_or_cohort_digest=probe_geometry_digest,
        )
        stress_required = capability.required
        stress_applicable = capability.applicable
        with member_provider(session.context, member) as provider:
            predictions = predict_all(session.context, provider, atoms_list)
        reference_energies = np.asarray([energy_of(item) for item in predictions], dtype=np.float64)
        reference_forces = [forces_of(item) for item in predictions]
        reference_stresses = [stress_of(item) for item in predictions]

        deployed = session.evaluate_deployed(
            member, atoms_list, stress_capability=capability
        )
        deployed_energies = np.asarray(deployed.energies_ev, dtype=np.float64)
        atom_counts = np.asarray([len(atoms) for atoms in atoms_list], dtype=np.float64)
        if deployed_energies.shape != reference_energies.shape or not np.all(
            np.isfinite(deployed_energies)
        ):
            raise QualificationError(
                "The deployed runtime returned a nonfinite or incomplete energy vector."
            )
        if len(deployed.forces_ev_per_angstrom) != len(reference_forces) or any(
            force.shape != expected.shape or not np.all(np.isfinite(force))
            for force, expected in zip(deployed.forces_ev_per_angstrom, reference_forces)
        ):
            raise QualificationError(
                "The deployed runtime returned nonfinite or incomplete forces."
            )
        energy_error = np.max(np.abs(deployed_energies - reference_energies) / atom_counts)
        force_error = 0.0
        for expected, observed in zip(reference_forces, deployed.forces_ev_per_angstrom):
            if observed.shape != expected.shape:
                raise QualificationError(
                    "The deployed runtime returned forces with a different shape than "
                    "the authenticated in-framework model."
                )
            tolerance = float(policy["force_atol_ev_per_angstrom"]) + float(
                policy["force_rtol"]
            ) * np.abs(expected)
            force_error = max(
                force_error, float(np.max(np.abs(observed - expected) - tolerance))
            )
        deployed_stresses = list(deployed.stresses_ev_per_angstrom3)
        if not deployed_stresses:
            deployed_stresses = [None] * len(atoms_list)
        if len(deployed_stresses) != len(atoms_list):
            raise QualificationError(
                "The deployed runtime returned a different number of stress tensors "
                "than probed configurations."
            )
        runtime_evidence = list(deployed.runtime_evidence)
        if runtime_evidence and len(runtime_evidence) != len(atoms_list):
            raise QualificationLineageError(
                "The deployed runtime returned an incomplete runtime-evidence vector."
            )
        stress_error: float | None = 0.0
        missing_stress = 0
        unavailable_stress = 0
        compared_stress = 0
        runtime_stress_unavailable = bool(
            stress_applicable and not capability.runtime_reports_stress
        )
        for stress_index, (expected, observed) in enumerate(
            zip(reference_stresses, deployed_stresses, strict=True)
        ):
            geometry_stress_applicable = capability.geometry_is_applicable(stress_index)
            if not geometry_stress_applicable:
                continue
            if runtime_stress_unavailable:
                unavailable_stress += 1
                missing_stress += 1
                continue
            if expected is None or observed is None:
                unavailable_stress += 1
                missing_stress += 1
                continue
            expected_tensor = np.asarray(expected, dtype=np.float64)
            observed_tensor = np.asarray(observed, dtype=np.float64)
            if (
                expected_tensor.shape != (3, 3)
                or observed_tensor.shape != (3, 3)
                or not np.all(np.isfinite(expected_tensor))
                or not np.all(np.isfinite(observed_tensor))
            ):
                raise QualificationError(
                    "The deployed runtime returned a stress tensor with an invalid "
                    "shape or nonfinite value."
                )
            compared_stress += 1
            tolerance = float(policy["stress_atol_ev_per_angstrom3"]) + float(
                policy["stress_rtol"]
            ) * np.abs(expected_tensor)
            if stress_error is not None:
                stress_error = max(
                    stress_error,
                    float(np.max(np.abs(observed_tensor - expected_tensor) - tolerance)),
                )
        if stress_applicable and missing_stress:
            # ``inf`` would be a non-JSON scientific placeholder. Missing
            # evidence is represented explicitly by the count/status fields;
            # the hard pass predicate remains false.
            stress_error = None
        stress_ok = bool(
            not stress_applicable
            or (stress_error is not None and stress_error <= 0.0)
        )
        energy_ok = float(energy_error) <= float(policy["energy_atol_ev_per_atom"])
        force_ok = force_error <= 0.0
        passed = bool(energy_ok and force_ok and (stress_ok or not stress_applicable))
        if stress_applicable and missing_stress:
            passed = False
        _validate_observed_geometry(
            deployed,
            atoms_list,
            require_observation=session.deployed_evaluator is None,
        )
        if not passed:
            failures.append(member.member_id)
        member_results.append(
            {
                "member_id": member.member_id,
                "representative_checkpoint_sha256": member.representative_checkpoint_sha256,
                "target_head_name": member.target_head_name,
                "deployment_artifact_sha256": deployed.artifact_sha256,
                "runtime_identity": deployed.runtime_identity,
                "maximum_energy_error_ev_per_atom": float(energy_error),
                "maximum_force_tolerance_excess_ev_per_angstrom": float(force_error),
                "maximum_stress_tolerance_excess_ev_per_angstrom3": (
                    None if stress_error is None else float(stress_error)
                ),
                "missing_stress_count": int(missing_stress),
                "stress_compared_count": int(compared_stress),
                "stress_unavailable_count": int(unavailable_stress),
                "stress_capability": (
                    "authenticated"
                    if stress_applicable and unavailable_stress == 0
                    else "unavailable"
                    if stress_applicable
                    else "not_applicable"
                ),
                "stress_applicable": stress_applicable,
                "stress_required": stress_required,
                "stress_capability_digest": capability.content_digest,
                "stress_capability_reasons": list(capability.reason_codes),
                "stress_capability_decision": capability.to_dict(),
                "runtime_evidence": (
                    runtime_evidence[0]
                    if runtime_evidence
                    else {}
                ),
                "passed": passed,
            }
        )

    status = ComponentStatus.PASSED if not failures else ComponentStatus.REJECTED
    reason = (
        "deployment_parity_within_tolerance"
        if not failures
        else "deployment_parity_out_of_tolerance"
    )
    detail = (
        ""
        if not failures
        else (
            "The exact frozen publication is rejected because member(s) "
            f"{failures} did not reproduce their in-framework behaviour through the "
            "deployed artifact. A committee is never shrunk to rescue a release."
        )
    )
    capability_set_digest = session.stress_capability_digest(
        COMPONENT_DEPLOYMENT_PARITY, None
    )
    return build_component_evidence(
        component=COMPONENT_DEPLOYMENT_PARITY,
        binding=binding,
        status=status,
        reason_code=reason,
        detail=detail,
        metrics={
            "member_count": len(member_results),
            "probe_configuration_count": len(cohort),
            "failed_members": failures,
            "stress_applicable": any(
                bool(row["stress_applicable"]) for row in member_results
            ),
            "stress_required": any(
                bool(row["stress_required"]) for row in member_results
            ),
            "stress_capability_reasons": sorted(
                {
                    reason
                    for row in member_results
                    for reason in row.get("stress_capability_reasons", ())
                }
            ),
            "stress_compared_configurations": sum(
                int(row["stress_compared_count"]) for row in member_results
            ),
            "stress_unavailable_configurations": sum(
                int(row["stress_unavailable_count"]) for row in member_results
            ),
            "stress_unavailable_members": [
                row["member_id"]
                for row in member_results
                if row["stress_unavailable_count"]
            ],
        },
        payload={
            "probe_cohort_digest": cohort_digest,
            "probe_geometry_digest": probe_geometry_digest,
            "probe_frame_uids": list(cohort),
            "used_real_deployed_runtime": session.deployed_evaluator is None,
            # Kept as a compatibility view for a single-member publication;
            # the authoritative collection is the member-keyed mapping below.
            "stress_capability": (
                member_results[0]["stress_capability_decision"]
                if len(member_results) == 1
                else None
            ),
            "stress_capabilities": {
                row["member_id"]: row["stress_capability_decision"]
                for row in member_results
            },
            "stress_capability_set_digest": capability_set_digest,
            "members": member_results,
        },
        component_input_digest=session.component_input_digest(
            COMPONENT_DEPLOYMENT_PARITY, None
        ),
    )


def _validate_observed_geometry(
    deployed: DeployedEvaluation,
    atoms_list: Sequence[Any],
    *,
    require_observation: bool,
) -> None:
    """Require the real runtime to return the box/PBC it actually executed."""

    if not deployed.cells_angstrom or not deployed.pbc:
        if require_observation:
            raise QualificationLineageError(
                "The deployed runtime returned no post-build cell/PBC observation; "
                "the requested geometry cannot authenticate the executed system."
            )
        return
    if len(deployed.cells_angstrom) != len(atoms_list) or len(deployed.pbc) != len(atoms_list):
        raise QualificationLineageError(
            "The deployed runtime returned an incomplete post-build cell/PBC observation."
        )
    for expected, observed_cell, observed_pbc in zip(
        atoms_list, deployed.cells_angstrom, deployed.pbc, strict=True
    ):
        expected_cell = np.asarray(expected.get_cell(), dtype=np.float64)
        cell = np.asarray(observed_cell, dtype=np.float64)
        requested_pbc = tuple(bool(value) for value in expected.get_pbc())
        if cell.shape != (3, 3) or not np.all(np.isfinite(cell)):
            raise QualificationLineageError(
                "The deployed runtime returned an invalid post-build cell observation."
            )
        if tuple(bool(value) for value in observed_pbc) != requested_pbc:
            raise QualificationLineageError(
                "The deployed runtime executed a different per-axis PBC than requested."
            )
        if not np.allclose(cell, expected_cell, rtol=0.0, atol=1.0e-8):
            raise QualificationLineageError(
                "The deployed runtime executed a different post-build cell than requested."
            )


__all__ = [
    "DeployedEvaluation",
    "default_deployment_exporter",
    "default_mliap_artifact_builder",
    "probe_cohort",
    "qualify_deployment_parity",
]
