"""Shared real-owner fixture for the P7 post-production qualification tests.

Every owner under test is production code: the P1-P5 lifecycle, the accepted
final-production publication resolver, the P7 binding/plan/reference/component/
record owners, the campaign store fences, and the real CLI parser and dispatch.
Only three things are substituted, and all three sit strictly below an accepted
owner boundary:

* MACE training, through the already accepted P5 trainer seam;
* the numerical model forward, through the already accepted P5 inference seam,
  replaced by a deterministic analytic pair potential with exact forces;
* MACE model conversion and the LAMMPS/ML-IAP execution of a *toy* checkpoint,
  which cannot be converted or executed by the real runtime at all.

The analytic potential is a genuine PES: it has real curvature, a real
minimum-energy geometry, and analytically exact forces, so the physical,
relaxation, and calibration checks are exercised as mathematics rather than as
tautologies.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import tests._mlff_post_selection_fixture as p5
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore

QUALIFICATION_CONFIG = """
[qualification]
required_components = ["deployment_parity", "physical_pes", "relaxation", "dynamics", "calibration"]

[qualification.reference]
protocol = "bounded-analytic-reference.v1"

[qualification.deployment_parity]
probe_configurations = 2
require_deployed_runtime = false

[qualification.physical]
base_count = 2
displaced_atoms_per_base = 1
displacement_amplitudes_angstrom = [-0.02, 0.02]

[qualification.relaxation]
maximum_steps = 25
force_convergence_ev_per_angstrom = 0.05

[qualification.dynamics]
warmup_steps = 20
propagation_steps = 20
sample_interval_steps = 10

[qualification.calibration]
minimum_frames = 1

