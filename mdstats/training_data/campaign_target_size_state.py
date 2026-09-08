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

#: The current schema.  It carries the *ordered collection* of provisional
#: per-size entries and, once ``cross-validate`` admits them, the ordered
#: collection of frozen per-size entries.
TARGET_SIZE_CAMPAIGN_STATE_SCHEMA = "mdstats.target-size-campaign-state.v3"
#: The scalar-selection predecessor schema.  A row written under it carried at
#: most one proposal and at most one frozen selection.  It is read - the chain
#: is append-only - and normalized in memory into a one-entry collection; it is
#: never rewritten in place and never written again.
TARGET_SIZE_CAMPAIGN_STATE_V2_SCHEMA = "mdstats.target-size-campaign-state.v2"
#: The pre-rework schema.  Rows written under it are still authenticated and
#: read, because the persisted chain is append-only and a campaign that cannot
#: read its own head cannot even advance to a fresh generation.  What a legacy
#: row cannot do is carry a proposal or a frozen selection: those fields do not
#: exist in it, so a pre-rework "terminal selected" row cannot create a
#: current-V3 freeze or new current binding.  Supported historical P5A6 workspaces
#: can reopen historical descendants through native historical identity (P1/P2
#: authority and V1 bindings), but cannot authorize new current post-selection work.
TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA = "mdstats.target-size-campaign-state.v1"
#: Every campaign-state schema this runtime can read, newest first.  Only the
#: first is ever written: a retired schema is history, not a target.
_READABLE_STATE_SCHEMAS = (
    TARGET_SIZE_CAMPAIGN_STATE_SCHEMA,
    TARGET_SIZE_CAMPAIGN_STATE_V2_SCHEMA,
    TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA,
)
TARGET_SIZE_CAMPAIGN_REVISION_SCHEMA = "mdstats.target-size-campaign-state-revision.v1"
TARGET_SIZE_CAMPAIGN_TRANSITION_IDENTITY_SCHEMA = (
    "mdstats.target-size-campaign-transition-identity.v1"
)
#: Historical P2/P3 terminology is deliberately retained in this record's wire
#: schema and field names.  The record is a projection of immutable reducer
#: evidence; renaming its persisted keys would invalidate expensive existing
#: screen evidence without changing one scientific fact.  Current code reads it
#: only through the automatic-diagnostic boundary, which projects it publicly as
#: a *recommendation* rather than as a selection.
TARGET_SIZE_AUTO_DIAGNOSTIC_SCHEMA = (
    "mdstats.target-size-campaign-terminal-projection.v1"
)
TARGET_SIZE_PROPOSAL_SCHEMA = "mdstats.target-size-provisional-proposal.v1"
TARGET_SIZE_FROZEN_SELECTION_SCHEMA = "mdstats.target-size-frozen-selection.v1"

