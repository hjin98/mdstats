from __future__ import annotations

import hashlib
import os
from pathlib import Path
import warnings

import numpy as np
import pytest

import mdstats


def _signature(*, architecture: str = "a" * 64, width: int = 8) -> mdstats.MaceDescriptorSignature:
    # Two-layer synthetic contract: first layer carries equivariants, final layer
    # is invariant-only.  Keep invariant channels at width/2 for simple lineage tests.
    invariant = width // 2
    return mdstats.MaceDescriptorSignature(
        model_class="tests.SyntheticMACE",
        architecture_signature=architecture,
        selected_head="default",
        num_interactions=2,
        per_layer_raw_dimensions=(width, invariant),
        invariant_features_per_layer=invariant,
        per_atom_invariant_dimension=2 * invariant,
        per_atom_full_dimension=width + invariant,
        returned_per_atom_dimension=2 * invariant,
        global_summary_dimension=4 * invariant,
        species_summary_dimension=2 * invariant,
        invariants_only=True,
        num_layers=2,
    )


def test_data6_1_descriptor_signature_roundtrip_and_cache_lineage() -> None:
    signature = _signature()
    assert mdstats.MaceDescriptorSignature.from_dict(signature.to_dict()) == signature

    identity = mdstats.ModelCheckpointIdentity(
        model_family="synthetic",
        checkpoint_locator="memory://synthetic",
        checkpoint_sha256="b" * 64,
        calculator_class="tests.SyntheticCalculator",
        model_version="test",
        supported_atomic_numbers=(1,),
    )
    policy = mdstats.MaceDescriptorPolicy()
    record = mdstats.MaceDescriptorFileRecord(
        frame_uid="1" * 64,
        frame_record_digest="2" * 64,
        checkpoint_identity_digest=identity.content_digest,
        descriptor_policy_digest=policy.policy_digest,
        relative_path="descriptors/frame.npy",
        shape=(2, signature.returned_per_atom_dimension),
        dtype="float64",
        file_sha256="3" * 64,
        array_content_digest="4" * 64,
    )
    first = mdstats.MaceDescriptorManifest(
        dataset_id="dataset",
        frame_catalog_digest="5" * 64,
        data5_bundle_digest="6" * 64,
        checkpoint_identity=identity,
        policy=policy,
        records=(record,),
        signature=signature,
    )
    changed = mdstats.MaceDescriptorManifest(
        dataset_id="dataset",
        frame_catalog_digest="5" * 64,
        data5_bundle_digest="6" * 64,
        checkpoint_identity=identity,
        policy=policy,
        records=(record,),
        signature=_signature(architecture="c" * 64),
    )
    assert first.to_dict()["schema"] == "mdstats.mace-descriptor-manifest.v2"
    assert mdstats.MaceDescriptorManifest.from_dict(first.to_dict()) == first
    assert first.content_digest != changed.content_digest


def test_data6_1_legacy_descriptor_manifest_remains_digest_stable() -> None:
    identity = mdstats.ModelCheckpointIdentity(
        model_family="synthetic",
        checkpoint_locator="memory://synthetic",
        checkpoint_sha256="7" * 64,
        calculator_class="tests.SyntheticCalculator",
        model_version="test",
        supported_atomic_numbers=(1,),
    )
    policy = mdstats.MaceDescriptorPolicy(policy_version="legacy-policy")
    record = mdstats.MaceDescriptorFileRecord(
        frame_uid="8" * 64,
        frame_record_digest="9" * 64,
        checkpoint_identity_digest=identity.content_digest,
        descriptor_policy_digest=policy.policy_digest,
        relative_path="descriptors/legacy.npy",
        shape=(1, 3),
        dtype="float64",
        file_sha256="a" * 64,
        array_content_digest="b" * 64,
    )
    legacy = mdstats.MaceDescriptorManifest(
        dataset_id="legacy",
        frame_catalog_digest="c" * 64,
        data5_bundle_digest="d" * 64,
        checkpoint_identity=identity,
        policy=policy,
        records=(record,),
        signature=None,
    )
    payload = legacy.to_dict()
    assert payload["schema"] == "mdstats.mace-descriptor-manifest.v1"
    assert mdstats.MaceDescriptorManifest.from_dict(payload).to_dict() == payload


def test_data6_1_model_sweep_plan_persists_descriptor_signature() -> None:
    identity = mdstats.ModelCheckpointIdentity(
        model_family="synthetic",
        checkpoint_locator="memory://plan",
        checkpoint_sha256="e" * 64,
        calculator_class="tests.SyntheticCalculator",
        model_version="test",
        supported_atomic_numbers=(1,),
    )
    policy = mdstats.MaceDescriptorPolicy()
    signature = _signature()
    plan = mdstats.Data6ModelSweepPlan(
        dataset_id="dataset",
        frame_catalog_digest="f" * 64,
        data5_bundle_digest="1" * 64,
        data6_policy_digest="2" * 64,
        checkpoint_identity=identity,
        descriptor_policy=policy,
        descriptor_frame_uids=("3" * 64,),
        prediction_frame_uids=(),
        requested_frame_uids=("3" * 64,),
        sealed_or_excluded_frame_uids=(),
        descriptor_signature=signature,
    )
    payload = plan.to_dict()
    assert payload["schema"] == "mdstats.data6-model-sweep-plan.v2"
    restored = mdstats.Data6ModelSweepPlan.from_dict(payload)
    assert restored == plan
    assert restored.descriptor_signature == signature
    changed = mdstats.Data6ModelSweepPlan(
        dataset_id=plan.dataset_id,
        frame_catalog_digest=plan.frame_catalog_digest,
        data5_bundle_digest=plan.data5_bundle_digest,
        data6_policy_digest=plan.data6_policy_digest,
        checkpoint_identity=plan.checkpoint_identity,
        descriptor_policy=plan.descriptor_policy,
        descriptor_frame_uids=plan.descriptor_frame_uids,
        prediction_frame_uids=plan.prediction_frame_uids,
        requested_frame_uids=plan.requested_frame_uids,
        sealed_or_excluded_frame_uids=plan.sealed_or_excluded_frame_uids,
        descriptor_signature=_signature(architecture="4" * 64),
    )
    assert changed.content_digest != plan.content_digest


