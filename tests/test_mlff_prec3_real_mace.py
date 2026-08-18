from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import mdstats


torch = pytest.importorskip("torch")
pytest.importorskip("e3nn")
pytest.importorskip("mace")

from ase import Atoms
from e3nn import o3
from mace import modules, tools
from mace.calculators import MACECalculator


def _tiny_mace(dtype: torch.dtype):
    previous = torch.get_default_dtype()
    torch.set_default_dtype(dtype)
    try:
        table = tools.AtomicNumberTable([1, 8])
        model = modules.ScaleShiftMACE(
            r_max=4.0,
            num_bessel=4,
            num_polynomial_cutoff=3,
            max_ell=1,
            interaction_cls=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
            interaction_cls_first=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
            num_interactions=2,
            num_elements=2,
            hidden_irreps=o3.Irreps("8x0e + 8x1o"),
            MLP_irreps=o3.Irreps("4x0e"),
            gate=torch.nn.functional.silu,
            atomic_energies=np.array([0.0, 0.0]),
            avg_num_neighbors=2.0,
            atomic_numbers=table.zs,
            correlation=2,
            atomic_inter_scale=1.0,
            atomic_inter_shift=0.0,
        )
    finally:
        torch.set_default_dtype(previous)
    return model.to(dtype=dtype)


def _water() -> Atoms:
    return Atoms(
        "H2O",
        positions=[[0.0, 0.0, 0.0], [0.8, 0.0, 0.0], [0.0, 0.8, 0.0]],
        cell=[10.0, 10.0, 10.0],
        pbc=True,
    )


def test_prec3_real_mace_single_and_double_calculator_profiles(tmp_path: Path) -> None:
    for dtype in ("float32", "float64"):
        torch_dtype = torch.float32 if dtype == "float32" else torch.float64
        path = tmp_path / f"{dtype}.model"
        torch.save(_tiny_mace(torch_dtype), path)
        policy = mdstats.MaceCriticalPrecisionPolicy.for_dtype(dtype)
        mdstats.activate_mace_critical_precision_policy(policy)
        calculator = MACECalculator(
            model_paths=str(path), device="cpu", default_dtype=dtype
        )
        assert {parameter.dtype for parameter in calculator.models[0].parameters()} == {torch_dtype}
        atoms = _water()
        atoms.calc = calculator
        assert np.isfinite(float(atoms.get_potential_energy()))
        assert np.isfinite(np.asarray(atoms.get_forces())).all()


def test_prec3_real_mace_refine_evaluation_promotes_fp32_checkpoint_model(tmp_path: Path) -> None:
    source = tmp_path / "early-fp32.model"
    torch.save(_tiny_mace(torch.float32), source)
    mdstats.activate_mace_critical_precision_policy(
        mdstats.MaceCriticalPrecisionPolicy.for_dtype("float64")
    )
    calculator = MACECalculator(
        model_paths=str(source), device="cpu", default_dtype="float64"
    )
    assert {parameter.dtype for parameter in calculator.models[0].parameters()} == {torch.float64}
    atoms = _water()
    atoms.calc = calculator
    assert np.isfinite(float(atoms.get_potential_energy()))
    assert np.isfinite(np.asarray(atoms.get_forces())).all()


def test_prec3_real_mace_refine_deployment_promotes_early_model(tmp_path: Path) -> None:
    source = tmp_path / "early-fp32.model"
    torch.save(_tiny_mace(torch.float32), source)
    artifact = mdstats.export_mace_deployment_artifact(
        source,
        tmp_path,
        deployment_dtype="float64",
        filename="refine-final.model",
        policy=mdstats.MaceDeploymentExportPolicy(
            deployment_dtype="float64", require_inference_probe=False
        ),
        overwrite=True,
    )
    precision = mdstats.inspect_mace_model_precision(
        tmp_path / "refine-final.model", expected_dtype="float64"
    )
    assert artifact.deployment_dtype == "float64"
    assert artifact.conversion_kind == "promotion_float32_to_float64"
    assert artifact.state_conversion_exact
    assert precision.passed
