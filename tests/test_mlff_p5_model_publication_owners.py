"""Owner-level acceptance for the P5 published-model representation.

These cases exercise the record, path, trust and pointer owners directly.
They are deliberately cheap: the claims here are about identity, confinement
and transactionality, none of which need a trained campaign to be true or
false. The real-owner publication claims - that the *selected* checkpoint is
what gets serialized, and that the result is a usable MACE model - live in the
assembled suite, because a toy stand-in could not establish them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
)
from mdstats.training_data.campaign_post_selection import PostSelectionError
from mdstats.training_data.model_artifact_trust import (
    ModelArtifactTrustError,
    authenticate_model_artifact,
    normalize_relative_artifact_path,
    open_publication_directory,
    place_immutable_file,
    read_model_artifact_identity,
    stage_authenticated_model,
)
from mdstats.training_data.post_selection_model_publication import (
    FinalProductionModelPublication,
    MODEL_SERIALIZER_IDENTITY,
    PublishedModelMember,
    SERIALIZATION_FORMAT_TORCH_FULL_MODEL,
    decision_directory_relative_path,
    fresh_locator_token,
    model_artifact_basename,
    validate_model_publication_against_decision,
)

_A = "a" * 64
_B = "b" * 64
_C = "c" * 64
_D = "d" * 64
_E = "e" * 64


def _member(
    *,
    member_id: str = "seed-1",
    seed: int = 1,
    model_sha: str = _B,
    locator: str | None = None,
    size: int = 4096,
    state_sha: str = _C,
    dtype: str = "float64",
) -> PublishedModelMember:
    token = locator or fresh_locator_token()
    name = model_artifact_basename(
        member_id=member_id, model_sha256=model_sha, artifact_locator_token=token
    )
    return PublishedModelMember(
        member_id=member_id,
        optimizer_seed=seed,
        run_identity=_A,
        representative_checkpoint_relative_path="model_run-7_epoch-17.pt",
        representative_checkpoint_sha256=_D,
        evaluation_model_state="ema",
        evaluated_model_state_digest=_E,
        model_execution_architecture_digest=_A,
        model_state_sha256=state_sha,
        model_dtype=dtype,
        artifact_locator_token=token,
        model_relative_path=f"production/g1/N_8/decision-{_A}/{name}",
        model_sha256=model_sha,
        model_size_bytes=size,
    )


def _publication(members) -> FinalProductionModelPublication:
    return FinalProductionModelPublication(
        selected_binding_digest=_A,
        final_publication_decision_digest=_B,
        final_publication_member_digest=_C,
        target_head_name="target_head",
        members=tuple(members),
        serialization_format=SERIALIZATION_FORMAT_TORCH_FULL_MODEL,
        serializer_identity=MODEL_SERIALIZER_IDENTITY,
        serialization_runtime={"torch": "2.13.0", "mace": "0.3.16"},
        published_at="2026-09-22T00:00:00+00:00",
    )


# -- record identity --------------------------------------------------------


def test_published_model_path_must_carry_member_sha_and_locator():
    """A bare mutable `seed-1.model` is never the canonical durable artifact."""

    token = fresh_locator_token()
    with pytest.raises(TrainingDataInputError, match="artifact locator token"):
        PublishedModelMember(
            member_id="seed-1",
            optimizer_seed=1,
            run_identity=_A,
            representative_checkpoint_relative_path="model_run-7_epoch-17.pt",
            representative_checkpoint_sha256=_D,
            evaluation_model_state="live",
            evaluated_model_state_digest=_E,
            model_execution_architecture_digest=_A,
            model_state_sha256=_C,
            model_dtype="float64",
            artifact_locator_token=token,
            model_relative_path="production/g1/N_8/seed-1.model",
            model_sha256=_B,
            model_size_bytes=10,
        )


@pytest.mark.parametrize(
    "bad",
    ["/abs/x.model", "../escape.model", "production/../../x.model", "a\\b.model", ""],
)
def test_published_model_path_is_confined_and_normalized(bad: str):
    with pytest.raises(ModelArtifactTrustError):
        normalize_relative_artifact_path(bad)


def test_published_model_requires_positive_size():
    with pytest.raises(TrainingDataInputError, match="positive byte count"):
        _member(size=0)


def test_model_artifact_set_digest_is_path_independent():
    """Relocation or a locator repair with identical bytes changes nothing."""

    token_one = fresh_locator_token()
    token_two = fresh_locator_token()
    assert token_one != token_two
    one = _publication([_member(locator=token_one)])
    two = _publication([_member(locator=token_two)])
    assert one.members[0].model_relative_path != two.members[0].model_relative_path
    assert one.model_artifact_set_digest == two.model_artifact_set_digest
    # ... while any changed executable model byte does change it.
    assert (
        _publication([_member(model_sha=_E)]).model_artifact_set_digest
        != one.model_artifact_set_digest
    )
    assert (
        _publication([_member(state_sha=_D)]).model_artifact_set_digest
        != one.model_artifact_set_digest
    )
    assert (
        _publication([_member(dtype="float32")]).model_artifact_set_digest
        != one.model_artifact_set_digest
    )


def test_model_publication_rejects_duplicate_members_and_paths():
    token = fresh_locator_token()
    with pytest.raises(PostSelectionError, match="duplicate member identity"):
        _publication([_member(locator=token), _member(locator=token)])


def test_model_publication_deserializer_recomputes_its_digest():
    record = _publication([_member()])
    payload = dict(record.to_dict())
    payload["target_head_name"] = "other_head"
    with pytest.raises(TrainingDataSerializationError, match="digest mismatch"):
        FinalProductionModelPublication.from_dict(payload)


class _Evidence:
    def __init__(self, member_id: str, seed: int, sha: str = _D):
        self.member_id = member_id
        self.optimizer_seed = seed
        self.run_identity = _A
        self.checkpoint_relative_path = "model_run-7_epoch-17.pt"
        self.representative_checkpoint_sha256 = sha


class _Decision:
    content_digest = _B
    member_digest = _C
    target_head_name = "target_head"

    def __init__(self, members):
        self.binding = type("B", (), {"content_digest": _A})()
        self.published_member_ids = tuple(item.member_id for item in members)
        self.published_seed_evidence = tuple(members)


def test_model_publication_must_be_the_decision_member_set_in_order():
    decision = _Decision([_Evidence("seed-1", 1), _Evidence("seed-2", 2)])
    record = _publication([_member(member_id="seed-2", seed=2)])
    with pytest.raises(PostSelectionError, match="exact ordered set"):
        validate_model_publication_against_decision(record, decision)


def test_model_publication_must_bind_exact_seed_checkpoint_evidence():
    decision = _Decision([_Evidence("seed-1", 1, sha=_E)])
    record = _publication([_member()])
    with pytest.raises(PostSelectionError, match="published seed evidence"):
        validate_model_publication_against_decision(record, decision)


def test_decision_directory_uses_the_full_digest():
    """Truncated digests are display-only; an authoritative path never collides."""

    relative = decision_directory_relative_path(1, 512, _B)
    assert relative.endswith(f"decision-{_B}")


# -- descriptor trust -------------------------------------------------------


def _write(root: Path, relative: str, data: bytes) -> str:
    import hashlib

    target = root / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return hashlib.sha256(data).hexdigest()


def test_authenticates_exact_bytes_and_rejects_mutation(tmp_path: Path):
    root = tmp_path / "models"
    sha = _write(root, "production/g1/N_8/x.model", b"payload")
    observed = authenticate_model_artifact(
        root, "production/g1/N_8/x.model", expected_sha256=sha, expected_size_bytes=7
    )
    assert observed.sha256 == sha and observed.size_bytes == 7
    (root / "production/g1/N_8/x.model").write_bytes(b"payloa!")
    with pytest.raises(ModelArtifactTrustError, match="bytes changed"):
        authenticate_model_artifact(
            root, "production/g1/N_8/x.model", expected_sha256=sha, expected_size_bytes=7
        )


def test_symlinked_leaf_is_refused(tmp_path: Path):
    root = tmp_path / "models"
    sha = _write(root, "real.model", b"payload")
    (root / "production").mkdir(parents=True, exist_ok=True)
    os.symlink(root / "real.model", root / "production" / "link.model")
    with pytest.raises(ModelArtifactTrustError, match="symbolic link"):
        authenticate_model_artifact(
            root, "production/link.model", expected_sha256=sha, expected_size_bytes=7
        )


def test_intermediate_symlink_substitution_is_refused(tmp_path: Path):
    """A planted `models/production` link cannot redirect product reads."""

    root = tmp_path / "models"
    root.mkdir(parents=True)
    outside = tmp_path / "outside"
    sha = _write(outside, "g1/N_8/x.model", b"payload")
    os.symlink(outside, root / "production")
    with pytest.raises(ModelArtifactTrustError, match="not a\\s+plain directory"):
        authenticate_model_artifact(
            root, "production/g1/N_8/x.model", expected_sha256=sha, expected_size_bytes=7
        )


def test_non_regular_leaf_is_refused(tmp_path: Path):
    root = tmp_path / "models"
    (root / "production").mkdir(parents=True)
    (root / "production" / "x.model").mkdir()
    with pytest.raises(ModelArtifactTrustError, match="not a regular file"):
        authenticate_model_artifact(
            root, "production/x.model", expected_sha256=_B, expected_size_bytes=7
        )


def test_size_mismatch_fails_before_bytes_are_trusted(tmp_path: Path):
    root = tmp_path / "models"
    sha = _write(root, "x.model", b"payload")
    with pytest.raises(ModelArtifactTrustError, match="bytes; the record binds"):
        authenticate_model_artifact(
            root, "x.model", expected_sha256=sha, expected_size_bytes=999
        )


def test_staging_yields_a_trusted_private_copy(tmp_path: Path):
    root = tmp_path / "models"
    sha = _write(root, "x.model", b"payload")
    with stage_authenticated_model(
        root,
        "x.model",
        expected_sha256=sha,
        expected_size_bytes=7,
        scratch_directory=tmp_path / "scratch",
    ) as staged:
        assert staged.read_bytes() == b"payload"
        assert staged.parent == tmp_path / "scratch"
        held = staged
    # The staged copy is owner-private and does not outlive its block.
    assert not held.exists()


def test_immutable_placement_never_clobbers(tmp_path: Path):
    root = tmp_path / "models"
    (root / "d").mkdir(parents=True)
    (root / "d" / "tmp").write_bytes(b"one")
    (root / "d" / "final").write_bytes(b"other")
    with open_publication_directory(root, "d", create=False) as fd:
        with pytest.raises(FileExistsError):
            place_immutable_file(fd, "tmp", "final")
    assert (root / "d" / "final").read_bytes() == b"other"


def test_write_side_refuses_a_planted_intermediate_symlink(tmp_path: Path):
    root = tmp_path / "models"
    root.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    os.symlink(outside, root / "production")
    with pytest.raises(ModelArtifactTrustError):
        with open_publication_directory(root, "production/g1", create=True):
            pass
    assert not (outside / "g1").exists()


def test_read_identity_reports_actual_bytes(tmp_path: Path):
    root = tmp_path / "models"
    sha = _write(root, "x.model", b"payload")
    observed = read_model_artifact_identity(root, "x.model")
    assert (observed.sha256, observed.size_bytes) == (sha, 7)


# -- durability -------------------------------------------------------------


def test_directory_creation_is_fsynced_through_the_whole_chain(tmp_path, monkeypatch):
    """Directory creation is part of durability, not only containment.

    A crash between creating `decision-<digest>/` and committing the pointer
    that names a file inside it must not lose the directory entry, so every
    newly installed component is fsynced as it is created.
    """

    import mdstats.training_data.model_artifact_trust as trust

    synced: list[int] = []
    real_fsync = os.fsync
    monkeypatch.setattr(
        trust.os, "fsync", lambda fd: (synced.append(fd), real_fsync(fd))[1]
    )
    root = tmp_path / "models"
    with open_publication_directory(root, "production/g1/N_8/decision-x", create=True):
        pass
    # One fsync per newly created component of the chain.
    assert len(synced) >= 4
    synced.clear()
    # Re-descending an existing chain creates nothing and syncs nothing.
    with open_publication_directory(root, "production/g1/N_8/decision-x", create=True):
        pass
    assert synced == []


def test_a_write_failure_leaves_no_published_entry(tmp_path, monkeypatch):
    """ENOSPC before placement publishes nothing; the temp is the only loss."""

    import mdstats.training_data.post_selection_model_products as products

    class _Realization:
        state_sha256 = _A
        execution_architecture_digest = _B
        dtype = "float64"
        head_inventory = ()

    def failing_serialize(model, destination):
        destination.write_bytes(b"partial")
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(products, "_serialize_portable_model", failing_serialize)
    context = type(
        "C",
        (),
        {"paths": type("P", (), {"models": tmp_path / "models"})(), "cfg": {}},
    )()
    relative = "production/g1/N_8/decision-" + _A
    with pytest.raises(OSError):
        products.place_member_model(
            context,
            model=object(),
            member_id="seed-1",
            realization=_Realization(),
            target_head_name="target_head",
            decision_relative_directory=relative,
        )
    published = list((tmp_path / "models" / relative).glob("*.model"))
    assert published == [], "a failed serialization published nothing"
    # Only the attempt's own private temp is removed; nothing else is touched.
    assert list((tmp_path / "models" / relative).glob("*.tmp")) == []


# -- publication-set coordination -------------------------------------------


def test_one_decision_set_lock_serializes_concurrent_committee_builders(tmp_path):
    """Per-member locks would let two builders assemble a mixed artifact set.

    Full PyTorch model serialization is not byte-deterministic, so two
    concurrent builders of the same committee cannot converge by content
    address the way immutable JSON evidence does. The lock is therefore derived
    from the decision identity, which is known *before* any serialization, not
    from a model SHA that only exists afterwards.
    """

    import threading

    from mdstats.training_data.post_selection_model_products import (
        model_publication_set_lock,
    )

    paths = type("P", (), {"internal": tmp_path / ".mdstats"})()
    binding = type("B", (), {"campaign_generation": 1})()
    context = type(
        "C", (), {"paths": paths, "selected": type("S", (), {"binding": binding})()}
    )()
    decision = type("D", (), {"content_digest": _A})()

    order: list[str] = []
    inside = threading.Event()
    release = threading.Event()

    def holder():
        with model_publication_set_lock(context, decision):
            order.append("holder-in")
            inside.set()
            release.wait(timeout=10.0)
            order.append("holder-out")

    def waiter():
        inside.wait(timeout=10.0)
        order.append("waiter-blocked")
        release.set()
        with model_publication_set_lock(context, decision):
            order.append("waiter-in")

    one = threading.Thread(target=holder)
    two = threading.Thread(target=waiter)
    one.start()
    two.start()
    one.join(timeout=20.0)
    two.join(timeout=20.0)
    assert order.index("holder-out") < order.index("waiter-in")

    # The coordination namespace is owner-internal, never in the operator
    # models tree where it would look like a product.
    assert (tmp_path / ".mdstats").exists()
    assert not (tmp_path / "models").exists()