#: Provenance of the immediate origin of a proposal.  It is never a numerical
#: variable: the same N under the same horizons is the same downstream
#: experiment however the operator arrived at it.
SELECTION_SOURCE_MANUAL = "manual"
SELECTION_SOURCE_AUTO_RECOMMENDATION = "auto_recommendation"
_SELECTION_SOURCES = frozenset(
    {SELECTION_SOURCE_MANUAL, SELECTION_SOURCE_AUTO_RECOMMENDATION}
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
    """Position of the *automatic diagnostic* for the canonical generation.

    This axis describes one thing only: how far the optional automatic
    target-size screen has got.  It says nothing about whether the operator has
    proposed target sizes or frozen them, because those are independent facts
    carried by :attr:`TargetSizeCampaignState.provisional_entries` and
    :attr:`TargetSizeCampaignState.frozen_entries`.  Encoding their
    cross-product here is exactly the enum maze this state deliberately does
    not have.
    """

    UNCONVERTED = "unconverted"
    AWAITING_AUTHORITIES = "awaiting_authorities"
    AUTHORITIES_BOUND = "authorities_bound"
    SCREEN_ACTIVE = "screen_active"
    #: The diagnostic ran to a terminal reducer outcome.  Whether it produced a
    #: recommendation is read from the diagnostic record, not from this value.
    DIAGNOSTIC_COMPLETE = "diagnostic_complete"


#: How the pre-rework schema spelled :attr:`TargetSizeLifecycle.DIAGNOSTIC_COMPLETE`.
_LEGACY_TERMINAL_SELECTED = "terminal_selected"
_LEGACY_TERMINAL_SCIENTIFIC_FAILURE = "terminal_scientific_failure"


class TargetSizeTransitionKind(str, Enum):
    """Logical kind of one mutable target-size campaign transition."""

    INITIALIZE = "initialize"
    BEGIN_CUTOVER = "begin_cutover"
    BIND_AUTHORITIES = "bind_authorities"
    COMPLETE_CUTOVER = "complete_cutover"
    OPEN_ATTEMPT = "open_attempt"
    CLOSE_ATTEMPT = "close_attempt"
    ADOPT_EXECUTION_HEAD = "adopt_execution_head"
    # The two diagnostic-completion kinds keep their pre-rework wire values so
    # the append-only chain of an existing campaign still authenticates.  They
    # record a diagnostic outcome; under the current contract neither freezes
    # anything.
    RECORD_AUTO_DIAGNOSTIC_RECOMMENDATION = "record_terminal_selection"
    RECORD_AUTO_DIAGNOSTIC_NO_RECOMMENDATION = "record_terminal_scientific_failure"
    SET_PROPOSAL = "set_proposal"
    #: Clear every provisional entry.  It is a distinct kind because it is the
    #: one selection transition whose successor collection is deliberately
    #: empty, and ``set_proposal`` must never be able to publish that.
    RESET_PROPOSAL = "reset_proposal"
    FREEZE_SELECTION = "freeze_selection"
    ADVANCE_GENERATION = "advance_generation"


#: Lifecycles at which the prepared scientific substrate is bound, so a
#: provisional proposal or a frozen selection may exist.
_SUBSTRATE_BOUND_LIFECYCLES = frozenset(
    {
        TargetSizeLifecycle.AUTHORITIES_BOUND,
        TargetSizeLifecycle.SCREEN_ACTIVE,
        TargetSizeLifecycle.DIAGNOSTIC_COMPLETE,
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
class TargetSizeAutoDiagnostic:
    """Authenticated projection of the terminal automatic-screen reducer state.

    Every field here is re-derivable from the authenticated terminal reducer
    state and the P2 training order.  Nothing in this record is an independent
    decision input; it exists so a reload can compare a fresh derivation
    against what was committed and fail closed on any divergence.

    It is *evidence*, not authority.  ``recommended_target_size`` is what the
    short-horizon screen ranked best under its configured protocol; it becomes a
    downstream training size only if an operator proposes it and
    ``cross-validate`` freezes it.  The persisted keys keep the historical P2/P3
    spelling (``selected_*``) so existing screen evidence stays valid bytes; the
    public projection of those keys is a recommendation.
    """

    reducer_status: str
    experiment_definition_digest: str
    reducer_state_digest: str
    execution_head_digest: str
    training_order_digest: str
    recommended_target_size: int | None = None
    recommended_membership_digest: str | None = None
    terminal_reason_codes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        status = str(self.reducer_status).strip()
        if not status:
            raise TrainingDataInputError(
                "An automatic target-size diagnostic requires a reducer status."
            )
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
            "recommended_membership_digest",
            _optional_digest(
                self.recommended_membership_digest,
                name="recommended_membership_digest",
            ),
        )
        if self.recommended_target_size is not None:
            size = int(self.recommended_target_size)
            if size <= 0:
                raise TrainingDataInputError(
                    "A recommended target size must be positive."
                )
            object.__setattr__(self, "recommended_target_size", size)
        if (self.recommended_target_size is None) != (
            self.recommended_membership_digest is None
        ):
            raise TrainingDataInputError(
                "An automatic diagnostic must bind its recommended N and the exact "
                "membership identity of that N together."
            )
        object.__setattr__(
            self,
            "terminal_reason_codes",
            tuple(str(code) for code in self.terminal_reason_codes),
        )

    @property
    def has_recommendation(self) -> bool:
        return self.recommended_target_size is not None

    def _payload(self) -> dict[str, Any]:
        # Historical P2/P3 key spelling; see the module constant.
        return {
            "schema": TARGET_SIZE_AUTO_DIAGNOSTIC_SCHEMA,
            "reducer_status": self.reducer_status,
            "experiment_definition_digest": self.experiment_definition_digest,
            "reducer_state_digest": self.reducer_state_digest,
            "execution_head_digest": self.execution_head_digest,
            "training_order_digest": self.training_order_digest,
            "selected_target_size": self.recommended_target_size,
            "selected_membership_digest": self.recommended_membership_digest,
            "terminal_reason_codes": list(self.terminal_reason_codes),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeAutoDiagnostic:
        if payload.get("schema") != TARGET_SIZE_AUTO_DIAGNOSTIC_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported automatic target-size diagnostic schema."
            )
        result = cls(
            reducer_status=str(payload["reducer_status"]),
            experiment_definition_digest=str(payload["experiment_definition_digest"]),
            reducer_state_digest=str(payload["reducer_state_digest"]),
            execution_head_digest=str(payload["execution_head_digest"]),
            training_order_digest=str(payload["training_order_digest"]),
            recommended_target_size=(
                None
                if payload.get("selected_target_size") is None
                else int(payload["selected_target_size"])
            ),
            recommended_membership_digest=(
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
                "Automatic target-size diagnostic digest does not authenticate its payload."
            )
        return result


def _selection_source(value: Any) -> str:
    text = str(value)
    if text not in _SELECTION_SOURCES:
        raise TrainingDataInputError(
            "Selection source must be one of " + ", ".join(sorted(_SELECTION_SOURCES))
        )
    return text


def _positive_epochs(value: Any, *, name: str) -> int:
    epochs = int(value)
    if epochs <= 0:
        raise TrainingDataInputError(f"{name} must be a positive number of epochs.")
    return epochs


@dataclass(frozen=True, slots=True)
class TargetSizeProposal:
    """One per-size entry of the mutable provisional downstream training design.

    The operator owns these records until ``cross-validate`` admits them.  Each
    is a complete per-size proposal by construction: the horizons it carries are
    the resolved effective values of the invocation that set *it*, so a later
    edit to ``campaign.toml`` cannot silently rewrite an entry that already
    exists, and reselecting one size never perturbs its siblings.

    ``T_provisional`` is never stored as a list.  ``membership_digest`` is the
    identity of ``pi_train[:n_provisional]`` under ``training_order_digest``, and
    it is re-derived from the P2 training order rather than trusted whenever the
    proposal is used.
    """

    n_provisional: int
    membership_digest: str
    training_order_digest: str
    selection_source: str
    cv_max_num_epochs: int
    production_max_num_epochs: int
    #: Identity of the automatic diagnostic this proposal came from, when it
    #: came from one.  Pure provenance: it never re-derives N.
    auto_diagnostic_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "n_provisional", _positive_epochs(self.n_provisional, name="n_provisional")
        )
        for name in ("membership_digest", "training_order_digest"):
            object.__setattr__(
                self, name, validate_digest(str(getattr(self, name)), name=name)
            )
        object.__setattr__(
            self, "selection_source", _selection_source(self.selection_source)
        )
        object.__setattr__(
            self,
            "cv_max_num_epochs",
            _positive_epochs(self.cv_max_num_epochs, name="cv_max_num_epochs"),
        )
        object.__setattr__(
            self,
            "production_max_num_epochs",
            _positive_epochs(
                self.production_max_num_epochs, name="production_max_num_epochs"
            ),
        )
        object.__setattr__(
            self,
            "auto_diagnostic_digest",
            _optional_digest(self.auto_diagnostic_digest, name="auto_diagnostic_digest"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_PROPOSAL_SCHEMA,
            "n_provisional": self.n_provisional,
            "membership_digest": self.membership_digest,
            "training_order_digest": self.training_order_digest,
            "selection_source": self.selection_source,
            "cv_max_num_epochs": self.cv_max_num_epochs,
            "production_max_num_epochs": self.production_max_num_epochs,
            "auto_diagnostic_digest": self.auto_diagnostic_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeProposal:
        if payload.get("schema") != TARGET_SIZE_PROPOSAL_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported provisional target-size proposal schema."
            )
        result = cls(
            n_provisional=int(payload["n_provisional"]),
            membership_digest=str(payload["membership_digest"]),
            training_order_digest=str(payload["training_order_digest"]),
            selection_source=str(payload["selection_source"]),
            cv_max_num_epochs=int(payload["cv_max_num_epochs"]),
            production_max_num_epochs=int(payload["production_max_num_epochs"]),
            auto_diagnostic_digest=_text_or_none(payload.get("auto_diagnostic_digest")),
        )
        expected = payload.get("content_digest")
        if expected is not None and str(expected) != result.content_digest:
            raise TrainingDataSerializationError(
                "Provisional target-size proposal digest does not authenticate its payload."
            )
        return result


@dataclass(frozen=True, slots=True)
class FrozenTargetSelection:
    """One immutable per-size entry of the design admitted at ``cross-validate``.

    Freeze fixes ``N_selected``, the exact ``T_selected`` identity, and both
    role-specific effective horizons in one decision.  Identity *projection*
    stays role-specific: the CV policy reads ``cv_max_num_epochs`` and never the
    production horizon, and the production policy reads
    ``production_max_num_epochs`` and never the CV horizon, so editing one role's
    budget cannot invalidate the other role's accepted evidence.

    ``selection_source`` and ``auto_diagnostic_digest`` are audit provenance.
    They are deliberately excluded from every downstream scientific identity.
    """

    n_selected: int
    selected_membership_digest: str
    training_order_digest: str
    cv_max_num_epochs: int
    production_max_num_epochs: int
    selection_source: str
    auto_diagnostic_digest: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "n_selected", _positive_epochs(self.n_selected, name="n_selected")
        )
        for name in ("selected_membership_digest", "training_order_digest"):
            object.__setattr__(
                self, name, validate_digest(str(getattr(self, name)), name=name)
            )
        object.__setattr__(
            self, "selection_source", _selection_source(self.selection_source)
        )
        object.__setattr__(
            self,
            "cv_max_num_epochs",
            _positive_epochs(self.cv_max_num_epochs, name="cv_max_num_epochs"),
        )
        object.__setattr__(
            self,
            "production_max_num_epochs",
            _positive_epochs(
                self.production_max_num_epochs, name="production_max_num_epochs"
            ),
        )
        object.__setattr__(
            self,
            "auto_diagnostic_digest",
            _optional_digest(self.auto_diagnostic_digest, name="auto_diagnostic_digest"),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_SIZE_FROZEN_SELECTION_SCHEMA,
            "n_selected": self.n_selected,
            "selected_membership_digest": self.selected_membership_digest,
            "training_order_digest": self.training_order_digest,
            "cv_max_num_epochs": self.cv_max_num_epochs,
            "production_max_num_epochs": self.production_max_num_epochs,
            "selection_source": self.selection_source,
            "auto_diagnostic_digest": self.auto_diagnostic_digest,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> FrozenTargetSelection:
        if payload.get("schema") != TARGET_SIZE_FROZEN_SELECTION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported frozen target-selection schema."
            )
        result = cls(
            n_selected=int(payload["n_selected"]),
            selected_membership_digest=str(payload["selected_membership_digest"]),
            training_order_digest=str(payload["training_order_digest"]),
            cv_max_num_epochs=int(payload["cv_max_num_epochs"]),
            production_max_num_epochs=int(payload["production_max_num_epochs"]),
            selection_source=str(payload["selection_source"]),
            auto_diagnostic_digest=_text_or_none(payload.get("auto_diagnostic_digest")),
        )
        expected = payload.get("content_digest")
        if expected is not None and str(expected) != result.content_digest:
            raise TrainingDataSerializationError(
                "Frozen target-selection digest does not authenticate its payload."
            )
        return result


def _validated_entry_collection(
    entries: Any, *, label: str, element: type
) -> tuple[Any, ...]:
    """Return one ordered, unique-by-N per-size collection or fail closed.

    Order is meaning here, not presentation: it is first-insertion order of the
    distinct selected sizes, and it drives deterministic downstream
    orchestration and rendering.  A duplicate ``N`` in authoritative state is
    corruption rather than something to deduplicate silently: two entries for
    one size means two different per-size designs claim the same identity, and
    guessing which one the operator meant is exactly the failure this refuses.
    """

    items = tuple(entries)
    for item in items:
        if not isinstance(item, element):
            raise TrainingDataInputError(
                f"Every {label} entry must be a {element.__name__}."
            )
    sizes = [int(_entry_size(item)) for item in items]
    if len(set(sizes)) != len(sizes):
        raise TrainingDataInputError(
            f"The {label} collection contains more than one entry for the same "
            f"target size ({sorted(sizes)}); a target-size design has at most one "
            "entry per N."
        )
    return items


def _entry_size(entry: Any) -> int:
    """The selected size of a provisional or frozen per-size entry."""

    value = getattr(entry, "n_provisional", None)
    if value is None:
        value = getattr(entry, "n_selected")
    return int(value)


def merge_provisional_entry(
    entries: Sequence[TargetSizeProposal], entry: TargetSizeProposal
) -> tuple[TargetSizeProposal, ...]:
    """Append a new size, or replace an existing size's complete entry in place.

    This is the *one* merge owner.  Manual selection and an adopted automatic
    recommendation both arrive here, so neither can gain collection authority
    the other lacks, and reselecting a size can never reorder the design.
    """

    existing = tuple(entries)
    size = int(entry.n_provisional)
    for index, item in enumerate(existing):
        if int(item.n_provisional) == size:
            return existing[:index] + (entry,) + existing[index + 1 :]
    return existing + (entry,)


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
    auto_diagnostic: TargetSizeAutoDiagnostic | None = None
    #: The ordered provisional design.  Empty is the canonical unselected
    #: state; there is no ``N=undefined`` placeholder record.
    provisional_entries: tuple[TargetSizeProposal, ...] = ()
    #: ``None`` until ``cross-validate`` admits the design, then the complete
    #: ordered frozen collection.  An empty tuple is never valid: freezing
    #: nothing is not a design.
    frozen_entries: tuple[FrozenTargetSelection, ...] | None = None
    #: True only for a design that was frozen by the scalar-selection
    #: predecessor.  Its single descendant binding keeps the predecessor's
    #: binding schema so existing accepted P5/P7 evidence stays current; new
    #: designs never set it and never inherit the identity coupling it carries.
    legacy_scalar_binding: bool = False
    disposition: str | None = None
    disposition_detail: str | None = None
    #: Wire schema of this row.  A row read back from the pre-rework schema
    #: keeps it, so its revision digest still authenticates; every transition
    #: this runtime writes publishes the current schema.
    schema_version: str = TARGET_SIZE_CAMPAIGN_STATE_SCHEMA

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
        if self.schema_version not in _READABLE_STATE_SCHEMAS:
            raise TrainingDataSerializationError(
                "Unsupported target-size campaign-state schema."
            )
        if self.auto_diagnostic is not None and not isinstance(
            self.auto_diagnostic, TargetSizeAutoDiagnostic
        ):
            raise TrainingDataInputError(
                "The automatic target-size diagnostic must be a TargetSizeAutoDiagnostic."
            )
        object.__setattr__(
            self,
            "provisional_entries",
            _validated_entry_collection(
                self.provisional_entries,
                label="provisional target-size",
                element=TargetSizeProposal,
            ),
        )
        if self.frozen_entries is not None:
            frozen_entries = _validated_entry_collection(
                self.frozen_entries,
                label="frozen target-size",
                element=FrozenTargetSelection,
            )
            if not frozen_entries:
                raise TrainingDataInputError(
                    "A frozen target-size design contains at least one selected size."
                )
            object.__setattr__(self, "frozen_entries", frozen_entries)
        object.__setattr__(self, "legacy_scalar_binding", bool(self.legacy_scalar_binding))
        if self.legacy_scalar_binding and (
            self.frozen_entries is None or len(self.frozen_entries) != 1
        ):
            raise TrainingDataInputError(
                "The predecessor scalar binding compatibility marker belongs only to "
                "a one-entry frozen design."
            )
        for name in ("disposition", "disposition_detail"):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, str(value))
        self._validate_consistency()

    def _validate_consistency(self) -> None:
        if self.regime is not TargetSizeRegime.CURRENT and self.lifecycle in (
            TargetSizeLifecycle.SCREEN_ACTIVE,
            TargetSizeLifecycle.DIAGNOSTIC_COMPLETE,
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
            or self.auto_diagnostic is not None
            or self.provisional_entries
            or self.frozen_entries is not None
        ):
            raise TrainingDataInputError(
                "An unconverted campaign cannot bind current target-size authority."
            )
        if self.lifecycle in _SUBSTRATE_BOUND_LIFECYCLES:
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
        if self.lifecycle in (
            TargetSizeLifecycle.SCREEN_ACTIVE,
            TargetSizeLifecycle.DIAGNOSTIC_COMPLETE,
        ):
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
        if self.auto_diagnostic is None:
            if self.lifecycle is TargetSizeLifecycle.DIAGNOSTIC_COMPLETE:
                raise TrainingDataInputError(
                    "A complete automatic target-size diagnostic requires its "
                    "authenticated diagnostic projection."
                )
        else:
            if self.lifecycle is not TargetSizeLifecycle.DIAGNOSTIC_COMPLETE:
                raise TrainingDataInputError(
                    "An automatic diagnostic projection cannot be attached to a "
                    "generation whose diagnostic has not completed."
                )
            if self.auto_diagnostic.experiment_definition_digest != (
                self.experiment_definition_digest
            ):
                raise TrainingDataInputError(
                    "The automatic diagnostic binds a different P2 experiment definition."
                )
            if self.auto_diagnostic.execution_head_digest != (
                self.adopted_execution_head_digest
            ):
                raise TrainingDataInputError(
                    "The automatic diagnostic binds a different adopted P3 execution head."
                )
            if (
                self.auto_diagnostic.reducer_state_digest
                != self.adopted_reducer_state_digest
            ):
                raise TrainingDataInputError(
                    "The automatic diagnostic binds a different adopted reducer state."
                )
        # A proposal and a frozen selection are independent of the diagnostic
        # axis, but both need the prepared scientific substrate that names
        # pi_train, and both are current-runtime facts.
        for present, label in (
            (bool(self.provisional_entries), "provisional design"),
            (self.frozen_entries is not None, "frozen design"),
        ):
            if not present:
                continue
            if (
                self.regime is not TargetSizeRegime.CURRENT
                or self.lifecycle not in _SUBSTRATE_BOUND_LIFECYCLES
            ):
                raise TrainingDataInputError(
                    f"A target-size {label} requires a bound current target-size substrate."
                )
        if self.provisional_entries and self.frozen_entries is not None:
            raise TrainingDataInputError(
                "A frozen target-size design replaces the provisional one; the two "
                "are never current at the same time."
            )
        if self.schema_version == TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA and (
            self.provisional_entries or self.frozen_entries is not None
        ):
            raise TrainingDataInputError(
                "The pre-rework campaign-state schema cannot carry a provisional "
                "proposal or a frozen selection."
            )
        if self.schema_version == TARGET_SIZE_CAMPAIGN_STATE_V2_SCHEMA and (
            len(self.provisional_entries) > 1
            or (self.frozen_entries is not None and len(self.frozen_entries) > 1)
        ):
            raise TrainingDataInputError(
                "The scalar-selection predecessor campaign-state schema carries at "
                "most one provisional and one frozen target size; a multi-size "
                "design is published under the current schema instead."
            )

    @property
    def is_legacy_schema(self) -> bool:
        """Whether this row was written under a retired schema.

        A retired row is read and authenticated under its own native bytes and
        is never rewritten in place.  The current runtime only ever *writes*
        :data:`TARGET_SIZE_CAMPAIGN_STATE_SCHEMA`.
        """

        return self.schema_version != TARGET_SIZE_CAMPAIGN_STATE_SCHEMA

    @property
    def is_prerework_schema(self) -> bool:
        """Whether this row predates the provisional/frozen selection axis."""

        return self.schema_version == TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA

    def _lifecycle_wire_value(self) -> str:
        """Serialize the lifecycle in this row's own schema.

        A pre-rework row spelled diagnostic completion as one of two terminal
        values, and its revision digest covers those exact bytes.  Reproducing
        them is what lets an existing campaign keep authenticating its own
        history while the current runtime writes the honest single value.
        """

        if not self.is_prerework_schema:
            return self.lifecycle.value
        if self.lifecycle is not TargetSizeLifecycle.DIAGNOSTIC_COMPLETE:
            return self.lifecycle.value
        return (
            _LEGACY_TERMINAL_SELECTED
            if self.auto_diagnostic is not None
            and self.auto_diagnostic.has_recommendation
            else _LEGACY_TERMINAL_SCIENTIFIC_FAILURE
        )

    def _base_payload(self) -> dict[str, Any]:
        return {
            "schema": self.schema_version,
            "regime": self.regime.value,
            "generation": self.generation,
            "attempt": self.attempt,
            "lifecycle": self._lifecycle_wire_value(),
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
            "terminal": (
                None if self.auto_diagnostic is None else self.auto_diagnostic.to_dict()
            ),
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
        if self.schema_version == TARGET_SIZE_CAMPAIGN_STATE_V2_SCHEMA:
            # A predecessor row is reproduced in its own bytes so its committed
            # revision digest still authenticates.  It held at most one entry
            # of each kind, which is exactly what the collection normalizes to.
            payload["proposal"] = (
                self.provisional_entries[0].to_dict()
                if self.provisional_entries
                else None
            )
            payload["frozen"] = (
                self.frozen_entries[0].to_dict()
                if self.frozen_entries is not None
                else None
            )
        elif not self.is_prerework_schema:
            payload["provisional_entries"] = [
                entry.to_dict() for entry in self.provisional_entries
            ]
            payload["frozen_entries"] = (
                None
                if self.frozen_entries is None
                else [entry.to_dict() for entry in self.frozen_entries]
            )
            if self.legacy_scalar_binding:
                # Present only for a design inherited from the scalar
                # predecessor, so an ordinary current row's identity is exactly
                # what it would have been without this compatibility axis.
                payload["legacy_scalar_binding"] = True
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> TargetSizeCampaignState:
        schema = payload.get("schema")
        if schema not in _READABLE_STATE_SCHEMAS:
            raise TrainingDataSerializationError(
                "Unsupported target-size campaign-state schema."
            )
        terminal_payload = payload.get("terminal")
        lifecycle_value = str(payload["lifecycle"])
        if lifecycle_value in (
            _LEGACY_TERMINAL_SELECTED,
            _LEGACY_TERMINAL_SCIENTIFIC_FAILURE,
        ):
            # Pre-rework terminality was an *automatic screen* outcome all
            # along.  It is read as exactly that, and it brings no proposal and
            # no frozen selection with it.
            lifecycle_value = TargetSizeLifecycle.DIAGNOSTIC_COMPLETE.value
        provisional_entries, frozen_entries, legacy_scalar_binding = (
            _selection_collections_from_payload(payload, schema=str(schema))
        )
        result = cls(
            regime=TargetSizeRegime(payload["regime"]),
            generation=int(payload["generation"]),
            lifecycle=TargetSizeLifecycle(lifecycle_value),
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
            auto_diagnostic=(
                None
                if terminal_payload is None
                else TargetSizeAutoDiagnostic.from_dict(terminal_payload)
            ),
            provisional_entries=provisional_entries,
            frozen_entries=frozen_entries,
            legacy_scalar_binding=legacy_scalar_binding,
            disposition=_text_or_none(payload.get("disposition")),
            disposition_detail=_text_or_none(payload.get("disposition_detail")),
            schema_version=str(schema),
        )
        expected = payload.get("content_digest")
        if expected is not None and str(expected) != result.content_digest:
            raise TrainingDataSerializationError(
                "Target-size campaign state digest does not authenticate its payload."
            )
        return result


def _text_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _selection_collections_from_payload(
    payload: Mapping[str, Any], *, schema: str
) -> tuple[
    tuple[TargetSizeProposal, ...], tuple[FrozenTargetSelection, ...] | None, bool
]:
    """Read the selection axis of any readable campaign-state schema.

    The predecessor's scalar keys project onto the collection - ``None`` means
    the empty design and a value means a one-entry design - without rewriting
    one byte of the persisted row.  A predecessor row that is already *frozen*
    additionally marks its descendant binding as the predecessor's, so accepted
    P5/P7 evidence under that exact legacy ancestry stays current.
    """

    if schema == TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA:
        return (), None, False
    if schema == TARGET_SIZE_CAMPAIGN_STATE_V2_SCHEMA:
        proposal_payload = payload.get("proposal")
        frozen_payload = payload.get("frozen")
        provisional = (
            ()
            if proposal_payload is None
            else (TargetSizeProposal.from_dict(proposal_payload),)
        )
        frozen = (
            None
            if frozen_payload is None
            else (FrozenTargetSelection.from_dict(frozen_payload),)
        )
        return provisional, frozen, frozen is not None
    provisional_payload = payload.get("provisional_entries") or ()
    frozen_payload = payload.get("frozen_entries")
    if not isinstance(provisional_payload, Sequence) or isinstance(
        provisional_payload, (str, bytes)
    ):
        raise TrainingDataSerializationError(
            "The provisional target-size design must be a sequence of entries."
        )
    if frozen_payload is not None and (
        not isinstance(frozen_payload, Sequence)
        or isinstance(frozen_payload, (str, bytes))
    ):
        raise TrainingDataSerializationError(
            "The frozen target-size design must be a sequence of entries."
        )
    provisional = tuple(
        TargetSizeProposal.from_dict(item) for item in provisional_payload
    )
    frozen = (
        None
        if frozen_payload is None
        else tuple(FrozenTargetSelection.from_dict(item) for item in frozen_payload)
    )
    return provisional, frozen, bool(payload.get("legacy_scalar_binding", False))


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
            schema_version=self.state.schema_version,
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
    # The expectation names the schema of the predecessor it read, not the
    # schema this runtime writes: an existing campaign is superseded *from* its
    # pre-rework head by a current-schema successor, which is the whole cutover.
    if expected.schema_version != head.state.schema_version:
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

    if successor.is_legacy_schema:
        raise TrainingDataInputError(
            "A target-size campaign transition must publish the current campaign-state "
            "schema; retired schemas are read for history, never written."
        )
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
    if kind is TargetSizeTransitionKind.FREEZE_SELECTION and not successor.frozen_entries:
        raise TrainingDataInputError(
            "A freeze transition must publish the frozen target-size design it admits."
        )
    if kind is TargetSizeTransitionKind.SET_PROPOSAL:
        if not successor.provisional_entries:
            raise TrainingDataInputError(
                "A proposal transition must publish the provisional design it sets."
            )
        if successor.frozen_entries is not None:
            raise TrainingDataInputError(
                "A frozen target-size design is never revised by a proposal transition."
            )
    if kind is TargetSizeTransitionKind.RESET_PROPOSAL:
        if successor.provisional_entries:
            raise TrainingDataInputError(
                "A reset transition clears every provisional entry."
            )
        if successor.frozen_entries is not None:
            raise TrainingDataInputError(
                "A frozen target-size design is never reset; it is retired only by a "
                "fresh prepared generation."
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
    "SELECTION_SOURCE_AUTO_RECOMMENDATION",
    "SELECTION_SOURCE_MANUAL",
    "TARGET_SIZE_AUTO_DIAGNOSTIC_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_REVISION_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_STATE_LEGACY_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_STATE_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_STATE_V2_SCHEMA",
    "TARGET_SIZE_CAMPAIGN_TRANSITION_IDENTITY_SCHEMA",
    "TARGET_SIZE_FROZEN_SELECTION_SCHEMA",
    "TARGET_SIZE_PROPOSAL_SCHEMA",
    "FrozenTargetSelection",
    "TargetSizeAutoDiagnostic",
    "TargetSizeCampaignConflictError",
    "TargetSizeCampaignCorruptionError",
    "TargetSizeCampaignRevision",
    "TargetSizeCampaignState",
    "TargetSizeCampaignStateError",
    "TargetSizeCasExpectation",
    "TargetSizeLifecycle",
    "TargetSizeRegime",
    "TargetSizeProposal",
    "TargetSizeTransitionKind",
    "TargetSizeTransitionResult",
    "commit_target_size_campaign_transition",
    "ensure_target_size_campaign_revision",
    "initial_target_size_campaign_state",
    "load_target_size_campaign_history",
    "load_target_size_campaign_revision",
    "merge_provisional_entry",
    "target_size_transition_identity",
]
