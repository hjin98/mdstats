"""Mutable current-runtime target-size campaign state owned by the campaign store.

This module owns exactly one mutable authority for the current target-size
runtime: the campaign regime, the canonical target-size generation, the
subordinate execution attempt, the lifecycle state, the authenticated
references to the accepted P1/P2/P3 scientific authorities, and the terminal
selection projection.

It deliberately owns *no* scientific decision logic.  Candidate qualification,
split construction, training/evaluation order, reducer advancement, execution
replay, and terminal selection all remain owned by
:mod:`mdstats.training_data.neutral_substrate`,
:mod:`mdstats.training_data.target_size_experiment`, and
:mod:`mdstats.training_data.target_size_execution`.  What lives here is the
persistence-facing state machine that references those owners and the
compare-and-set contract that makes its transitions exclusive.

Every mutable transition executes inside one real serialized SQLite
transaction supplied by the campaign store and compares the expected regime,
schema, canonical generation, subordinate attempt, and predecessor state
revision before writing the successor.  The persisted chain is append-only and
structurally exclusive: at most one successor may exist for any predecessor
revision, so two divergent transitions from one predecessor can never both
commit even across processes.

Because a transition's identity is derived deterministically from its kind,
its expected predecessor authority, and the complete canonical successor
payload, an interrupted writer can safely retry: an exactly identical retry is
recognized and returns the already-committed successor, while a retry that
changed any authoritative reference is a conflict rather than a duplicate.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence
import json
import sqlite3

from ._common import (
    TrainingDataError,
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)

TARGET_SIZE_CAMPAIGN_STATE_SCHEMA = "mdstats.target-size-campaign-state.v1"
TARGET_SIZE_CAMPAIGN_REVISION_SCHEMA = "mdstats.target-size-campaign-state-revision.v1"
TARGET_SIZE_CAMPAIGN_TRANSITION_IDENTITY_SCHEMA = (
    "mdstats.target-size-campaign-transition-identity.v1"
)
TARGET_SIZE_CAMPAIGN_TERMINAL_PROJECTION_SCHEMA = (
    "mdstats.target-size-campaign-terminal-projection.v1"
)

_STATE_TABLE = "target_size_campaign_state"


class TargetSizeCampaignStateError(TrainingDataError):
    """Base class for current target-size campaign-state failures."""


class TargetSizeCampaignCorruptionError(TargetSizeCampaignStateError):
    """Persisted campaign state is malformed, unauthenticated, or tampered."""


class TargetSizeCampaignConflictError(TargetSizeCampaignStateError):
    """A writer lost the generation/attempt/predecessor compare-and-set."""

    def __init__(self, message: str, *, conflict_kind: str) -> None:
        super().__init__(message)
        self.conflict_kind = str(conflict_kind)


class TargetSizeRegime(str, Enum):
    """Durable campaign-wide target-size runtime regime."""

    LEGACY = "legacy"
    TRANSITIONING = "transitioning"
    CURRENT = "current"


class TargetSizeLifecycle(str, Enum):
    """Current lifecycle position of the canonical target-size generation."""

    UNCONVERTED = "unconverted"
    AWAITING_AUTHORITIES = "awaiting_authorities"
    AUTHORITIES_BOUND = "authorities_bound"
    SCREEN_ACTIVE = "screen_active"
    TERMINAL_SELECTED = "terminal_selected"
    TERMINAL_SCIENTIFIC_FAILURE = "terminal_scientific_failure"


class TargetSizeTransitionKind(str, Enum):
    """Logical kind of one mutable target-size campaign transition."""

    INITIALIZE = "initialize"
    BEGIN_CUTOVER = "begin_cutover"
    BIND_AUTHORITIES = "bind_authorities"
    COMPLETE_CUTOVER = "complete_cutover"
    OPEN_ATTEMPT = "open_attempt"
    CLOSE_ATTEMPT = "close_attempt"
    ADOPT_EXECUTION_HEAD = "adopt_execution_head"
    RECORD_TERMINAL_SELECTION = "record_terminal_selection"
    RECORD_TERMINAL_SCIENTIFIC_FAILURE = "record_terminal_scientific_failure"
    ADVANCE_GENERATION = "advance_generation"


_TERMINAL_LIFECYCLES = frozenset(
    {
        TargetSizeLifecycle.TERMINAL_SELECTED,
        TargetSizeLifecycle.TERMINAL_SCIENTIFIC_FAILURE,
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _optional_digest(value: Any, *, name: str) -> str | None:
    if value is None:
        return None
    return validate_digest(str(value), name=name)


def _canonical_relative_locator(value: Any, *, name: str) -> str | None:
    """Return a campaign-relative POSIX locator, never an escaping path."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        raise TrainingDataInputError(f"{name} must not be empty.")
    from pathlib import PurePosixPath

    path = PurePosixPath(text.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts:
        raise TrainingDataInputError(
            f"{name} must be a campaign-relative locator that does not escape the workspace."
        )
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class TargetSizeTerminalProjection:
    """Authenticated downstream materialization of terminal P2/P3 state.

    Every field here is re-derivable from the authenticated terminal reducer
    state and the P2 training order.  Nothing in this record is an independent
    decision input; it exists so a reload can compare a fresh derivation
    against what was committed and fail closed on any divergence.
    """

    reducer_status: str
    experiment_definition_digest: str
    reducer_state_digest: str
    execution_head_digest: str
    training_order_digest: str
    selected_target_size: int | None = None
    selected_membership_digest: str | None = None
    terminal_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        status = str(self.reducer_status).strip()
        if not status:
            raise TrainingDataInputError("Terminal projection requires a reducer status.")
        object.__setattr__(self, "reducer_status", status)
        for name in (
            "experiment_definition_digest",
            "reducer_state_digest",
            "execution_head_digest",
            "training_order_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(str(getattr(self, name)), name=name)
            )
        object.__setattr__(
            self,
            "selected_membership_digest",
            _optional_digest(
                self.selected_membership_digest, name="selected_membership_digest"
            ),
        )
        if self.selected_target_size is not None:
            size = int(self.selected_target_size)
            if size <= 0:
                raise TrainingDataInputError(
                    "Terminal projection selected target size must be positive."
                )
            object.__setattr__(self, "selected_target_size", size)
        if (self.selected_target_size is None) != (
            self.selected_membership_digest is None
        ):
            raise TrainingDataInputError(
                "Terminal projection must bind N_selected and exact T_selected identity together."
            )
        object.__setattr__(
            self,
            "terminal_reason_codes",
            tuple(str(code) for code in self.terminal_reason_codes),
        )

    @property
    def is_selection(self) -> bool:
        return self.selected_target_size is not None

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_CAMPAIGN_TERMINAL_PROJECTION_SCHEMA,
            "reducer_status": self.reducer_status,
            "experiment_definition_digest": self.experiment_definition_digest,
            "reducer_state_digest": self.reducer_state_digest,
            "execution_head_digest": self.execution_head_digest,
            "training_order_digest": self.training_order_digest,
            "selected_target_size": self.selected_target_size,
            "selected_membership_digest": self.selected_membership_digest,
            "terminal_reason_codes": list(self.terminal_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeTerminalProjection:
        if payload.get("schema") != TARGET_SIZE_CAMPAIGN_TERMINAL_PROJECTION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size terminal projection schema."
            )
        result = cls(
            reducer_status=str(payload["reducer_status"]),
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            reducer_state_digest=str(payload["reducer_state_digest"]),
            execution_head_digest=str(payload["execution_head_digest"]),
            training_order_digest=str(payload["training_order_digest"]),
            selected_target_size=(
                None
                if payload.get("selected_target_size") is None
                else int(payload["selected_target_size"])
            ),
            selected_membership_digest=(
                None
                if payload.get("selected_membership_digest") is None
                else str(payload["selected_membership_digest"])
            ),
            terminal_reason_codes=tuple(
                str(code) for code in payload.get("terminal_reason_codes", ())
            ),
        )
        expected = payload.get("content_digest")
        if expected is not None and str(expected) != result.content_digest:
            raise TrainingDataSerializationError(
                "Target-size terminal projection digest does not authenticate its payload."
            )
        return result


@dataclass(frozen=True, slots=True)
class TargetSizeCampaignState:
    """The single mutable current-runtime target-size authority.

    ``generation`` is the canonical target-size generation.  No other counter
    may advance target-size authority; ``attempt`` is strictly subordinate to
    it and is cleared whenever the generation is replaced.
    """

    regime: TargetSizeRegime
    generation: int
    lifecycle: TargetSizeLifecycle
    attempt: str | None = None
    frame_authority_digest: str | None = None
    neutral_statistical_base_digest: str | None = None
    split_exclusion_digest: str | None = None
    policy_digest: str | None = None
    experiment_definition_digest: str | None = None
    aggregate_digest: str | None = None
    prepared_manifest_digest: str | None = None
    execution_context_digest: str | None = None
    common_preparation_digest: str | None = None
    screen_window_digest: str | None = None
    execution_root: str | None = None
    adopted_execution_head_digest: str | None = None
    adopted_reducer_state_digest: str | None = None
    terminal: TargetSizeTerminalProjection | None = None
    disposition: str | None = None
    disposition_detail: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "regime", TargetSizeRegime(self.regime))
        object.__setattr__(self, "lifecycle", TargetSizeLifecycle(self.lifecycle))
        generation = int(self.generation)
        if generation < 0:
            raise TrainingDataInputError(
                "Canonical target-size generation must be non-negative."
            )
        object.__setattr__(self, "generation", generation)
        if self.attempt is not None:
            attempt = str(self.attempt).strip()
            if not attempt:
                raise TrainingDataInputError(
                    "Subordinate execution attempt identity must not be empty."
                )
            object.__setattr__(self, "attempt", attempt)
        for name in (
            "frame_authority_digest",
            "neutral_statistical_base_digest",
            "split_exclusion_digest",
            "policy_digest",
            "experiment_definition_digest",
            "aggregate_digest",
            "prepared_manifest_digest",
            "execution_context_digest",
            "common_preparation_digest",
            "screen_window_digest",
            "adopted_execution_head_digest",
            "adopted_reducer_state_digest",
        ):
            object.__setattr__(
                self, name, _optional_digest(getattr(self, name), name=name)
            )
        object.__setattr__(
            self,
            "execution_root",
            _canonical_relative_locator(self.execution_root, name="execution_root"),
        )
        if self.terminal is not None and not isinstance(
            self.terminal, TargetSizeTerminalProjection
        ):
            raise TrainingDataInputError(
                "Terminal campaign projection must be a TargetSizeTerminalProjection."
            )
        for name in ("disposition", "disposition_detail"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, str(value))
        self._validate_consistency()

    def _validate_consistency(self) -> None:
        if self.regime is not TargetSizeRegime.CURRENT and self.lifecycle in (
            TargetSizeLifecycle.SCREEN_ACTIVE,
            *_TERMINAL_LIFECYCLES,
        ):
            raise TrainingDataInputError(
                "Target-size execution lifecycle requires the current runtime regime."
            )
        if (
            self.regime is TargetSizeRegime.LEGACY
            and self.lifecycle is not TargetSizeLifecycle.UNCONVERTED
        ):
            raise TrainingDataInputError(
                "An unconverted campaign cannot carry current target-size lifecycle state."
            )
        if self.lifecycle is TargetSizeLifecycle.UNCONVERTED and (
            self.attempt is not None
            or self.aggregate_digest is not None
            or self.adopted_execution_head_digest is not None
            or self.terminal is not None
        ):
            raise TrainingDataInputError(
                "An unconverted campaign cannot bind current target-size authority."
            )
        if self.lifecycle in (
            TargetSizeLifecycle.AUTHORITIES_BOUND,
            TargetSizeLifecycle.SCREEN_ACTIVE,
            *_TERMINAL_LIFECYCLES,
        ):
            for name in (
                "frame_authority_digest",
                "neutral_statistical_base_digest",
                "split_exclusion_digest",
                "policy_digest",
                "experiment_definition_digest",
                "aggregate_digest",
            ):
                if getattr(self, name) is None:
                    raise TrainingDataInputError(
                        f"Bound target-size campaign state requires {name}."
                    )
        if self.lifecycle in (TargetSizeLifecycle.SCREEN_ACTIVE, *_TERMINAL_LIFECYCLES):
            for name in (
                "execution_context_digest",
                "common_preparation_digest",
                "screen_window_digest",
                "execution_root",
            ):
                if getattr(self, name) is None:
                    raise TrainingDataInputError(
                        f"An active target-size screen requires {name}."
                    )
        if self.adopted_execution_head_digest is not None and (
            self.adopted_reducer_state_digest is None
        ):
            raise TrainingDataInputError(
                "An adopted execution head must be bound together with its reducer state digest."
            )
        if self.terminal is None:
            if self.lifecycle in _TERMINAL_LIFECYCLES:
                raise TrainingDataInputError(
                    "Terminal target-size lifecycle requires a terminal projection."
                )
        else:
            if self.lifecycle not in _TERMINAL_LIFECYCLES:
                raise TrainingDataInputError(
                    "A terminal projection cannot be attached to a nonterminal lifecycle."
                )
            if (
                self.lifecycle is TargetSizeLifecycle.TERMINAL_SELECTED
            ) != self.terminal.is_selection:
                raise TrainingDataInputError(
                    "Terminal lifecycle and terminal projection disagree about selection."
                )
            if self.terminal.experiment_definition_digest != (
                self.experiment_definition_digest
            ):
                raise TrainingDataInputError(
                    "Terminal projection binds a different P2 experiment definition."
                )
            if self.terminal.execution_head_digest != (
                self.adopted_execution_head_digest
            ):
                raise TrainingDataInputError(
                    "Terminal projection binds a different adopted P3 execution head."
                )
            if self.terminal.reducer_state_digest != self.adopted_reducer_state_digest:
                raise TrainingDataInputError(
                    "Terminal projection binds a different adopted reducer state."
                )

    def _base_payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_CAMPAIGN_STATE_SCHEMA,
            "regime": self.regime.value,
            "generation": self.generation,
            "attempt": self.attempt,
            "lifecycle": self.lifecycle.value,
            "frame_authority_digest": self.frame_authority_digest,
            "neutral_statistical_base_digest": self.neutral_statistical_base_digest,
            "split_exclusion_digest": self.split_exclusion_digest,
            "policy_digest": self.policy_digest,
            "experiment_definition_digest": self.experiment_definition_digest,
            "aggregate_digest": self.aggregate_digest,
            "execution_context_digest": self.execution_context_digest,
            "common_preparation_digest": self.common_preparation_digest,
            "screen_window_digest": self.screen_window_digest,
            "execution_root": self.execution_root,
            "adopted_execution_head_digest": self.adopted_execution_head_digest,
            "adopted_reducer_state_digest": self.adopted_reducer_state_digest,
            "terminal": None if self.terminal is None else self.terminal.to_dict(),
            "disposition": self.disposition,
            "disposition_detail": self.disposition_detail,
        }

    def _payload(self) -> dict[str, Any]:
        payload = self._base_payload()
        if self.prepared_manifest_digest is not None:
            # Only a state that actually binds an immutable prepared generation
            # carries this key. Omitting it when absent keeps the identity of a
            # pre-repair campaign row exactly what it was when committed, so an
            # old-format workspace still loads and can be told, truthfully, that
            # it needs one explicit `prepare`.
            payload["prepared_manifest_digest"] = self.prepared_manifest_digest
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCampaignState:
        if payload.get("schema") != TARGET_SIZE_CAMPAIGN_STATE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported target-size campaign-state schema."
            )
        terminal_payload = payload.get("terminal")
        result = cls(
            regime=TargetSizeRegime(payload["regime"]),
            generation=int(payload["generation"]),
            lifecycle=TargetSizeLifecycle(payload["lifecycle"]),
            attempt=(
                None if payload.get("attempt") is None else str(payload["attempt"])
            ),
            frame_authority_digest=_text_or_none(payload.get("frame_authority_digest")),
            neutral_statistical_base_digest=_text_or_none(
                payload.get("neutral_statistical_base_digest")
            ),
            split_exclusion_digest=_text_or_none(payload.get("split_exclusion_digest")),
            policy_digest=_text_or_none(payload.get("policy_digest")),
            experiment_definition_digest=_text_or_none(
                payload.get("experiment_definition_digest")
            ),
            aggregate_digest=_text_or_none(payload.get("aggregate_digest")),
            prepared_manifest_digest=_text_or_none(
                payload.get("prepared_manifest_digest")
            ),
            execution_context_digest=_text_or_none(
                payload.get("execution_context_digest")
            ),
            common_preparation_digest=_text_or_none(
                payload.get("common_preparation_digest")
            ),
            screen_window_digest=_text_or_none(payload.get("screen_window_digest")),
            execution_root=_text_or_none(payload.get("execution_root")),
            adopted_execution_head_digest=_text_or_none(
                payload.get("adopted_execution_head_digest")
            ),
            adopted_reducer_state_digest=_text_or_none(
                payload.get("adopted_reducer_state_digest")
            ),
            terminal=(
                None
                if terminal_payload is None
                else TargetSizeTerminalProjection.from_dict(terminal_payload)
            ),
            disposition=_text_or_none(payload.get("disposition")),
            disposition_detail=_text_or_none(payload.get("disposition_detail")),
        )
        expected = payload.get("content_digest")
        if expected is not None and str(expected) != result.content_digest:
            raise TrainingDataSerializationError(
                "Target-size campaign state digest does not authenticate its payload."
            )
        return result