[qualification.locked]
minimum_frames = 1
"""


# ---------------------------------------------------------------------------
# The bounded analytic potential used below every expensive numerical boundary
# ---------------------------------------------------------------------------


class AnalyticPairPotential:
    """A deterministic harmonic pair potential with analytically exact forces.

    ``E = sum_{i<j, r < cutoff} k/2 (r - r0)^2``.  Positive ``k`` gives a genuine
    positive local stiffness, so the restoring-sign and curvature checks are
    real tests rather than accidents of a constant model.
    """

    def __init__(self, *, stiffness: float = 2.0, r0: float = 6.0, cutoff: float = 9.0) -> None:
        self.stiffness = float(stiffness)
        self.r0 = float(r0)
        self.cutoff = float(cutoff)

    def evaluate(self, atoms) -> tuple[float, np.ndarray]:
        positions = np.asarray(atoms.get_positions(), dtype=np.float64)
        cell = np.asarray(atoms.get_cell(), dtype=np.float64)
        pbc = np.asarray(atoms.get_pbc(), dtype=bool)
        count = positions.shape[0]
        forces = np.zeros((count, 3), dtype=np.float64)
        energy = 0.0
        inverse = np.linalg.inv(cell) if np.any(pbc) else None
        for index in range(count - 1):
            delta = positions[index + 1 :] - positions[index]
            if inverse is not None:
                fractional = delta @ inverse
                shift = np.round(fractional)
                shift[:, ~pbc] = 0.0
                delta = (fractional - shift) @ cell
            distances = np.sqrt(np.sum(delta * delta, axis=1))
            mask = (distances < self.cutoff) & (distances > 1.0e-9)
            if not np.any(mask):
                continue
            selected = delta[mask]
            radius = distances[mask]
            stretch = radius - self.r0
            energy += float(np.sum(0.5 * self.stiffness * stretch**2))
            # dE/dr_j = k * stretch * unit(r_j - r_i); force on j is -dE/dr_j.
            magnitude = (self.stiffness * stretch / radius)[:, None]
            pair_force = magnitude * selected
            partners = np.nonzero(mask)[0] + index + 1
            forces[partners] -= pair_force
            forces[index] += float(1.0) * np.sum(pair_force, axis=0)
        return float(energy), forces

    def prediction(self, atoms):
        energy, forces = self.evaluate(atoms)
        return SimpleNamespace(
            energy_ev=energy, forces_ev_per_angstrom=forces, stress_ev_per_angstrom3=None
        )


class QualificationHarness:
    """The bounded seams plus a record of exactly what was executed."""

    def __init__(
        self,
        *,
        potential: AnalyticPairPotential | None = None,
        deployed_potential: AnalyticPairPotential | None = None,
        member_bias: dict[str, float] | None = None,
        checkpoint_force_bias: dict[str, float] | None = None,
        dynamics_overrides: dict | None = None,
    ) -> None:
        self.potential = potential or AnalyticPairPotential()
        self.deployed_potential = deployed_potential or self.potential
        self.member_bias = dict(member_bias or {})
        self.checkpoint_force_bias = dict(checkpoint_force_bias or {})
        self.dynamics_overrides = dict(dynamics_overrides or {})
        self.labels: dict[str, tuple[float, np.ndarray]] = {}
        #: When set, a per-member bias applies only to these frames, so a test
        #: can make two committee members differ on one evidence role without
        #: perturbing the geometries another component depends on.
        self.bias_frame_uids: set[str] | None = None
        self.evaluated_atoms = 0
        self.deployed_calls: list[str] = []
        self.dynamics_calls: list[str] = []
        #: Instrumentation the revision-11 acceptance suite reads back.
        self.dynamics_start_positions: list[np.ndarray] = []
        self.export_heads: list[str | None] = []
        self.mliap_heads: list[str | None] = []
        self.locked_evaluations = 0
        self.locked_frame_uids: set[str] = set()
        self.evaluated_frames: list[str] = []

    # -- label-anchored analytic model ---------------------------------------
    def attach_labels(self, context) -> None:
        """Anchor the analytic potential to each frame's own labels.

        The bounded model is ``analytic + constant offset per frame``, where the
        offset is chosen so the model reproduces that frame's authenticated
        first-principles energy and forces exactly at its canonical geometry.
        A constant offset cancels in every central difference, so local
        stiffness and energy curvature remain the analytic potential's real,
        positive values while the locked and calibration comparisons run against
        genuine reference labels.
        """

        from mdstats.training_data._frame_access import ase_atoms_for_frame

        for frame_uid, (record, frame_data, local_index) in (
            context.selected.authorities.frame_array_index.items()
        ):
            energies = frame_data.energies_ev
            forces = frame_data.forces_ev_per_angstrom
            if energies is None or forces is None:
                continue
            atoms = ase_atoms_for_frame(record, frame_data, local_index)
            base_energy, base_forces = self.potential.evaluate(atoms)
            self.labels[str(frame_uid)] = (
                float(np.asarray(energies, dtype=np.float64)[local_index]) - base_energy,
                np.asarray(forces, dtype=np.float64)[local_index] - base_forces,
            )

    def evaluate_atoms(self, atoms) -> tuple[float, np.ndarray]:
        """The exact bounded model, without any member-specific bias."""

        energy, forces = self.potential.evaluate(atoms)
        offset = self.labels.get(str(atoms.info.get("frame_uid", "")))
        if offset is not None:
            energy = energy + offset[0]
            forces = forces + offset[1]
        return float(energy), np.asarray(forces, dtype=np.float64)

    def _checkpoint_bias(self, provider) -> float:
        """Per-member force bias, keyed by the member's own run identity.

        The bounded trainer writes byte-identical toy checkpoints for every
        seed, so the checkpoint digest cannot distinguish two published members;
        the authenticated checkpoint *locator* can, and it is what the provider
        owner reports.
        """

        identity = getattr(provider, "checkpoint_identity", None)
        locator = "" if identity is None else str(getattr(identity, "checkpoint_locator", ""))
        for key, value in self.checkpoint_force_bias.items():
            if key and key in locator:
                return float(value)
        return 0.0

    # -- accepted P5 inference seam -----------------------------------------
    def evaluate(self, provider, atoms_list):
        self.evaluated_atoms += len(atoms_list)
        if self.locked_frame_uids and any(
            str(atoms.info.get("frame_uid", "")) in self.locked_frame_uids
            for atoms in atoms_list
        ):
            self.locked_evaluations += 1
        bias = self._checkpoint_bias(provider)
        predictions = []
        for atoms in atoms_list:
            frame_uid = str(atoms.info.get("frame_uid", ""))
            self.evaluated_frames.append(frame_uid)
            energy, forces = self.evaluate_atoms(atoms)
            predictions.append(
                SimpleNamespace(
                    energy_ev=energy,
                    forces_ev_per_angstrom=forces + self._applied_bias(bias, frame_uid),
                    stress_ev_per_angstrom3=None,
                )
            )
        return predictions

    def _applied_bias(self, bias: float, frame_uid: str) -> float:
        if self.bias_frame_uids is None:
            return bias
        return bias if frame_uid in self.bias_frame_uids else 0.0

    # -- P7 deployment seams -------------------------------------------------
    def export_deployment(self, source_model_path, output_directory, *, deployment_dtype, target_head):
        self.export_heads.append(target_head)
        root = Path(output_directory)
        root.mkdir(parents=True, exist_ok=True)
        target = root / "deployment.model"
        target.write_bytes(Path(source_model_path).read_bytes())
        return SimpleNamespace(
            deployment_relative_path="deployment.model",
            deployment_artifact_sha256=None,
        )

    def build_mliap(self, deployment_path, output_path, *, head):
        self.mliap_heads.append(head)
        Path(output_path).write_bytes(Path(deployment_path).read_bytes())
        return Path(output_path)

    def deployed_evaluator(self, session, member, atoms_list):
        from mdstats.training_data.qualification.deployment import DeployedEvaluation
        import hashlib

        self.deployed_calls.append(member.member_id)
        # The deployed path must reproduce the in-framework model exactly unless
        # a test deliberately introduces a deployment divergence, so it carries
        # the same per-member bias plus any explicit deployment-only bias.
        bias = float(self.member_bias.get(member.member_id, 0.0)) + float(
            next(
                (
                    value
                    for key, value in self.checkpoint_force_bias.items()
                    if key and key in member.run_identity
                ),
                0.0,
            )
        )
        energies = []
        forces = []
        for atoms in atoms_list:
            energy, force = self.evaluate_atoms(atoms)
            if self.deployed_potential is not self.potential:
                energy, force = self.deployed_potential.evaluate(atoms)
            energies.append(energy)
            forces.append(
                np.asarray(force, dtype=np.float64)
                + self._applied_bias(bias, str(atoms.info.get("frame_uid", "")))
            )
        artifact_path, sha = session.deployed_artifact(member)
        return DeployedEvaluation(
            energies_ev=tuple(energies),
            forces_ev_per_angstrom=tuple(forces),
            artifact_sha256=sha,
            runtime_identity=session.binding.environment.content_digest,
        )

    def dynamics_runner(
        self, session, member, atoms, *, temperature_kelvin, velocity_seed, case_identity
    ):
        """Emit faithful *raw* observations; every verdict stays in the reducer.

        The knobs below perturb only what a real runtime could plausibly
        report - temperatures, energies, geometry, forces - so each frozen
        diagnostic is exercised through the production reduction rather than by
        asserting a decision the fixture made.
        """

        self.dynamics_calls.append(case_identity)
        self.dynamics_start_positions.append(
            np.asarray(atoms.get_positions(), dtype=np.float64)
        )
        overrides = self.dynamics_overrides
        _energy, raw_forces = self.evaluate_atoms(atoms)
        raw_forces = np.asarray(raw_forces, dtype=np.float64)
        cell = np.asarray(atoms.get_cell(), dtype=np.float64).tolist()
        pbc = [bool(value) for value in atoms.get_pbc()]
        base_positions = np.asarray(atoms.get_positions(), dtype=np.float64)

        def _sample(stage: float, positions, *, nve: bool, index: int, drift: float):
            sample = {
                "stage": stage,
                "temperature_kelvin": float(
                    overrides.get("nvt_temperature", temperature_kelvin)
                ),
                "potential_energy_ev": -1.0,
                "kinetic_energy_ev": 0.5,
                "total_energy_ev": -0.5 + drift * index,
                "positions_angstrom": np.asarray(positions, dtype=np.float64).tolist(),
                "forces_ev_per_angstrom": raw_forces.tolist(),
                "cell_angstrom": cell,
                "pbc": pbc,
            }
            if nve:
                sample["nve_temperature_kelvin"] = float(
                    overrides.get("nve_temperature", temperature_kelvin)
                )
            return sample

        nve_sample_count = int(overrides.get("nve_sample_count", 4))
        nvt_sample_count = int(overrides.get("nvt_sample_count", 2))

        # Geometry perturbations. A displacement/bond/angle knob moves atoms in
        # every NVE sample; a topology knob breaks a protected bond in only the
        # first N samples, which is what separates transient noise from
        # persistent damage under the frozen persistence rule.
        displaced = base_positions.copy()
        if "protected_displacement" in overrides:
            displaced[0] = displaced[0] + np.array(
                [float(overrides["protected_displacement"]), 0.0, 0.0]
            )
        if "protected_bond_error" in overrides and displaced.shape[0] > 1:
            direction = displaced[1] - displaced[0]
            norm = float(np.linalg.norm(direction)) or 1.0
            displaced[1] = displaced[1] + direction / norm * float(
                overrides["protected_bond_error"]
            )
        if "protected_angle_error" in overrides and displaced.shape[0] > 2:
            displaced[2] = displaced[2] + np.array(
                [0.0, float(overrides["protected_angle_error"]) * 0.05, 0.0]
            )
        # A topology break has to be a *bond* break, not a large displacement,
        # or a topology test would be indistinguishable from a displacement one.
        broken = displaced.copy()
        if broken.shape[0] > 1:
            direction = broken[1] - broken[0]
            norm = float(np.linalg.norm(direction)) or 1.0
            broken[1] = broken[1] + direction / norm * float(
                overrides.get("topology_break_angstrom", 1.5)
            )
        transient = int(overrides.get("transient_topology_violations", 0))
        if overrides.get("collapse"):
            displaced = displaced.copy()
            displaced[1] = displaced[0] + np.array([0.05, 0.0, 0.0])

        drift = float(overrides.get("total_energy_drift_ev", 0.0))
        warmup = [
            _sample(0.0, base_positions, nve=False, index=index, drift=0.0)
            for index in range(max(1, nvt_sample_count))
        ]
        propagation = []
        for index in range(max(2, nve_sample_count)):
            positions = broken if index < transient else displaced
            propagation.append(_sample(1.0, positions, nve=True, index=index, drift=drift))

        final = np.asarray(propagation[-1]["positions_angstrom"], dtype=np.float64)
        return {
            "mode": "dynamics",
            "warmup_samples": warmup,
            "propagation_samples": propagation,
            "nvt_samples": warmup,
            "nve_samples": propagation,
            "minimum_pair_distance_angstrom": float(
                overrides.get("minimum_pair_distance_angstrom", 2.0)
            ),
            "maximum_force_ev_per_angstrom": float(
                overrides.get("maximum_force_ev_per_angstrom", 1.0)
            ),
            "final_positions_angstrom": final.tolist(),
            "atom_count": int(len(atoms)),
        }

    def seams(self) -> dict:
        return {
            "_external_inference_evaluator": self.evaluate,
            "_external_deployment_exporter": self.export_deployment,
            "_external_mliap_builder": self.build_mliap,
            "_external_deployed_evaluator": self.deployed_evaluator,
            "_external_dynamics_runner": self.dynamics_runner,
        }


# ---------------------------------------------------------------------------
# Campaign construction
# ---------------------------------------------------------------------------


def fixture_config_text(
    *,
    production_seeds: str = "[5]",
    committee_policy: str | None = None,
    calibration_overrides: str = "",
    strain_magnitudes: str | None = None,
    dynamics_overrides: str = "",
) -> str:
    text = p5.fixture_config_text().replace("seeds = [5]", f"seeds = {production_seeds}")
    if committee_policy is not None:
        text += f'committee_policy = "{committee_policy}"\n'
    qualification = QUALIFICATION_CONFIG
    if strain_magnitudes is not None:
        qualification = qualification.replace(
            "displacement_amplitudes_angstrom = [-0.02, 0.02]",
            "displacement_amplitudes_angstrom = [-0.02, 0.02]\n"
            f"strain_magnitudes = {strain_magnitudes}",
        )
    if dynamics_overrides:
        qualification = qualification.replace(
            "sample_interval_steps = 10\n",
            f"sample_interval_steps = 10\n{dynamics_overrides}",
        )
    if calibration_overrides:
        qualification = qualification.replace(
            "[qualification.calibration]\nminimum_frames = 1\n",
            f"[qualification.calibration]\nminimum_frames = 1\n{calibration_overrides}",
        )
    return text + qualification


def build_qualified_campaign(
    tmp_path: Path, *, config_text: str | None = None, harness: "QualificationHarness | None" = None
):
    """A real campaign driven through the accepted P1-P5 lifecycle."""

    template = fixture_config_text() if config_text is None else config_text
    config, workspace = p5.build_selected_campaign(tmp_path, config_text=template)
    p5_harness = p5.PostSelectionHarness()
    assert p5.run_cross_validate(config, p5_harness) == 0
    assert p5.run_train_production(config, p5_harness) == 0
    if harness is not None:
        attach_labels(harness, config)
    return config, workspace


def attach_labels(harness: "QualificationHarness", config: Path) -> None:
    """Bind the authenticated frame labels to the bounded model seam."""

    from mdstats.training_data.campaign_post_selection_runtime import (
        build_post_selection_context,
    )

    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    try:
        context = build_post_selection_context(cfg, paths, store)
        harness.attach_labels(context)
        from mdstats.training_data.qualification import resolve_evidence_role_membership

        harness.locked_frame_uids = set(
            resolve_evidence_role_membership(context).locked_frame_uids
        )
    finally:
        store.close()


def run_qualification_command(config: Path, *subcommand: str, harness=None, **extra) -> int:
    """Dispatch through the real CLI parser, exactly as an operator would."""

    active = QualificationHarness() if harness is None else harness
    return p4d._run(config, "qualification", *subcommand, **active.seams(), **extra)


def load_session(config: Path, harness=None, **overrides):
    """Build a session on the real owners, with the bounded seams injected.

    Any seam may be overridden with ``None`` to exercise the real owner path
    instead, which is how the real-runtime blocking cases are reached.
    """

    from mdstats.training_data.qualification import build_qualification_session

    active = QualificationHarness() if harness is None else harness
    cfg, paths = cli._load_config(config)
    store = CampaignStore(paths.state_db)
    seams = {
        "inference_evaluator": active.evaluate,
        "deployment_exporter": active.export_deployment,
        "mliap_builder": active.build_mliap,
        "deployed_evaluator": active.deployed_evaluator,
        "dynamics_runner": active.dynamics_runner,
    }
    seams.update(overrides)
    session = build_qualification_session(cfg, paths, store, **seams)
    return cfg, paths, store, session


def supply_analytic_reference_bundle(session, harness: QualificationHarness) -> Path:
    """Fulfil the exact frozen reference request with the analytic potential."""

    from mdstats.training_data.qualification.geometry import (
        atoms_for_frame,
        displaced_atoms,
        relax_fixed_cell,
    )
    from mdstats.training_data.qualification.reference import (
        BASE_MODE,
        RELAXED_MODE,
        ReferenceObservation,
        write_reference_bundle,
    )

    request = session.reference_request
    by_identity = {}
    for base in session.plan.physical_plan.bases:
        atoms = atoms_for_frame(session.context, base.frame_uid)
        by_identity[(base.frame_uid, BASE_MODE)] = atoms
        by_identity[(base.frame_uid, RELAXED_MODE)] = atoms
        from mdstats.training_data.qualification.geometry import strained_atoms
        from mdstats.training_data.qualification.reference import (
            mode_name,
            strain_mode_name,
        )

        for atom_index, axis, amplitude in base.modes():
            by_identity[(base.frame_uid, mode_name(atom_index, axis, amplitude))] = displaced_atoms(
                atoms, atom_index=atom_index, axis=axis, amplitude=amplitude
            )
        for magnitude in session.plan.physical_plan.strain_magnitudes:
            by_identity[(base.frame_uid, strain_mode_name(magnitude))] = strained_atoms(
                atoms, magnitude
            )
    observations = []
    for item in request.geometries:
        atoms = by_identity[(item.frame_uid, item.mode)]
        energy, forces = harness.evaluate_atoms(atoms)
        relaxed = None
        if item.mode == RELAXED_MODE:
            outcome = relax_fixed_cell(
                atoms,
                harness.evaluate_atoms,
                maximum_steps=25,
                force_convergence=0.05,
            )
            relaxed = np.asarray(outcome.relaxed.get_positions(), dtype=np.float64)
        observations.append(
            ReferenceObservation(
                geometry_identity=item.geometry_identity,
                energy_ev=energy,
                forces_ev_per_angstrom=tuple(tuple(row) for row in forces.tolist()),
                relaxed_positions_angstrom=(
                    None if relaxed is None else tuple(tuple(row) for row in relaxed.tolist())
                ),
            )
        )
    return write_reference_bundle(session.reference_root, request, observations)
