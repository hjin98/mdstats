from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time
import warnings

import numpy as np
import pytest
from ase import Atoms
from ase.stress import full_3x3_to_voigt_6_stress

from mdstats.training_data.evaluation_views import (
    build_evaluation_dataset_view,
    cached_evaluation_dataset_view,
    clear_evaluation_dataset_view_cache,
    metrics_from_prediction_view,
)
from mdstats.training_data.model_features import (
    AtomicModelPrediction,
    clear_mace_monitor_graph_cache,
)


def _labelled_frames() -> tuple[Atoms, ...]:
    frames = []
    for index, distance in enumerate((1.6, 1.8, 2.0)):
        atoms = Atoms(
            numbers=[3, 8, 8],
            positions=[[0.0, 0.0, 0.0], [distance, 0.0, 0.0], [0.0, distance, 0.0]],
            cell=np.eye(3) * 7.0,
            pbc=True,
        )
        atoms.info["REF_energy"] = -3.0 + 0.2 * index
        atoms.arrays["REF_forces"] = np.full((3, 3), 0.01 * index)
        if index != 1:
            atoms.info["REF_stress"] = np.arange(6, dtype=float) * (index + 1) * 1.0e-3
        atoms.info["temperature"] = 300 if index < 2 else 700
        frames.append(atoms)
    return tuple(frames)


def _predictions(frames: tuple[Atoms, ...]) -> tuple[AtomicModelPrediction, ...]:
    values = []
    for index, atoms in enumerate(frames):
        stress = np.eye(3) * (index + 1) * 2.0e-3
        values.append(
            AtomicModelPrediction(
                energy_ev=float(atoms.info["REF_energy"]) + 0.15 * (index + 1),
                forces_ev_per_angstrom=np.asarray(atoms.arrays["REF_forces"]) + 0.02 * (index + 1),
                stress_ev_per_angstrom3=stress,
            )
        )
    return tuple(values)


def _manual_metrics(frames, predictions):
    energy_abs_sum = 0.0
    force_sse = 0.0
    force_n = 0
    focus_sse = 0.0
    focus_n = 0
    condition = {}
    stress_sse = 0.0
    stress_n = 0
    for atoms, prediction in zip(frames, predictions, strict=True):
        energy_abs_sum += abs(prediction.energy_ev - atoms.info["REF_energy"]) / len(atoms)
        error = np.asarray(prediction.forces_ev_per_angstrom) - np.asarray(atoms.arrays["REF_forces"])
        sq = float(np.sum(error * error, dtype=np.float64))
        force_sse += sq
        force_n += error.size
        mask = np.asarray(atoms.numbers) == 3
        selected = error[mask]
        focus_sse += float(np.sum(selected * selected, dtype=np.float64))
        focus_n += selected.size
        key = str(atoms.info["temperature"])
        acc = condition.setdefault(key, [0.0, 0])
        acc[0] += sq
        acc[1] += error.size
        if "REF_stress" in atoms.info:
            pred = full_3x3_to_voigt_6_stress(np.asarray(prediction.stress_ev_per_angstrom3)).reshape(-1)
            err = pred - np.asarray(atoms.info["REF_stress"]).reshape(-1)
            stress_sse += float(np.sum(err * err, dtype=np.float64))
            stress_n += err.size
    return {
        "energy": energy_abs_sum / len(frames),
        "force": np.sqrt(force_sse / force_n),
        "focus": np.sqrt(focus_sse / focus_n),
        "stress": np.sqrt(stress_sse / stress_n),
        "conditions": tuple((key, np.sqrt(v[0] / v[1])) for key, v in sorted(condition.items())),
    }