def _text_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


@dataclass(frozen=True, slots=True)
class TargetSizeCampaignRevision:
    """One committed link of the append-only campaign-state chain."""

    sequence: int
    state_revision: str
    predecessor_revision: str | None
    transition_identity: str
    transition_kind: TargetSizeTransitionKind
    state: TargetSizeCampaignState
    committed_utc: str

    @property
    def regime(self) -> TargetSizeRegime:
        return self.state.regime

    @property
    def generation(self) -> int:
        return self.state.generation

    @property
    def attempt(self) -> str | None:
        return self.state.attempt

    def expectation(self) -> TargetSizeCasExpectation:
        """The exact predecessor token a successor transition must present."""

        return TargetSizeCasExpectation(
            regime=self.state.regime,
            generation=self.state.generation,
            attempt=self.state.attempt,
            state_revision=self.state_revision,
        )


@dataclass(frozen=True, slots=True)
class TargetSizeCasExpectation:
    """The complete predecessor authority a mutation must match."""

    regime: TargetSizeRegime
    generation: int
    attempt: str | None
    state_revision: str
    schema_version: str = TARGET_SIZE_CAMPAIGN_STATE_SCHEMA

    def __post_init__(self) -> None:
        object.__setattr__(self, "regime", TargetSizeRegime(self.regime))
        object.__setattr__(self, "generation", int(self.generation))
        object.__setattr__(
            self,
            "state_revision",
            validate_digest(str(self.state_revision), name="state_revision"),
        )
        if self.attempt is not None:
            object.__setattr__(self, "attempt", str(self.attempt))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "regime": self.regime.value,
            "generation": self.generation,
            "attempt": self.attempt,
            "state_revision": self.state_revision,
        }


