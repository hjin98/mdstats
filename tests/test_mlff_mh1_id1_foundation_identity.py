from __future__ import annotations

from pathlib import Path
import hashlib
import importlib.util
import os

import pytest

import mdstats
from mdstats.training_data._common import TrainingDataInputError, TrainingDataSerializationError, digest


MH1_MODEL = Path(os.environ.get("MDSTATS_TEST_MH1_MODEL", "/mnt/data/mace-mh-1.model"))
MPA0_MODEL = Path(os.environ.get("MDSTATS_TEST_MPA0_MODEL", "/mnt/data/mace-mpa-0-medium.model"))
MH1_SHA256 = "ec00a2705854622fbbd898ccfb7701072fcd674709102d009fb919c1b8cc5dde"
MPA0_SHA256 = "75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638"


def _synthetic_inspection(*, mh1: bool) -> mdstats.MaceFoundationInspection:
    if mh1:
        heads = ("matpes_r2scan", "omol", "omat_pbe")
        interactions = (
            {"class": "RealAgnosticResidualNonLinearInteractionBlock", "node_feats_irreps": "512x0e"},
            {"class": "RealAgnosticResidualNonLinearInteractionBlock", "node_feats_irreps": "512x0e+512x1o"},
        )
        return mdstats.MaceFoundationInspection(
            reference="/model/mh1.model",
            sha256="1" * 64,
            model_class="ScaleShiftMACE",
            model_module="mace.modules.models",
            available_heads=heads,
            atomic_numbers=(1, 3, 8, 11, 17),
            r_max_angstrom=6.0,
            num_interactions=2,
            model_dtype="float64",
            atomic_energies_shape=(3, 5),
            interaction_signatures=interactions,
            product_signatures=({"class": "EquivariantProductBasisBlock"},) * 2,
            readout_signatures=({"class": "LinearReadoutBlock"}, {"class": "NonLinearReadoutBlock"}),
            edge_irreps="128x0e+128x1o",
            use_agnostic_product=True,
            use_last_readout_only=False,
            state_shape_digest="a" * 64,
        )
    return mdstats.MaceFoundationInspection(
        reference="/model/mpa0.model",
        sha256="2" * 64,
        model_class="ScaleShiftMACE",
        model_module="mace.modules.models",
        available_heads=("default",),
        atomic_numbers=(1, 3, 8, 11, 17),
        r_max_angstrom=6.0,
        num_interactions=2,
        model_dtype="float64",
        atomic_energies_shape=(5,),
        interaction_signatures=(
            {"class": "RealAgnosticDensityInteractionBlock", "node_feats_irreps": "128x0e"},
            {"class": "RealAgnosticDensityResidualInteractionBlock", "node_feats_irreps": "128x0e+128x1o"},
        ),
        product_signatures=({"class": "EquivariantProductBasisBlock"},) * 2,
        readout_signatures=({"class": "LinearReadoutBlock"}, {"class": "NonLinearReadoutBlock"}),
        state_shape_digest="b" * 64,
    )


def test_id1_head_resolution_family_and_species_are_fail_closed_without_calculator() -> None:
    mh1 = _synthetic_inspection(mh1=True)
    mpa0 = _synthetic_inspection(mh1=False)

    omat = mdstats.MaceFoundationSpec("mace_mh_1", "omat_pbe", (3, 8, 11, 17)).resolve(mh1)
    omol = mdstats.MaceFoundationSpec("MACE-MH-1", "omol", (3, 8)).resolve(mh1)
    assert omat.foundation_head == "omat_pbe"
    assert omat.model_family == "mace_mh_1"
    assert omat.content_digest != omol.content_digest
    assert omat.canonical_content_digest == omat.content_digest

    singleton = mdstats.MaceFoundationSpec("MACE-MPA-0", requested_head=None, requested_atomic_numbers=(3, 8)).resolve(mpa0)
    assert singleton.foundation_head == "default"
    assert singleton.model_family == "mace_mpa_0"

    with pytest.raises(TrainingDataInputError, match="requires an explicit foundation head"):
        mdstats.MaceFoundationSpec("mace_mh_1").resolve(mh1)
    with pytest.raises(TrainingDataInputError, match="unavailable"):
        mdstats.MaceFoundationSpec("mace_mh_1", "not_a_head").resolve(mh1)
    with pytest.raises(TrainingDataInputError, match="incompatible"):
        mdstats.MaceFoundationSpec("mace_mh_1", "default").resolve(mpa0)
    with pytest.raises(TrainingDataInputError, match="incompatible"):
        mdstats.MaceFoundationSpec("mace_mpa_0", "omat_pbe").resolve(mh1)
    with pytest.raises(TrainingDataInputError, match="missing atomic numbers"):
        mdstats.MaceFoundationSpec("mace_mh_1", "omat_pbe", (3, 8, 92)).resolve(mh1)


def test_id1_v2_round_trip_preserves_legacy_parent_digest_semantics() -> None:
    payload = {
        "schema": "mdstats.foundation-checkpoint-identity.v2",
        "sha256": "3" * 64,
        "foundation_head": "default",
        "model_family": "MACE-MPA-0",
        "reference": "/legacy/mpa.model",
    }
    payload["content_digest"] = digest({k: payload[k] for k in ("schema", "sha256", "foundation_head", "model_family")})
    restored = mdstats.FoundationCheckpointIdentity.from_dict(payload)
    assert restored.to_dict() == payload
    assert restored.content_digest == payload["content_digest"]
    assert restored.canonical_content_digest != restored.content_digest
    assert restored.family is mdstats.MaceFoundationFamily.MPA_0


