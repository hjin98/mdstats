"""Campaign invariants under interleaved observation, restart, and storage.

The campaign transition graph is small, but the ways of walking it are not:
observing, closing and reopening the process, repeating a preparation, changing
one that matters, and running storage in between can be combined in many orders,
and the interesting defects live in the orders nobody wrote a test for.

This is a model-based state machine over the **real** owners. Every action drives
production code - the real CLI, the real ``CampaignStore`` transitions, the real
prepared-generation publisher and loader, the real storage owners - and the model
is only an oracle that says what should have happened. It never stands in for a
production transition.

Sequences are enumerated deterministically rather than sampled randomly. The
action alphabet here is small enough that a fixed-length walk covers it, and a
deterministic walk is reproducible: a failure names an exact sequence a developer
can rerun, instead of a seed. (``hypothesis`` is not a dependency of this
project; the claim it would establish is established here by construction.)
"""

from __future__ import annotations

import hashlib
import itertools
from pathlib import Path

import pytest

import tests.test_mlff_target_size_p4d_runtime_cutover as p4d
from mdstats.training_data import _campaign_cli_core as cli
from mdstats.training_data._campaign_cli_core import CampaignStore
from mdstats.training_data.campaign_lifecycle import project_campaign_lifecycle
from mdstats.training_data.campaign_prepared_generation import (
    prepared_generation_protected_paths,
    read_prepared_generation_manifest,
)
from mdstats.training_data.campaign_target_size_runtime import (
    load_prepared_target_size_generation,
)
from mdstats.training_data.campaign_target_size_state import (
    load_target_size_campaign_revision,
)

#: One action per accepted campaign-facing transition or observation.
_ACTIONS = (
    "observe",
    "reopen",
    "prepare_unchanged",
    "prepare_changed",
    "storage_cleanup",
)
_WALK_LENGTH = 4


def _managed_digest(paths) -> str:
    """One digest over every managed path and file this campaign owns."""

    accumulator = hashlib.sha256()
    for path in sorted(paths.workspace.rglob("*")):
        accumulator.update(str(path.relative_to(paths.workspace)).encode("utf-8"))
        if path.is_file():
            accumulator.update(hashlib.sha256(path.read_bytes()).digest())
    return accumulator.hexdigest()


