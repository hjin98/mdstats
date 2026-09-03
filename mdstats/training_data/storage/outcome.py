"""What a storage mutation actually did, as a value rather than a boolean.

``bool + reason`` cannot express the state a certified recursive removal can
genuinely reach: some authorized members unlinked, then a later contradiction -
an unrecorded node, a nested mount, a substituted root - stopping the enclosing
action.  Mapping that to ``True`` would claim a completion that did not happen;
mapping it to ``False`` would claim nothing changed when bytes are already gone.
Both lies reach the durable audit.

So every cleanup removal owner returns one of four terminal dispositions, and
the executor settles status and reclaimed bytes from the disposition rather than
from a reason string.  Parsing prose to decide what happened is exactly the
fragility this replaces.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: The requested target was removed by this execution.
OUTCOME_REMOVED = "removed"
#: The desired terminal state already held - an earlier action in this cleanup,
#: or an interrupted prior one, already removed it.  Terminally satisfied, but
#: this execution reclaimed nothing and may not claim the planned bytes.
OUTCOME_ALREADY_ABSENT = "already_absent"
#: The owner withheld the mutation and nothing changed on disk.
OUTCOME_REFUSED_NO_CHANGE = "refused_no_change"
#: Some authorized mutation happened, then the action was stopped.  Neither a
#: clean completion nor a no-op refusal.
OUTCOME_PARTIAL_CHANGE_REFUSED = "partial_change_refused"

TERMINAL_OUTCOMES = frozenset(
    {
        OUTCOME_REMOVED,
        OUTCOME_ALREADY_ABSENT,
        OUTCOME_REFUSED_NO_CHANGE,
        OUTCOME_PARTIAL_CHANGE_REFUSED,
    }
)


@dataclass(frozen=True, slots=True)
class MutationOutcome:
    """One removal owner's terminal disposition and what it can substantiate.

    ``removed_bytes`` is what this execution can actually account for, measured
    before the unlink that removed it.  It is deliberately not the planned
    action size: a partial removal that credited the whole target would inflate
    the reclaim figure an operator uses to decide whether cleanup helped.
    """

    outcome: str
    detail: str = ""
    #: Bytes this execution substantiated as removed, measured before deletion.
    #: ``None`` means "the whole planned target went", so the caller may credit
    #: the planned size; a number is always the exact substantiated amount.
    removed_bytes: int | None = None

    def __post_init__(self) -> None:
        if self.outcome not in TERMINAL_OUTCOMES:
            raise ValueError(f"unknown mutation outcome: {self.outcome!r}")

    @property
    def succeeded(self) -> bool:
        """Whether the action reached its desired terminal state."""

        return self.outcome in (OUTCOME_REMOVED, OUTCOME_ALREADY_ABSENT)

    @property
    def mutated(self) -> bool:
        """Whether anything on disk actually changed."""

        return self.outcome in (OUTCOME_REMOVED, OUTCOME_PARTIAL_CHANGE_REFUSED)

    @property
    def refused(self) -> bool:
        """Whether the owner withheld the action, wholly or part-way through."""

        return self.outcome in (
            OUTCOME_REFUSED_NO_CHANGE,
            OUTCOME_PARTIAL_CHANGE_REFUSED,
        )

    def credited_bytes(self, planned_bytes: int) -> int:
        """The reclaim this execution may honestly claim for one action."""

        if self.outcome == OUTCOME_REMOVED:
            return int(planned_bytes) if self.removed_bytes is None else int(self.removed_bytes)
        if self.outcome == OUTCOME_PARTIAL_CHANGE_REFUSED:
            # Never the planned size: only what was measured before deletion.
            return int(self.removed_bytes or 0)
        # Absence this execution did not create, and refusals, reclaim nothing.
        return 0

    def to_dict(self, planned_bytes: int = 0) -> dict[str, object]:
        """This action's evidence, including the bytes it actually removed.

        ``planned_bytes`` resolves the "the whole target went" sentinel at the
        one place that knows the planned size. An aggregate alone cannot say
        which of several actions mutated, or explain two partial actions, so
        the exact amount is recorded per action rather than only summed.
        """

        return {
            "outcome": self.outcome,
            "removed": self.outcome == OUTCOME_REMOVED,
            "mutated": self.mutated,
            "reclaimed_bytes": self.credited_bytes(planned_bytes),
            "detail": self.detail,
        }


class PartialMutationError(Exception):
    """A failure that happened *after* this action already changed the disk.

    An owner can unlink a certified member and then fail on the fsync that was
    supposed to make the removal durable, or on a later sibling. Letting that
    exception fly straight past the action boundary would leave the executor
    knowing only that "something failed" - not which action mutated, nor how
    many bytes are already gone. The audit would inherit that blindness.

    So the failure carries the truth with it: the structured outcome the action
    had earned at the moment it failed, and the original cause. The engine
    records the action from ``outcome`` before letting the exception continue.
    """

    def __init__(self, outcome: MutationOutcome, cause: BaseException | None = None):
        super().__init__(outcome.detail)
        self.outcome = outcome
        self.cause = cause


@dataclass
class MutationLedger:
    """What one action has actually removed so far.

    A recursive removal makes many destructive transitions. If a later one
    fails, the question the audit needs answered is not "did the top-level path
    disappear" - a subset can be gone while the container survives - but "how
    much did this action already take". Only a running account kept at the
    moment of each successful removal can answer that.

    ``(device, inode)`` is remembered across the whole action so a file reached
    through several hard links is counted once, matching the planner's own tree
    metric.
    """

    removed_bytes: int = 0
    mutated: bool = False
    _seen: set[tuple[int, int]] = field(default_factory=set)

    def credit(self, size: int, identity: tuple[int, int] | None) -> None:
        """Record one removal that has already succeeded."""

        self.mutated = True
        if identity is not None:
            if identity in self._seen:
                return
            self._seen.add(identity)
        self.removed_bytes += int(size)

    def note_mutation(self) -> None:
        """Record a destructive transition that frees no accountable bytes."""

        self.mutated = True

    def stop(self, detail: str) -> MutationOutcome:
        """The outcome this action has earned when it must stop here."""

        if self.mutated:
            return partial_change_refused(detail, removed_bytes=self.removed_bytes)
        return refused_no_change(detail)

    def failure(self, exc: BaseException, detail: str) -> BaseException:
        """The failure to raise, carrying this action's truth when it mutated."""

        if not self.mutated:
            return exc
        return PartialMutationError(
            partial_change_refused(detail, removed_bytes=self.removed_bytes), exc
        )


def removed(detail: str, *, removed_bytes: int | None = None) -> MutationOutcome:
    return MutationOutcome(OUTCOME_REMOVED, detail, removed_bytes)


def already_absent(detail: str) -> MutationOutcome:
    return MutationOutcome(OUTCOME_ALREADY_ABSENT, detail, 0)


def refused_no_change(detail: str) -> MutationOutcome:
    return MutationOutcome(OUTCOME_REFUSED_NO_CHANGE, detail, 0)


def partial_change_refused(detail: str, *, removed_bytes: int) -> MutationOutcome:
    return MutationOutcome(OUTCOME_PARTIAL_CHANGE_REFUSED, detail, int(removed_bytes))


__all__ = [
    "MutationLedger",
    "MutationOutcome",
    "PartialMutationError",
    "OUTCOME_ALREADY_ABSENT",
    "OUTCOME_PARTIAL_CHANGE_REFUSED",
    "OUTCOME_REFUSED_NO_CHANGE",
    "OUTCOME_REMOVED",
    "TERMINAL_OUTCOMES",
    "already_absent",
    "partial_change_refused",
    "refused_no_change",
    "removed",
]
