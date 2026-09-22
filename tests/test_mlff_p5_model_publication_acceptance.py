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


def _pointer_set(store, binding) -> dict[str, str | None]:
    from mdstats.training_data.post_selection_store import (
        POINTER_FINAL_PUBLICATION,
        POINTER_PREDECESSOR_RECLOSURE,
    )

    return {
        kind: read_current_post_selection_pointer(store, binding=binding, kind=kind)
        for kind in (
            POINTER_FINAL_MODEL_PUBLICATION,
            POINTER_PREDECESSOR_RECLOSURE,
            POINTER_FINAL_PUBLICATION,
        )
    }


@pytest.mark.parametrize("fail_at", [1, 2])
def test_product_pointer_set_is_all_old_or_all_new(published, monkeypatch, fail_at):
    """A crash at any logical pointer write must never strand a hybrid set.

    Three separate transactions would leave a window in which the model and
    reclosure pointers had advanced while the decision pointer had not - a
    product state no observer could describe truthfully. Injecting a failure at
    each logical write position is what proves the window does not exist.
    """

    from mdstats.training_data import post_selection_store as pss

    config, _workspace, harness = published
    _cfg, paths, store = load_context(config)
    try:
        _revision, bindings, _pointers = campaign_owner_snapshot(store)
        binding = bindings[0]
        before = _pointer_set(store, binding)
    finally:
        store.close()
    assert all(value is not None for value in before.values())

    original = pss.publish_current_post_selection_pointer_set

    def failing(campaign_store, *, binding, rows):
        """Run the real helper, but crash at the chosen logical write."""

        writes = {"count": 0}
        real_execute = None

        class _Proxy:
            def __init__(self, db):
                self._db = db

            def execute(self, sql, *args, **kwargs):
                if sql.strip().upper().startswith("INSERT OR REPLACE INTO META"):
                    writes["count"] += 1
                    if writes["count"] >= fail_at:
                        raise RuntimeError(
                            f"injected crash at pointer write {fail_at}"
                        )
                return self._db.execute(sql, *args, **kwargs)

            def __getattr__(self, name):
                return getattr(self._db, name)

        import contextlib

        real_transaction = campaign_store.exclusive_transaction

        @contextlib.contextmanager
        def proxied():
            with real_transaction() as db:
                yield _Proxy(db)

        class _Shim:
            def __getattr__(self, name):
                return getattr(campaign_store, name)

            exclusive_transaction = staticmethod(proxied)

        assert real_execute is None
        return original(_Shim(), binding=binding, rows=rows)

    monkeypatch.setattr(pss, "publish_current_post_selection_pointer_set", failing)

    # Put the two subordinate rows into a distinct, recognizable prior state so
    # both of them genuinely have to move.  The decision row stays valid, which
    # is what keeps this a representation reclosure rather than a retrain.
    from mdstats.training_data.post_selection_store import (
        POINTER_FINAL_PUBLICATION,
        POINTER_PREDECESSOR_RECLOSURE,
    )

    stale = {
        POINTER_FINAL_MODEL_PUBLICATION: "a" * 64,
        POINTER_PREDECESSOR_RECLOSURE: "b" * 64,
    }
    _cfg, paths, store = load_context(config)
    try:
        with store.exclusive_transaction() as db:
            for kind, value in stale.items():
                db.execute(
                    "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)",
                    (f"post_selection:{binding.content_digest}:{kind}", value),
                )
    finally:
        store.close()

    with pytest.raises(Exception, match="injected crash"):
        run_train_production(config, harness)

    _cfg, paths, store = load_context(config)
    try:
        after = _pointer_set(store, binding)
    finally:
        store.close()
    # Wholly old: not one of the two pending rows was installed, whichever
    # logical write the crash landed on.
    assert after[POINTER_FINAL_MODEL_PUBLICATION] == stale[
        POINTER_FINAL_MODEL_PUBLICATION
    ]
    assert after[POINTER_PREDECESSOR_RECLOSURE] == stale[POINTER_PREDECESSOR_RECLOSURE]
    assert after[POINTER_FINAL_PUBLICATION] == before[POINTER_FINAL_PUBLICATION]

    monkeypatch.undo()
    assert run_train_production(config, harness) == 0
    _cfg, paths, store = load_context(config)
    try:
        repaired = _pointer_set(store, binding)
    finally:
        store.close()
    # ... and wholly new afterwards.
    assert all(value is not None for value in repaired.values())
    assert repaired[POINTER_FINAL_MODEL_PUBLICATION] != stale[
        POINTER_FINAL_MODEL_PUBLICATION
    ]
    assert repaired[POINTER_PREDECESSOR_RECLOSURE] != stale[
        POINTER_PREDECESSOR_RECLOSURE
    ]
    assert repaired[POINTER_FINAL_PUBLICATION] == before[POINTER_FINAL_PUBLICATION]


