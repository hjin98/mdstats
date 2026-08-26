from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from ase import Atoms
from ase.calculators.calculator import Calculator, all_changes

import mdstats


class _FakeMaceCalculator(Calculator):
    implemented_properties = ["energy", "forces", "stress"]
    pure_bad = False

    def __init__(self, *, enable_cueq=False, enable_oeq=False, **kwargs):
        super().__init__()
        self.enable_cueq = bool(enable_cueq)
        self.enable_oeq = bool(enable_oeq)

    @property
    def _delta(self) -> float:
        if self.enable_cueq and not self.enable_oeq:
            return 1.0e-1 if type(self).pure_bad else 1.0e-8
        if self.enable_cueq and self.enable_oeq:
            return 2.0e-8
        return 0.0

    def calculate(self, atoms=None, properties=("energy",), system_changes=all_changes):
        super().calculate(atoms, properties, system_changes)
        pos = np.asarray(atoms.positions, dtype=np.float64)
        d = self._delta
        self.results["energy"] = float(np.sum(pos * pos) * 0.01 + d)
        self.results["forces"] = -0.02 * pos + d
        self.results["stress"] = np.arange(6, dtype=np.float64) * 1.0e-3 + d

    def get_descriptors(self, atoms, invariants_only=True, **kwargs):
        pos = np.asarray(atoms.positions, dtype=np.float64)
        z = np.asarray(atoms.numbers, dtype=np.float64)[:, None]
        return np.hstack([pos, z * 0.01]) + self._delta


def _structures() -> tuple[Atoms, ...]:
    a = Atoms("NaCl", positions=[[0, 0, 0], [2.6, 2.6, 2.6]], cell=[5.2] * 3, pbc=True)
    b = a.copy()
    b.positions[1, 0] += 0.08
    c = a.copy()
    c.set_cell(np.diag([5.25, 5.15, 5.2]), scale_atoms=True)
    return a, b, c


def _probe(*, oeq=True) -> mdstats.MaceAccelerationProbe:
    return mdstats.MaceAccelerationProbe(
        device="cpu", torch_version="test", torch_cuda_version=None,
        cuda_available=False, mace_version="0.3.16",
        calculator_enable_cueq_supported=True,
        cueq_versions=(("cuequivariance", "0.2.test"),), cueq_imports_passed=True,
        model_smoke_attempted=False, model_smoke_passed=None,
        finite_energy=None, finite_forces=None, finite_stress=None,
        error_type=None, error_message=None,
        calculator_enable_oeq_supported=oeq,
        oeq_version="test" if oeq else None, oeq_import_passed=oeq,
    )


def test_accel1_realization_roundtrip_and_phase_split() -> None:
    inference = mdstats.FoundationInferenceIdentity(
        foundation_potential_digest="a" * 64, default_dtype="float32",
        backend="cueq", resolved_kernel_mode="cueq_oeq_hybrid",
        mace_version="0.3.16", adapter_version="test",
    )
    record = mdstats.AccelerationRealizationRecord(
        requested_backend="cueq", resolved_kernel_mode="cueq_oeq_hybrid",
        training_kernel_mode="cueq_pure", device="cuda", dtype="float32",
        foundation_inference_identity_digest=inference.content_digest,
        mace_version="0.3.16", cueq_versions=(("cueq", "test"),),
        oeq_version="test", inference_parity_record_digest="b" * 64,
        training_parity_record_digest="c" * 64, qualified=True,
    )
    restored = mdstats.AccelerationRealizationRecord.from_dict(record.to_dict())
    assert restored == record
    assert restored.calculator_kwargs() == {"enable_cueq": True, "enable_oeq": True}
    assert restored.training_config() == {
        "enable_cueq": True, "enable_oeq": False, "only_cueq": False
    }


def test_accel1_prefers_hybrid_inference_but_requires_pure_training(monkeypatch, tmp_path: Path) -> None:
    import mace.calculators

    _FakeMaceCalculator.pure_bad = False
    monkeypatch.setattr(mace.calculators, "MACECalculator", _FakeMaceCalculator)
    realization, inference, inference_parity, training_parity = mdstats.qualify_cueq_realization(
        model_path=tmp_path / "fake.model", head="omat_pbe", structures=_structures(),
        device="cpu", dtype="float32", foundation_potential_digest="a" * 64,
        adapter_version="test", probe=_probe(), prefer_hybrid=True,
    )
    assert realization.qualified
    assert realization.resolved_kernel_mode == "cueq_oeq_hybrid"
    assert realization.training_kernel_mode == "cueq_pure"
    assert inference.resolved_kernel_mode == "cueq_oeq_hybrid"
    assert inference_parity is not None and inference_parity.passed
    assert training_parity is not None and training_parity.passed
    assert inference_parity.selection_identical
    assert training_parity.selection_identical


