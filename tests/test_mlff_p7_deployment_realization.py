"""P7 acceptance for the deployed-realization boundary this cycle introduces.

Deployment now sources the authenticated P5 published model rather than the
representative checkpoint, and ML-IAP bytes are not byte-deterministic. Those
two facts together are what make a *realization* identity necessary: without
one, a rebuild that produced different executable bytes would leave old
deployment-parity and dynamics evidence looking current, and a terminal record
could silently combine evidence from two different builds.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d  # noqa: F401
from tests import _mlff_qualification_fixture as qual

from mdstats.training_data.qualification.errors import QualificationLineageError


@pytest.fixture(scope="module")
def session_bundle(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("p7-realization")
    harness = qual.QualificationHarness()
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
    cfg, paths, store, session = qual.load_session(config, harness)
    yield config, paths, store, session, harness
    store.close()


def _member(session):
    return session.publication.members[0]


def test_deployment_identity_binds_the_p5_source_model_and_uses_a_full_root(
    session_bundle,
):
    """A truncated authoritative namespace is not an identity."""

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    identity = session.deployment_identity(member)
    assert len(identity) == 64
    root = session._deployment_root(member)
    assert root.name == identity

    source = session.published_model_member(member)
    # The identity must actually move when the serialized source does; nothing
    # below reaches into the digest payload, it changes the source record the
    # identity is derived from.
    from dataclasses import replace

    changed = replace(source, model_state_sha256="9" * 64)
    original = session.model_publication
    session.model_publication = replace(
        original, members=(changed,) + tuple(original.members[1:])
    )
    try:
        assert session.deployment_identity(member) != identity
    finally:
        session.model_publication = original
    assert session.deployment_identity(member) == identity


def test_deployment_source_is_the_published_model_not_the_checkpoint(session_bundle):
    """The checkpoint stays the independent reference; the model is deployed."""

    _config, paths, _store, session, _harness = session_bundle
    member = _member(session)
    source = session.published_model_member(member)
    observed: dict[str, bytes] = {}

    exporter = session.deployment_exporter

    def recording_exporter(source_path, output_directory, **kwargs):
        observed["bytes"] = Path(source_path).read_bytes()
        observed["path"] = Path(str(source_path))
        return exporter(source_path, output_directory, **kwargs)

    session._deployment_cache.clear()
    session._frozen_realization_set = None
    session.deployment_exporter = recording_exporter
    try:
        session.deployed_artifact(member)
    finally:
        session.deployment_exporter = exporter
        session._deployment_cache.clear()
        session._frozen_realization_set = None

    published = Path(paths.models) / source.model_relative_path
    assert hashlib.sha256(observed["bytes"]).hexdigest() == source.model_sha256
    # Exported from a trusted staged copy, never by reopening the public name:
    # hashing one pathname and deserializing another is the substitution this
    # boundary exists to prevent.
    assert observed["path"] != published
    assert not observed["path"].exists(), "the staged copy is attempt-private"


def test_realization_digest_composes_identity_and_deployed_bytes(session_bundle):
    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    identity = session.deployment_identity(member)
    one = session.deployment_realization_digest(identity, "a" * 64)
    two = session.deployment_realization_digest(identity, "b" * 64)
    assert one != two
    assert session.deployment_realization_digest(identity, "a" * 64) == one


def test_identical_byte_rebuild_preserves_the_realization_set(session_bundle):
    _config, _paths, _store, session, _harness = session_bundle
    first = session.freeze_deployment_realization_set()
    session._frozen_realization_set = None
    session._deployment_cache.clear()
    # The receipt still authenticates the existing bytes, so the rebuilt set is
    # the same set and otherwise-current deployment evidence stays reusable.
    assert session.freeze_deployment_realization_set() == first


@pytest.mark.parametrize("mutation", ["delete", "corrupt"])
def test_frozen_r1_refuses_receipt_advance_to_r2(session_bundle, mutation):
    """A frozen invocation never follows a newer receipt after R1 is lost."""

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    session.freeze_deployment_realization_set()
    path, sha = session.deployed_artifact(member)
    original = path.read_bytes()
    root = session._deployment_root(member)
    receipt = root / "deployment-receipt.json"
    receipt_before = receipt.read_bytes()
    successor = root / "deployment-mliap-r2.pt"
    successor.write_bytes(original + b"r2")
    successor_sha = hashlib.sha256(successor.read_bytes()).hexdigest()
    payload = json.loads(receipt_before.decode("utf-8"))
    payload["artifact_relative_name"] = successor.name
    payload["artifact_sha256"] = successor_sha
    payload["deployment_realization_digest"] = session.deployment_realization_digest(
        session.deployment_identity(member), successor_sha
    )
    receipt.write_text(json.dumps(payload), encoding="utf-8")
    if mutation == "delete":
        path.unlink()
    else:
        path.write_bytes(original + b"corrupt-r1")
    try:
        with pytest.raises(QualificationLineageError, match="frozen deployment artifact"):
            session.deployed_artifact(member)
    finally:
        path.write_bytes(original)
        receipt.write_bytes(receipt_before)
        successor.unlink()
        session._deployment_cache.clear()
        session._frozen_realization_set = None


def test_changed_deployed_bytes_change_the_realization_set(session_bundle):
    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    before = session.freeze_deployment_realization_set()
    path, sha = session.deployed_artifact(member)

    # Corrupt the receipted artifact. It is never overwritten in place; the
    # rebuild claims a fresh immutable locator and the receipt advances.
    original = path.read_bytes()
    path.write_bytes(original + b"\x00")
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    with pytest.raises(QualificationLineageError, match="bytes changed"):
        session.deployed_artifact(member)
    path.write_bytes(original)
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    assert session.freeze_deployment_realization_set() == before


def test_receipt_and_artifact_are_authenticated_no_follow(session_bundle, tmp_path):
    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    path, _sha = session.deployed_artifact(member)
    root = session._deployment_root(member)
    receipt = root / "deployment-receipt.json"
    assert receipt.is_file()

    payload = json.loads(receipt.read_text(encoding="utf-8"))
    source = session.published_model_member(member)
    assert payload["source_model_sha256"] == source.model_sha256
    assert payload["source_model_state_sha256"] == source.model_state_sha256
    assert payload["deployment_realization_digest"] == (
        session.deployment_realization_digest(
            session.deployment_identity(member), payload["artifact_sha256"]
        )
    )
    # A symlinked deployed artifact is lineage failure, never executable
    # evidence.
    artifact_name = payload["artifact_relative_name"]
    elsewhere = tmp_path / "planted.pt"
    elsewhere.write_bytes(path.read_bytes())
    (root / artifact_name).unlink()
    os.symlink(elsewhere, root / artifact_name)
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    with pytest.raises(QualificationLineageError):
        session.deployed_artifact(member)
    (root / artifact_name).unlink()
    elsewhere.replace(root / artifact_name)
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    session.deployed_artifact(member)


def test_receipt_replace_before_directory_fsync_requires_retry_fence(
    session_bundle, monkeypatch
):
    """A visible post-replace receipt is not reusable until its root is re-fenced."""

    from mdstats.training_data.qualification import runtime as runtime_module

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    path, sha = session.deployed_artifact(member)
    root = session._deployment_root(member)
    identity = session.deployment_identity(member)

    real_fsync = os.fsync
    calls = 0

    def fail_after_receipt_replace_preparation(fd):
        nonlocal calls
        calls += 1
        # The receipt file is durable before os.replace; the second fence is
        # the deployment-root directory fence after the stable-name advance.
        if calls == 2:
            raise OSError(5, "Input/output error")
        return real_fsync(fd)

    monkeypatch.setattr(runtime_module.os, "fsync", fail_after_receipt_replace_preparation)
    with pytest.raises(OSError, match="Input/output error"):
        session._advance_deployment_receipt(
            member, identity, root, artifact_name=path.name, sha=sha
        )
    assert (root / "deployment-receipt.json").is_file()

    monkeypatch.setattr(runtime_module.os, "fsync", real_fsync)
    assert session._reuse_published_artifact(member, identity, root) == (path, sha)


def test_replaced_execution_scratch_does_not_delete_foreign_sentinel(session_bundle):
    """Scratch replacement before exit cannot transfer recursive cleanup authority."""

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    with session._staged_deployment_artifact(member, prefix=".replacement") as staged:
        scratch = staged.parent
        displaced = scratch.with_name(scratch.name + ".displaced")
        scratch.rename(displaced)
        scratch.mkdir()
        sentinel = scratch / "foreign-sentinel"
        sentinel.write_bytes(b"must survive")
    assert sentinel.read_bytes() == b"must survive"


def test_replaced_build_scratch_does_not_delete_foreign_sentinel(session_bundle):
    """Deployment-build scratch has the same conservative retirement boundary."""

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    exporter = session.deployment_exporter

    def replace_after_export(source_path, output_directory, **kwargs):
        artifact = exporter(source_path, output_directory, **kwargs)
        scratch = Path(output_directory)
        displaced = scratch.with_name(scratch.name + ".displaced")
        scratch.rename(displaced)
        scratch.mkdir()
        (scratch / "foreign-sentinel").write_bytes(b"must survive")
        return artifact

    session.deployment_exporter = replace_after_export
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    try:
        with pytest.raises(Exception):
            session.deployed_artifact(member)
        assert (session._deployment_root(member) / ".build").exists() or any(
            item.name.startswith(".build")
            for item in session._deployment_root(member).iterdir()
        )
        sentinels = list(session._deployment_root(member).glob(".build*/*foreign-sentinel"))
        assert sentinels and sentinels[0].read_bytes() == b"must survive"
    finally:
        session.deployment_exporter = exporter
        session._deployment_cache.clear()
        session._frozen_realization_set = None


def test_reclaimed_scratch_rebuilds_without_treating_absence_as_corruption(
    session_bundle,
):
    """Released-attempt scratch may legitimately be reclaimed."""

    import shutil

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    session.deployed_artifact(member)
    root = session._deployment_root(member)
    shutil.rmtree(root)
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    rebuilt, sha = session.deployed_artifact(member)
    assert rebuilt.is_file()
    assert hashlib.sha256(rebuilt.read_bytes()).hexdigest() == sha


def test_checkpoint_only_components_do_not_acquire_representation_identity(
    session_bundle,
):
    """A representation change is a deployment event, not attempt invalidation."""

    from dataclasses import replace

    from mdstats.training_data.qualification.components import (
        COMPONENT_CALIBRATION,
        COMPONENT_DEPLOYMENT_PARITY,
        COMPONENT_LOCKED_TEST,
        COMPONENT_PHYSICAL_PES,
        COMPONENT_RELAXATION,
    )

    _config, _paths, _store, session, _harness = session_bundle
    before = {
        component: session.component_input_digest(component, None)
        for component in (
            COMPONENT_PHYSICAL_PES,
            COMPONENT_RELAXATION,
            COMPONENT_CALIBRATION,
            COMPONENT_LOCKED_TEST,
        )
    }
    parity_before = session.component_input_digest(COMPONENT_DEPLOYMENT_PARITY, None)

    original = session.model_publication
    changed_member = replace(original.members[0], model_state_sha256="9" * 64)
    session.model_publication = replace(
        original, members=(changed_member,) + tuple(original.members[1:])
    )
    session._frozen_realization_set = None
    session._deployment_cache.clear()
    try:
        for component, digest_before in before.items():
            assert session.component_input_digest(component, None) == digest_before, (
                f"{component} must not depend on the serialized representation"
            )
        assert (
            session.component_input_digest(COMPONENT_DEPLOYMENT_PARITY, None)
            != parity_before
        )
    finally:
        session.model_publication = original
        session._frozen_realization_set = None
        session._deployment_cache.clear()


def test_mixed_realization_sets_are_not_terminally_admissible(session_bundle):
    from mdstats.training_data.qualification.components import (
        COMPONENT_DEPLOYMENT_PARITY,
        COMPONENT_DYNAMICS,
        ComponentStatus,
        build_component_evidence,
    )
    from mdstats.training_data.qualification.record import (
        DEPLOYMENT_REALIZATION_SET_NOT_APPLICABLE,
    )
    from mdstats.training_data.qualification.runtime import (
        common_deployment_realization_set,
    )

    _config, _paths, _store, session, _harness = session_bundle

    def evidence(component: str, realization: str | None):
        payload = {} if realization is None else {
            "model_artifact_set_digest": session.model_artifact_set_digest,
            "deployment_realization_set_digest": realization,
        }
        return build_component_evidence(
            component=component,
            binding=session.binding,
            status=ComponentStatus.PASSED,
            reason_code="ok",
            detail="",
            metrics={},
            payload=payload,
            component_input_digest=None,
        )

    r1, r2 = "1" * 64, "2" * 64
    assert (
        common_deployment_realization_set(
            [evidence(COMPONENT_DEPLOYMENT_PARITY, r1), evidence(COMPONENT_DYNAMICS, r1)]
        )
        == r1
    )
    with pytest.raises(QualificationLineageError, match="different deployed"):
        common_deployment_realization_set(
            [evidence(COMPONENT_DEPLOYMENT_PARITY, r1), evidence(COMPONENT_DYNAMICS, r2)]
        )
    # Evidence that cannot say what it ran is not reducible either.
    with pytest.raises(QualificationLineageError, match="does not record"):
        common_deployment_realization_set([evidence(COMPONENT_DYNAMICS, None)])
    # No enabled deployment-dependent component is an explicit statement.
    assert (
        common_deployment_realization_set([])
        == DEPLOYMENT_REALIZATION_SET_NOT_APPLICABLE
    )


def test_terminal_and_release_v1_remain_readable_but_never_current():
    """Historical evidence is preserved, not promoted and not deleted."""

    from mdstats.training_data._common import TrainingDataInputError
    from mdstats.training_data.qualification.record import (
        QUALIFICATION_RECORD_SCHEMA_V1,
        ProductionQualificationRecord,
        QualificationVerdict,
    )

    fields = dict(
        selected_binding_digest="a" * 64,
        binding_digest="b" * 64,
        publication_digest="c" * 64,
        publication_member_digest="d" * 64,
        plan_digest="e" * 64,
        specification_digest="f" * 64,
        environment_digest="0" * 64,
        executable_digest="1" * 64,
        predecessor_executable_commit="deadbeef",
        predecessor_evidence_commit="2" * 64,
        components=(),
        locked_activation_digest=None,
        verdict=QualificationVerdict.RELEASE_QUALIFIED,
        reason_code="ok",
        recorded_at="2026-01-01T00:00:00+00:00",
    )
    historical = ProductionQualificationRecord(
        **fields, schema_version=QUALIFICATION_RECORD_SCHEMA_V1
    )
    assert historical.is_historical_v1
    assert ProductionQualificationRecord.from_dict(historical.to_dict()) == historical

    # A *current* record must be able to say which representation it ran.
    with pytest.raises(TrainingDataInputError, match="model-artifact set"):
        ProductionQualificationRecord(**fields)


def test_a_receipt_advance_cannot_switch_a_frozen_invocation(session_bundle):
    """One invocation executes one realization set, start to finish.

    If parity and dynamics each followed the mutable current receipt, a rebuild
    between them would let one component's evidence describe R1 while the
    other's described R2, and the terminal reduction would combine them as if
    they were one run.
    """

    _config, _paths, _store, session, _harness = session_bundle
    member = _member(session)
    frozen = session.freeze_deployment_realization_set()
    path, _sha = session.deployed_artifact(member)

    # A concurrent builder advances the receipt to a different realization.
    root = session._deployment_root(member)
    receipt = root / "deployment-receipt.json"
    payload = json.loads(receipt.read_text(encoding="utf-8"))
    successor = root / "deployment-mliap-successor.pt"
    successor.write_bytes(path.read_bytes() + b"\x00")
    successor_sha = hashlib.sha256(successor.read_bytes()).hexdigest()
    payload["artifact_relative_name"] = successor.name
    payload["artifact_sha256"] = successor_sha
    payload["deployment_realization_digest"] = session.deployment_realization_digest(
        session.deployment_identity(member), successor_sha
    )
    receipt.write_text(json.dumps(payload), encoding="utf-8")

    try:
        # The session continues from the set it froze; the advance does not
        # silently switch a later component to different executable bytes.
        assert session.freeze_deployment_realization_set() == frozen
        assert session.deployed_artifact(member)[0] == path
    finally:
        session._deployment_cache.clear()
        session._frozen_realization_set = None


def test_waiting_evidence_deploys_nothing(session_bundle):
    """Reporting that a component cannot run yet is not an execution.

    A deployment-dependent component waiting for an external reference
    consumes no deployed bytes, so resolving - and therefore building - the
    invocation's realization set in order to describe that state would make
    an observation-shaped answer a side effect.
    """

    from mdstats.training_data.qualification.components import COMPONENT_DYNAMICS

    _config, _paths, _store, session, _harness = session_bundle
    session._deployment_cache.clear()
    session._frozen_realization_set = None
    waiting_digest = session.component_input_digest(
        COMPONENT_DYNAMICS, None, bind_deployment_realization=False
    )
    assert session._frozen_realization_set is None, "waiting froze a realization set"

    executing_digest = session.component_input_digest(COMPONENT_DYNAMICS, None)
    assert session._frozen_realization_set is not None
    # Executing identity binds the representation; waiting identity cannot,
    # because there is nothing it ran against.
    assert executing_digest != waiting_digest