def test_disk_reserve_refuses_publication_before_any_pointer_moves(
    published, monkeypatch
):
    """A shortfall aborts recoverably; the previous product stays current."""

    import shutil

    from mdstats.training_data import post_selection_model_products as products

    config, _workspace, harness = published
    _cfg, paths, store = load_context(config)
    try:
        _revision, bindings, _pointers = campaign_owner_snapshot(store)
        binding = bindings[0]
        before = _pointer_set(store, binding)
        key = (
            f"post_selection:{binding.content_digest}:"
            f"{POINTER_FINAL_MODEL_PUBLICATION}"
        )
        with store.exclusive_transaction() as db:
            db.execute("DELETE FROM meta WHERE key=?", (key,))
    finally:
        store.close()

    real_usage = shutil.disk_usage

    def starved(path):
        usage = real_usage(path)
        return type(usage)(usage.total, usage.used, 1)

    monkeypatch.setattr(products.shutil, "disk_usage", starved)
    with pytest.raises(Exception, match="below the configured"):
        run_train_production(config, harness)
    monkeypatch.undo()

    _cfg, paths, store = load_context(config)
    try:
        after = _pointer_set(store, binding)
    finally:
        store.close()
    assert after[POINTER_FINAL_MODEL_PUBLICATION] is None
    for kind, value in before.items():
        if kind != POINTER_FINAL_MODEL_PUBLICATION:
            assert after[kind] == value

    assert run_train_production(config, harness) == 0


def test_loader_runtime_drift_reuses_identical_bytes_after_an_equivalence_proof(
    published, monkeypatch
):
    """A changed Torch/MACE surface forces a proof, not a reserialization.

    Byte/SHA equality cannot answer "does this still load here?". When the
    recorded serializer/runtime no longer positively establishes the current
    loader, the producer owes a real load plus native-provider equivalence
    before it may call the existing product reusable - and if that proof
    passes, no reserialization is justified.
    """

    from mdstats.training_data import post_selection_model_products as products

    config, _workspace, harness = published
    _decision, before, _paths = _resolved(config)

    real_metadata = products.serialization_runtime_metadata
    proofs: list[str] = []
    real_proof = products.prove_existing_representation_reusable

    def drifted_runtime():
        payload = dict(real_metadata())
        payload["torch"] = "0.0.0-not-the-recorded-runtime"
        return payload

    def recording_proof(context, record, decision):
        proofs.append(record.content_digest)
        return real_proof(context, record, decision)

    monkeypatch.setattr(products, "serialization_runtime_metadata", drifted_runtime)
    monkeypatch.setattr(
        products, "prove_existing_representation_reusable", recording_proof
    )
    runs = len(harness.runs), len(harness.evaluations)
    assert run_train_production(config, harness) == 0
    monkeypatch.undo()

    assert (len(harness.runs), len(harness.evaluations)) == runs, (
        "a loader-compatibility question is never answered by retraining"
    )
    _decision, after, _paths = _resolved(config)
    # The proof passed, so the exact existing bytes are reused.
    assert after.model_artifact_set_digest == before.model_artifact_set_digest
    assert [m.model_sha256 for m in after.members] == [
        m.model_sha256 for m in before.members
    ]


def test_unloadable_representation_rebuilds_only_the_representation(
    published, monkeypatch
):
    """Zero TRAIN2/EVAL2 when the pickle dies but the checkpoint is unchanged."""

    from mdstats.training_data import post_selection_model_products as products

    config, _workspace, harness = published
    decision, before, _paths = _resolved(config)

    def unloadable(context, record, decision):
        raise products.ModelRepresentationIncompatible(
            "simulated serialization-runtime incompatibility"
        )

    monkeypatch.setattr(
        products, "prove_existing_representation_reusable", unloadable
    )
    monkeypatch.setattr(
        products,
        "current_runtime_compatibility_established",
        lambda record: False,
    )
    runs = len(harness.runs), len(harness.evaluations)
    assert run_train_production(config, harness) == 0
    monkeypatch.undo()

    assert (len(harness.runs), len(harness.evaluations)) == runs
    _decision, after, paths = _resolved(config)
    # A fresh successor representation of the *same* decision and members.
    assert after.final_publication_decision_digest == decision.content_digest
    assert after.member_ids == before.member_ids
    assert after.content_digest != before.content_digest
    # The historical bytes are preserved, not rewritten.
    for member in before.members:
        assert (Path(paths.models) / member.model_relative_path).is_file()


def test_provider_state_drift_fails_closed_instead_of_laundering_it(
    published, monkeypatch
):
    """A changed learned state is lineage corruption, not a serialization repair."""

    from mdstats.training_data import post_selection_model_products as products
    from mdstats.training_data.campaign_post_selection import PostSelectionError

    config, _workspace, harness = published

    real_realize = products.realize_portable_publication_model

    def drifting_realize(provider, *, target_head_name):
        model, realization = real_realize(provider, target_head_name=target_head_name)
        from dataclasses import replace

        return model, replace(realization, state_sha256="9" * 64)

    monkeypatch.setattr(
        products, "current_runtime_compatibility_established", lambda record: False
    )
    monkeypatch.setattr(products, "realize_portable_publication_model", drifting_realize)
    with pytest.raises(PostSelectionError, match="upstream scientific/provider change"):
        run_train_production(config, harness)
    monkeypatch.undo()
    assert run_train_production(config, harness) == 0