def test_id1_inference_identity_scaffolding_separates_execution_from_scientific_identity() -> None:
    potential = mdstats.MaceFoundationSpec("mace_mh_1", "omat_pbe").resolve(_synthetic_inspection(mh1=True))
    e3nn = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="e3nn",
        resolved_kernel_mode="e3nn",
        mace_version="0.3.16",
        adapter_version="foundation-inference-scaffold-v1",
    )
    cueq = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest=potential.canonical_content_digest,
        default_dtype="float32",
        backend="cueq",
        resolved_kernel_mode="cueq_unresolved",
        mace_version="0.3.16",
        adapter_version="foundation-inference-scaffold-v1",
    )
    assert e3nn.foundation_potential_digest == cueq.foundation_potential_digest
    assert e3nn.content_digest != cueq.content_digest
    assert mdstats.FoundationInferenceIdentity.from_dict(e3nn.to_dict()) == e3nn


@pytest.mark.slow
def test_id1_real_uploaded_checkpoints_inspect_and_resolve_exactly() -> None:
    if importlib.util.find_spec("mace") is None:
        pytest.skip("real MACE environment is not active")
    if not (MH1_MODEL.is_file() and MPA0_MODEL.is_file()):
        pytest.skip("locked MH-1/MPA-0 checkpoints are not mounted")
    assert hashlib.sha256(MH1_MODEL.read_bytes()).hexdigest() == MH1_SHA256
    assert hashlib.sha256(MPA0_MODEL.read_bytes()).hexdigest() == MPA0_SHA256

    mh1 = mdstats.inspect_mace_foundation(MH1_MODEL)
    mpa0 = mdstats.inspect_mace_foundation(MPA0_MODEL)
    assert mh1.available_heads == (
        "matpes_r2scan",
        "mp_pbe_refit_add",
        "spice_wB97M",
        "oc20_usemppbe",
        "omol",
        "omat_pbe",
    )
    assert mpa0.available_heads == ("default",)
    assert len(mh1.atomic_numbers) == len(mpa0.atomic_numbers) == 89
    assert mh1.atomic_numbers == mpa0.atomic_numbers
    assert mh1.atomic_energies_shape == (6, 89)
    assert mpa0.atomic_energies_shape == (89,)
    assert mh1.edge_irreps == "128x0e+128x1o"
    assert mh1.use_agnostic_product is True
    assert mh1.interaction_signatures[0]["class"] == "RealAgnosticResidualNonLinearInteractionBlock"
    assert mpa0.interaction_signatures[0]["class"] == "RealAgnosticDensityInteractionBlock"

    omat = mdstats.MaceFoundationSpec("mace_mh_1", "omat_pbe", (3, 8, 11, 13, 14, 17, 19)).resolve(mh1)
    omol = mdstats.MaceFoundationSpec("mace_mh_1", "omol").resolve(mh1)
    default = mdstats.MaceFoundationSpec("mace_mpa_0").resolve(mpa0)
    assert omat.sha256 == MH1_SHA256 and default.sha256 == MPA0_SHA256
    assert omat.content_digest != omol.content_digest
    assert default.foundation_head == "default"
    assert default.available_heads == ("default",)

    with pytest.raises(TrainingDataInputError, match="requires an explicit foundation head"):
        mdstats.MaceFoundationSpec("mace_mh_1").resolve(mh1)
    with pytest.raises(TrainingDataInputError, match="incompatible"):
        mdstats.MaceFoundationSpec("mace_mh_1", "omat_pbe").resolve(mpa0)
    with pytest.raises(TrainingDataInputError, match="incompatible"):
        mdstats.MaceFoundationSpec("mace_mpa_0").resolve(mh1)


@pytest.mark.slow
def test_id1_head_blind_legacy_normalization_requires_authenticated_singleton() -> None:
    if importlib.util.find_spec("mace") is None:
        pytest.skip("real MACE environment is not active")
    if not (MH1_MODEL.is_file() and MPA0_MODEL.is_file()):
        pytest.skip("locked MH-1/MPA-0 checkpoints are not mounted")

    def legacy(path: Path, sha: str, family: str) -> dict:
        core = {
            "schema": "mdstats.foundation-checkpoint-identity.v1",
            "sha256": sha,
            "model_family": family,
        }
        return {**core, "reference": str(path), "content_digest": digest(core)}

    restored = mdstats.FoundationCheckpointIdentity.from_dict(legacy(MPA0_MODEL, MPA0_SHA256, "MACE-MPA-0"))
    assert restored.foundation_head == "default"
    assert restored.inspection_state == "legacy_singleton_authenticated"
    canonical = restored.canonicalized()
    fresh = mdstats.MaceFoundationSpec("mace_mpa_0").resolve_file(MPA0_MODEL)
    assert canonical.canonical_content_digest == fresh.canonical_content_digest

    with pytest.raises(TrainingDataSerializationError, match="ambiguous"):
        mdstats.FoundationCheckpointIdentity.from_dict(legacy(MH1_MODEL, MH1_SHA256, "MACE-MH-1"))
