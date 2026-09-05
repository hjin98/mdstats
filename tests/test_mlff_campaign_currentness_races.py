"""Stale writers lose at the adoption boundary, whichever stage they belong to.

The concurrency matrix already covered stale P5 and P7 writers, but not a
long-running P3 screen that finishes *after* a new `prepare` has adopted a fresh
generation. Screening is the longest-running work in the campaign, so it is the
most likely writer to outlive its own generation. Its old evidence may remain
valid history for the generation that produced it; what it may never do is
become current under a generation it never saw.

Concurrent preparation has the same shape from the other side: two preparations
must not both populate a generation, and a preparation that loses the race must
not have damaged anything the winner or the previous current generation needs.

These tests drive the real CampaignStore transitions and the real adoption
owner; nothing about the race is simulated in the harness.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_prepared_generation import (
    preparation_configuration_identity,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_cutover import (
    ensure_current_target_size_authorities,
)
from mdstats.training_data.campaign_target_size_state import (
    TargetSizeCampaignConflictError,
    TargetSizeCampaignState,
    TargetSizeLifecycle,
    TargetSizeRegime,
    TargetSizeTransitionKind,
    commit_target_size_campaign_transition,
    load_target_size_campaign_revision,
)


def _selected(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    harness = p4d._BoundedNumericalHarness()
    assert (
        p4d._run(
            config,
            "select-target-size",
            _external_boundary_trainer=harness.train,
            _external_inference_evaluator=harness.evaluate,
        )
        == 0
    )
    _cfg, paths = cli._load_config(config)
    return config, paths


def _identity(state) -> dict[str, str]:
    return {
        name: getattr(state, name)
        for name in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "policy_digest",
            "experiment_definition_digest",
            "aggregate_digest",
        )
    }


def _advance_generation(store, revision) -> object:
    """Adopt a fresh generation through the real cutover owner."""

    identity = _identity(revision.state)
    identity["aggregate_digest"] = "0" * 64
    return ensure_current_target_size_authorities(
        store,
        identity,
        common_preparation_digest=revision.state.common_preparation_digest,
        prepared_manifest_digest=revision.state.prepared_manifest_digest,
    )


def test_a_stale_p3_publisher_cannot_become_current_after_generation_advance(
    tmp_path: Path,
):
    _config, paths = _selected(tmp_path)
    store = CampaignStore(paths.state_db)
    try:
        stale = load_target_size_campaign_revision(store)
        assert stale.state.adopted_execution_head_digest is not None

        # A new prepare adopts a fresh generation while the old screen worker
        # still holds its own view of the campaign.
        advanced = _advance_generation(store, stale)
        assert advanced.state.generation == stale.state.generation + 1

        # The stale worker now tries to make its own head current.
        successor = TargetSizeCampaignState(
            regime=TargetSizeRegime.CURRENT,
            generation=stale.state.generation,
            lifecycle=TargetSizeLifecycle.SCREEN_ACTIVE,
            attempt=stale.state.attempt,
            prepared_manifest_digest=stale.state.prepared_manifest_digest,
            execution_context_digest=stale.state.execution_context_digest,
            screen_window_digest=stale.state.screen_window_digest,
            execution_root=stale.state.execution_root,
            adopted_execution_head_digest=stale.state.adopted_execution_head_digest,
            adopted_reducer_state_digest=stale.state.adopted_reducer_state_digest,
            **_identity(stale.state),
            common_preparation_digest=stale.state.common_preparation_digest,
        )
        with pytest.raises(TargetSizeCampaignConflictError):
            commit_target_size_campaign_transition(
                store,
                kind=TargetSizeTransitionKind.ADOPT_EXECUTION_HEAD,
                expected=stale.expectation(),
                successor=successor,
            )

        # The newer generation is untouched and the lifecycle never regressed.
        current = load_target_size_campaign_revision(store)
        assert current.state.generation == advanced.state.generation
        assert current.state_revision == advanced.state_revision
        assert current.state.adopted_execution_head_digest is None
    finally:
        store.close()


def _prepared(tmp_path: Path):
    config, _workspace = p4d._fixture_campaign(tmp_path)
    assert p4d._run(config, "prepare") == 0
    _cfg, paths = cli._load_config(config)
    return config, paths


def test_two_identical_preparations_converge_on_one_generation(tmp_path: Path):
    """Idempotent preparation is convergence, not a second generation."""

    config, paths = _prepared(tmp_path)
    store = CampaignStore(paths.state_db)
    try:
        before = load_target_size_campaign_revision(store)
    finally:
        store.close()

    assert p4d._run(config, "prepare") == 0
    assert p4d._run(config, "prepare") == 0

    store = CampaignStore(paths.state_db)
    try:
        after = load_target_size_campaign_revision(store)
    finally:
        store.close()
    assert after.state.generation == before.state.generation
    assert after.state.prepared_manifest_digest == (
        before.state.prepared_manifest_digest
    )
    assert after.state.common_preparation_digest == (
        before.state.common_preparation_digest
    )


def test_a_generation_that_loses_the_race_damages_nothing_it_did_not_own(
    tmp_path: Path,
):
    """A future generation may only add unreachable content before adoption."""

    _config, paths = _selected(tmp_path)
    store = CampaignStore(paths.state_db)
    try:
        before = load_target_size_campaign_revision(store)
        manifest = read_prepared_generation_manifest(
            paths, before.state.prepared_manifest_digest
        )
        members = {
            str(record["relative_path"]): (
                paths.internal / "frame-cache" / str(record["relative_path"])
            ).read_bytes()
            for record in manifest.frame_records
        }
        # Another writer wins the current transition first.
        advanced = _advance_generation(store, before)
        assert advanced.state.generation == before.state.generation + 1
    finally:
        store.close()

    # Everything the previous generation bound is still exactly present: an
    # adoption transition publishes an identity, it does not rewrite content.
    for relative, payload in members.items():
        path = paths.internal / "frame-cache" / relative
        assert path.is_file()
        assert path.read_bytes() == payload
    again = read_prepared_generation_manifest(
        paths, before.state.prepared_manifest_digest
    )
    assert again.content_digest == manifest.content_digest


def test_preparation_configuration_identity_ignores_downstream_domains(
    tmp_path: Path,
):
    """Only the preparation-owning configuration participates in this identity."""

    import json

    config, _paths = _selected(tmp_path)
    cfg, _paths2 = cli._load_config(config)
    baseline = preparation_configuration_identity(cfg)

    downstream = json.loads(json.dumps(cfg))
    downstream.setdefault("cv", {})["folds"] = 9
    downstream.setdefault("production", {})["horizon_epochs"] = 4096
    downstream.setdefault("qualification", {})["dynamics_steps"] = 17
    assert preparation_configuration_identity(downstream) == baseline

    # A transient execution resource is likewise not preparation identity.
    resource = json.loads(json.dumps(cfg))
    resource.setdefault("training", {})["num_workers"] = 8
    assert preparation_configuration_identity(resource) == baseline

    # Preparation-scientific policy is.
    scientific = json.loads(json.dumps(cfg))
    scientific["partition"]["development_minimum_independent_units"] = 6
    assert preparation_configuration_identity(scientific) != baseline