def test_vectorized_evaluation_view_matches_pre_opt_eval3_metric_definitions() -> None:
    frames = _labelled_frames()
    predictions = _predictions(frames)
    view = build_evaluation_dataset_view(
        frames,
        energy_key="REF_energy",
        forces_key="REF_forces",
        stress_key="REF_stress",
        focus_atomic_numbers=(3,),
        condition_keys=("temperature",),
    )
    observed = metrics_from_prediction_view(
        view,
        predictions,
        combined_energy_weight=1.0,
        combined_force_weight=2.0,
        combined_stress_weight=3.0,
    )
    expected = _manual_metrics(frames, predictions)
    assert observed["energy_mae_ev_per_atom"] == pytest.approx(expected["energy"], abs=1e-15)
    assert observed["force_component_rmse_ev_per_angstrom"] == pytest.approx(expected["force"], abs=1e-15)
    assert observed["focus_force_rmse_ev_per_angstrom"][0][0] == "Li"
    assert observed["focus_force_rmse_ev_per_angstrom"][0][1] == pytest.approx(expected["focus"], abs=1e-15)
    assert observed["stress_rmse_ev_per_angstrom3"] == pytest.approx(expected["stress"], abs=1e-15)
    assert tuple(label for label, _ in observed["condition_force_rmse_ev_per_angstrom"]) == tuple(label for label, _ in expected["conditions"])
    for (_, observed_value), (_, expected_value) in zip(
        observed["condition_force_rmse_ev_per_angstrom"], expected["conditions"], strict=True
    ):
        assert observed_value == pytest.approx(expected_value, abs=1e-15)
    assert observed["worst_condition_force_rmse_ev_per_angstrom"] == pytest.approx(
        max(value for _, value in expected["conditions"])
    )


def test_evaluation_view_cache_reuses_one_immutable_extraction() -> None:
    clear_evaluation_dataset_view_cache()
    frames = _labelled_frames()
    kwargs = dict(
        energy_key="REF_energy",
        forces_key="REF_forces",
        stress_key="REF_stress",
        focus_atomic_numbers=(3,),
        condition_keys=("temperature",),
    )
    first = cached_evaluation_dataset_view(("monitor", "sha"), frames, **kwargs)
    # A repeated checkpoint sees exactly the same immutable arrays rather than
    # traversing ASE dictionaries again.
    second = cached_evaluation_dataset_view(("monitor", "sha"), frames, **kwargs)
    assert second is first
    assert not first.reference_forces.flags.writeable
    clear_evaluation_dataset_view_cache()


def _real_mace_provider():
    torch = pytest.importorskip("torch")
    pytest.importorskip("e3nn")
    pytest.importorskip("mace")
    from e3nn import o3
    from mace import modules
    from mace.calculators import MACECalculator
    from mdstats.training_data.model_features import MaceCalculatorProvider, ModelCheckpointIdentity

    model = modules.MACE(
        r_max=4.0,
        num_bessel=4,
        num_polynomial_cutoff=5,
        max_ell=1,
        interaction_cls=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
        interaction_cls_first=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
        num_interactions=2,
        num_elements=2,
        hidden_irreps=o3.Irreps("4x0e + 4x1o"),
        MLP_irreps=o3.Irreps("4x0e"),
        gate=torch.nn.functional.silu,
        atomic_energies=np.asarray([0.0, 0.0], dtype=np.float64),
        avg_num_neighbors=2.0,
        atomic_numbers=[1, 8],
        correlation=2,
        radial_type="bessel",
    )
    calculator = MACECalculator(models=model, device="cpu", default_dtype="float64")
    identity = ModelCheckpointIdentity(
        model_family="MACE",
        checkpoint_locator="opt-eval3-real-mace",
        checkpoint_sha256="1" * 64,
        calculator_class="mace.calculators.mace.MACECalculator",
        model_version="0.3.16",
        supported_atomic_numbers=(1, 8),
        device="cpu",
        default_dtype="float64",
    )
    return MaceCalculatorProvider.from_calculator(calculator, checkpoint_identity=identity)


def _graph_frames() -> tuple[Atoms, ...]:
    return (
        Atoms("H2O", positions=((0, 0, 0), (0.8, 0, 0), (0, 0.8, 0)), cell=(8, 8, 8), pbc=True),
        Atoms("H2O", positions=((0, 0, 0), (0.9, 0, 0), (0, 0.9, 0)), cell=(8, 8, 8), pbc=True),
    )