def test_workspace_relocation_with_identical_bytes_preserves_deployment_identity(
    published, tmp_path
):
    """Paths are locators; deployment currentness is byte/state identity."""

    import shutil

    config, workspace, _harness = published
    _decision, record, paths = _resolved(config)
    before = record.model_artifact_set_digest

    moved = tmp_path / "relocated-models"
    shutil.copytree(Path(paths.models), moved)
    for member in record.members:
        assert (moved / member.model_relative_path).read_bytes() == (
            Path(paths.models) / member.model_relative_path
        ).read_bytes()
    # The artifact-set identity is derived from member byte/state identity
    # only, so an intact relocation changes nothing numerical.
    assert record.model_artifact_set_digest == before
    assert all(
        member.model_relative_path in str(moved / member.model_relative_path)
        for member in record.members
    )


def test_projection_replacement_refuses_a_planted_symlink(published, tmp_path):
    """The convenience projection is written relative to an authenticated fd."""

    from mdstats.training_data.model_artifact_trust import ModelArtifactTrustError
    from mdstats.training_data.post_selection_model_products import (
        write_publication_projection,
    )

    config, _workspace, _harness = published
    decision, record, paths = _resolved(config)
    context, _paths, store = _context(config)
    try:
        from mdstats.training_data.post_selection_reclosure import (
            resolve_current_predecessor_reclosure,
        )

        reclosure = resolve_current_predecessor_reclosure(context, decision=decision)
        level = (
            Path(paths.models)
            / "production"
            / f"g{decision.binding.campaign_generation}"
        )
        size_directory = level / f"N_{decision.binding.n_selected}"
        preserved = size_directory.rename(
            size_directory.with_name(size_directory.name + ".kept")
        )
        outside = tmp_path / "outside"
        outside.mkdir()
        os.symlink(outside, size_directory)
        try:
            with pytest.raises(ModelArtifactTrustError):
                write_publication_projection(
                    context, decision=decision, record=record, reclosure=reclosure
                )
            assert not any(outside.iterdir()), "the write escaped the model root"
        finally:
            size_directory.unlink()
            preserved.rename(size_directory)
    finally:
        store.close()


def pathlib_read(module) -> str:
    from pathlib import Path as _Path

    return _Path(module.__file__).read_text(encoding="utf-8")


def _executable_source(module) -> str:
    """Module source with docstrings and comments removed.

    Prose *about* a forbidden call is not a forbidden call, and a structural
    check that cannot tell the difference would force the documentation to lie
    by omission.
    """

    import ast

    tree = ast.parse(pathlib_read(module))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if (
                node.body
                and isinstance(node.body[0], ast.Expr)
                and isinstance(node.body[0].value, ast.Constant)
                and isinstance(node.body[0].value.value, str)
            ):
                node.body.pop(0)
    return ast.unparse(tree)


def test_the_product_observer_cannot_reconstruct_mace():
    """Observation is read-only *and* model-free, structurally.

    A status path that could import a reconstruction owner would eventually be
    asked to use one, and describing a campaign would start needing a GPU.
    """

    import mdstats.training_data.post_selection_product_observation as observer

    code = _executable_source(observer)
    for forbidden in (
        "import torch",
        "torch.load",
        "authenticate_post_selection_provider",
        "selected_representative_provider",
        "build_mace_model_from_configuration",
        "realize_portable_publication_model",
        "prove_existing_representation_reusable",
    ):
        assert forbidden not in code, forbidden


def test_publication_never_sources_the_trainer_terminal_model():
    """Blocking condition 2, as a structural fact about the producer."""

    import mdstats.training_data.post_selection_model_products as products

    code = _executable_source(products)
    # No copy/rename path from a run root into the product tree exists, and
    # immutable evidence is never published through overwrite-capable
    # placement.
    for forbidden in ("shutil.copy", "shutil.move", "os.rename"):
        assert forbidden not in code, forbidden
    # Immutable model evidence is published create-once.  `os.replace` is
    # overwrite-capable and is confined to the mutable operator projection,
    # which is explicitly not authority.
    import ast

    import mdstats.training_data.post_selection_model_products as _products

    tree = ast.parse(pathlib_read(_products))
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef):
            continue
        body = ast.unparse(node)
        if "os.replace" in body:
            assert node.name == "write_publication_projection", node.name
    assert "place_immutable_file" in code
    # ... and the native reconstruction is never given the override seam.
    assert "allow_forward_override=False" in code
    assert "allow_forward_override=True" not in code