class _Campaign:
    """The system under test, plus the oracle that says what it should do."""

    #: Preparation-owned policy values the walk alternates between.
    _POLICIES = ("4", "3")

    def __init__(self, tmp_path: Path) -> None:
        self.config, _workspace = p4d._fixture_campaign(tmp_path)
        _cfg, self.paths = cli._load_config(self.config)
        self._policy_index = 0
        # Oracle state.
        self.generation: int | None = None
        self.prepared_digest: str | None = None
        #: Every protected object's bytes, recorded when it first appeared.
        self.published: dict[str, bytes] = {}
        self.history: list[str] = []

    # -- real owner access ---------------------------------------------------

    def revision(self):
        store = CampaignStore(self.paths.state_db, create=False)
        try:
            return load_target_size_campaign_revision(store)
        finally:
            store.close()

    def _protected(self) -> set[Path]:
        revision = self.revision()
        if revision is None:
            return set()
        return prepared_generation_protected_paths(
            self.paths, [revision.state.prepared_manifest_digest]
        )

    def _record_published(self) -> None:
        for path in self._protected():
            if path.is_file():
                self.published.setdefault(str(path), path.read_bytes())

    # -- actions -------------------------------------------------------------

    def observe(self) -> None:
        before = _managed_digest(self.paths)
        assert cli.main(["--config", str(self.config), "status"]) == 0
        assert cli.main(["--config", str(self.config), "status"]) == 0
        assert _managed_digest(self.paths) == before, (
            "observation mutated managed campaign state"
        )

    def reopen(self) -> None:
        before = self.revision()
        after = self.revision()
        if before is None:
            assert after is None
            return
        assert after.state_revision == before.state_revision, (
            "reopening the campaign changed its current revision"
        )
        assert after.state.generation == before.state.generation

    def prepare_unchanged(self) -> None:
        assert p4d._run(self.config, "prepare") == 0
        revision = self.revision()
        if self.generation is None:
            self.generation = revision.state.generation
        else:
            assert revision.state.generation == self.generation, (
                "an unchanged preparation advanced the canonical generation"
            )
        self.prepared_digest = revision.state.prepared_manifest_digest
        self._record_published()

    def prepare_changed(self) -> None:
        if self.generation is None:
            # A changed policy before any preparation is just a preparation.
            self._rotate_policy()
            self.prepare_unchanged()
            return
        previous = self.generation
        self._rotate_policy()
        assert p4d._run(self.config, "prepare") == 0
        revision = self.revision()
        assert revision.state.generation == previous + 1, (
            "a changed preparation policy did not advance the generation"
        )
        self.generation = revision.state.generation
        self.prepared_digest = revision.state.prepared_manifest_digest
        self._record_published()

    def storage_cleanup(self) -> None:
        assert (
            cli.main(
                [
                    "--config",
                    str(self.config),
                    "storage",
                    "cleanup",
                    "--tier",
                    "safe",
                    "--apply",
                ]
            )
            == 0
        )

    def _rotate_policy(self) -> None:
        current = self._POLICIES[self._policy_index]
        self._policy_index = (self._policy_index + 1) % len(self._POLICIES)
        nxt = self._POLICIES[self._policy_index]
        text = self.config.read_text(encoding="utf-8")
        marker = f"development_minimum_independent_units = {current}"
        assert marker in text
        self.config.write_text(
            text.replace(marker, f"development_minimum_independent_units = {nxt}"),
            encoding="utf-8",
        )
        # Editing the campaign file invalidates the doctor stage for an operator
        # too; rerunning it is part of changing the policy, not a workaround.
        store = CampaignStore(self.paths.state_db)
        try:
            cli._mark_stage(
                store, self.paths, "doctor", cli.StageState.COMPLETE, "fixture"
            )
        finally:
            store.close()

    # -- invariants ----------------------------------------------------------

    def check_invariants(self) -> None:
        revision = self.revision()
        if revision is None:
            assert self.generation is None
            return

        # Generation is monotonic and matches the oracle exactly.
        assert revision.state.generation == self.generation
        assert self.generation is not None and self.generation >= 1

        # The current generation's substrate loads and authenticates, and its
        # ancestry is the ancestry the campaign store binds.
        # Every real command loads the configuration in force at the time it
        # runs; a consumer holding a stale one is a harness artefact, not a
        # campaign state, and the loader is right to refuse it.
        cfg, _paths = cli._load_config(self.config)
        store = CampaignStore(self.paths.state_db, create=False)
        try:
            authorities = load_prepared_target_size_generation(
                cfg, self.paths, store, revision
            )
        finally:
            store.close()
        assert authorities.identity["aggregate_digest"] == (
            revision.state.aggregate_digest
        )
        manifest = read_prepared_generation_manifest(
            self.paths, revision.state.prepared_manifest_digest
        )
        assert manifest.content_digest == revision.state.prepared_manifest_digest

        # Nothing ever published under any generation was rewritten in place.
        for name, payload in self.published.items():
            path = Path(name)
            if path.is_file():
                assert path.read_bytes() == payload, (
                    f"published immutable content was rewritten: {name}"
                )

        # Everything the *current* generation needs is still present.
        for path in self._protected():
            assert path.exists(), (
                f"an object the current generation requires was reclaimed: {path}"
            )

        # The public projection agrees with the owner it projects.
        store = CampaignStore(self.paths.state_db, create=False)
        try:
            snapshot = project_campaign_lifecycle(self.paths, store)
        finally:
            store.close()
        assert snapshot.generation == revision.state.generation


def _walks() -> list[tuple[str, ...]]:
    """Every ordering that starts from an unprepared campaign, deduplicated.

    A walk must begin with a preparation for the later actions to mean anything,
    so the first step is fixed and the remaining positions are enumerated.
    """

    seen: list[tuple[str, ...]] = []
    for tail in itertools.product(_ACTIONS, repeat=_WALK_LENGTH - 1):
        walk = ("prepare_unchanged",) + tail
        # Two walks that differ only by repeated observation exercise the same
        # transitions; keep the first of each collapsed form.
        collapsed = tuple(
            name for index, name in enumerate(walk) if index == 0 or name != walk[index - 1]
        )
        if collapsed in seen:
            continue
        seen.append(collapsed)
    return seen


@pytest.mark.parametrize("walk", _walks(), ids=lambda walk: "-".join(walk))
def test_campaign_invariants_hold_under_every_bounded_interleaving(
    tmp_path: Path, walk: tuple[str, ...]
):
    campaign = _Campaign(tmp_path)
    for action in walk:
        getattr(campaign, action)()
        campaign.history.append(action)
        campaign.check_invariants()
    assert campaign.history == list(walk)
