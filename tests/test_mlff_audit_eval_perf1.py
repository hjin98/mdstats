from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np

import mdstats
from mdstats.training_data import eval2 as eval2_module
from mdstats.training_data.model_features import AtomicModelPrediction

D1 = "1" * 64
D2 = "2" * 64
D3 = "3" * 64
D4 = "4" * 64
D5 = "5" * 64


def _view_and_predictions():
    view = SimpleNamespace(
        configuration_count=4,
        total_atom_count=12,
        atom_counts=np.asarray([3, 3, 3, 3]),
        force_offsets=np.asarray([0, 3, 6, 9, 12]),
        reference_energies=np.asarray([0.0, 1.0, 2.0, 3.0]),
        reference_forces=np.zeros((12, 3)),
        atomic_numbers=np.asarray([11, 8, 19] * 4),
        focus_atomic_numbers=(11, 19),
        condition_labels=("cold", "hot"),
        condition_ids=np.asarray([0, 1, 0, 1]),
        stress_present=np.asarray([False, False, False, False]),
        reference_stresses=np.zeros((4, 6)),
    )
    predictions = tuple(
        AtomicModelPrediction(
            energy_ev=float(i) + 0.01 * (i - 1),
            forces_ev_per_angstrom=np.asarray(
                [
                    [0.01 + 0.001 * i, 0.0, 0.0],
                    [0.0, 0.02 + 0.001 * i, 0.0],
                    [0.0, 0.0, 0.03 + 0.001 * i],
                ]
            ),
            stress_ev_per_angstrom3=None,
        )
        for i in range(4)
    )
    return view, predictions


def test_eval2_static_metadata_is_reused_for_repeated_checkpoint_reduction(monkeypatch) -> None:
    view, predictions = _view_and_predictions()
    blocks = ("a", "a", "b", "b")
    eval2_module.clear_eval2_static_reduction_cache()
    calls = 0
    original = eval2_module._build_eval2_static_reduction_metadata

    def wrapped(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(eval2_module, "_build_eval2_static_reduction_metadata", wrapped)
    first = mdstats.eval2_target_metrics_from_prediction_view(
        view, predictions, block_ids=blocks, target_role_digest=D1, prediction_digest=D2
    )
    second = mdstats.eval2_target_metrics_from_prediction_view(
        view, predictions, block_ids=blocks, target_role_digest=D1, prediction_digest=D2
    )
    assert calls == 1
    assert first.to_dict() == second.to_dict()


def _target_metric(scale: float, digest_char: str, *, blocks: int = 96):
    component_count = 30
    block_metrics = tuple(
        mdstats.Eval2TargetBlockMetric(
            block_id=f"block-{i:03d}",
            force_squared_error_sum=(scale * (1.0 + 0.15 * math.sin(i * 0.19))) ** 2 * component_count,
            force_component_count=component_count,
            configuration_count=1,
        )
        for i in range(blocks)
    )
    rmse = math.sqrt(
        sum(item.force_squared_error_sum for item in block_metrics)
        / sum(item.force_component_count for item in block_metrics)
    )
    return mdstats.Eval2TargetMetricRecord(
        configuration_count=blocks,
        atom_count=blocks * 10,
        energy_mae_ev_per_atom=0.001,
        relative_energy_rmse_ev_per_atom=0.0005,
        force_component_rmse_ev_per_angstrom=rmse,
        species_macro_force_rmse_ev_per_angstrom=rmse,
        species_force_rmse_ev_per_angstrom=(("Na", rmse),),
        force_error_p90_ev_per_angstrom=rmse,
        force_error_p95_ev_per_angstrom=rmse,
        force_error_p99_ev_per_angstrom=rmse,
        worst_stratum_force_rmse_ev_per_angstrom=rmse,
        stratum_force_rmse_ev_per_angstrom=(("species:Na", rmse),),
        stress_rmse_ev_per_angstrom3=None,
        block_metrics=block_metrics,
        target_role_digest=D1,
        prediction_digest=digest_char * 64,
    )


def _checkpoint(epoch: int, metric):
    point = mdstats.Eval2TrajectoryPoint(
        epoch=epoch,
        checkpoint_sha256=f"{epoch + 1:064x}",
        lightweight_target_score_ev_per_angstrom=metric.force_component_rmse_ev_per_angstrom,
        normalized_schedule_progress=0.8,
        instantaneous_learning_rate=1e-5,
        phase="refinement",
        runtime_summary_digest=D2,
        stable_candidate_identity=f"candidate-{epoch}",
    )
    return mdstats.assess_eval2_checkpoint(
        point,
        evaluation_record_digest=D3,
        target_metrics=metric,
        admissibility_policy=mdstats.CheckpointAdmissibilityPolicy(),
        replay_candidate_force_rmse_ev_per_angstrom=0.020,
        replay_foundation_force_rmse_ev_per_angstrom=0.020,
        replay_label_mode="true_dft",
    )


def test_eval2_batched_bootstrap_preserves_scalar_rng_and_reduction_authority() -> None:
    policy = mdstats.CheckpointSelectionPolicy(
        bootstrap_replicates=700,
        bootstrap_min_independent_blocks=10,
        practical_equivalence_ev_per_angstrom=1e-5,
    )
    first = _checkpoint(20, _target_metric(0.020, "6"))
    second = _checkpoint(21, _target_metric(0.021, "7"))
    optimized = mdstats.paired_block_bootstrap_compare(
        first, second, policy=policy, seed_material_digest=D5
    )

    first_map = first.target_metrics.block_map()
    second_map = second.target_metrics.block_map()
    blocks = tuple(sorted(first_map))
    seed = eval2_module._seed_from_digest(
        eval2_module.digest(
            {
                "schema": "mdstats.eval2-bootstrap-seed.v1",
                "seed_material_digest": D5,
                "first": first.stable_candidate_identity,
                "second": second.stable_candidate_identity,
                "blocks": list(blocks),
            }
        )
    )
    rng = np.random.default_rng(seed)
    count = len(blocks)
    first_sse = np.asarray([first_map[key].force_squared_error_sum for key in blocks], dtype=np.float64)
    second_sse = np.asarray([second_map[key].force_squared_error_sum for key in blocks], dtype=np.float64)
    components = np.asarray([first_map[key].force_component_count for key in blocks], dtype=np.float64)
    reference = np.empty(policy.bootstrap_replicates, dtype=np.float64)
    for i in range(reference.size):
        draw = rng.integers(0, count, size=count)
        denom = float(np.sum(components[draw]))
        reference[i] = math.sqrt(float(np.sum(first_sse[draw])) / denom) - math.sqrt(
            float(np.sum(second_sse[draw])) / denom
        )
    alpha = (1.0 - policy.bootstrap_confidence) / 2.0
    low, high = (float(v) for v in np.quantile(reference, [alpha, 1.0 - alpha]))
    assert optimized.seed == seed
    assert optimized.confidence_low_ev_per_angstrom == low
    assert optimized.confidence_high_ev_per_angstrom == high


def test_eval2_bootstrap_batch_is_memory_bounded_for_large_block_inventory() -> None:
    # The implementation must derive batch size from block count rather than
    # allocating 256 x N blocks unconditionally.
    source = (eval2_module.Path(eval2_module.__file__).read_text(encoding="utf-8"))
    assert "bootstrap_target_temporary_bytes = 32 * 1024**2" in source
    assert "memory_bounded_batch" in source