@dataclass(frozen=True, slots=True)
class TargetSizeTransitionResult:
    """Outcome of one attempted mutable campaign transition."""

    revision: TargetSizeCampaignRevision
    idempotent: bool

    @property
    def state(self) -> TargetSizeCampaignState:
        return self.revision.state


def target_size_transition_identity(
    *,
    kind: TargetSizeTransitionKind,
    expected: TargetSizeCasExpectation | None,
    successor: TargetSizeCampaignState,
) -> str:
    """Deterministic logical identity of one campaign transition.

    The identity binds the transition kind, the exact expected predecessor
    authority (schema, regime, canonical generation, subordinate attempt, and
    predecessor state revision), and the complete canonical successor payload.
    Two attempts share an identity only when they are the same logical
    transition; changing any authoritative reference in the successor produces
    a different identity and is therefore a conflict rather than a duplicate.
    """

    return digest(
        {
            "schema": TARGET_SIZE_CAMPAIGN_TRANSITION_IDENTITY_SCHEMA,
            "kind": TargetSizeTransitionKind(kind).value,
            "expected": None if expected is None else expected._payload(),
            "successor": successor._payload(),
        }
    )


def _state_revision(
    *,
    sequence: int,
    predecessor_revision: str | None,
    transition_identity: str,
    kind: TargetSizeTransitionKind,
    successor: TargetSizeCampaignState,
) -> str:
    return digest(
        {
            "schema": TARGET_SIZE_CAMPAIGN_REVISION_SCHEMA,
            "sequence": int(sequence),
            "predecessor_revision": predecessor_revision,
            "transition_identity": transition_identity,
            "kind": TargetSizeTransitionKind(kind).value,
            "state": successor._payload(),
        }
    )


