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
    + P5 pointer rows and compact records   (inside every current per-size binding)
    + P7 pointer rows and compact records   (only where qualification is authorized)
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
revision and every P5/P7 pointer row of every current per-size binding are read
inside one SQLite read transaction, so the ancestry reported is an ancestry that
actually existed.  Iterating sizes with independently timed authoritative reads
would be a second, weaker assembly that could report a combination of moments
that never coexisted.  Re-reading the target revision afterwards would not have been enough:
publishing a P5 or P7 pointer mutates ``meta`` without moving the target-size
state revision at all.

Integrity is separate from coherence and equally required.  A pointer names a
content digest, and the compact record it names is loaded through its accepted
read-only typed store, which reproduces that digest before any field is read.
Cheap observation may skip re-authenticating models and sources; it may not
report ``accepted`` or a release verdict out of bytes that merely parse.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .campaign_target_size_state import (
    TargetSizeLifecycle,
    TargetSizeRegime,
)


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


def _post_selection_prefix(binding: Any) -> tuple[str, tuple[str, ...]]:
    from .post_selection_store import (
        POINTER_CV_ACCEPTANCE,
        POINTER_CV_PLAN,
        POINTER_FINAL_PLAN,
        POINTER_FINAL_PUBLICATION,
    )

    return (
        f"post_selection:{binding.content_digest}:",
        (
            POINTER_CV_PLAN,
            POINTER_CV_ACCEPTANCE,
            POINTER_FINAL_PLAN,
            POINTER_FINAL_PUBLICATION,
        ),
    )


def _qualification_prefix(binding: Any) -> tuple[str, tuple[str, ...]]:
    from .qualification.store import (
        POINTER_LOCKED_ACTIVATION,
        POINTER_QUALIFICATION_PLAN,
        POINTER_QUALIFICATION_RECORD,
        POINTER_RELEASE_EVIDENCE,
    )

    return (
        f"qualification:{binding.content_digest}:",
        (
            POINTER_QUALIFICATION_PLAN,
            POINTER_QUALIFICATION_RECORD,
            POINTER_LOCKED_ACTIVATION,
            POINTER_RELEASE_EVIDENCE,
        ),
    )


