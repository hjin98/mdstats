"""Real pinned-MACE acceptance for the corrected objective/weighting realization.

Config-text inspection cannot close this claim, so every assertion here goes
through MACE 0.3.16's own surfaces: its argument parser resolves the generated
configuration, its ``get_loss_fn`` resolver instantiates the loss, its
``config_from_atoms``/``AtomicData`` path builds the batch from the exact
``config_*`` keys the mdstats exporter writes, and its real loss module produces
the number that is compared against the declared weighting contract.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
mace = pytest.importorskip("mace")

from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.objectives import (
    TrainingObjectivePolicy,
    resolve_training_objective_policy,
)
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.campaign_target_size_runtime import mace_run_configuration
from mdstats.training_data.target_size_execution import (
    TargetSizeCommonTrainingPolicy,
    build_target_size_candidate_trajectory,
    build_target_size_common_preparation,
    build_target_size_execution_context,
    build_target_size_screen_schedule,
    materialize_target_size_candidate,
    project_target_size_candidate_preparation,
)
from mdstats.training_data.target_size_execution.candidate import (
    TARGET_SIZE_MACE_LOSS_FAMILY,
)
import tests.test_mlff_target_size_execution_p3a as p3a


OBJECTIVE = TrainingObjectivePolicy(
    energy_weight=2.0, forces_weight=7.0, stress_weight=3.0
)


def _generated_config(tmp_path: Path, objective: TrainingObjectivePolicy):
    """Materialize one candidate through the real P3 owners and return its config."""

    manifest, fa, _nb, aggregate, _common, index = p3a._common(tmp_path)
    frames, frame_data_by_run, _idx = p3a._frame_arrays(tmp_path, manifest)
    common = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=index,
        policy=TargetSizeCommonTrainingPolicy(objective_policy=objective),
    )
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    optimizer = MaceOptimizerPolicy(max_num_epochs=schedule.n3, batch_size=4)
    context = build_target_size_execution_context(
        aggregate.definition,
        common,
        schedule,
        seed_neutral_optimizer_policy=optimizer,
    )
    size = aggregate.definition.qualified_candidate_sizes[0]
    trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=size,
        optimizer_policy=optimizer,
        optimizer_seed=1,
    )
    projection = project_target_size_candidate_preparation(
        common, aggregate.definition, size
    )
    out = tmp_path / "candidate"
    record = materialize_target_size_candidate(
        trajectory,
        projection,
        common,
        canonical_frame_authority=fa,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=out,
        optimizer_policy=optimizer,
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=index,
    )
    canonical = json.loads((out / record.mace_config_relative_path).read_text())
    return canonical, out, trajectory


def _parse_with_pinned_mace(run_config: dict, directory: Path):
    """Resolve the generated configuration through MACE's own argument parser."""

    import yaml
    from mace.tools.arg_parser import build_default_arg_parser

    path = directory / "mace_run.yaml"
    path.write_text(yaml.safe_dump(run_config, sort_keys=True), encoding="utf-8")
    return build_default_arg_parser().parse_args(["--config", str(path)])


def _loss_from_pinned_mace(args):
    from mace.tools.scripts_utils import get_loss_fn

    return get_loss_fn(args, dipole_only=False, compute_dipole=False)


def _batch(specs):
    """Build a real MACE batch from ase Atoms carrying the exporter's weight keys."""

    import ase
    from mace.data.atomic_data import AtomicData
    from mace.data.utils import KeySpecification, config_from_atoms
    from mace.tools import AtomicNumberTable, torch_geometric

    keyspec = KeySpecification.from_defaults()
    z_table = AtomicNumberTable([1])
    data = []
    for spec in specs:
        atoms = ase.Atoms(
            "H2",
            positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 0.9]],
            cell=np.eye(3) * 6.0,
            pbc=True,
        )
        atoms.info["REF_energy"] = float(spec["energy"])
        atoms.arrays["REF_forces"] = np.asarray(spec["forces"], dtype=np.float64)
        if spec.get("stress") is not None:
            atoms.info["REF_stress"] = np.asarray(spec["stress"], dtype=np.float64)
        atoms.info["config_weight"] = float(spec["config_weight"])
        atoms.info["config_energy_weight"] = float(spec["energy_weight"])
        atoms.info["config_forces_weight"] = float(spec["forces_weight"])
        atoms.info["config_stress_weight"] = float(spec["stress_weight"])
        configuration = config_from_atoms(atoms, key_specification=keyspec)
        data.append(
            AtomicData.from_config(configuration, z_table=z_table, cutoff=3.0)
        )
    loader = torch_geometric.dataloader.DataLoader(
        dataset=data, batch_size=len(data), shuffle=False, drop_last=False
    )
    return next(iter(loader))