_SELECT_COLUMNS = (
    "sequence, state_revision, predecessor_revision, transition_identity, "
    "transition_kind, payload, committed_utc"
)


def _revision_from_row(row: Sequence[Any]) -> TargetSizeCampaignRevision:
    (
        sequence,
        state_revision,
        predecessor_revision,
        transition_identity,
        transition_kind,
        payload,
        committed_utc,
    ) = row
    try:
        decoded = json.loads(payload)
        state = TargetSizeCampaignState.from_dict(decoded)
        kind = TargetSizeTransitionKind(transition_kind)
    except (
        ValueError,
        KeyError,
        TypeError,
        TrainingDataError,
    ) as exc:
        raise TargetSizeCampaignCorruptionError(
            f"Persisted target-size campaign state is corrupt at sequence {sequence}: {exc}"
        ) from exc
    recomputed = _state_revision(
        sequence=int(sequence),
        predecessor_revision=(
            None if predecessor_revision is None else str(predecessor_revision)
        ),
        transition_identity=str(transition_identity),
        kind=kind,
        successor=state,
    )
    if recomputed != str(state_revision):
        raise TargetSizeCampaignCorruptionError(
            "Persisted target-size campaign state revision does not authenticate its payload; "
            "the campaign state database was modified outside the campaign store."
        )
    return TargetSizeCampaignRevision(
        sequence=int(sequence),
        state_revision=str(state_revision),
        predecessor_revision=(
            None if predecessor_revision is None else str(predecessor_revision)
        ),
        transition_identity=str(transition_identity),
        transition_kind=kind,
        state=state,
        committed_utc=str(committed_utc),
    )


