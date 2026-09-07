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
import re
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
mace = pytest.importorskip("mace")

import mdstats
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
import tests.test_mlff_neutral_scientific_substrate as neutral_fixtures


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


def _exported_candidate(tmp_path: Path, objective: TrainingObjectivePolicy):
    """Build a mixed-label, mixed-stratum candidate through real P1-P3 owners.

    The two source runs deliberately have different condition populations and
    the second run has no stress array.  The resulting P3 common fit therefore
    supplies non-unit configuration weights and an actual missing-property
    frame to the production target-size ExtXYZ exporter.
    """

    source_root = tmp_path / "sources"
    source_root.mkdir(parents=True, exist_ok=True)
    run_specs = (("runA", 64, 650, True), ("runB", 48, 900, False))
    for run_id, frame_count, temperature, has_stress in run_specs:
        source = neutral_fixtures._write(
            source_root,
            run_id,
            ("Li", "O"),
            n_frames=frame_count,
            tebeg=temperature,
        )
        if not has_stress:
            source.write_text(
                re.sub(
                    r'<varray name="stress">.*?</varray>',
                    "",
                    source.read_text(encoding="utf-8"),
                    flags=re.DOTALL,
                ),
                encoding="utf-8",
            )
    manifest = mdstats.TrainingDataManifest(
        dataset_id="mace-objective-export",
        system_profile="generic",
        runs=tuple(
            mdstats.TrainingDataRunSpec(
                run_id=run_id,
                vasprun=f"{run_id}/vasprun.xml",
                reference_group="bulk",
                assertions=(("regime", "production"),),
            )
            for run_id, _count, _temperature, _has_stress in run_specs
        ),
    )
    _source, frame_authority, _features, neutral_base = (
        p3a._build_full_neutral_chain(
            manifest, source_root, partition_policy=p3a._neutral_policy()
        )
    )
    aggregate = mdstats.build_target_size_statistical_aggregate(
        frame_authority,
        neutral_base,
        policy=p3a._order_divergent_policy(),
    )
    frames, frame_data_by_run, frame_array_index = p3a._frame_arrays(
        source_root, manifest
    )
    common = build_target_size_common_preparation(
        aggregate,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        frame_array_index=frame_array_index,
        policy=TargetSizeCommonTrainingPolicy(objective_policy=objective),
        mace_architecture=p3a.fixture_mace_architecture(),
    )
    schedule = build_target_size_screen_schedule(
        tuple(aggregate.definition.policy.fidelity_epochs)
    )
    optimizer = MaceOptimizerPolicy(
        device="cpu", max_num_epochs=schedule.n3, batch_size=4
    )
    context = build_target_size_execution_context(
        aggregate.definition,
        common,
        schedule,
        seed_neutral_optimizer_policy=optimizer,
    )

    selected = None
    for target_size in aggregate.definition.qualified_candidate_sizes:
        membership = aggregate.definition.candidate_membership(target_size)
        projection = project_target_size_candidate_preparation(
            common, aggregate.definition, target_size
        )
        weights = {item.frame_uid: item for item in common.fitted_frame_weights}
        selected_weights = [weights[uid] for uid in membership]
        selected_data = [frame_array_index[uid][1] for uid in membership]
        if (
            any(
                not np.isclose(item.configuration_weight, 1.0)
                for item in selected_weights
            )
            and any(data.stresses_ev_per_angstrom3 is None for data in selected_data)
            and any(data.stresses_ev_per_angstrom3 is not None for data in selected_data)
        ):
            selected = (target_size, projection, selected_weights)
            break
    if selected is None:
        raise AssertionError(
            "export fixture did not produce non-unit and mixed stress metadata"
        )
    target_size, projection, selected_weights = selected
    trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=target_size,
        optimizer_policy=optimizer,
        optimizer_seed=1,
    )
    output = tmp_path / "candidate"
    record = materialize_target_size_candidate(
        trajectory,
        projection,
        common,
        canonical_frame_authority=frame_authority,
        frame_catalog=frames,
        frame_data_by_run=frame_data_by_run,
        output_directory=output,
        optimizer_policy=optimizer,
        extxyz_policy=MaceExtxyzPolicy(),
        frame_array_index=frame_array_index,
    )
    canonical = json.loads((output / record.mace_config_relative_path).read_text())
    return canonical, output, trajectory, record, selected_weights


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


