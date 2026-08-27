"""G6/G7/G9 requalification acceptance tests.

Covers workplans/active/MLFF_TARGET_SIZE_EVAL2_STAGED_EXECUTION_OPT1_G6_G7_REQUALIFICATION_AMENDMENT.md.

The amendment's blocking defect: strict ``load_state_dict`` compatibility
based on exact model class / state-key set / tensor shapes / tensor dtypes is
not a sufficient execution-architecture proof for MACE, because a retained
``MACECalculator`` shell caches non-state configuration (cutoff radius used
for neighbor-list construction) at construction time that is never refreshed
by ``load_state_dict``.  These tests use real MACE 0.3.x models -- not mocks
-- to prove the canonical execution-architecture identity (R17A) rejects a
same-state-structure/different-``r_max`` swap, accepts a genuine
same-architecture/different-weight swap, poisons a shell whose transaction
fails, and that calibration-profile/graph-policy identity derive from the
same canonical authority (R18A/R19A).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch")
pytest.importorskip("e3nn")
pytest.importorskip("mace")

from ase import Atoms
from e3nn import o3
from mace import modules, tools
from mace.calculators import MACECalculator

from mdstats.training_data.model_features import (
    MaceCalculatorProvider,
    MaceDescriptorPolicy,
    MaceModelStateCompatibilityError,
    STATIC_INFERENCE_EVIDENCE_SEMANTICS,
    StaticInferenceRuntimeAuthority,
    _mace_graph_policy_key,
    _mace_model_execution_architecture_descriptor,
    digest,
)


def _tiny_mace(
    *,
    r_max: float = 4.0,
    num_bessel: int = 4,
    num_polynomial_cutoff: int = 3,
    interaction_cls_name: str = "RealAgnosticResidualInteractionBlock",
    num_interactions: int = 2,
    correlation: int = 2,
    atomic_numbers: tuple[int, ...] = (1, 8),
    heads: list[str] | None = None,
    seed: int = 0,
    scale: float = 1.0,
    shift: float = 0.0,
    atomic_energies: tuple[float, ...] | None = None,
    dtype: torch.dtype = torch.float64,
):
    previous = torch.get_default_dtype()
    torch.set_default_dtype(dtype)
    torch.manual_seed(seed)
    try:
        table = tools.AtomicNumberTable(list(atomic_numbers))
        kwargs = dict(
            r_max=r_max,
            num_bessel=num_bessel,
            num_polynomial_cutoff=num_polynomial_cutoff,
            max_ell=1,
            interaction_cls=modules.interaction_classes[interaction_cls_name],
            interaction_cls_first=modules.interaction_classes[interaction_cls_name],
            num_interactions=num_interactions,
            num_elements=len(atomic_numbers),
            hidden_irreps=o3.Irreps("8x0e + 8x1o"),
            MLP_irreps=o3.Irreps("4x0e"),
            gate=torch.nn.functional.silu,
            atomic_energies=np.array(
                atomic_energies if atomic_energies is not None else [0.0] * len(atomic_numbers)
            ),
            avg_num_neighbors=2.0,
            atomic_numbers=table.zs,
            correlation=correlation,
            atomic_inter_scale=scale,
            atomic_inter_shift=shift,
        )
        if heads is not None:
            kwargs["heads"] = heads
        model = modules.ScaleShiftMACE(**kwargs)
    finally:
        torch.set_default_dtype(previous)
    return model.to(dtype=dtype)


def _pair(distance: float) -> Atoms:
    return Atoms(
        "H2",
        positions=[[0.0, 0.0, 0.0], [distance, 0.0, 0.0]],
        cell=[30.0, 30.0, 30.0],
        pbc=False,
    )


def _save(model, path: Path) -> Path:
    torch.save(model, path)
    return path


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fresh_provider(path: Path) -> MaceCalculatorProvider:
    return MaceCalculatorProvider.from_model_path(path, device="cpu", default_dtype="float64")


# --------------------------------------------------------------------------
# G6.1 -- different-r_max false-compatibility regression (mandatory blocker)
# --------------------------------------------------------------------------


def test_g6_1_different_r_max_false_compatibility_is_rejected(tmp_path: Path) -> None:
    model_a = _tiny_mace(r_max=4.0, seed=1)
    model_b = _tiny_mace(r_max=6.0, seed=1)  # same architecture, only cutoff differs
    path_a = _save(model_a, tmp_path / "a.model")
    path_b = _save(model_b, tmp_path / "b.model")

    # Old structural state checks alone would not distinguish the pair: same
    # model class, same state-key set, same tensor shapes/dtypes (r_max is a
    # 0-d buffer, so its differing VALUE is invisible to shape/dtype checks).
    state_a, state_b = model_a.state_dict(), model_b.state_dict()
    assert set(state_a) == set(state_b)
    for key in state_a:
        assert tuple(state_a[key].shape) == tuple(state_b[key].shape)
        assert state_a[key].dtype == state_b[key].dtype

    # Canonical execution-architecture digests differ.
    digest_a = digest(_mace_model_execution_architecture_descriptor(model_a))
    digest_b = digest(_mace_model_execution_architecture_descriptor(model_b))
    assert digest_a != digest_b

    provider = _fresh_provider(path_a)
    original_sha = provider.checkpoint_identity.checkpoint_sha256

    # The retained provider does NOT hot-swap the incoming weights.
    with pytest.raises(MaceModelStateCompatibilityError, match="execution-architecture identity differs"):
        provider.load_compatible_model_state(path_b, expected_sha256=_sha(path_b))

    # The retained shell is untouched (checkpoint identity unchanged) and
    # usable -- rejection is not itself a poisoning event.
    assert provider.checkpoint_identity.checkpoint_sha256 == original_sha
    assert not provider._poisoned

    # Safe reconstruction path: build a fresh provider for the incoming
    # checkpoint instead.
    rebuilt = _fresh_provider(path_b)

    # Forward-equivalence geometry actually exercises the cutoff difference:
    # a separation between the two cutoffs, so the pair is disconnected under
    # r_max=4.0 but connected under r_max=6.0.
    atoms = _pair(5.0)
    energy_rebuilt = float(rebuilt._calculator.get_potential_energy(atoms))
    fresh_reference = MACECalculator(model_paths=str(path_b), device="cpu", default_dtype="float64")
    energy_fresh = float(fresh_reference.get_potential_energy(atoms))
    assert energy_rebuilt == pytest.approx(energy_fresh, abs=1e-9)

    # Demonstrate the actual retained-calculator failure mode this amendment
    # closes: a raw ``load_state_dict`` into the ORIGINAL calculator's model
    # (bypassing the canonical-identity gate, as the pre-amendment code did)
    # leaves the calculator's cached ``r_max``/neighbor-list construction
    # stale, producing a WRONG energy relative to a fresh model_b provider on
    # this cutoff-sensitive geometry.
    stale_calculator = provider._calculator
    stale_calculator.models[0].load_state_dict(model_b.state_dict(), strict=True)
    stale_energy = float(stale_calculator.get_potential_energy(atoms))
    assert stale_energy != pytest.approx(energy_fresh, abs=1e-9)
    provider.close()


# --------------------------------------------------------------------------
# G6.2 -- genuine same-architecture real-MACE hot swap
# --------------------------------------------------------------------------


def test_g6_2_same_architecture_different_weights_hot_swaps(tmp_path: Path) -> None:
    model_a = _tiny_mace(seed=1, scale=1.0, shift=0.0, atomic_energies=(0.0, 0.0))
    model_b = _tiny_mace(seed=7, scale=2.5, shift=0.3, atomic_energies=(-13.6, -2000.0))
    path_a = _save(model_a, tmp_path / "a.model")
    path_b = _save(model_b, tmp_path / "b.model")
    sha_b = _sha(path_b)

    provider = _fresh_provider(path_a)
    original_digest = provider.runtime_architecture_digest

    new_identity = provider.load_compatible_model_state(path_b, expected_sha256=sha_b)

    assert new_identity.checkpoint_sha256 == sha_b
    # Provider/shell reuse actually occurred (same calculator instance).
    assert provider.checkpoint_identity.checkpoint_sha256 == sha_b

    # Post-swap canonical architecture invariant holds; digest is unchanged
    # because weights/calibration constants are deliberately excluded.
    assert provider.runtime_architecture_digest == original_digest

    fresh = _fresh_provider(path_b)
    assert provider.runtime_architecture_digest == fresh.runtime_architecture_digest

    atoms = _pair(2.0)  # well within r_max=4.0 so both models see the edge
    swapped_energy = float(provider._calculator.get_potential_energy(atoms))
    fresh_energy = float(fresh._calculator.get_potential_energy(atoms))
    assert swapped_energy == pytest.approx(fresh_energy, abs=1e-9)
    provider.close()
    fresh.close()


# --------------------------------------------------------------------------
# G6.3 -- identity coverage and negative cases
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "variant_kwargs",
    [
        pytest.param({"r_max": 6.0}, id="cutoff"),
        pytest.param({"atomic_numbers": (1, 6)}, id="species-table"),
        pytest.param({"heads": ["Default", "Other"]}, id="head-structure"),
        pytest.param({"num_bessel": 6}, id="radial-embedding"),
        pytest.param({"num_polynomial_cutoff": 5}, id="cutoff-function"),
        pytest.param(
            {"interaction_cls_name": "RealAgnosticInteractionBlock"}, id="interaction-architecture"
        ),
        pytest.param({"correlation": 3}, id="product-correlation-architecture"),
        pytest.param({"dtype": torch.float32}, id="dtype"),
    ],
)
def test_g6_3_architecture_dimension_differences_reject_hot_swap(variant_kwargs) -> None:
    baseline = _tiny_mace(seed=3)
    variant = _tiny_mace(seed=3, **variant_kwargs)
    baseline_digest = digest(_mace_model_execution_architecture_descriptor(baseline))
    variant_digest = digest(_mace_model_execution_architecture_descriptor(variant))
    assert baseline_digest != variant_digest


def test_g6_3_atomic_number_reordering_changes_identity() -> None:
    forward = _tiny_mace(seed=3, atomic_numbers=(1, 8))
    reordered = _tiny_mace(seed=3, atomic_numbers=(8, 1))
    assert digest(_mace_model_execution_architecture_descriptor(forward)) != digest(
        _mace_model_execution_architecture_descriptor(reordered)
    )


def test_g6_3_non_model_object_fails_closed_rather_than_reporting_compatible() -> None:
    from mdstats import TrainingDataInputError

    with pytest.raises(TrainingDataInputError):
        _mace_model_execution_architecture_descriptor(object())


def test_g6_3_same_architecture_different_calibration_constants_share_identity() -> None:
    """Weight-like calibration buffers (E0/scale/shift) must not gate hot swap."""

    a = _tiny_mace(seed=1, scale=1.0, shift=0.0, atomic_energies=(0.0, 0.0))
    b = _tiny_mace(seed=2, scale=9.0, shift=-4.0, atomic_energies=(-13.6, -2000.0))
    assert digest(_mace_model_execution_architecture_descriptor(a)) == digest(
        _mace_model_execution_architecture_descriptor(b)
    )


# --------------------------------------------------------------------------
# G6.4 -- transaction-failure regression
# --------------------------------------------------------------------------


def test_g6_4_failed_transaction_poisons_shell_and_blocks_later_inference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model_a = _tiny_mace(seed=1)
    model_b = _tiny_mace(seed=2)  # same architecture, different weights
    path_a = _save(model_a, tmp_path / "a.model")
    path_b = _save(model_b, tmp_path / "b.model")

    provider = _fresh_provider(path_a)
    target = provider._calculator.models[0]

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated post-load-hook failure")

    monkeypatch.setattr(target, "load_state_dict", _boom)

    with pytest.raises(MaceModelStateCompatibilityError, match="poisoned"):
        provider.load_compatible_model_state(path_b, expected_sha256=_sha(path_b))

    assert provider._poisoned

    # No later inference may reuse the contaminated shell.
    from mdstats.training_data.model_features import MaceDescriptorPolicy

    with pytest.raises(MaceModelStateCompatibilityError, match="poisoned"):
        provider.predict(_pair(2.0))
    with pytest.raises(MaceModelStateCompatibilityError, match="poisoned"):
        provider.get_descriptors(_pair(2.0), MaceDescriptorPolicy())
    with pytest.raises(MaceModelStateCompatibilityError, match="poisoned"):
        provider.load_compatible_model_state(path_b, expected_sha256=_sha(path_b))
    with pytest.raises(MaceModelStateCompatibilityError, match="poisoned"):
        provider.set_head("Default")


# --------------------------------------------------------------------------
# G7 -- profile compatibility and migration
# --------------------------------------------------------------------------


def test_g7_legacy_compatibility_schema_is_invalidated() -> None:
    payload = {"fixture": "g7-migration"}
    current = StaticInferenceRuntimeAuthority.compatibility_key(payload)
    legacy = digest(
        {
            "schema": "mdstats.static-inference-compatibility.v3",
            "evidence_semantics": STATIC_INFERENCE_EVIDENCE_SEMANTICS,
            **payload,
        }
    )
    assert current != legacy


def test_g7_different_execution_architecture_invalidates_compatibility_even_with_matching_state(
    tmp_path: Path,
) -> None:
    model_a = _tiny_mace(r_max=4.0, seed=1)
    model_b = _tiny_mace(r_max=6.0, seed=1)
    path_a = _save(model_a, tmp_path / "a.model")
    path_b = _save(model_b, tmp_path / "b.model")

    provider_a = _fresh_provider(path_a)
    provider_b = _fresh_provider(path_b)
    try:
        key_a = StaticInferenceRuntimeAuthority.compatibility_key(
            {"runtime_architecture_identity": provider_a.runtime_architecture_digest}
        )
        key_b = StaticInferenceRuntimeAuthority.compatibility_key(
            {"runtime_architecture_identity": provider_b.runtime_architecture_digest}
        )
        assert key_a != key_b
    finally:
        provider_a.close()
        provider_b.close()


def test_g7_same_architecture_profile_remains_reusable(tmp_path: Path) -> None:
    model_a = _tiny_mace(seed=1)
    model_b = _tiny_mace(seed=2)  # same architecture, different weights
    path_a = _save(model_a, tmp_path / "a.model")
    path_b = _save(model_b, tmp_path / "b.model")

    provider_a = _fresh_provider(path_a)
    provider_b = _fresh_provider(path_b)
    try:
        assert provider_a.runtime_architecture_digest == provider_b.runtime_architecture_digest
        key_a = StaticInferenceRuntimeAuthority.compatibility_key(
            {"runtime_architecture_identity": provider_a.runtime_architecture_digest}
        )
        key_b = StaticInferenceRuntimeAuthority.compatibility_key(
            {"runtime_architecture_identity": provider_b.runtime_architecture_digest}
        )
        assert key_a == key_b
    finally:
        provider_a.close()
        provider_b.close()


def test_g7_graph_policy_key_is_canonical_projection_and_tracks_cutoff(tmp_path: Path) -> None:
    model_a = _tiny_mace(r_max=4.0, seed=1)
    model_b = _tiny_mace(r_max=6.0, seed=1)
    provider_a = _fresh_provider(_save(model_a, tmp_path / "a.model"))
    provider_b = _fresh_provider(_save(model_b, tmp_path / "b.model"))
    try:
        assert _mace_graph_policy_key(provider_a._calculator) != _mace_graph_policy_key(
            provider_b._calculator
        )
    finally:
        provider_a.close()
        provider_b.close()


# --------------------------------------------------------------------------
# G9 -- dependent assembled provider/graph/profile requalification
# --------------------------------------------------------------------------


def test_g9_reusable_candidate_session_rebuilds_on_architecture_change_and_reuses_same_architecture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from mdstats.training_data import campaign_execution

    model_a = _tiny_mace(r_max=4.0, seed=1)
    model_b = _tiny_mace(r_max=6.0, seed=1)  # incompatible architecture
    model_c = _tiny_mace(r_max=6.0, seed=9)  # same architecture as model_b, different weights
    path_a = _save(model_a, tmp_path / "a.model")
    path_b = _save(model_b, tmp_path / "b.model")
    path_c = _save(model_c, tmp_path / "c.model")

    monkeypatch.setattr(
        campaign_execution,
        "_build_prepared_mace_candidate_provider",
        lambda prepared, path: _fresh_provider(Path(path)),
    )
    prepared = SimpleNamespace(policy=SimpleNamespace(target_head_name=None))
    session = campaign_execution.ReusableMaceCandidateProviderSession()

    first = session.acquire(prepared, path_a)
    assert session.rebuild_count == 1 and session.reuse_count == 0
    assert first.checkpoint_identity.checkpoint_sha256 == _sha(path_a)

    # Incompatible execution architecture (different r_max) rebuilds rather
    # than reusing graph/profile state whose compatibility dimensions changed.
    second = session.acquire(prepared, path_b)
    assert session.rebuild_count == 2 and session.reuse_count == 0
    assert second is not first
    assert second.checkpoint_identity.checkpoint_sha256 == _sha(path_b)

    # Genuinely same-architecture checkpoint reuses the intended provider shell.
    third = session.acquire(prepared, path_c)
    assert session.rebuild_count == 2 and session.reuse_count == 1
    assert third is second
    assert third.checkpoint_identity.checkpoint_sha256 == _sha(path_c)

    session.close()