def _load_head(db: sqlite3.Connection) -> TargetSizeCampaignRevision | None:
    row = db.execute(
        f"SELECT {_SELECT_COLUMNS} FROM {_STATE_TABLE} "
        "ORDER BY sequence DESC LIMIT 1"
    ).fetchone()
    return None if row is None else _revision_from_row(row)


def _load_by_identity(
    db: sqlite3.Connection, identity: str
) -> TargetSizeCampaignRevision | None:
    row = db.execute(
        f"SELECT {_SELECT_COLUMNS} FROM {_STATE_TABLE} WHERE transition_identity=?",
        (identity,),
    ).fetchone()
    return None if row is None else _revision_from_row(row)


def load_target_size_campaign_revision(store: Any) -> TargetSizeCampaignRevision | None:
    """Return the current campaign-state revision, or ``None`` before genesis."""

    with store._connect() as db:  # noqa: SLF001 - campaign store owns its connection pool
        return _load_head(db)


def load_target_size_campaign_history(
    store: Any,
) -> tuple[TargetSizeCampaignRevision, ...]:
    """Return the complete authenticated campaign-state chain, oldest first."""

    with store._connect() as db:  # noqa: SLF001
        rows = db.execute(
            f"SELECT {_SELECT_COLUMNS} FROM {_STATE_TABLE} ORDER BY sequence ASC"
        ).fetchall()
    return tuple(_revision_from_row(row) for row in rows)


