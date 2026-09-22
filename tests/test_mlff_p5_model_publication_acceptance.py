"""Assembled acceptance for the P5 published full-model product.

Everything here runs through the real P1-P5 owners with the real MACE
reconstruction and serialization path. The central claims - that the
*selected* representative is what gets published, that the published file is a
usable MACE model, and that an already-completed campaign can obtain that file
without retraining - cannot be established by a toy stand-in, so none is used
below the owners that make them true.

The campaign is built once for the module: it is a real trained campaign, and
rebuilding it per case would buy nothing but minutes.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d  # noqa: F401
from tests._mlff_post_selection_fixture import (
    PostSelectionHarness,
    build_selected_campaign,
    load_context,
    run_cross_validate,
    run_train_production,
)

from mdstats.training_data.campaign_lifecycle import campaign_owner_snapshot
from mdstats.training_data.campaign_post_selection_runtime import (
    build_post_selection_context,
    resolve_current_final_production_publication,
)
from mdstats.training_data.post_selection_model_products import (
    campaign_models_root,
    resolve_current_final_production_model_publication,
)
from mdstats.training_data.post_selection_model_publication import (
    PUBLICATION_PROJECTION_FILENAME,
    SERIALIZATION_FORMAT_TORCH_FULL_MODEL,
)
from mdstats.training_data.post_selection_product_observation import (
    PRODUCT_STATE_BLOCKED,
    PRODUCT_STATE_COMPLETE,
    PRODUCT_STATE_WAITING,
    observe_current_product,
)
from mdstats.training_data.post_selection_product_observation import (
    required_final_seed_locators,
)
from mdstats.training_data.post_selection_store import (
    POINTER_FINAL_MODEL_PUBLICATION,
    POINTER_ASSESSMENT_POSITION,
    open_post_selection_store,
    read_current_post_selection_pointer,
)


@pytest.fixture(scope="module")
def published(tmp_path_factory):
    """One real campaign driven to a complete final-production product."""

    tmp_path = tmp_path_factory.mktemp("p5-model-publication")
    harness = PostSelectionHarness()
    config, workspace = build_selected_campaign(tmp_path)
    assert run_cross_validate(config, harness) == 0
    assert run_train_production(config, harness) == 0
    return config, Path(workspace), harness


def _context(config: Path):
    cfg, paths, store = load_context(config)
    return build_post_selection_context(cfg, paths, store), paths, store


def _resolved(config: Path):
    context, paths, store = _context(config)
    try:
        decision = resolve_current_final_production_publication(context)
        record = resolve_current_final_production_model_publication(context, decision)
        return decision, record, paths
    finally:
        store.close()


def test_published_model_follows_the_selected_representative_not_the_terminal_epoch(
    published,
):
    """The motivating defect: MACE saves the last epoch, P5 selects another."""

    config, _workspace, _harness = published
    decision, record, paths = _resolved(config)
    assert record is not None
    assert record.member_ids == tuple(decision.published_member_ids)

    for member, evidence in zip(
        record.members, decision.published_seed_evidence, strict=True
    ):
        # The published product is bound to the exact selected checkpoint...
        assert (
            member.representative_checkpoint_sha256
            == evidence.representative_checkpoint_sha256
        )
        selected_epoch = int(
            re.search(r"_epoch-(\d+)\.pt$", evidence.checkpoint_relative_path).group(1)
        )
        checkpoints = sorted(
            int(re.search(r"_epoch-(\d+)\.pt$", item.name).group(1))
            for item in (
                Path(paths.internal)
                / "post-selection"
                / f"g{decision.binding.campaign_generation}"
                / "runs"
                / evidence.run_identity
                / "checkpoints"
            ).glob("model_run-*_epoch-*.pt")
        )
        # ... and the fixture's monitored error grows with epoch, so the
        # selected representative is deliberately *not* the terminal one.
        assert selected_epoch != max(checkpoints), (
            "this acceptance case is only meaningful when the selected "
            "representative differs from the trainer's terminal epoch"
        )


def test_published_file_is_a_complete_reloadable_mace_model(published):
    """Not a checkpoint dict, not a state dict, not a symlink, not ML-IAP."""

    import torch

    config, _workspace, _harness = published
    _decision, record, paths = _resolved(config)
    models_root = Path(paths.models)
    for member in record.members:
        path = models_root / member.model_relative_path
        assert path.is_file() and not path.is_symlink()
        assert path.stat().st_size == member.model_size_bytes
        assert hashlib.sha256(path.read_bytes()).hexdigest() == member.model_sha256

        model = torch.load(path, map_location="cpu", weights_only=False)
        assert not isinstance(model, dict), "a checkpoint dictionary is not a product"
        assert hasattr(model, "state_dict")
        # Inference mode is object state the tensor state dict cannot carry, so
        # it is checked explicitly rather than assumed from tensor equality.
        assert not model.training
        assert all(not module.training for module in model.modules())
        dtypes = {
            str(tensor.dtype)
            for _name, tensor in model.named_parameters()
            if torch.is_floating_point(tensor)
        }
        assert dtypes == {f"torch.{member.model_dtype}"}
    assert record.serialization_format == SERIALIZATION_FORMAT_TORCH_FULL_MODEL


def test_published_model_state_equals_the_authenticated_provider_realization(published):
    """The bytes carry the exact state P5 evaluated, by the shared digest owner."""

    import torch

    from mdstats.training_data.model_features import (
        mace_model_execution_architecture_digest,
        mace_model_state_digest,
        mace_model_state_dict_clone,
    )

    config, _workspace, _harness = published
    _decision, record, paths = _resolved(config)
    for member in record.members:
        model = torch.load(
            Path(paths.models) / member.model_relative_path,
            map_location="cpu",
            weights_only=False,
        )
        assert mace_model_state_digest(mace_model_state_dict_clone(model)) == (
            member.model_state_sha256
        )
        assert mace_model_execution_architecture_digest(model) == (
            member.model_execution_architecture_digest
        )


def test_published_model_performs_bounded_finite_inference(published):
    """Structural/operational usability through the supported consumer path.

    No numerical threshold is invented here: this case proves the published
    file loads through the supported MACE calculator path and produces finite
    energies and forces on non-locked known geometry.
    """

    import numpy as np
    import torch
    from ase import Atoms

    config, _workspace, _harness = published
    _decision, record, paths = _resolved(config)
    member = record.members[0]
    model = torch.load(
        Path(paths.models) / member.model_relative_path,
        map_location="cpu",
        weights_only=False,
    )
    try:
        from mace.calculators import MACECalculator
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"the supported MACE consumer path is unavailable: {exc}")
    heads = tuple(str(value) for value in (getattr(model, "heads", ()) or ()))
    path = str(Path(paths.models) / member.model_relative_path)
    kwargs = {"model_paths": path, "device": "cpu", "default_dtype": member.model_dtype}
    if len(heads) > 1:
        kwargs["head"] = record.target_head_name
    calculator = MACECalculator(**kwargs)
    atoms = Atoms("LiO", positions=[[0.0, 0.0, 0.0], [0.0, 0.0, 2.0]], cell=np.eye(3) * 8.0, pbc=True)
    atoms.calc = calculator
    energy = float(atoms.get_potential_energy())
    forces = np.asarray(atoms.get_forces(), dtype=float)
    assert np.isfinite(energy)
    assert forces.shape == (2, 3) and np.all(np.isfinite(forces))


def test_train_production_prints_the_canonical_product_locator(published, capsys):
    """Discovery must not require inspecting internal hash directories."""

    config, _workspace, harness = published
    # A second invocation is create-or-verify: no TRAIN2, no EVAL2, same output.
    before = len(harness.runs), len(harness.evaluations)
    assert run_train_production(config, harness) == 0
    assert (len(harness.runs), len(harness.evaluations)) == before
    printed = capsys.readouterr().out

    _decision, record, paths = _resolved(config)
    for member in record.members:
        line = [
            row
            for row in printed.splitlines()
            if row.startswith("[PRODUCT]") and f"member={member.member_id}" in row
        ]
        assert line, f"no product line printed for {member.member_id}"
        row = line[-1]
        assert str(Path(paths.models) / member.model_relative_path) in row
        assert member.model_sha256 in row
        assert f"head={record.target_head_name}" in row
        # Never the trainer's run-root terminal model.
        assert "/runs/" not in row.split("model=")[1].split()[0]


def test_operator_projection_is_written_and_is_not_authority(published):
    config, _workspace, _harness = published
    decision, record, paths = _resolved(config)
    projection = (
        Path(paths.models)
        / "production"
        / f"g{decision.binding.campaign_generation}"
        / f"N_{decision.binding.n_selected}"
        / PUBLICATION_PROJECTION_FILENAME
    )
    payload = json.loads(projection.read_text(encoding="utf-8"))
    assert payload["authority"] == "non_authoritative_operator_projection"
    assert payload["model_publication_digest"] == record.content_digest
    assert payload["model_artifact_set_digest"] == record.model_artifact_set_digest

    # A stale projection can never override content-addressed authority.
    projection.write_text(json.dumps({"schema": "nonsense"}), encoding="utf-8")
    _cfg, paths2, store = load_context(config)
    try:
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        observation = observe_current_product(paths2, bindings[0], pointers)
        assert observation.state == PRODUCT_STATE_COMPLETE
    finally:
        store.close()
    # Repaired by projection-only work: no retraining, no re-evaluation.
    assert run_train_production(config, _harness) == 0
    assert json.loads(projection.read_text(encoding="utf-8"))[
        "model_publication_digest"
    ] == record.content_digest


def test_status_authenticates_product_bytes_and_is_side_effect_free(published):
    config, _workspace, _harness = published
    _cfg, paths, store = load_context(config)
    try:
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        binding = bindings[0]
        models_root = Path(paths.models)
        before = sorted(
            str(item.relative_to(models_root)) for item in models_root.rglob("*")
        )
        observation = observe_current_product(paths, binding, pointers)
        assert observation.state == PRODUCT_STATE_COMPLETE
        after = sorted(
            str(item.relative_to(models_root)) for item in models_root.rglob("*")
        )
        assert before == after, "observation created state"

        member = observation.model_publication.members[0]
        target = models_root / member.model_relative_path
        original = target.read_bytes()
        try:
            # Same size, different bytes: a cheap existence check would call
            # this COMPLETE.
            target.write_bytes(b"\x00" + original[1:])
            corrupted = observe_current_product(paths, binding, pointers)
            assert corrupted.state == PRODUCT_STATE_BLOCKED
            assert "not authentic" in corrupted.message
        finally:
            target.write_bytes(original)
        assert observe_current_product(paths, binding, pointers).state == (
            PRODUCT_STATE_COMPLETE
        )
    finally:
        store.close()


def test_missing_model_publication_is_reclosure_not_completion(published):
    """A decision with no materialized model is recoverable, never COMPLETE."""

    config, _workspace, harness = published
    _cfg, paths, store = load_context(config)
    try:
        _revision, bindings, _pointers = campaign_owner_snapshot(store)
        binding = bindings[0]
        key = (
            f"post_selection:{binding.content_digest}:"
            f"{POINTER_FINAL_MODEL_PUBLICATION}"
        )
        with store.exclusive_transaction() as db:
            previous = db.execute(
                "SELECT value FROM meta WHERE key=?", (key,)
            ).fetchone()[0]
            db.execute("DELETE FROM meta WHERE key=?", (key,))
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        observation = observe_current_product(paths, bindings[0], pointers)
        assert observation.state == PRODUCT_STATE_WAITING
        assert "reclose the product representation" in observation.message
    finally:
        store.close()

    # Representation-only reclosure: zero TRAIN2, zero EVAL2.
    before = len(harness.runs), len(harness.evaluations)
    assert run_train_production(config, harness) == 0
    assert (len(harness.runs), len(harness.evaluations)) == before

    _cfg, paths, store = load_context(config)
    try:
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        observation = observe_current_product(paths, bindings[0], pointers)
        assert observation.state == PRODUCT_STATE_COMPLETE
        successor = observation.model_publication
        assert (
            read_current_post_selection_pointer(
                store, binding=bindings[0], kind=POINTER_FINAL_MODEL_PUBLICATION
            )
            == successor.content_digest
        )
    finally:
        store.close()
    # A fresh representation of the *same* decision and the same ordered member
    # set.  Full-model serialization is not byte-deterministic, so a rebuilt
    # representation legitimately has new bytes; what may never change is the
    # science it represents.
    decision, _record, _paths = _resolved(config)
    assert successor.final_publication_decision_digest == decision.content_digest
    assert successor.final_publication_member_digest == decision.member_digest
    assert successor.member_ids == tuple(decision.published_member_ids)
    assert previous


def test_corrupt_leaf_recovers_at_a_fresh_locator_without_overwrite(published):
    """Same reconstructed SHA must not wedge reclosure on an occupied leaf."""

    config, _workspace, harness = published
    decision, record, paths = _resolved(config)
    member = record.members[0]
    target = Path(paths.models) / member.model_relative_path
    original = target.read_bytes()
    target.write_bytes(b"\x00" * len(original))

    before = len(harness.runs), len(harness.evaluations)
    assert run_train_production(config, harness) == 0
    assert (len(harness.runs), len(harness.evaluations)) == before

    _decision, successor, paths = _resolved(config)
    successor_member = successor.member_for(member.member_id)
    assert successor_member.model_relative_path != member.model_relative_path
    assert successor_member.artifact_locator_token != member.artifact_locator_token
    # The corrupted leaf is never overwritten; it stays inert residue.
    assert target.read_bytes() == b"\x00" * len(original)
    fresh = Path(paths.models) / successor_member.model_relative_path
    assert hashlib.sha256(fresh.read_bytes()).hexdigest() == (
        successor_member.model_sha256
    )
    # The same decision, the same members: representation only.
    assert successor.final_publication_decision_digest == decision.content_digest
    assert successor.member_ids == record.member_ids


def test_same_run_evidence_at_a_different_position_is_not_currentness(published):
    """Only the exact canonical locator key may satisfy a final-seed parent."""

    config, _workspace, _harness = published
    _cfg, paths, store = load_context(config)
    try:
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        binding = bindings[0]
        prefix = (
            f"post_selection:{binding.content_digest}:{POINTER_ASSESSMENT_POSITION}:"
        )
        # The *required* final-seed positions specifically: this pointer kind
        # also carries CV fold positions, which are not this decision's parents.
        observation = observe_current_product(paths, binding, pointers)
        store_view = open_post_selection_store(paths, binding, create=False)
        required, failure = required_final_seed_locators(
            binding, observation.decision, store_view
        )
        assert failure is None and required
        key, value = sorted(required.items())[0]
        assert pointers.get(key) == value
        forged = prefix + ("f" * 64)
        with store.exclusive_transaction() as db:
            # Plant the same run-evidence digest at a *different* position and
            # remove it from the canonical one.  A value search would find it;
            # key identity must not.
            db.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (forged, value)
            )
            db.execute("DELETE FROM meta WHERE key=?", (key,))
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        observation = observe_current_product(paths, bindings[0], pointers)
        assert observation.state == PRODUCT_STATE_WAITING
        assert "assessment position has advanced" in observation.message
        with store.exclusive_transaction() as db:
            db.execute(
                "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, value)
            )
            db.execute("DELETE FROM meta WHERE key=?", (forged,))
        _revision, bindings, pointers = campaign_owner_snapshot(store)
        assert observe_current_product(paths, bindings[0], pointers).state == (
            PRODUCT_STATE_COMPLETE
        )
    finally:
        store.close()


def test_storage_owner_certifies_the_exact_published_models(published):
    """The models root stays a container; P5 owns the exact current artifacts."""

    from mdstats.training_data.storage.owners import post_selection_views

    config, _workspace, _harness = published
    cfg, paths, store = load_context(config)
    try:
        _revision, bindings, _pointers = campaign_owner_snapshot(store)
        views, unresolved = post_selection_views(
            cfg,
            paths,
            store,
            current_generation=int(bindings[0].campaign_generation),
        )
    finally:
        store.close()
    assert not unresolved, unresolved
    _decision, record, paths2 = _resolved(config)
    model_views = {
        view.artifact_id: view
        for view in views
        if view.artifact_id.startswith("p5:published_model:")
    }
    assert len(model_views) == len(record.members)
    for member in record.members:
        view = model_views[f"p5:published_model:{member.member_id}:{member.model_sha256}"]
        assert view.path == Path(paths2.models) / member.model_relative_path
        assert view.current and view.immutable and view.hot_path_required
    publication_view = next(
        view for view in views if view.artifact_id.startswith("p5:publication:")
    )
    assert record.content_digest in publication_view.state_identity
    assert record.model_artifact_set_digest in publication_view.state_identity