def test_accel1_hybrid_cannot_rescue_bad_pure_cueq_training(monkeypatch, tmp_path: Path) -> None:
    import mace.calculators

    _FakeMaceCalculator.pure_bad = True
    monkeypatch.setattr(mace.calculators, "MACECalculator", _FakeMaceCalculator)
    realization, inference, inference_parity, training_parity = mdstats.qualify_cueq_realization(
        model_path=tmp_path / "fake.model", head="omat_pbe", structures=_structures(),
        device="cpu", dtype="float32", foundation_potential_digest="a" * 64,
        adapter_version="test", probe=_probe(), prefer_hybrid=True,
    )
    assert not realization.qualified
    assert realization.resolved_kernel_mode == "cueq_oeq_hybrid"
    assert realization.training_kernel_mode == "cueq_pure"
    assert inference_parity is not None and inference_parity.passed
    assert training_parity is not None and not training_parity.passed
    assert "training cannot be authorized" in (realization.failure_reason or "")
    assert "Emax=" in (realization.failure_reason or "")
    assert "Fmax=" in (realization.failure_reason or "")
    assert "Dmax=" in (realization.failure_reason or "")
    assert "selection_identical=" in (realization.failure_reason or "")


def test_accel1_qualifier_condenses_mace_torch_userwarnings(monkeypatch, tmp_path: Path) -> None:
    import warnings
    import mace.calculators
    import mdstats.training_data.mace_compatibility as compatibility

    class _WarningMaceCalculator(_FakeMaceCalculator):
        pure_bad = False

        def __init__(self, **kwargs):
            warnings.warn_explicit(
                "To copy construct from a tensor, it is recommended to use "
                "sourceTensor.detach().clone() rather than torch.tensor(sourceTensor).",
                UserWarning, "/runtime/site-packages/mace/modules/models.py", 86,
            )
            warnings.warn_explicit(
                "The TorchScript type system doesn't support instance-level annotations "
                "on empty non-base types in `__init__`.",
                UserWarning, "/usr/lib/python3.11/ast.py", 418,
            )
            super().__init__(**kwargs)

    monkeypatch.setattr(mace.calculators, "MACECalculator", _WarningMaceCalculator)
    with compatibility._EMITTED_LOCK:
        compatibility._EMITTED_SIGNATURES.clear()
    with warnings.catch_warnings(record=True) as observed:
        warnings.simplefilter("always")
        realization, _, _, _ = mdstats.qualify_cueq_realization(
            model_path=tmp_path / "fake.model", head="omat_pbe", structures=_structures(),
            device="cpu", dtype="float32", foundation_potential_digest="a" * 64,
            adapter_version="test", probe=_probe(oeq=False), prefer_hybrid=False,
        )

    assert realization.qualified
    assert [item.category for item in observed] == [mdstats.MaceRuntimeCompatibilityWarning]
    text = str(observed[0].message)
    assert "MACE CuEq/e3nn acceleration qualification" in text
    assert "tensor-copy construction warning" in text
    assert "TorchScript instance-annotation warning" in text


def test_accel1_missing_cueq_is_fail_closed(tmp_path: Path) -> None:
    probe = mdstats.MaceAccelerationProbe(
        device="cpu", torch_version="test", torch_cuda_version=None,
        cuda_available=False, mace_version="0.3.16",
        calculator_enable_cueq_supported=True, cueq_versions=(), cueq_imports_passed=False,
        model_smoke_attempted=False, model_smoke_passed=None,
        finite_energy=None, finite_forces=None, finite_stress=None,
        error_type="ModuleNotFoundError", error_message="cueq unavailable",
        calculator_enable_oeq_supported=True, oeq_version=None, oeq_import_passed=False,
    )
    realization, _, inference_parity, training_parity = mdstats.qualify_cueq_realization(
        model_path=tmp_path / "fake.model", head="omat_pbe", structures=_structures(),
        device="cpu", dtype="float32", foundation_potential_digest="a" * 64,
        adapter_version="test", probe=probe, prefer_hybrid=True,
    )
    assert not realization.qualified
    assert realization.resolved_kernel_mode == "cueq_unresolved"
    assert inference_parity is None and training_parity is None
    with pytest.raises(mdstats.TrainingDataInputError):
        realization.calculator_kwargs()