def initial_target_size_campaign_state() -> TargetSizeCampaignState:
    """The genesis state of a campaign that has not been converted yet."""

    return TargetSizeCampaignState(
        regime=TargetSizeRegime.LEGACY,
        generation=0,
        lifecycle=TargetSizeLifecycle.UNCONVERTED,
    )


def ensure_target_size_campaign_revision(store: Any) -> TargetSizeCampaignRevision:
    """Return the current revision, creating the genesis unconverted state once.

    Genesis creation is itself a CAS transition, so two processes opening the
    same fresh campaign concurrently cannot both create a root.
    """

    existing = load_target_size_campaign_revision(store)
    if existing is not None:
        return existing
    result = commit_target_size_campaign_transition(
        store,
        kind=TargetSizeTransitionKind.INITIALIZE,
        expected=None,
        successor=initial_target_size_campaign_state(),
    )
    return result.revision


def commit_target_size_campaign_transition(
    store: Any,
    *,
    kind: TargetSizeTransitionKind,
    expected: TargetSizeCasExpectation | None,
    successor: TargetSizeCampaignState,
) -> TargetSizeTransitionResult:
    """Commit one mutable target-size campaign transition under full CAS.

    The compare and the write happen inside one serialized SQLite write
    transaction.  The comparison covers the expected schema, regime, canonical
    generation, subordinate attempt, and predecessor state revision; the same
    transaction advances the revision and appends the successor.

    An exactly identical retry of an already-committed transition returns that
    committed successor with ``idempotent=True``.  Any other mismatch raises
    :class:`TargetSizeCampaignConflictError` with a ``conflict_kind``
    describing why the writer lost.
    """

    kind = TargetSizeTransitionKind(kind)
    if not isinstance(successor, TargetSizeCampaignState):
        raise TrainingDataInputError(
            "A target-size campaign transition requires one TargetSizeCampaignState successor."
        )
    if expected is not None and not isinstance(expected, TargetSizeCasExpectation):
        raise TrainingDataInputError(
            "A target-size campaign transition requires one TargetSizeCasExpectation."
        )
    _validate_transition_semantics(kind=kind, expected=expected, successor=successor)
    identity = target_size_transition_identity(
        kind=kind, expected=expected, successor=successor
    )

    with store.exclusive_transaction() as db:
        head = _load_head(db)
        if head is None:
            if expected is not None:
                duplicate = _load_by_identity(db, identity)
                if duplicate is not None:  # pragma: no cover - head implies a row
                    return TargetSizeTransitionResult(duplicate, idempotent=True)
                raise TargetSizeCampaignConflictError(
                    "No target-size campaign state exists yet; the expected predecessor "
                    "revision cannot be satisfied.",
                    conflict_kind="uninitialized",
                )
            sequence = 0
            predecessor_revision = None
        else:
            if expected is None:
                duplicate = _load_by_identity(db, identity)
                if duplicate is not None:
                    return TargetSizeTransitionResult(duplicate, idempotent=True)
                raise TargetSizeCampaignConflictError(
                    "Target-size campaign state already exists; a genesis transition "
                    "cannot replace it.",
                    conflict_kind="already_initialized",
                )
            mismatch = _expectation_mismatch(expected, head)
            if mismatch is not None:
                duplicate = _load_by_identity(db, identity)
                if duplicate is not None:
                    return TargetSizeTransitionResult(duplicate, idempotent=True)
                raise TargetSizeCampaignConflictError(
                    _conflict_message(mismatch, expected, head),
                    conflict_kind=mismatch,
                )
            sequence = head.sequence + 1
            predecessor_revision = head.state_revision

        state_revision = _state_revision(
            sequence=sequence,
            predecessor_revision=predecessor_revision,
            transition_identity=identity,
            kind=kind,
            successor=successor,
        )
        committed_utc = _utc_now()
        try:
            db.execute(
                f"INSERT INTO {_STATE_TABLE}"
                "(state_revision, sequence, predecessor_revision, transition_identity,"
                " transition_kind, payload, committed_utc) VALUES (?,?,?,?,?,?,?)",
                (
                    state_revision,
                    sequence,
                    predecessor_revision,
                    identity,
                    kind.value,
                    json.dumps(
                        successor.to_dict(), sort_keys=True, separators=(",", ":")
                    ),
                    committed_utc,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise TargetSizeCampaignConflictError(
                "Another target-size campaign transition already claimed this predecessor "
                f"revision: {exc}",
                conflict_kind="stale_revision",
            ) from exc
        revision = TargetSizeCampaignRevision(
            sequence=sequence,
            state_revision=state_revision,
            predecessor_revision=predecessor_revision,
            transition_identity=identity,
            transition_kind=kind,
            state=successor,
            committed_utc=committed_utc,
        )
    return TargetSizeTransitionResult(revision, idempotent=False)


def _expectation_mismatch(
    expected: TargetSizeCasExpectation, head: TargetSizeCampaignRevision
) -> str | None:
    if expected.schema_version != TARGET_SIZE_CAMPAIGN_STATE_SCHEMA:
        return "schema_mismatch"
    # The canonical generation is the coarse authority, so report generation
    # loss before revision staleness: a writer whose generation was replaced
    # needs a different recovery than one that merely lost a same-generation
    # race.
    if expected.generation < head.generation:
        return "stale_generation"
    if expected.generation > head.generation:
        return "unknown_generation"
    if expected.state_revision != head.state_revision:
        return "stale_revision"
    # The revision digest authenticates the whole persisted state, so a regime
    # or attempt disagreement at a matching revision is a forged expectation
    # rather than a lost race.
    if expected.regime is not head.regime:
        return "regime_mismatch"
    if expected.attempt != head.attempt:
        return "attempt_mismatch"
    return None


def _conflict_message(
    mismatch: str,
    expected: TargetSizeCasExpectation,
    head: TargetSizeCampaignRevision,
) -> str:
    if mismatch == "stale_generation":
        return (
            f"Target-size campaign generation {expected.generation} no longer owns this "
            f"campaign; generation {head.generation} is current."
        )
    if mismatch == "unknown_generation":
        return (
            f"Target-size campaign generation {expected.generation} is ahead of the "
            f"persisted canonical generation {head.generation}."
        )
    if mismatch == "regime_mismatch":
        return (
            f"Target-size campaign regime changed to {head.regime.value!r}; the writer "
            f"expected {expected.regime.value!r}."
        )
    if mismatch == "attempt_mismatch":
        return (
            "Target-size campaign execution attempt changed; the writer expected "
            f"{expected.attempt!r} but {head.attempt!r} is current."
        )
    if mismatch == "schema_mismatch":
        return (
            "Target-size campaign state schema mismatch; retired schemas are never "
            "reinterpreted as current authority."
        )
    return (
        "Target-size campaign state advanced since this writer read it; the expected "
        "predecessor revision is stale."
    )


def _validate_transition_semantics(
    *,
    kind: TargetSizeTransitionKind,
    expected: TargetSizeCasExpectation | None,
    successor: TargetSizeCampaignState,
) -> None:
    """Reject transitions that would break subordination or regime invariants."""

    if kind is TargetSizeTransitionKind.INITIALIZE:
        if expected is not None:
            raise TrainingDataInputError(
                "A genesis target-size campaign transition cannot expect a predecessor."
            )
        if successor != initial_target_size_campaign_state():
            raise TrainingDataInputError(
                "A genesis target-size campaign transition must publish the unconverted state."
            )
        return
    if expected is None:
        raise TrainingDataInputError(
            "Every non-genesis target-size campaign transition requires an expected predecessor."
        )
    if kind is TargetSizeTransitionKind.ADVANCE_GENERATION:
        if successor.generation <= expected.generation:
            raise TrainingDataInputError(
                "Advancing the canonical target-size generation must increase it."
            )
        if successor.attempt is not None:
            raise TrainingDataInputError(
                "A replaced target-size generation cannot inherit a subordinate attempt."
            )
        return
    if kind is TargetSizeTransitionKind.BEGIN_CUTOVER:
        if successor.generation <= expected.generation:
            raise TrainingDataInputError(
                "Entering the target-size cutover must allocate a new canonical generation."
            )
        if successor.regime is not TargetSizeRegime.TRANSITIONING:
            raise TrainingDataInputError(
                "Entering the target-size cutover must publish the transitioning regime."
            )
        return
    if successor.generation != expected.generation:
        raise TrainingDataInputError(
            "Only an explicit generation transition may change the canonical target-size "
            "generation; attempts and lifecycle state are subordinate to it."
        )


__all__ = [
    "TARGET_SIZE_CAMPAIGN_REVISION_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_STATE_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_TERMINAL_PROJECTION_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_TRANSITION_IDENTITY_SCHEMA",
    "TargetSizeCampaignConflictError",
    "TargetSizeCampaignCorruptionError",
    "TargetSizeCampaignRevision",
    "TargetSizeCampaignState",
    "TargetSizeCampaignStateError",
    "TargetSizeCasExpectation",
    "TargetSizeLifecycle",
    "TargetSizeRegime",
    "TargetSizeTerminalProjection",
    "TargetSizeTransitionKind",
    "TargetSizeTransitionResult",
    "commit_target_size_campaign_transition",
    "ensure_target_size_campaign_revision",
    "initial_target_size_campaign_state",
    "load_target_size_campaign_history",
    "load_target_size_campaign_revision",
    "target_size_transition_identity",
]
