"""The pure public campaign lifecycle projection.

``status`` and ``advance`` need to answer two cheap questions -- which durable
stage is current, and which command is admissible next -- and nothing more.  The
previous implementation answered them by constructing operational state: it
built a post-selection context (resolving a trainer, which created ``.mdstats``
wrapper scripts), and qualification status built an entire ``QualificationSession``
that could re-enter P4/P5 currentness and even run model inference to decide
stress applicability.  Describing a campaign therefore cost more than some of
the work it described, and could create the very state it claimed to observe.

This module derives the lifecycle from persisted owner state alone:

.. code-block:: text

    CampaignStore target-size revision      (the sole current-generation authority)
    + P5 pointer rows and compact records   (inside the current selected binding)
    + P7 pointer rows and compact records   (inside the same binding)
      -> CampaignLifecycleSnapshot

It constructs no provider, trainer, session, or evidence root, parses no source,
restores no DATA4, and loads no prepared generation.  It is deliberately *not* a
new authority: every value it reports is read from the owner that already owns
it, and nothing here decides anything.

Routing is advisory.  The command `advance` selects with this projection and the
selected consequential command then performs its own full admission, so a
snapshot that was already stale when it was read cannot authorize work.

Reads are taken as one coherent snapshot.  A concurrent writer may make status
report the state before or after a transition, but never a hybrid: the target
revision is re-read after the descendant pointers and the projection is retaken
if it moved.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
    load_target_size_campaign_revision,
)

#: How many times a moving campaign is re-observed before the projection gives
#: up on a quiet snapshot.  A writer that keeps committing this fast is itself
#: worth reporting, and the last read is still a coherent single-revision view.
_COHERENCE_ATTEMPTS = 4


class LifecycleObservationState:
    """States the pure projection can report from durable evidence alone."""

    NOT_STARTED = "not_started"
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True)
class LifecycleStep:
    key: str
    command: str
    label: str
    description: str
    state: str
    message: str
    terminal: bool = False


@dataclass(frozen=True, slots=True)
class CampaignLifecycleSnapshot:
    """One coherent read of the public campaign lifecycle."""

    state_revision: str | None
    generation: int | None
    steps: tuple[LifecycleStep, ...]

    def step(self, key: str) -> LifecycleStep | None:
        return next((item for item in self.steps if item.key == key), None)

    @property
    def terminal_step(self) -> LifecycleStep | None:
        return next((item for item in self.steps if item.terminal), None)

    @property
    def next_command(self) -> str | None:
        """The command `advance` should route to, or ``None`` when there is none.

        This is routing, not authorization.  A blocked stage still routes to
        its own command -- that command is the owner that can report the
        blockage precisely and fail closed -- but nothing downstream of it is
        ever proposed.
        """

        if self.terminal_step is not None:
            return None
        for item in self.steps:
            if item.state != LifecycleObservationState.COMPLETE:
                return item.command
        return None


def _meta(store: Any, key: str) -> str | None:
    with store._connect() as db:  # noqa: SLF001 - the store owns its pool
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def _read_object(root: Path, content_digest: str) -> Mapping[str, Any] | None:
    """Read one immutable evidence object without creating anything."""

    path = root / "objects" / content_digest[:2] / f"{content_digest}.json"
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _binding_for(revision: Any) -> Any | None:
    """Derive the current selected binding from campaign state alone.

    The binding is a pure function of the terminal projection the campaign
    store already committed, so the pointer namespace of every P5/P7 descendant
    is reachable without loading the prepared generation or re-deriving the
    selection.
    """

    from .campaign_post_selection import PostSelectionBinding

    state = revision.state
    terminal = state.terminal
    if state.lifecycle is not TargetSizeLifecycle.TERMINAL_SELECTED or terminal is None:
        return None
    if terminal.selected_target_size is None or not terminal.selected_membership_digest:
        return None
    try:
        return PostSelectionBinding(
            campaign_generation=state.generation,
            campaign_state_revision=revision.state_revision,
            experiment_definition_digest=state.experiment_definition_digest,
            training_order_digest=terminal.training_order_digest,
            frame_authority_digest=state.frame_authority_digest,
            neutral_statistical_base_digest=state.neutral_statistical_base_digest,
            split_exclusion_digest=state.split_exclusion_digest,
            target_size_policy_digest=state.policy_digest,
            aggregate_digest=state.aggregate_digest,
            adopted_execution_head_digest=state.adopted_execution_head_digest,
            adopted_reducer_state_digest=state.adopted_reducer_state_digest,
            n_selected=int(terminal.selected_target_size),
            selected_membership_digest=str(terminal.selected_membership_digest),
        )
    except Exception:  # noqa: BLE001 - reported as a blocked observation
        return None


def _doctor_step(store: Any, paths: Any) -> LifecycleStep:
    from ._campaign_cli_core import StageState, _effective_stage

    state, message = _effective_stage(store, paths, "doctor")
    mapping = {
        StageState.COMPLETE: LifecycleObservationState.COMPLETE,
        StageState.FAILED: LifecycleObservationState.FAILED,
        StageState.RUNNING: LifecycleObservationState.RUNNING,
        StageState.WAITING: LifecycleObservationState.WAITING,
        StageState.NOT_STARTED: LifecycleObservationState.NOT_STARTED,
    }
    return LifecycleStep(
        "doctor",
        "doctor",
        "doctor",
        "environment and input checks",
        mapping[state],
        message,
    )


def _short(value: Any) -> str:
    text = "" if value is None else str(value)
    return f"{text[:12]}..." if text else "unbound"


def _prepare_step(state: Any) -> LifecycleStep:
    if state is None or state.regime is TargetSizeRegime.LEGACY:
        observed = LifecycleObservationState.NOT_STARTED
        message = (
            "the current target-size substrate has not been bound; `prepare` performs "
            "the one-time destructive cutover"
        )
    elif state.regime is TargetSizeRegime.TRANSITIONING:
        observed = LifecycleObservationState.WAITING
        message = (
            f"a destructive cutover for canonical generation {state.generation} is "
            "interrupted; rerun `prepare` to resume it"
        )
    elif state.prepared_manifest_digest is None:
        # The generation predates immutable prepared publication. Downstream
        # commands do not retrofit it, so the truthful observation is that one
        # explicit `prepare` is required.
        observed = LifecycleObservationState.BLOCKED
        message = (
            f"canonical generation {state.generation} was prepared before the "
            "immutable prepared substrate existed; run `prepare` once to bind a "
            "fresh generation. Existing evidence stays historical and is never "
            "reinterpreted under the new contract."
        )
    else:
        observed = LifecycleObservationState.COMPLETE
        message = (
            f"current substrate bound at canonical generation {state.generation}; "
            f"experiment={_short(state.experiment_definition_digest)}; "
            f"prepared={_short(state.prepared_manifest_digest)}"
        )
    return LifecycleStep(
        "current_prepare",
        "prepare",
        "prepare",
        "current target-size scientific substrate; selects nothing",
        observed,
        message,
    )


def _screen_step(state: Any, prepare_complete: bool) -> LifecycleStep:
    terminal_outcome = False
    if not prepare_complete:
        observed = LifecycleObservationState.NOT_STARTED
        message = "the current substrate must be bound first"
    elif (
        state.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
        and state.terminal is not None
    ):
        observed = LifecycleObservationState.COMPLETE
        message = (
            f"selected target size frozen at N={state.terminal.selected_target_size}; "
            f"T_selected={_short(state.terminal.selected_membership_digest)}"
        )
    elif state.lifecycle is TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE:
        observed = LifecycleObservationState.COMPLETE
        terminal_outcome = True
        reasons = (
            ", ".join(state.terminal.terminal_reason_codes)
            if state.terminal is not None
            else ""
        )
        message = (
            "the paired-seed screen reached a typed scientific terminal outcome"
            + (f": {reasons}" if reasons else "")
        )
    elif state.lifecycle is TargetSizeLifecycle.SCREEN_ACTIVE:
        observed = LifecycleObservationState.RUNNING
        message = (
            f"screen attempt {state.attempt} is open at canonical generation "
            f"{state.generation}"
        )
    else:
        observed = LifecycleObservationState.NOT_STARTED
        message = "no candidate has been screened for this generation"
    return LifecycleStep(
        "target_size_selection",
        "select-target-size",
        "select-target-size",
        "paired optimizer-seed target-size screen; the only command that decides N",
        observed,
        message,
        terminal=terminal_outcome,
    )


def _post_selection_steps(
    paths: Any, store: Any, binding: Any
) -> tuple[LifecycleStep, LifecycleStep]:
    from .post_selection_store import (
        POINTER_CV_ACCEPTANCE,
        POINTER_CV_PLAN,
        POINTER_FINAL_PLAN,
        POINTER_FINAL_PUBLICATION,
        post_selection_root,
    )

    if binding is None:
        blocked = "no target size is frozen yet"
        return (
            LifecycleStep(
                "post_selection_cv",
                "cross-validate",
                "cross-validate",
                "post-selection cross-validation of the frozen method on exactly T_selected",
                LifecycleObservationState.NOT_STARTED,
                blocked,
            ),
            LifecycleStep(
                "final_production",
                "train-production",
                "train-production",
                "fresh final production on the complete selected dataset",
                LifecycleObservationState.NOT_STARTED,
                "the frozen method is not cross-validation accepted",
            ),
        )

    root = post_selection_root(paths, binding.campaign_generation)
    prefix = f"post_selection:{binding.content_digest}:"
    plan_digest = _meta(store, prefix + POINTER_CV_PLAN)
    acceptance_digest = _meta(store, prefix + POINTER_CV_ACCEPTANCE)
    final_plan_digest = _meta(store, prefix + POINTER_FINAL_PLAN)
    publication_digest = _meta(store, prefix + POINTER_FINAL_PUBLICATION)

    if acceptance_digest is not None:
        payload = _read_object(root, acceptance_digest)
        if payload is None:
            cv_state = LifecycleObservationState.BLOCKED
            cv_message = (
                "the current cross-validation acceptance pointer names an object "
                f"that is missing or unreadable ({_short(acceptance_digest)}); this "
                "is durable-state corruption, not an unstarted stage"
            )
        elif bool(payload.get("accepted")):
            cv_state = LifecycleObservationState.COMPLETE
            cv_message = (
                "the frozen method passed every required fold of every required CV seed"
            )
        else:
            cv_state = LifecycleObservationState.FAILED
            cv_message = "cross-validation rejected the frozen training method"
    elif plan_digest is not None:
        cv_state = LifecycleObservationState.NOT_STARTED
        cv_message = (
            f"CV plan is current ({_short(plan_digest)}); no acceptance exists yet"
        )
    else:
        cv_state = LifecycleObservationState.NOT_STARTED
        cv_message = "the exact selected dataset has not been cross-validated"

    if cv_state is not LifecycleObservationState.COMPLETE:
        production_state = LifecycleObservationState.NOT_STARTED
        production_message = "the frozen method is not cross-validation accepted"
    elif final_plan_digest is None:
        production_state = LifecycleObservationState.NOT_STARTED
        production_message = "no fresh final production run has been published"
    elif publication_digest is None:
        production_state = LifecycleObservationState.WAITING
        production_message = (
            "fresh final production plan is published on the full exact T_selected "
            f"({_short(final_plan_digest)}); required final production run(s) are "
            "incomplete"
        )
    elif _read_object(root, publication_digest) is None:
        production_state = LifecycleObservationState.BLOCKED
        production_message = (
            "the current final-production publication pointer names an object that "
            f"is missing or unreadable ({_short(publication_digest)})"
        )
    else:
        production_state = LifecycleObservationState.COMPLETE
        production_message = (
            "fresh production is published on the full exact T_selected under the "
            f"accepted method ({_short(final_plan_digest)})"
        )

    return (
        LifecycleStep(
            "post_selection_cv",
            "cross-validate",
            "cross-validate",
            "post-selection cross-validation of the frozen method on exactly T_selected",
            cv_state,
            cv_message,
        ),
        LifecycleStep(
            "final_production",
            "train-production",
            "train-production",
            "fresh final production on the complete selected dataset",
            production_state,
            production_message,
        ),
    )


def _qualification_step(
    paths: Any, store: Any, binding: Any, production_complete: bool
) -> LifecycleStep:
    """Compact P7 projection.

    The public campaign does not end at final production: a frozen product is
    still unqualified until P7 says otherwise.  This reads only pointer rows and
    the small records they name, and it never routes to locked activation --
    opening locked evidence is irreversible and stays an explicit operator act.
    """

    description = "post-production qualification of the frozen final publication"
    if not production_complete or binding is None:
        return LifecycleStep(
            "post_production_qualification",
            "qualification run",
            "qualification",
            description,
            LifecycleObservationState.NOT_STARTED,
            "no final-production publication has been frozen yet",
        )

    from .qualification.store import (
        POINTER_LOCKED_ACTIVATION,
        POINTER_QUALIFICATION_PLAN,
        POINTER_QUALIFICATION_RECORD,
        POINTER_RELEASE_EVIDENCE,
        qualification_root,
    )

    root = qualification_root(paths, binding.campaign_generation)
    prefix = f"qualification:{binding.content_digest}:"
    plan_digest = _meta(store, prefix + POINTER_QUALIFICATION_PLAN)
    record_digest = _meta(store, prefix + POINTER_QUALIFICATION_RECORD)
    locked_digest = _meta(store, prefix + POINTER_LOCKED_ACTIVATION)
    release_digest = _meta(store, prefix + POINTER_RELEASE_EVIDENCE)

    if record_digest is not None:
        payload = _read_object(root, record_digest)
        if payload is None:
            return LifecycleStep(
                "post_production_qualification",
                "qualification run",
                "qualification",
                description,
                LifecycleObservationState.BLOCKED,
                "the current qualification record pointer names an object that is "
                f"missing or unreadable ({_short(record_digest)})",
            )
        verdict = str(payload.get("verdict", "")) or "unknown"
        release = "release evidence published" if release_digest else "no release index"
        # Only `rejected` and `release_qualified` are terminal verdicts.
        # `waiting_for_reference` and `incomplete` are truthful *nonterminal*
        # product states: qualification has run and has said, correctly, that it
        # cannot finish yet. Reporting either as a completed stage would tell an
        # operator the campaign is done when the product is still unqualified.
        if verdict == "rejected":
            return LifecycleStep(
                "post_production_qualification",
                "qualification run",
                "qualification",
                description,
                LifecycleObservationState.COMPLETE,
                f"terminal qualification verdict: rejected ({release})",
                terminal=True,
            )
        if verdict == "release_qualified":
            return LifecycleStep(
                "post_production_qualification",
                "qualification run",
                "qualification",
                description,
                LifecycleObservationState.COMPLETE,
                f"terminal qualification verdict: release_qualified ({release})",
            )
        if verdict == "waiting_for_reference":
            return LifecycleStep(
                "post_production_qualification",
                "qualification run",
                "qualification",
                description,
                LifecycleObservationState.WAITING,
                "qualification is waiting for independent external reference "
                "evidence; supply the requested bundle and rerun "
                "`qualification run`",
            )
        return LifecycleStep(
            "post_production_qualification",
            "qualification run",
            "qualification",
            description,
            LifecycleObservationState.WAITING,
            f"qualification is incomplete (verdict: {verdict}); rerun "
            "`qualification run`. Locked evidence, when required, is activated "
            "only by the explicit `qualification activate-locked` command",
        )

    if plan_digest is None:
        return LifecycleStep(
            "post_production_qualification",
            "qualification run",
            "qualification",
            description,
            LifecycleObservationState.NOT_STARTED,
            "the frozen publication has not been qualified; run `qualification run`",
        )
    locked = (
        "locked cohort activated"
        if locked_digest
        else "locked cohort not activated (explicit `qualification activate-locked` only)"
    )
    return LifecycleStep(
        "post_production_qualification",
        "qualification run",
        "qualification",
        description,
        LifecycleObservationState.WAITING,
        f"qualification plan is current ({_short(plan_digest)}); no terminal verdict "
        f"has been published yet; {locked}",
    )


def project_campaign_lifecycle(
    paths: Any, store: Any
) -> CampaignLifecycleSnapshot:
    """Project the public lifecycle from persisted owner state, coherently."""

    for _attempt in range(_COHERENCE_ATTEMPTS):
        revision = load_target_size_campaign_revision(store)
        state = None if revision is None else revision.state
        steps: list[LifecycleStep] = [_doctor_step(store, paths)]
        prepare = _prepare_step(state)
        steps.append(prepare)
        prepare_complete = prepare.state == LifecycleObservationState.COMPLETE
        screen = _screen_step(state, prepare_complete)
        steps.append(screen)
        binding = (
            None
            if revision is None or not prepare_complete
            else _binding_for(revision)
        )
        cv_step, production_step = _post_selection_steps(paths, store, binding)
        steps.append(cv_step)
        steps.append(production_step)
        steps.append(
            _qualification_step(
                paths,
                store,
                binding,
                production_step.state == LifecycleObservationState.COMPLETE,
            )
        )
        after = load_target_size_campaign_revision(store)
        moved = (None if after is None else after.state_revision) != (
            None if revision is None else revision.state_revision
        )
        if not moved:
            return CampaignLifecycleSnapshot(
                state_revision=None if revision is None else revision.state_revision,
                generation=None if state is None else state.generation,
                steps=tuple(steps),
            )
    return CampaignLifecycleSnapshot(
        state_revision=None if revision is None else revision.state_revision,
        generation=None if state is None else state.generation,
        steps=tuple(steps),
    )


__all__ = [
    "CampaignLifecycleSnapshot",
    "LifecycleObservationState",
    "LifecycleStep",
    "project_campaign_lifecycle",
]