def test_accel1_optimizer_binds_training_realization_and_rejects_hybrid() -> None:
    policy = mdstats.MaceAccelerationPolicy(backend="cueq")
    opt = mdstats.MaceOptimizerPolicy(
        acceleration_policy=policy, acceleration_realization_digest="d" * 64,
        resolved_acceleration_kernel_mode="cueq_pure",
    )
    assert mdstats.MaceOptimizerPolicy.from_dict(opt.to_dict()) == opt
    with pytest.raises(mdstats.TrainingDataInputError, match="inference-only"):
        mdstats.MaceOptimizerPolicy(
            acceleration_policy=policy, acceleration_realization_digest="e" * 64,
            resolved_acceleration_kernel_mode="cueq_oeq_hybrid",
        )

@pytest.mark.slow
def test_accel1_real_e3nn_reference_qualifies_uploaded_foundations(monkeypatch) -> None:
    """Real-model acceptance: e3nn is the numerical reference for both foundations."""
    import os

    cases = (
        ("MDSTATS_TEST_MH1_MODEL", "mace_mh_1", "omat_pbe"),
        ("MDSTATS_TEST_MPA0_MODEL", "mace_mpa_0", "default"),
    )
    structures = _structures()
    for env_name, family, head in cases:
        raw = os.environ.get(env_name)
        if not raw:
            pytest.skip(f"{env_name} is not set")
        model = Path(raw)
        if not model.is_file():
            pytest.skip(f"{env_name} does not point to a file")
        potential = mdstats.MaceFoundationSpec(
            family=family,
            requested_head=head,
            requested_atomic_numbers=(11, 17),
        ).resolve_file(model)
        for dtype in ("float32", "float64"):
            realization, inference = mdstats.qualify_e3nn_realization(
                model_path=model,
                head=head,
                structures=structures,
                device="cpu",
                dtype=dtype,
                foundation_potential_digest=potential.content_digest,
                adapter_version="mh1-accel1-test",
            )
            assert realization.qualified, realization.failure_reason
            assert realization.requested_backend == "e3nn"
            assert realization.resolved_kernel_mode == "e3nn"
            assert realization.training_kernel_mode == "e3nn"
            assert realization.dtype == dtype
            assert inference.backend == "e3nn"
            assert inference.resolved_kernel_mode == "e3nn"
            assert realization.foundation_inference_identity_digest == inference.content_digest

def test_accel1_probe_records_oeq_constructor_capability(monkeypatch) -> None:
    import mdstats.training_data.acceleration as accel

    class _Ctor:
        def __init__(self, *, enable_cueq=False, enable_oeq=False):
            pass

    # Keep this test independent of whether accelerator distributions exist on host.
    import mace.calculators
    monkeypatch.setattr(mace.calculators, "MACECalculator", _Ctor)
    probe = accel.probe_mace_acceleration(device="cpu", run_model_smoke=False)
    assert probe.calculator_enable_cueq_supported
    assert probe.calculator_enable_oeq_supported


def test_accel1_evaluation_policy_binds_inference_realization() -> None:
    acceleration = mdstats.MaceAccelerationPolicy(backend="cueq")
    policy = mdstats.CheckpointEvaluationPolicy(
        acceleration_policy=acceleration,
        acceleration_realization_digest="a" * 64,
        resolved_acceleration_kernel_mode="cueq_oeq_hybrid",
    )
    restored = mdstats.CheckpointEvaluationPolicy.from_dict(policy.to_dict())
    assert restored == policy
    assert restored.to_dict()["schema"] == "mdstats.checkpoint-evaluation-policy.v8"
    assert restored.resolved_acceleration_kernel_mode == "cueq_oeq_hybrid"

def test_accel1_legacy_probe_roundtrip_preserves_v1_digest() -> None:
    import mdstats.training_data.acceleration as accel

    legacy = accel.MaceAccelerationProbe(
        device="cpu", torch_version="legacy", torch_cuda_version=None,
        cuda_available=False, mace_version="0.3.16",
        calculator_enable_cueq_supported=True,
        cueq_versions=(("cuequivariance", None),), cueq_imports_passed=False,
        model_smoke_attempted=False, model_smoke_passed=None,
        finite_energy=None, finite_forces=None, finite_stress=None,
        error_type="ModuleNotFoundError", error_message="legacy",
        serialization_schema=accel.MACE_ACCELERATION_PROBE_LEGACY_SCHEMA,
    )
    payload = legacy.to_dict()
    assert payload["schema"] == "mdstats.mace-acceleration-probe.v1"
    assert "calculator_enable_oeq_supported" not in payload
    restored = accel.MaceAccelerationProbe.from_dict(payload)
    assert restored.to_dict() == payload
    corrupted = dict(payload)
    corrupted["content_digest"] = "0" * 64
    with pytest.raises(mdstats.TrainingDataSerializationError, match="digest mismatch"):
        accel.MaceAccelerationProbe.from_dict(corrupted)