def test_persistent_monitor_graph_shard_survives_memory_cache_clear(tmp_path: Path, monkeypatch) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")
    from mace import data as mace_data

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    clear_mace_monitor_graph_cache()
    try:
        provider = _real_mace_provider()
        frames = _graph_frames()
        identities = ("frame-a", "frame-b")
        calls = 0
        original = mace_data.AtomicData.from_config

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(mace_data.AtomicData, "from_config", counted)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            first = provider.predict_batch(
                frames, geometry_identities=identities, graph_cache_directory=tmp_path
            )
        assert calls == len(frames)
        assert list(tmp_path.rglob("*.pt"))

        clear_mace_monitor_graph_cache()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            second = provider.predict_batch(
                frames, geometry_identities=identities, graph_cache_directory=tmp_path
            )
        assert calls == len(frames), "persistent graph load must avoid AtomicData reconstruction"
        for a, b in zip(first, second, strict=True):
            assert a.energy_ev == pytest.approx(b.energy_ev, rel=0, abs=0)
            np.testing.assert_allclose(a.forces_ev_per_angstrom, b.forces_ev_per_angstrom, rtol=0, atol=0)
    finally:
        clear_mace_monitor_graph_cache()
        torch.set_default_dtype(previous_dtype)


def test_corrupt_persistent_graph_is_rebuilt_from_source_geometry(tmp_path: Path, monkeypatch) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")
    from mace import data as mace_data

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    clear_mace_monitor_graph_cache()
    try:
        provider = _real_mace_provider()
        frames = _graph_frames()
        identities = ("frame-c", "frame-d")
        calls = 0
        original = mace_data.AtomicData.from_config

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(mace_data.AtomicData, "from_config", counted)
        provider.predict_batch(frames, geometry_identities=identities, graph_cache_directory=tmp_path)
        assert calls == len(frames)
        graph_file = next(tmp_path.rglob("*.pt"))
        graph_file.write_bytes(b"corrupt")
        clear_mace_monitor_graph_cache()
        provider.predict_batch(frames, geometry_identities=identities, graph_cache_directory=tmp_path)
        assert calls == 2 * len(frames)
    finally:
        clear_mace_monitor_graph_cache()
        torch.set_default_dtype(previous_dtype)


def test_parallel_monitor_graph_miss_is_single_flight(tmp_path: Path, monkeypatch) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")
    from mace import data as mace_data

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    clear_mace_monitor_graph_cache()
    try:
        first_provider = _real_mace_provider()
        second_provider = _real_mace_provider()
        frames = _graph_frames()
        identities = ("frame-e", "frame-f")
        calls = 0
        original = mace_data.AtomicData.from_config

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            time.sleep(0.01)
            return original(*args, **kwargs)

        monkeypatch.setattr(mace_data.AtomicData, "from_config", counted)
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [
                executor.submit(
                    provider.predict_batch,
                    frames,
                    geometry_identities=identities,
                    graph_cache_directory=tmp_path,
                )
                for provider in (first_provider, second_provider)
            ]
            [future.result() for future in futures]
        assert calls == len(frames)
    finally:
        clear_mace_monitor_graph_cache()
        torch.set_default_dtype(previous_dtype)


def test_monitor_graph_identity_change_forces_new_shard(tmp_path: Path, monkeypatch) -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")
    from mace import data as mace_data

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    clear_mace_monitor_graph_cache()
    try:
        provider = _real_mace_provider()
        frames = _graph_frames()
        calls = 0
        original = mace_data.AtomicData.from_config

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(mace_data.AtomicData, "from_config", counted)
        provider.predict_batch(
            frames,
            geometry_identities=("same-a", "same-b"),
            graph_cache_directory=tmp_path,
        )
        clear_mace_monitor_graph_cache()
        provider.predict_batch(
            frames,
            geometry_identities=("changed-a", "changed-b"),
            graph_cache_directory=tmp_path,
        )
        assert calls == 2 * len(frames)
        assert len(list(tmp_path.rglob("*.pt"))) == 2
    finally:
        clear_mace_monitor_graph_cache()
        torch.set_default_dtype(previous_dtype)
