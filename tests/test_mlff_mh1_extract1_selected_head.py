from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import os

import numpy as np
import pytest

import mdstats
from mdstats.training_data._common import TrainingDataInputError
from mdstats.training_data.mace_head_extraction import _extract_selected_head_model


MH1_MODEL = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
MH1_SHA256 = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"


def _synthetic_identity() -> mdstats.FoundationPotentialIdentity:
    return mdstats.FoundationPotentialIdentity(
        reference="/synthetic/mh1.model",
        sha256="1" * 64,
        foundation_head="omat_pbe",
        model_family="mace_mh_1",
        architecture_signature="2" * 64,
        model_atomic_numbers=(3, 8, 11, 13, 14, 17),
        available_heads=("omol", "omat_pbe"),
        inspection_state="inspected",
    )


def test_extract1_compatibility_policy_round_trip() -> None:
    policy = mdstats.MaceSelectedHeadCompatibilityPolicy()
    assert policy.affected_package_version == "0.3.16"
    assert policy.inferred_attribute == "use_edge_irreps_first"
    assert policy.inferred_value is True
    assert policy.preserve_source_dtype is True
    assert mdstats.MaceSelectedHeadCompatibilityPolicy.from_dict(policy.to_dict()) == policy


def test_extract1_stock_success_self_disables_architecture_shim() -> None:
    torch = pytest.importorskip("torch")

    class FakeModel(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.ones(1, dtype=torch.float64))
            self.heads = ["omol", "omat_pbe"]

    source = FakeModel()
    sentinel = FakeModel()
    calls: list[str] = []

    def stock(model, head):
        calls.append(head)
        return sentinel

    result = _extract_selected_head_model(
        source,
        head="omat_pbe",
        source_identity=_synthetic_identity(),
        mace_version="9.9.9",
        policy=mdstats.MaceSelectedHeadCompatibilityPolicy(),
        stock_extractor=stock,
    )
    derived, stock_ok, failure_type, failure_digest, failure_excerpt, evidence = result
    assert derived is sentinel
    assert stock_ok is True
    assert calls == ["omat_pbe"]
    assert failure_type is failure_digest is failure_excerpt is None
    assert evidence["shim_applied"] is False
    assert evidence["self_disabled_reason"] == "stock_selected_head_extraction_passed"
    assert torch.get_default_dtype() == torch.float32


def test_extract1_failed_stock_is_not_patched_outside_exact_guard() -> None:
    torch = pytest.importorskip("torch")

    class FakeModel(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.weight = torch.nn.Parameter(torch.ones(1, dtype=torch.float64))
            self.heads = ["omol", "omat_pbe"]
            self.interactions = torch.nn.ModuleList([torch.nn.Linear(1, 1)])

    def fail(model, head):
        raise RuntimeError("synthetic stock failure")

    with pytest.raises(TrainingDataInputError, match="does not match the exact version/architecture"):
        _extract_selected_head_model(
            FakeModel(),
            head="omat_pbe",
            source_identity=_synthetic_identity(),
            mace_version="9.9.9",
            policy=mdstats.MaceSelectedHeadCompatibilityPolicy(),
            stock_extractor=fail,
        )


@pytest.mark.slow
def test_extract1_real_mh1_omat_pbe_extraction_and_parity(tmp_path: Path) -> None:
    if importlib.util.find_spec("mace") is None:
        pytest.skip("real MACE environment is not active")
    if not MH1_MODEL.is_file():
        pytest.skip("locked MH-1 checkpoint is not mounted")
    assert hashlib.sha256(MH1_MODEL.read_bytes()).hexdigest() == MH1_SHA256

    from ase import Atoms
    import torch

    identity = mdstats.MaceFoundationSpec(
        family="mace_mh_1", requested_head="omat_pbe"
    ).resolve_file(MH1_MODEL)
    source_sha_before = hashlib.sha256(MH1_MODEL.read_bytes()).hexdigest()
    derived_path = tmp_path / "mace-mh-1-omat_pbe-derived.model"
    extraction, compatibility_evidence = mdstats.extract_mace_selected_foundation_head(
        MH1_MODEL,
        derived_path,
        source_identity=identity,
    )
    assert extraction.source_checkpoint_sha256 == MH1_SHA256
    assert extraction.source_head == "omat_pbe"
    assert extraction.source_model_dtype == "float64"
    assert extraction.derived_model_dtype == "float64"
    assert extraction.stock_extraction_succeeded is False
    assert extraction.stock_failure_type == "RuntimeError"
    assert extraction.compatibility_shim_applied is True
    assert extraction.source_bytes_preserved is True
    assert compatibility_evidence["shim_attribute"] == "use_edge_irreps_first"
    assert compatibility_evidence["shim_value"] is True
    assert compatibility_evidence["edge_projection_matches_serialized_modules"] is True
    assert compatibility_evidence["first_interaction_edge_irreps"] == "128x0e"
    assert compatibility_evidence["linear_up_irreps_out"] == "128x0e"
    assert hashlib.sha256(MH1_MODEL.read_bytes()).hexdigest() == source_sha_before

    derived_inspection = mdstats.inspect_mace_foundation(derived_path)
    assert derived_inspection.available_heads == ("omat_pbe",)
    assert derived_inspection.model_dtype == "float64"
    derived_model = torch.load(derived_path, map_location="cpu", weights_only=False)
    assert getattr(derived_model, "use_edge_irreps_first") is True
    assert str(derived_model.interactions[0].linear_up.irreps_out) == "128x0e"

    structures = (
        Atoms("NaCl", positions=[[0, 0, 0], [2.8, 0, 0]], cell=[8, 8, 8], pbc=True),
        Atoms("SiO2", positions=[[0, 0, 0], [1.6, 0, 0], [-0.8, 1.4, 0]], cell=[9, 9, 9], pbc=True),
        Atoms(
            "AlNaSiO4",
            positions=[
                [0, 0, 0], [2.8, 0, 0], [0, 2.8, 0], [1.4, 1.4, 1.4],
                [4.2, 1.4, 1.4], [1.4, 4.2, 1.4], [1.4, 1.4, 4.2],
            ],
            cell=[10, 10, 10],
            pbc=True,
        ),
    )
    qualification = mdstats.qualify_mace_selected_foundation_head(
        MH1_MODEL,
        extraction,
        structures,
        policy=mdstats.MaceSelectedHeadParityPolicy(default_dtype="float64"),
        device="cpu",
    )
    assert qualification.training_qualified
    parity = qualification.parity
    assert parity.passed
    assert parity.structure_count == 3
    assert parity.atom_count == 12
    assert parity.descriptor_width == 1024
    assert parity.atomic_e0_abs_max_ev == 0.0
    assert parity.energy_abs_max_ev < 1.0e-12
    assert parity.force_abs_max_ev_per_angstrom < 1.0e-12
    assert parity.stress_abs_max_ev_per_angstrom3 < 1.0e-12
    assert parity.descriptor_abs_max < 1.0e-11
    assert mdstats.MaceSelectedHeadExtractionRecord.from_dict(extraction.to_dict()) == extraction
    assert mdstats.MaceSelectedHeadQualificationRecord.from_dict(qualification.to_dict()) == qualification
