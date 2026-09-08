"""Historical replay must survive acceleration-realization turnover.

A restarted ``select-target-size`` failed while *authenticating* a cell it had
already published:

.. code-block:: text

    TrainingDataInputError: Trajectory realization is stale for the current
    exact T_N; loader/update geometry or precision realization differs.

Nothing about that cell was stale.  The screen's seed-neutral execution
identity deliberately excludes the optimizer seed and the acceleration
realization -- those are candidate-local execution provenance, bound by each
trajectory -- but the shared replay owner rebuilt the replay optimizer policy
from the *current* template and only put the historical seed back.  A later
invocation running under a newly qualified acceleration realization therefore
demanded that already accepted evidence carry today's realization, and rejected
it before partial-boundary recovery could reuse it.

Replay authenticates what was accepted.  These tests drive the real production
owners -- ``select-target-size`` -> ``build_screen_context`` -> P3 root
reconciliation -> ``recover_authenticated_boundary_progress`` ->
``authenticate_boundary_cell_completion_record`` -> the shared trajectory
replay owner -- across a genuine acceleration turnover, and prove that valid
history is reused, that missing work still executes exactly once under current
authorization, and that forged historical provenance still fails closed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import mdstats
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data._common import digest

import tests.test_mlff_target_size_partial_boundary_resume as resume
import tests.test_mlff_target_size_p4d_runtime_cutover as p4d

_RestartHarness = resume._RestartHarness


def _turn_over_acceleration(paths, *, mace_version: str = "0.3.17") -> str:
    """Requalify a different training acceleration realization.

    This is the ordinary operational event: the runtime changed, ``doctor``
    froze a new realization, and the same campaign continues.  Backend, device,
    dtype, and qualification are unchanged, so the seed-neutral screen identity
    is untouched -- only the realization's content identity moves.
    """

    store = CampaignStore(paths.state_db)
    try:
        previous = store.get_record_optional(
            "acceleration_realization", mdstats.AccelerationRealizationRecord
        )
        assert previous is not None
        assert previous.mace_version != mace_version
        current = mdstats.AccelerationRealizationRecord(
            requested_backend=previous.requested_backend,
            resolved_kernel_mode=previous.resolved_kernel_mode,
            training_kernel_mode=previous.training_kernel_mode,
            device=previous.device,
            dtype=previous.dtype,
            foundation_inference_identity_digest=(
                previous.foundation_inference_identity_digest
            ),
            mace_version=mace_version,
            qualified=True,
        )
        assert current.content_digest != previous.content_digest
        store.put_record("acceleration_realization", current)
        return previous.content_digest
    finally:
        store.close()


#: The durable target-size evidence a replay may only ever read.  Head
#: pointers and TRAIN2 continuation workspaces are mutable execution scratch
#: and are deliberately excluded.
_IMMUTABLE_EVIDENCE_DIRECTORIES = (
    "trajectories",
    "progress",
    "completions",
    "batches",
    "heads",
    "bulk/materialization",
    "bulk/snapshot",
)


def _immutable_inventory(root: Path) -> dict[str, int]:
    inventory = resume._root_inventory(root)
    return {
        path: size
        for path, size in inventory.items()
        if path.startswith(_IMMUTABLE_EVIDENCE_DIRECTORIES)
    }


def _trajectory_acceleration_digests(root: Path) -> set[str | None]:
    return {
        json.loads(path.read_text(encoding="utf-8"))["realization"][
            "acceleration_realization_digest"
        ]
        for path in sorted((root / "trajectories").glob("*.json"))
    }


def test_partial_boundary_recovery_survives_acceleration_turnover(tmp_path: Path):
    """The reported failure, reproduced and closed at the production owner."""

    config, paths = resume._prepared(tmp_path)
    first_keys = resume._active_keys(config, boundary_epoch=1)

    interrupted = _RestartHarness(stop_after=2)
    with pytest.raises(OSError):
        resume._select(config, interrupted)
    published = interrupted.rungs_at(1)
    assert len(published) == 2

    revision = resume._revision(paths)
    root = resume._screen_root(paths, revision)
    historical = _trajectory_acceleration_digests(root)
    assert historical and None not in historical

    # The runtime turns over between invocations.
    previous_digest = _turn_over_acceleration(paths)
    assert historical == {previous_digest}

    resumed = _RestartHarness(
        forbidden={(size, seed, 1) for size, seed in published}
    )
    assert resume._select(config, resumed) == 0

    # Already published A cells authenticated; only the missing cells ran, and
    # each ran exactly once.
    executed = resumed.rungs_at(1)
    assert set(executed).isdisjoint(set(published))
    assert len(executed) == len(set(executed))
    assert set(executed) | set(published) == set(first_keys)

    # No historical trajectory was rewritten to the current realization, and
    # the cells executed now bound it.
    current = _trajectory_acceleration_digests(root)
    assert previous_digest in current
    assert len(current) == 2, "new work must bind the currently authorized realization"

    # Exact P2 order, one batch, one head, and no duplicate publication.
    batches = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((root / "batches").glob("*.json"))
    ]
    first_boundary = [b for b in batches if b["boundary_epoch"] == 1]
    assert len(first_boundary) == 1
    resolver = resume.TargetSizeExecutionResolver(root)
    ordered = [
        json.loads(resolver.completion_path(1, d).read_text(encoding="utf-8"))
        for d in first_boundary[0]["completion_record_digests"]
    ]
    assert [
        (record["target_size"], record["optimizer_seed"]) for record in ordered
    ] == list(first_keys)
    assert len(sorted((root / "progress" / "1").glob("*.json"))) == len(first_keys)
    assert resume._revision(paths).state.adopted_execution_head_digest is not None


def test_committed_head_and_continuation_replay_after_acceleration_turnover(
    tmp_path: Path,
):
    """A committed head and a later-rung predecessor stay replayable.

    ``_validate_replayed_candidate_lineage`` is shared by partial-progress
    recovery, committed-head/root reconciliation, and continuation resolution,
    so the turnover must be survivable at each of them without a
    consumer-specific bypass.
    """

    config, paths = resume._prepared(tmp_path)

    interrupted = _RestartHarness(stop_after=0, stop_at_epoch_limit=3)
    with pytest.raises(OSError):
        resume._select(config, interrupted)
    completed_first = interrupted.rungs_at(1)
    assert completed_first, "the first boundary never committed"
    assert interrupted.rungs_at(3) == []

    revision = resume._revision(paths)
    root = resume._screen_root(paths, revision)
    committed_head = revision.state.adopted_execution_head_digest
    committed_state = revision.state.adopted_reducer_state_digest
    assert committed_head is not None
    inventory = _immutable_inventory(root)
    assert inventory, "the committed boundary published no durable evidence"
    survivors = set(resume._active_keys(config, boundary_epoch=3))

    previous_digest = _turn_over_acceleration(paths)
    assert _trajectory_acceleration_digests(root) == {previous_digest}

    resumed = _RestartHarness(
        forbidden={(size, seed, 1) for size, seed in completed_first}
    )
    assert resume._select(config, resumed) == 0

    # The committed boundary reconciled from its own durable ancestry: no
    # boundary-1 cell was retrained, and the same immutable head and
    # post-reducer state were reproduced rather than replaced.
    assert resumed.rungs_at(1) == []
    after = _immutable_inventory(root)
    assert {path: after[path] for path in inventory} == inventory, (
        "reconciliation rewrote immutable historical evidence"
    )
    heads = sorted((root / "heads").glob("*.json"))
    assert committed_head in {path.stem for path in heads} or any(
        json.loads(path.read_text(encoding="utf-8")).get("content_digest")
        == committed_head
        for path in heads
    )

    # Every boundary-3 survivor continued from its authenticated boundary-1
    # predecessor, which was created under the previous realization.
    executed_second = resumed.rungs_at(3)
    assert set(executed_second) == survivors
    assert all(
        resumed.start_epochs[(size, seed, 3)] == 1 for size, seed in executed_second
    )
    # Continuation reuses the one trajectory per (N, seed); it never mints a
    # second one under the current realization.
    assert _trajectory_acceleration_digests(root) == {previous_digest}

    final = resume._revision(paths).state
    assert final.auto_diagnostic is not None
    assert final.adopted_reducer_state_digest != committed_state


def test_forged_historical_acceleration_provenance_still_fails_closed(
    tmp_path: Path,
):
    """Replaying the historical realization is not trusting the JSON.

    The trajectory's acceleration provenance is now what replay authenticates
    against, so a rewritten one must be refused by the durable parent graph
    before the cell can count as reusable completion evidence.
    """

    config, paths = resume._prepared(tmp_path)
    interrupted = _RestartHarness(stop_after=2)
    with pytest.raises(OSError):
        resume._select(config, interrupted)
    revision = resume._revision(paths)
    root = resume._screen_root(paths, revision)
    _turn_over_acceleration(paths)

    trajectory_path = sorted((root / "trajectories").glob("*.json"))[0]
    payload = json.loads(trajectory_path.read_text(encoding="utf-8"))
    payload["realization"]["acceleration_realization_digest"] = digest(
        {"forged-training-acceleration-realization": True}
    )
    payload["realization"].pop("content_digest", None)
    payload.pop("content_digest", None)
    trajectory_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")

    blocked = _RestartHarness()
    with pytest.raises(
        (mdstats.TrainingDataInputError, mdstats.TrainingDataSerializationError)
    ):
        resume._select(config, blocked)
    assert blocked.trained == [], "new scientific work started on a forged root"


def test_one_owner_recombines_the_candidate_acceleration_realization():
    """Absence: no parallel current/restart/recovery/continuation policy path.

    The defect existed because "policy for new work" and "policy for replaying
    accepted evidence" were the same ambiguous helper.  The repair is one
    canonical recombination owner, so a second place assembling a candidate
    optimizer policy out of an acceleration realization would reintroduce
    exactly the ambiguity that caused the failure.
    """

    import ast

    training_data = Path(mdstats.__file__).resolve().parent / "training_data"
    owners: set[str] = set()
    for path in sorted(training_data.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and any(
                keyword.arg == "resolved_acceleration_kernel_mode"
                for keyword in node.keywords
            ):
                owners.add(str(path.relative_to(training_data)))
    assert owners == {
        # ``MaceOptimizerPolicy`` deserializing its own persisted payload.
        "protocol.py",
        # The one current/new-work construction, from the qualified realization
        # this invocation stored.
        "_campaign_cli_core.py",
        # The one candidate/replay recombination.
        "target_size_execution/context.py",
    }, owners