def _batch_from_exported_atoms(atoms_list):
    """Build a MACE batch from ExtXYZ frames produced by mdstats."""

    from mace.data.atomic_data import AtomicData
    from mace.data.utils import KeySpecification, config_from_atoms
    from mace.tools import AtomicNumberTable, torch_geometric

    keyspec = KeySpecification.from_defaults()
    z_table = AtomicNumberTable(
        sorted({int(number) for atoms in atoms_list for number in atoms.numbers})
    )
    data = []
    for atoms in atoms_list:
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

    from importlib.metadata import version

    from mace.modules.loss import (
        UniversalLoss,
        WeightedEnergyForcesStressLoss,
    )

    assert version("mace-torch") == "0.3.16"
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
    """Cases 2, 5, and 6: real loss consumes mdstats-exported metadata."""

    canonical, directory, _trajectory, record, expected_weights = _exported_candidate(
        tmp_path, OBJECTIVE
    )
    args = _parse_with_pinned_mace(mace_run_configuration(canonical), directory)
    loss_fn = _loss_from_pinned_mace(args)

    from ase.io import iread

    target_path = directory / record.target_train_artifact.relative_path
    exported = tuple(iread(target_path, index=":", format="extxyz"))
    assert len(exported) == len(expected_weights)
    weights_by_uid = {
        item.frame_uid: item for item in expected_weights
    }
    for atoms in exported:
        uid = atoms.info["frame_uid"]
        expected = weights_by_uid[uid]
        # These values came from the production P3 materialization/export
        # owner.  Nothing below rewrites them before MACE sees the frame.
        assert float(atoms.info["config_weight"]) == pytest.approx(
            expected.configuration_weight
        )
        assert float(atoms.info["config_energy_weight"]) == pytest.approx(1.0)
        assert float(atoms.info["config_forces_weight"]) == pytest.approx(1.0)
        assert float(atoms.info["config_stress_weight"]) == pytest.approx(
            1.0 if "REF_stress" in atoms.info else 0.0
        )
    assert any(
        not np.isclose(float(atoms.info["config_weight"]), 1.0)
        for atoms in exported
    )
    assert any("REF_stress" not in atoms.info for atoms in exported)
    assert any("REF_stress" in atoms.info for atoms in exported)
    assert canonical["energy_weight"] == pytest.approx(OBJECTIVE.energy_weight)
    assert canonical["forces_weight"] == pytest.approx(OBJECTIVE.forces_weight)
    assert canonical["stress_weight"] == pytest.approx(OBJECTIVE.stress_weight)

    ref = _batch_from_exported_atoms(exported)
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

    # The actual exported absent-stress frame contributes no stress term even
    # when its prediction tensor is perturbed arbitrarily.
    assert torch.any(ref.stress_weight == 0.0)
    assert torch.any(ref.stress_weight == 1.0)
    masked = reference_loss
    pred_perturbed = dict(pred)
    pred_perturbed["stress"] = pred["stress"].clone()
    pred_perturbed["stress"][ref.stress_weight == 0.0] += 12.0
    assert float(loss_fn(ref=ref, pred=pred_perturbed, ddp=False)) == pytest.approx(
        masked
    )


def test_local_weights_are_masks_not_copies_of_the_global_ratio(
    tmp_path: Path,
) -> None:
    """The global objective and exported local masks remain separate owners."""

    canonical, directory, _trajectory, record, _expected_weights = _exported_candidate(
        tmp_path, OBJECTIVE
    )
    assert canonical["energy_weight"] == pytest.approx(OBJECTIVE.energy_weight)
    assert canonical["forces_weight"] == pytest.approx(OBJECTIVE.forces_weight)
    assert canonical["stress_weight"] == pytest.approx(OBJECTIVE.stress_weight)
    from ase.io import iread

    exported = tuple(
        iread(directory / record.target_train_artifact.relative_path, index=":", format="extxyz")
    )
    assert all(float(atoms.info["config_energy_weight"]) == 1.0 for atoms in exported)
    assert all(float(atoms.info["config_forces_weight"]) == 1.0 for atoms in exported)
    assert all(
        float(atoms.info["config_stress_weight"])
        in (0.0, 1.0)
        for atoms in exported
    )
    assert any(
        tuple(
            float(atoms.info[key])
            for key in (
                "config_energy_weight",
                "config_forces_weight",
                "config_stress_weight",
            )
        )
        != (
            OBJECTIVE.energy_weight,
            OBJECTIVE.forces_weight,
            OBJECTIVE.stress_weight,
        )
        for atoms in exported
    )


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