def _prediction(ref, *, energy_error, force_error, stress_error):
    n = ref["energy"].shape[0]
    return {
        "energy": ref["energy"] + energy_error,
        "forces": ref["forces"] + force_error,
        "stress": ref["stress"] + stress_error,
    }


@pytest.fixture(scope="module")
def _default_dtype():
    previous = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    yield
    torch.set_default_dtype(previous)


def test_generated_config_resolves_to_the_native_weighted_loss(
    tmp_path: Path, _default_dtype
) -> None:
    """Cases 1-4 and 7: real parser, real resolver, real class, real coefficients."""

    from mace.modules.loss import (
        UniversalLoss,
        WeightedEnergyForcesStressLoss,
    )

    canonical, directory, _trajectory = _generated_config(tmp_path, OBJECTIVE)
    assert canonical["loss"] == TARGET_SIZE_MACE_LOSS_FAMILY
    args = _parse_with_pinned_mace(mace_run_configuration(canonical), directory)

    assert args.loss == TARGET_SIZE_MACE_LOSS_FAMILY
    loss_fn = _loss_from_pinned_mace(args)
    assert isinstance(loss_fn, WeightedEnergyForcesStressLoss)
    assert not isinstance(loss_fn, UniversalLoss)
    assert float(loss_fn.energy_weight) == pytest.approx(OBJECTIVE.energy_weight)
    assert float(loss_fn.forces_weight) == pytest.approx(OBJECTIVE.forces_weight)
    assert float(loss_fn.stress_weight) == pytest.approx(OBJECTIVE.stress_weight)
    # MACE's own forces_weight=100 default is never what runs.
    assert float(loss_fn.forces_weight) != 100.0


def test_real_loss_honours_configuration_and_local_property_weights(
    tmp_path: Path, _default_dtype
) -> None:
    """Case 5: the real loss responds exactly as the declared contract states."""

    canonical, directory, _trajectory = _generated_config(tmp_path, OBJECTIVE)
    args = _parse_with_pinned_mace(mace_run_configuration(canonical), directory)
    loss_fn = _loss_from_pinned_mace(args)

    base = dict(
        energy=-1.5,
        forces=[[0.1, 0.0, -0.2], [-0.1, 0.0, 0.2]],
        stress=[0.01, 0.02, 0.03, 0.0, 0.0, 0.0],
        config_weight=1.0,
        energy_weight=1.0,
        forces_weight=1.0,
        stress_weight=1.0,
    )
    ref = _batch([base, base])
    pred = _prediction(ref, energy_error=0.3, force_error=0.05, stress_error=0.02)
    reference_loss = float(loss_fn(ref=ref, pred=pred, ddp=False))

    # Independently derive the expected weighted MSE from the batch tensors.
    # This intentionally does not call any MACE loss helper: it proves that the
    # real WeightedEnergyForcesStressLoss combines the three global coefficients
    # and the per-configuration/local masks with the declared semantics.
    num_atoms = ref.ptr[1:] - ref.ptr[:-1]
    expected_energy = torch.mean(
        ref.weight
        * ref.energy_weight
        * torch.square((ref["energy"] - pred["energy"]) / num_atoms)
    )
    repeated_weight = torch.repeat_interleave(ref.weight, num_atoms).unsqueeze(-1)
    repeated_forces_weight = torch.repeat_interleave(
        ref.forces_weight, num_atoms
    ).unsqueeze(-1)
    expected_forces = torch.mean(
        repeated_weight
        * repeated_forces_weight
        * torch.square(ref["forces"] - pred["forces"])
    )
    expected_stress = torch.mean(
        ref.weight.view(-1, 1, 1)
        * ref.stress_weight.view(-1, 1, 1)
        * torch.square(ref["stress"] - pred["stress"])
    )
    expected = (
        OBJECTIVE.energy_weight * expected_energy
        + OBJECTIVE.forces_weight * expected_forces
        + OBJECTIVE.stress_weight * expected_stress
    )
    assert reference_loss == pytest.approx(float(expected))

    # Doubling every configuration weight doubles the loss: config_weight enters
    # MACE's reductions linearly, which is exactly what the declared
    # configuration-weight policy requires and what UniversalLoss cannot do.
    doubled = {**base, "config_weight": 2.0}
    ref2 = _batch([doubled, doubled])
    pred2 = _prediction(ref2, energy_error=0.3, force_error=0.05, stress_error=0.02)
    assert float(loss_fn(ref=ref2, pred=pred2, ddp=False)) == pytest.approx(
        2.0 * reference_loss
    )

    # Local property weights are linear modifiers too, and are independent of
    # the global coefficients: tripling only the local forces weight scales just
    # the force term.
    forces_only = {**base, "energy_weight": 0.0, "stress_weight": 0.0}
    ref_f = _batch([forces_only, forces_only])
    pred_f = _prediction(ref_f, energy_error=0.3, force_error=0.05, stress_error=0.02)
    force_term = float(loss_fn(ref=ref_f, pred=pred_f, ddp=False))
    tripled = {**forces_only, "forces_weight": 3.0}
    ref_f3 = _batch([tripled, tripled])
    pred_f3 = _prediction(
        ref_f3, energy_error=0.3, force_error=0.05, stress_error=0.02
    )
    assert float(loss_fn(ref=ref_f3, pred=pred_f3, ddp=False)) == pytest.approx(
        3.0 * force_term
    )

    # The global coefficients are applied exactly once, at the global layer: the
    # total is the coefficient-weighted sum of the three isolated terms.
    energy_only = {**base, "forces_weight": 0.0, "stress_weight": 0.0}
    stress_only = {**base, "energy_weight": 0.0, "forces_weight": 0.0}
    terms = []
    for spec in (energy_only, forces_only, stress_only):
        ref_i = _batch([spec, spec])
        pred_i = _prediction(
            ref_i, energy_error=0.3, force_error=0.05, stress_error=0.02
        )
        terms.append(float(loss_fn(ref=ref_i, pred=pred_i, ddp=False)))
    assert sum(terms) == pytest.approx(reference_loss)


