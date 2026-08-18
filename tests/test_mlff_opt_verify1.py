from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from mdstats.training_data import campaign_cli


def _dense_minimum(atoms) -> float:
    distances = atoms.get_all_distances(mic=True)
    mask = ~np.eye(len(atoms), dtype=bool)
    return float(np.min(distances[mask]))


def test_neighbor_minimum_matches_dense_orthorhombic() -> None:
    from ase import Atoms

    rng = np.random.default_rng(1234)
    atoms = Atoms(
        "Li32",
        positions=rng.uniform(0.0, 12.0, size=(32, 3)),
        cell=[12.0, 13.0, 14.0],
        pbc=True,
    )
    assert campaign_cli._minimum_distance(atoms) == pytest.approx(
        _dense_minimum(atoms), rel=1e-12, abs=1e-12
    )


def test_neighbor_minimum_matches_dense_triclinic() -> None:
    from ase import Atoms

    rng = np.random.default_rng(4321)
    cell = np.array(
        [[10.0, 0.0, 0.0], [3.1, 9.7, 0.0], [1.8, 2.4, 11.2]], dtype=float
    )
    scaled = rng.uniform(0.0, 1.0, size=(40, 3))
    atoms = Atoms("Na40", scaled_positions=scaled, cell=cell, pbc=True)
    assert campaign_cli._minimum_distance(atoms) == pytest.approx(
        _dense_minimum(atoms), rel=1e-12, abs=1e-12
    )


def test_neighbor_minimum_does_not_call_dense_matrix(monkeypatch) -> None:
    from ase import Atoms

    atoms = Atoms(
        "Li4",
        positions=[[0, 0, 0], [1.5, 0, 0], [0, 2.0, 0], [0, 0, 2.5]],
        cell=[20, 20, 20],
        pbc=True,
    )

    def forbidden(*args, **kwargs):
        raise AssertionError("dense distance matrix must not be used")

    monkeypatch.setattr(atoms, "get_all_distances", forbidden)
    assert campaign_cli._minimum_distance(atoms) == pytest.approx(1.5)


def test_neighbor_minimum_expands_for_sparse_cell() -> None:
    from ase import Atoms

    atoms = Atoms(
        "Li2",
        positions=[[0, 0, 0], [7.0, 0, 0]],
        cell=[30, 30, 30],
        pbc=True,
    )
    assert campaign_cli._minimum_distance(atoms) == pytest.approx(7.0)


def test_worker_calculator_cache_reuses_only_same_identity(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_calculator(model_path, *, device, dtype, acceleration_policy):
        calls.append(str(model_path))
        return object()

    monkeypatch.setattr(campaign_cli, "_nve_calculator", fake_calculator)
    campaign_cli._VERIFICATION_WORKER_LOCAL.__dict__.clear()
    policy = SimpleNamespace(policy_digest="policy")
    model_a = tmp_path / "a.model"
    model_b = tmp_path / "b.model"

    first, reused = campaign_cli._worker_cached_nve_calculator(
        model_a, device="cpu", dtype="float32", acceleration_policy=policy
    )
    assert reused is False
    second, reused = campaign_cli._worker_cached_nve_calculator(
        model_a, device="cpu", dtype="float32", acceleration_policy=policy
    )
    assert reused is True
    assert second is first
    third, reused = campaign_cli._worker_cached_nve_calculator(
        model_b, device="cpu", dtype="float32", acceleration_policy=policy
    )
    assert reused is False
    assert third is not first
    assert calls == [str(model_a), str(model_b)]


def test_verification_structure_templates_parse_once(monkeypatch, tmp_path: Path) -> None:
    from ase import Atoms
    import ase.io

    paths = [tmp_path / "a.xyz", tmp_path / "b.xyz"]
    calls: list[Path] = []

    def fake_read(path):
        calls.append(Path(path))
        return Atoms("Li2", positions=[[0, 0, 0], [2, 0, 0]], cell=[10, 10, 10], pbc=True)

    monkeypatch.setattr(ase.io, "read", fake_read)
    templates = campaign_cli._load_verification_structure_templates(paths)
    assert calls == paths
    assert set(templates) == {str(path) for path in paths}
    assert all(value.calc is None for value in templates.values())


def test_nve_verify_uses_structure_template_without_reparse(tmp_path: Path, monkeypatch) -> None:
    from ase import Atoms
    from ase.calculators.calculator import Calculator, all_changes
    import ase.io

    class ZeroCalculator(Calculator):
        implemented_properties = ["energy", "forces"]

        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            self.results["energy"] = 0.0
            self.results["forces"] = np.zeros((len(atoms), 3), dtype=float)

    def forbidden_read(*args, **kwargs):
        raise AssertionError("structure template should avoid ase.io.read")

    monkeypatch.setattr(ase.io, "read", forbidden_read)
    template = Atoms(
        "Li3",
        positions=[[0, 0, 0], [2, 0, 0], [0, 2, 0]],
        cell=[20, 20, 20],
        pbc=True,
    )
    acceleration = SimpleNamespace(backend=SimpleNamespace(value="e3nn"))
    result = campaign_cli._nve_verify(
        tmp_path / "unused.model",
        tmp_path / "unused.xyz",
        device="cpu",
        dtype="float32",
        acceleration_policy=acceleration,
        temperature=10.0,
        timestep_fs=0.1,
        steps=5,
        velocity_seed=7,
        sample_interval_steps=5,
        calculator=ZeroCalculator(),
        structure_atoms=template,
    )
    assert result["structure_template_reused"] is True
    assert result["minimum_distance_backend"] == "periodic_neighbor_list_adaptive_v1"


def test_nve_worker_reuses_calculator_across_cases(monkeypatch, tmp_path: Path) -> None:
    from ase import Atoms
    from ase.calculators.calculator import Calculator, all_changes

    class ZeroCalculator(Calculator):
        implemented_properties = ["energy", "forces"]

        def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
            super().calculate(atoms, properties, system_changes)
            self.results["energy"] = 0.0
            self.results["forces"] = np.zeros((len(atoms), 3), dtype=float)

    calls = 0

    def fake_calculator(*args, **kwargs):
        nonlocal calls
        calls += 1
        return ZeroCalculator()

    monkeypatch.setattr(campaign_cli, "_nve_calculator", fake_calculator)
    campaign_cli._VERIFICATION_WORKER_LOCAL.__dict__.clear()
    template = Atoms(
        "Li3",
        positions=[[0, 0, 0], [2, 0, 0], [0, 2, 0]],
        cell=[20, 20, 20],
        pbc=True,
    )
    acceleration = SimpleNamespace(
        backend=SimpleNamespace(value="e3nn"), policy_digest="same-policy"
    )
    kwargs = dict(
        model_path=tmp_path / "model.model",
        structure=tmp_path / "unused.xyz",
        device="cpu",
        dtype="float32",
        acceleration_policy=acceleration,
        timestep_fs=0.1,
        steps=2,
        velocity_seed=7,
        sample_interval_steps=2,
        structure_atoms=template,
        reuse_worker_calculator=True,
    )
    first = campaign_cli._nve_verify(temperature=10.0, **kwargs)
    second = campaign_cli._nve_verify(temperature=20.0, **kwargs)
    assert first["calculator_reused"] is False
    assert second["calculator_reused"] is True
    assert calls == 1