def _pointer_prefixes(bindings: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Every pointer row one lifecycle answer reads, grouped by namespace.

    P5 namespaces are read for every current per-size binding.  P7 namespaces
    are read only where qualification is actually authorized - a single-size
    frozen design - because for a multi-size design there is no authorized
    release path to observe and reading one would suggest otherwise.
    """

    prefixes = [_post_selection_prefix(binding) for binding in bindings]
    if len(bindings) == 1:
        prefixes.append(_qualification_prefix(bindings[0]))
    return tuple(prefixes)


def campaign_owner_snapshot(store: Any) -> tuple[Any, tuple[Any, ...], dict[str, str | None]]:
    """Read the target revision and every descendant pointer atomically.

    One deferred read transaction spans the campaign-state head and the P5/P7
    pointer rows of *every* current per-size binding.  The bindings are derived
    inside it because they are a pure function of the revision, so the pointer
    namespaces this answer reads are the namespaces that revision actually
    owned.  Looping over sizes with independently timed authoritative reads
    would let a concurrent publication produce a combined answer that never
    existed at any instant; that is exactly what this boundary prevents.

    This is the *only* coherent-read boundary for public observation.  Every
    public status answer -- the campaign lifecycle projection and
    `qualification status` alike -- derives its revision, bindings and pointer
    digests here, so no second, weaker assembly of independently moving pointer
    reads can exist beside it.
    """

    from .campaign_target_size_state import _load_head

    db = store._connect()  # noqa: SLF001 - the store owns its connection pool
    db.execute("BEGIN")
    try:
        revision = _load_head(db)
        bindings = () if revision is None else _bindings_for(revision)
        pointers: dict[str, str | None] = {}
        for prefix, kinds in _pointer_prefixes(bindings):
            for kind in kinds:
                row = db.execute(
                    "SELECT value FROM meta WHERE key=?", (prefix + kind,)
                ).fetchone()
                pointers[prefix + kind] = None if row is None else str(row[0])
    finally:
        db.rollback()
    return revision, bindings, pointers


def _authenticated(store: Any, content_digest: str, deserializer: Any) -> Any | None:
    """Load one compact record through its owner, or report nothing.

    ``None`` means missing, unreadable, or not reproducing the digest the
    pointer named -- three different accidents with the same consequence for an
    observer: the referenced fact cannot be believed, so it is reported as
    blocked rather than interpreted.
    """

    try:
        return store.get(content_digest, deserializer)
    except Exception:  # noqa: BLE001 - every failure is one blocked observation
        return None


def _bindings_for(revision: Any) -> tuple[Any, ...]:
    """Derive every current descendant binding from campaign state alone.

    A binding is a pure function of the frozen design the campaign store
    already committed at ``cross-validate`` admission, so the pointer namespace
    of every P5/P7 descendant is reachable without loading the prepared
    generation or re-deriving anything.  Before that freeze there are none,
    which is exactly right: a provisional design has no descendants.
    """

    from .campaign_post_selection import current_target_size_bindings

    try:
        return current_target_size_bindings(revision.state)
    except Exception:  # noqa: BLE001 - reported as a blocked observation
        return ()


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


#: One sentence, used wherever the target-size decision step is described.
_SELECT_DESCRIPTION = (
    "choose the provisional target size and role horizons; the optional "
    "automatic screen only recommends"
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
    """The target-size *decision* step: propose, optionally diagnose, then freeze.

    The automatic screen is one optional input to this step, never the step
    itself.  A generation whose diagnostic could not make a valid comparison is
    therefore not terminal for the campaign: an explicit qualified choice is
    still admissible, and the step reports that rather than stopping.
    """

    if not prepare_complete:
        return LifecycleStep(
            "target_size_selection",
            "select-target-size",
            "select-target-size",
            _SELECT_DESCRIPTION,
            LifecycleObservationState.NOT_STARTED,
            "the current substrate must be bound first",
        )

    diagnostic = state.auto_diagnostic
    if diagnostic is None:
        if state.lifecycle is TargetSizeLifecycle.SCREEN_ACTIVE:
            diagnostic_note = (
                f"automatic diagnostic attempt {state.attempt} is open at canonical "
                f"generation {state.generation}"
            )
        else:
            diagnostic_note = "no automatic diagnostic has been run for this generation"
    elif diagnostic.has_recommendation:
        warnings = ", ".join(diagnostic.terminal_reason_codes)
        diagnostic_note = (
            "automatic diagnostic recommends "
            f"N={diagnostic.recommended_target_size}"
            + (f" (warning: {warnings})" if warnings else "")
        )
    else:
        reasons = ", ".join(diagnostic.terminal_reason_codes)
        diagnostic_note = (
            "the automatic diagnostic completed without a recommendation"
            + (f": {reasons}" if reasons else "")
            + "; an explicit qualified choice remains available"
        )

    entries = state.frozen_entries
    if entries is not None:
        sizes = "; ".join(
            f"[{index}] N={entry.n_selected} "
            f"T_selected={_short(entry.selected_membership_digest)} "
            f"H_cv={entry.cv_max_num_epochs} "
            f"H_prod={entry.production_max_num_epochs} "
            f"source={entry.selection_source}"
            for index, entry in enumerate(entries, start=1)
        )
        return LifecycleStep(
            "target_size_selection",
            "select-target-size",
            "select-target-size",
            _SELECT_DESCRIPTION,
            LifecycleObservationState.COMPLETE,
            (
                f"frozen target-size design: {len(entries)} selected size(s). "
                f"{sizes}. Frozen: yes. {diagnostic_note}"
            ),
        )

    proposals = state.provisional_entries
    if proposals:
        # A nonempty provisional design is a complete decision for routing
        # purposes: the next consequential command is `cross-validate`, which
        # freezes the whole collection at once.
        sizes = "; ".join(
            f"[{index}] N={entry.n_provisional} "
            f"T_provisional={_short(entry.membership_digest)} "
            f"H_cv={entry.cv_max_num_epochs} "
            f"H_prod={entry.production_max_num_epochs} "
            f"source={entry.selection_source}"
            for index, entry in enumerate(proposals, start=1)
        )
        return LifecycleStep(
            "target_size_selection",
            "select-target-size",
            "select-target-size",
            _SELECT_DESCRIPTION,
            LifecycleObservationState.COMPLETE,
            (
                f"provisional target-size design: {len(proposals)} selected size(s). "
                f"{sizes}. Frozen: no. {diagnostic_note}"
            ),
        )

    return LifecycleStep(
        "target_size_selection",
        "select-target-size",
        "select-target-size",
        _SELECT_DESCRIPTION,
        LifecycleObservationState.WAITING,
        (
            "no provisional target size has been chosen; run "
            "`select-target-size <N>` to choose one explicitly, or "
            "`select-target-size --auto` to run the optional automatic "
            "diagnostic and adopt its recommendation. Selecting further sizes "
            f"appends them to the design. {diagnostic_note}"
        ),
    )


def _per_size_post_selection(
    paths: Any, binding: Any, pointers: Mapping[str, str | None]
) -> tuple[tuple[str, str], tuple[str, str]]:
    """The (cv, production) observation for exactly one per-size binding."""

    from .post_selection_cv_acceptance import CvCampaignAcceptance
    from .post_selection_publication import FinalProductionPublicationDecision
    from .post_selection_store import (
        POINTER_CV_ACCEPTANCE,
        POINTER_CV_PLAN,
        POINTER_FINAL_PLAN,
        POINTER_FINAL_PUBLICATION,
        open_post_selection_store,
    )

    prefix = f"post_selection:{binding.content_digest}:"
    plan_digest = pointers.get(prefix + POINTER_CV_PLAN)
    acceptance_digest = pointers.get(prefix + POINTER_CV_ACCEPTANCE)
    final_plan_digest = pointers.get(prefix + POINTER_FINAL_PLAN)
    publication_digest = pointers.get(prefix + POINTER_FINAL_PUBLICATION)
    # Observational open: describing a campaign must never bring an evidence
    # root into existence, or "no evidence" and "an empty store" stop being
    # distinguishable afterwards.
    store = open_post_selection_store(paths, binding, create=False)

    if acceptance_digest is not None:
        acceptance = _authenticated(
            store, acceptance_digest, CvCampaignAcceptance.from_dict
        )
        if acceptance is None:
            cv_state = LifecycleObservationState.BLOCKED
            cv_message = (
                "the current cross-validation acceptance pointer names an object "
                f"that is missing, unreadable, or does not reproduce its own "
                f"identity ({_short(acceptance_digest)}); this is durable-state "
                "corruption, not an unstarted stage"
            )
        elif bool(acceptance.accepted):
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
    elif (
        _authenticated(
            store, publication_digest, FinalProductionPublicationDecision.from_dict
        )
        is None
    ):
        production_state = LifecycleObservationState.BLOCKED
        production_message = (
            "the current final-production publication pointer names an object that "
            f"is missing, unreadable, or does not reproduce its own identity "
            f"({_short(publication_digest)})"
        )
    else:
        production_state = LifecycleObservationState.COMPLETE
        production_message = (
            "fresh production is published on the full exact T_selected under the "
            f"accepted method ({_short(final_plan_digest)})"
        )
    return (cv_state, cv_message), (production_state, production_message)


#: Worst-first precedence when several sizes disagree.  A campaign stage is only
#: as complete as its least complete requested size: every selected N stays
#: accounted for, and no failure is averaged away by a successful sibling.
_AGGREGATE_PRECEDENCE = (
    LifecycleObservationState.BLOCKED,
    LifecycleObservationState.FAILED,
    LifecycleObservationState.NOT_STARTED,
    LifecycleObservationState.WAITING,
    LifecycleObservationState.RUNNING,
    LifecycleObservationState.COMPLETE,
)


def _aggregate(observations: "list[tuple[int, str, str]]") -> tuple[str, str]:
    """Fold per-size observations into one truthful campaign-stage answer."""

    states = {state for _size, state, _message in observations}
    combined = next(
        (state for state in _AGGREGATE_PRECEDENCE if state in states),
        LifecycleObservationState.NOT_STARTED,
    )
    detail = "; ".join(
        f"N={size}: {message}" for size, _state, message in observations
    )
    return combined, detail


def _post_selection_steps(
    paths: Any, bindings: Any, pointers: Mapping[str, str | None]
) -> tuple[LifecycleStep, LifecycleStep]:
    if not bindings:
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

    cv_observations: list[tuple[int, str, str]] = []
    production_observations: list[tuple[int, str, str]] = []
    for binding in bindings:
        (cv_state, cv_message), (prod_state, prod_message) = _per_size_post_selection(
            paths, binding, pointers
        )
        cv_observations.append((binding.n_selected, cv_state, cv_message))
        production_observations.append((binding.n_selected, prod_state, prod_message))

    cv_state, cv_message = _aggregate(cv_observations)
    production_state, production_message = _aggregate(production_observations)
    if cv_state is not LifecycleObservationState.COMPLETE:
        # Production is not the relevant stage until every requested size has
        # accepted CV: admission is a collection-wide barrier, not a per-size one.
        production_state = LifecycleObservationState.NOT_STARTED

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


#: What a completed multi-size training experiment is, and is not.  Several
#: final publications exist and every requested size closed successfully, but
#: this revision authorizes no rule for choosing one release product and no
#: qualification over several products.  Reporting anything else here would be
#: the release decision itself, made silently.
MULTI_SIZE_TERMINAL_MESSAGE = (
    "the multi-size target training experiment is complete: every selected size "
    "has its own current final-production publication. It is NOT release "
    "qualified: this revision authorizes no rule for selecting one release "
    "product from several sizes, so qualification is unavailable and there is no "
    "next consequential command. `qualification status` explains the boundary."
)


def _qualification_step(
    paths: Any,
    bindings: Any,
    production_complete: bool,
    pointers: Mapping[str, str | None],
) -> LifecycleStep:
    """Compact P7 projection.

    The public campaign does not end at final production: a frozen product is
    still unqualified until P7 says otherwise.  This reads only pointer rows and
    the small records they name, and it never routes to locked activation --
    opening locked evidence is irreversible and stays an explicit operator act.

    For a multi-size frozen design there is no authorized release path at all,
    so the completed experiment is reported as terminal rather than routed into
    a command that is guaranteed to fail closed.
    """

    description = "post-production qualification of the frozen final publication"

    def step(state: str, message: str, *, terminal: bool = False) -> LifecycleStep:
        return LifecycleStep(
            "post_production_qualification",
            "qualification run",
            "qualification",
            description,
            state,
            message,
            terminal=terminal,
        )

    if not production_complete or not bindings:
        return step(
            LifecycleObservationState.NOT_STARTED,
            "no final-production publication has been frozen yet",
        )
    if len(bindings) > 1:
        return step(
            LifecycleObservationState.COMPLETE,
            MULTI_SIZE_TERMINAL_MESSAGE,
            terminal=True,
        )
    binding = bindings[0]

    from .qualification.record import ProductionQualificationRecord
    from .qualification.store import (
        POINTER_LOCKED_ACTIVATION,
        POINTER_QUALIFICATION_PLAN,
        POINTER_QUALIFICATION_RECORD,
        POINTER_RELEASE_EVIDENCE,
        QualificationEvidenceStore,
        qualification_root,
    )

    # ``QualificationEvidenceStore`` is a pure path holder; naming a root does
    # not create one.
    store = QualificationEvidenceStore(
        root=qualification_root(paths, binding.campaign_generation)
    )
    prefix = f"qualification:{binding.content_digest}:"
    plan_digest = pointers.get(prefix + POINTER_QUALIFICATION_PLAN)
    record_digest = pointers.get(prefix + POINTER_QUALIFICATION_RECORD)
    locked_digest = pointers.get(prefix + POINTER_LOCKED_ACTIVATION)
    release_digest = pointers.get(prefix + POINTER_RELEASE_EVIDENCE)

    if record_digest is not None:
        record = _authenticated(
            store, record_digest, ProductionQualificationRecord.from_dict
        )
        if record is None:
            return step(
                LifecycleObservationState.BLOCKED,
                "the current qualification record pointer names an object that is "
                f"missing, unreadable, or does not reproduce its own identity "
                f"({_short(record_digest)})",
            )
        verdict = str(record.verdict.value) or "unknown"
        release = "release evidence published" if release_digest else "no release index"
        # Only `rejected` and `release_qualified` are terminal verdicts.
        # `waiting_for_reference` and `incomplete` are truthful *nonterminal*
        # product states: qualification has run and has said, correctly, that it
        # cannot finish yet. Reporting either as a completed stage would tell an
        # operator the campaign is done when the product is still unqualified.
        if verdict == "rejected":
            return step(
                LifecycleObservationState.COMPLETE,
                f"terminal qualification verdict: rejected ({release})",
                terminal=True,
            )
        if verdict == "release_qualified":
            return step(
                LifecycleObservationState.COMPLETE,
                f"terminal qualification verdict: release_qualified ({release})",
            )
        if verdict == "waiting_for_reference":
            return step(
                LifecycleObservationState.WAITING,
                "qualification is waiting for independent external reference "
                "evidence; supply the requested bundle and rerun "
                "`qualification run`",
            )
        return step(
            LifecycleObservationState.WAITING,
            f"qualification is incomplete (verdict: {verdict}); rerun "
            "`qualification run`. Locked evidence, when required, is activated "
            "only by the explicit `qualification activate-locked` command",
        )

    if plan_digest is None:
        return step(
            LifecycleObservationState.NOT_STARTED,
            "the frozen publication has not been qualified; run `qualification run`",
        )
    locked = (
        "locked cohort activated"
        if locked_digest
        else "locked cohort not activated (explicit `qualification activate-locked` only)"
    )
    return step(
        LifecycleObservationState.WAITING,
        f"qualification plan is current ({_short(plan_digest)}); no terminal verdict "
        f"has been published yet; {locked}",
    )


def project_campaign_lifecycle(
    paths: Any, store: Any
) -> CampaignLifecycleSnapshot:
    """Project the public lifecycle from persisted owner state, coherently."""

    steps: list[LifecycleStep] = [_doctor_step(store, paths)]
    revision, bindings, pointers = campaign_owner_snapshot(store)
    state = None if revision is None else revision.state
    prepare = _prepare_step(state)
    steps.append(prepare)
    prepare_complete = prepare.state == LifecycleObservationState.COMPLETE
    steps.append(_screen_step(state, prepare_complete))
    if not prepare_complete:
        bindings = ()
    cv_step, production_step = _post_selection_steps(paths, bindings, pointers)
    steps.append(cv_step)
    steps.append(production_step)
    steps.append(
        _qualification_step(
            paths,
            bindings,
            production_step.state == LifecycleObservationState.COMPLETE,
            pointers,
        )
    )
    return CampaignLifecycleSnapshot(
        state_revision=None if revision is None else revision.state_revision,
        generation=None if state is None else state.generation,
        steps=tuple(steps),
    )


__all__ = [
    "MULTI_SIZE_TERMINAL_MESSAGE",
    "CampaignLifecycleSnapshot",
    "campaign_owner_snapshot",
    "LifecycleObservationState",
    "LifecycleStep",
    "project_campaign_lifecycle",
]
