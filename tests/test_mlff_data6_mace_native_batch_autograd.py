from __future__ import annotations

import warnings

import numpy as np
import pytest


def _real_mace_provider():
    torch = pytest.importorskip("torch")
    pytest.importorskip("ase")
    pytest.importorskip("e3nn")
    pytest.importorskip("mace")

    from e3nn import o3
    from mace import modules
    from mace.calculators import MACECalculator

    from mdstats.training_data.model_features import (
        MaceCalculatorProvider,
        ModelCheckpointIdentity,
    )

    model = modules.MACE(
        r_max=4.0,
        num_bessel=4,
        num_polynomial_cutoff=5,
        max_ell=1,
        interaction_cls=modules.interaction_classes[
            "RealAgnosticResidualInteractionBlock"
        ],
        interaction_cls_first=modules.interaction_classes[
            "RealAgnosticResidualInteractionBlock"
        ],
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
    calculator = MACECalculator(
        models=model,
        device="cpu",
        default_dtype="float64",
    )
    identity = ModelCheckpointIdentity(
        model_family="MACE",
        checkpoint_locator="synthetic-real-mace-0.3.16",
        checkpoint_sha256="0" * 64,
        calculator_class="mace.calculators.mace.MACECalculator",
        model_version="0.3.16",
        supported_atomic_numbers=(1, 8),
        device="cpu",
        default_dtype="float64",
    )
    return (
        MaceCalculatorProvider.from_calculator(
            calculator,
            checkpoint_identity=identity,
        ),
        model,
    )


def test_native_descriptor_batch_disables_mace_derivative_outputs() -> None:
    torch = pytest.importorskip("torch")
    from ase import Atoms

    from mdstats.training_data.model_features import MaceDescriptorPolicy

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            provider, model = _real_mace_provider()

        atoms_batch = (
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.8, 0.0, 0.0), (0.0, 0.8, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            ),
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.9, 0.0, 0.0), (0.0, 0.9, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            ),
        )
        policy = MaceDescriptorPolicy()

        calls: list[tuple[bool, dict[str, object]]] = []
        original_forward = model.forward

        def probed_forward(*args, **kwargs):
            calls.append((torch.is_grad_enabled(), dict(kwargs)))
            return original_forward(*args, **kwargs)

        model.forward = probed_forward
        batched = provider.get_descriptors_batch(atoms_batch, policy)
        model.forward = original_forward

        assert len(calls) == 1
        grad_enabled, kwargs = calls[0]
        assert not grad_enabled
        assert kwargs["training"] is False
        for name in (
            "compute_force",
            "compute_virials",
            "compute_stress",
            "compute_displacement",
            "compute_hessian",
            "compute_edge_forces",
            "compute_atomic_stresses",
        ):
            assert kwargs[name] is False

        serial = tuple(provider.get_descriptors(atoms, policy) for atoms in atoms_batch)
        assert len(batched) == len(serial) == 2
        for observed, expected in zip(batched, serial, strict=True):
            assert observed.shape == expected.shape
            assert np.all(np.isfinite(observed))
            np.testing.assert_allclose(observed, expected, rtol=1.0e-12, atol=1.0e-12)
    finally:
        torch.set_default_dtype(previous_dtype)


def test_combined_native_batch_reuses_one_forward_and_matches_serial() -> None:
    torch = pytest.importorskip("torch")
    from ase import Atoms

    from mdstats.training_data.model_features import MaceDescriptorPolicy

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            provider, model = _real_mace_provider()
        atoms_batch = (
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.8, 0.0, 0.0), (0.0, 0.8, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            ),
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.9, 0.0, 0.0), (0.0, 0.9, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            ),
        )
        policy = MaceDescriptorPolicy()
        calls = []
        original_forward = model.forward

        def probed_forward(*args, **kwargs):
            calls.append(dict(kwargs))
            return original_forward(*args, **kwargs)

        model.forward = probed_forward
        descriptors, predictions = provider.evaluate_batch(atoms_batch, policy)
        model.forward = original_forward
        assert len(calls) == 1

        serial_descriptors = tuple(
            provider.get_descriptors(atoms, policy) for atoms in atoms_batch
        )
        serial_predictions = tuple(provider.predict(atoms) for atoms in atoms_batch)
        for observed, expected in zip(
            descriptors, serial_descriptors, strict=True
        ):
            np.testing.assert_allclose(
                observed, expected, rtol=1.0e-12, atol=1.0e-12
            )
        for observed, expected in zip(
            predictions, serial_predictions, strict=True
        ):
            assert observed.energy_ev == pytest.approx(
                expected.energy_ev, rel=1.0e-12, abs=1.0e-12
            )
            np.testing.assert_allclose(
                observed.forces_ev_per_angstrom,
                expected.forces_ev_per_angstrom,
                rtol=1.0e-12,
                atol=1.0e-12,
            )
            if expected.stress_ev_per_angstrom3 is not None:
                np.testing.assert_allclose(
                    observed.stress_ev_per_angstrom3,
                    expected.stress_ev_per_angstrom3,
                    rtol=1.0e-12,
                    atol=1.0e-12,
                )
    finally:
        torch.set_default_dtype(previous_dtype)


def test_native_graph_batch_cache_reuses_graphs_across_providers(monkeypatch) -> None:
    torch = pytest.importorskip("torch")
    from ase import Atoms
    pytest.importorskip("mace")
    from mace import data as mace_data

    from mdstats.training_data.model_features import (
        MaceDescriptorPolicy,
        clear_mace_graph_batch_cache,
    )

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        atoms_batch = (
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.8, 0.0, 0.0), (0.0, 0.8, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            ),
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.9, 0.0, 0.0), (0.0, 0.9, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            ),
        )
        clear_mace_graph_batch_cache()
        calls = 0
        original = mace_data.AtomicData.from_config

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(mace_data.AtomicData, "from_config", counted)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            first, _ = _real_mace_provider()
            second, _ = _real_mace_provider()
        policy = MaceDescriptorPolicy()
        first.get_descriptors_batch(atoms_batch, policy)
        assert calls == len(atoms_batch)
        second.get_descriptors_batch(atoms_batch, policy)
        assert calls == len(atoms_batch)
    finally:
        clear_mace_graph_batch_cache()
        torch.set_default_dtype(previous_dtype)