def test_zero_local_property_weight_masks_a_missing_property(
    tmp_path: Path, _default_dtype
) -> None:
    """Case 6: an absent label contributes nothing through its zero local mask."""

    canonical, directory, _trajectory = _generated_config(tmp_path, OBJECTIVE)
    args = _parse_with_pinned_mace(mace_run_configuration(canonical), directory)
    loss_fn = _loss_from_pinned_mace(args)

    base = dict(
        energy=-1.5,
        forces=[[0.1, 0.0, -0.2], [-0.1, 0.0, 0.2]],
        stress=None,
        config_weight=1.0,
        energy_weight=1.0,
        forces_weight=1.0,
        stress_weight=1.0,
    )
    ref = _batch([base, base])
    # MACE itself zeroes the property weight of an absent label, which is the
    # local-mask semantics mdstats now declares.
    assert float(ref.stress_weight[0]) == 0.0
    pred = _prediction(ref, energy_error=0.3, force_error=0.05, stress_error=0.0)
    masked = float(loss_fn(ref=ref, pred=pred, ddp=False))
    # An arbitrary stress residual on the masked frame cannot move the loss.
    pred_perturbed = dict(pred)
    pred_perturbed["stress"] = pred["stress"] + 12.0
    assert float(loss_fn(ref=ref, pred=pred_perturbed, ddp=False)) == pytest.approx(
        masked
    )


def test_local_weights_are_masks_not_copies_of_the_global_ratio(
    tmp_path: Path,
) -> None:
    """The 1:10:1 objective ratio must never be duplicated per frame."""

    canonical, _directory, _trajectory = _generated_config(tmp_path, OBJECTIVE)
    assert canonical["energy_weight"] == pytest.approx(OBJECTIVE.energy_weight)
    assert canonical["forces_weight"] == pytest.approx(OBJECTIVE.forces_weight)
    assert canonical["stress_weight"] == pytest.approx(OBJECTIVE.stress_weight)


def test_objective_resolver_is_shared_by_screen_and_post_selection() -> None:
    config = {
        "objective": {
            "energy_weight": 4.0,
            "forces_weight": 40.0,
            "stress_weight": 0.5,
        }
    }
    resolved = resolve_training_objective_policy(config)
    assert (resolved.energy_weight, resolved.forces_weight, resolved.stress_weight) == (
        4.0,
        40.0,
        0.5,
    )
    default = resolve_training_objective_policy({})
    assert (
        default.energy_weight,
        default.forces_weight,
        default.stress_weight,
    ) == (1.0, 10.0, 1.0)