def test_data6_1_cpu_batch_calibration_is_model_aware() -> None:
    torch = pytest.importorskip("torch")
    pytest.importorskip("mace")
    from ase import Atoms
    from tests.test_mlff_data6_mace_native_batch_autograd import _real_mace_provider

    previous = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            provider, _ = _real_mace_provider()
        atoms = (
            Atoms("H2O", positions=((0, 0, 0), (0.8, 0, 0), (0, 0.8, 0)), cell=(8, 8, 8), pbc=True),
            Atoms("H2O", positions=((0, 0, 0), (0.9, 0, 0), (0, 0.9, 0)), cell=(8, 8, 8), pbc=True),
        )
        calibration = provider.calibrate_batch_capacity(
            atoms, mdstats.MaceDescriptorPolicy(), maximum_batch_size=4
        )
        restored = mdstats.MaceBatchCapacityCalibration.from_dict(calibration.to_dict())
        assert restored == calibration
        assert calibration.successful_batch_sizes == (1,)
        assert calibration.recommended_batch_size == 1  # CPU has no VRAM authority.
        assert calibration.descriptor_bytes_per_structure > 0
        assert calibration.graph_bytes_per_structure > 0
        assert calibration.peak_device_bytes_per_structure is None
    finally:
        torch.set_default_dtype(previous)


@pytest.mark.slow
def test_data6_1_real_uploaded_models_match_official_and_native_batch() -> None:
    """Real acceptance for the e3nn reference path on both locked foundations."""
    pytest.importorskip("mace")
    from ase import Atoms
    from mace.calculators import MACECalculator

    cases = (
        ("MDSTATS_TEST_MH1_MODEL", "omat_pbe", 1024, 2560),
        ("MDSTATS_TEST_MPA0_MODEL", "default", 256, 640),
    )
    structures = (
        Atoms("NaCl", positions=((0, 0, 0), (2.6, 2.6, 2.6)), cell=(5.2, 5.2, 5.2), pbc=True),
        Atoms("NaCl", positions=((0, 0, 0), (2.68, 2.6, 2.6)), cell=(5.2, 5.2, 5.2), pbc=True),
    )
    observed_widths: list[int] = []
    for env_name, head, expected_invariant, expected_full in cases:
        raw = os.environ.get(env_name)
        if not raw:
            pytest.skip(f"{env_name} is not set")
        path = Path(raw)
        if not path.is_file():
            pytest.skip(f"{env_name} does not point to a file")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            calculator = MACECalculator(
                model_paths=str(path), head=head, device="cpu", default_dtype="float64"
            )
        identity = mdstats.ModelCheckpointIdentity(
            model_family="MACE",
            checkpoint_locator=str(path),
            checkpoint_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            calculator_class="mace.calculators.MACECalculator",
            model_version="0.3.16",
            supported_atomic_numbers=tuple(int(v) for v in calculator.z_table.zs),
            device="cpu",
            default_dtype="float64",
            foundation_head=None,
        )
        provider = mdstats.MaceCalculatorProvider.from_calculator(
            calculator, checkpoint_identity=identity
        )
        invariant_policy = mdstats.MaceDescriptorPolicy(invariants_only=True)
        full_policy = mdstats.MaceDescriptorPolicy(invariants_only=False)
        inv_signature = provider.descriptor_signature(invariant_policy)
        full_signature = provider.descriptor_signature(full_policy)
        assert inv_signature.per_atom_invariant_dimension == expected_invariant
        assert inv_signature.returned_per_atom_dimension == expected_invariant
        assert full_signature.per_atom_full_dimension == expected_full
        assert full_signature.returned_per_atom_dimension == expected_full
        assert inv_signature.selected_head == head

        for active_policy, expected_width in (
            (invariant_policy, expected_invariant),
            (full_policy, expected_full),
        ):
            batched = provider.get_descriptors_batch(structures, active_policy)
            serial = tuple(provider.get_descriptors(atoms, active_policy) for atoms in structures)
            for got, expected in zip(batched, serial, strict=True):
                assert got.shape[1] == expected_width
                np.testing.assert_allclose(got, expected, rtol=1e-10, atol=1e-12)
        observed_widths.append(expected_invariant)

    assert observed_widths == [1024, 256]
    assert observed_widths[0] == 4 * observed_widths[1]