def test_accel1_qualified_cueq_requires_both_parity_records() -> None:
    with pytest.raises(mdstats.TrainingDataInputError, match="requires both"):
        mdstats.AccelerationRealizationRecord(
            requested_backend="cueq", resolved_kernel_mode="cueq_pure",
            training_kernel_mode="cueq_pure", device="cuda", dtype="float32",
            foundation_inference_identity_digest="a" * 64,
            mace_version="0.3.16", qualified=True,
        )


def test_accel1_passing_parity_record_cannot_hide_selection_change() -> None:
    policy = mdstats.MaceAccelerationParityPolicy()
    with pytest.raises(mdstats.TrainingDataInputError, match="identical selection"):
        mdstats.MaceAccelerationParityRecord(
            reference_mode="e3nn", candidate_mode="cueq_pure", dtype="float32",
            structure_count=2, atom_count=4,
            energy_max_abs=0.0, energy_rmse=0.0,
            force_max_abs=0.0, force_rmse=0.0,
            stress_max_abs=0.0, stress_rmse=0.0,
            descriptor_max_abs=0.0, descriptor_rmse=0.0,
            reference_selection=("q0000",), candidate_selection=("q0001",),
            policy_digest=policy.policy_digest, passed=True,
        )


def test_doctor_acceleration_corpus_has_local_numpy_dependency() -> None:
    """Regression for CERT1 doctor NameError: np was previously only imported elsewhere."""
    from mdstats.training_data import campaign_cli

    corpus = campaign_cli._doctor_acceleration_corpus(_structures()[0])
    assert len(corpus) >= 2
    assert all(len(atoms) == 2 for atoms in corpus)


def test_accel1_splits_multhead_source_inference_from_selected_head_training(monkeypatch, tmp_path: Path) -> None:
    import mace.calculators

    class _PhaseAwareMaceCalculator(_FakeMaceCalculator):
        def __init__(self, *, model_paths=None, enable_cueq=False, enable_oeq=False, **kwargs):
            self._is_training_foundation = "derived" in str(model_paths)
            super().__init__(enable_cueq=enable_cueq, enable_oeq=enable_oeq, **kwargs)

        @property
        def _delta(self) -> float:
            if self.enable_cueq and not self.enable_oeq:
                return 1.0e-8 if self._is_training_foundation else 1.0e-1
            if self.enable_cueq and self.enable_oeq:
                return 2.0e-8
            return 0.0

    monkeypatch.setattr(mace.calculators, "MACECalculator", _PhaseAwareMaceCalculator)
    realization, inference, inference_parity, training_parity = mdstats.qualify_cueq_realization(
        model_path=tmp_path / "multihead.model",
        head="omat_pbe",
        training_model_path=tmp_path / "derived-omat_pbe.model",
        training_head="omat_pbe",
        structures=_structures(), device="cpu", dtype="float32",
        foundation_potential_digest="a" * 64, adapter_version="test",
        probe=_probe(oeq=True), prefer_hybrid=True,
    )
    assert realization.qualified
    assert realization.resolved_kernel_mode == "cueq_oeq_hybrid"
    assert realization.training_kernel_mode == "cueq_pure"
    assert inference.resolved_kernel_mode == "cueq_oeq_hybrid"
    assert inference_parity is not None and inference_parity.passed
    assert training_parity is not None and training_parity.passed
    assert inference_parity.content_digest != training_parity.content_digest


def test_accel1_reports_source_inference_block_separately_when_training_foundation_passes(monkeypatch, tmp_path: Path) -> None:
    import mace.calculators

    class _PhaseAwareMaceCalculator(_FakeMaceCalculator):
        def __init__(self, *, model_paths=None, enable_cueq=False, enable_oeq=False, **kwargs):
            self._is_training_foundation = "derived" in str(model_paths)
            super().__init__(enable_cueq=enable_cueq, enable_oeq=enable_oeq, **kwargs)

        @property
        def _delta(self) -> float:
            if self.enable_cueq and not self.enable_oeq:
                return 1.0e-8 if self._is_training_foundation else 1.0e-1
            return 0.0

    monkeypatch.setattr(mace.calculators, "MACECalculator", _PhaseAwareMaceCalculator)
    realization, _, inference_parity, training_parity = mdstats.qualify_cueq_realization(
        model_path=tmp_path / "multihead.model",
        head="omat_pbe",
        training_model_path=tmp_path / "derived-omat_pbe.model",
        training_head="omat_pbe",
        structures=_structures(), device="cpu", dtype="float32",
        foundation_potential_digest="a" * 64, adapter_version="test",
        probe=_probe(oeq=False), prefer_hybrid=True,
    )
    assert not realization.qualified
    assert inference_parity is None
    assert training_parity is not None and training_parity.passed
    reason = realization.failure_reason or ""
    assert "source-foundation inference parity failed" in reason
    assert "training-foundation parity failed" not in reason
