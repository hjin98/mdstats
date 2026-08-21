"""Authenticated compact MVSEL2 rank history for fast MVSTATE2 resume.

MVSTATE2 remains the scientific continuation-state authority.  This companion
journal stores only already-authorized plan history that cannot be recovered
from the final compact state without rescoring the selected prefix: selection
entries, completed rung records, and the Phase-A boundary.  It contains no
candidate marginals, lazy frontier, or mutable scientific state.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ._common import TrainingDataInputError, digest
from .target_multi_view_selector import (
    TargetMultiViewSelectionEntry,
    TargetMultiViewSelectionRung,
)


MVSTATE2_HISTORY_SCHEMA = "mdstats.target-data2c-mvstate2.rank-history.v1"
MVSTATE2_HISTORY_RECORD_SCHEMA = "mdstats.target-data2c-mvstate2.rank-history-record.v1"


@dataclass(frozen=True, slots=True)
class TargetMultiViewSelectionHistoryV2:
    """Immutable selected-prefix plan history paired with one MVSTATE2 rung."""

    entries: tuple[TargetMultiViewSelectionEntry, ...]
    rungs: tuple[TargetMultiViewSelectionRung, ...]
    phase_a_completed_at: int | None

    def __post_init__(self) -> None:
        entries = tuple(self.entries)
        rungs = tuple(self.rungs)
        if any(int(entry.rank) != index for index, entry in enumerate(entries)):
            raise TrainingDataInputError("MVSTATE2 rank history is not contiguous.")
        sizes = tuple(int(rung.target_size) for rung in rungs)
        if sizes != tuple(sorted(set(sizes))):
            raise TrainingDataInputError("MVSTATE2 rank-history rungs are not strictly ordered.")
        if any(not rung.materializable for rung in rungs):
            raise TrainingDataInputError("MVSTATE2 rank history may contain only materialized rungs.")
        if any(size < 1 or size > len(entries) for size in sizes):
            raise TrainingDataInputError("MVSTATE2 rank-history rung size is invalid.")
        uids = tuple(entry.frame_uid for entry in entries)
        for rung in rungs:
            size = int(rung.target_size)
            if tuple(rung.frame_uids) != uids[:size]:
                raise TrainingDataInputError("MVSTATE2 rank-history rung prefix disagrees with entries.")
        if rungs and int(rungs[-1].target_size) != len(entries):
            raise TrainingDataInputError("MVSTATE2 rank history must terminate at its checkpoint rung.")
        if self.phase_a_completed_at is not None:
            boundary = int(self.phase_a_completed_at)
            if boundary < 1 or boundary > len(entries):
                raise TrainingDataInputError("MVSTATE2 Phase-A boundary is outside rank history.")
        object.__setattr__(self, "entries", entries)
        object.__setattr__(self, "rungs", rungs)

    @property
    def selected_count(self) -> int:
        return len(self.entries)

    @property
    def content_digest(self) -> str:
        return digest(self.to_dict(include_digest=False))

    def to_dict(self, *, include_digest: bool = True) -> dict[str, Any]:
        payload = {
            "schema": MVSTATE2_HISTORY_SCHEMA,
            "entries": [entry.to_dict() for entry in self.entries],
            "rungs": [rung.to_dict() for rung in self.rungs],
            "phase_a_completed_at": self.phase_a_completed_at,
        }
        return {**payload, "content_digest": digest(payload)} if include_digest else payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewSelectionHistoryV2":
        if payload.get("schema") != MVSTATE2_HISTORY_SCHEMA:
            raise TrainingDataInputError("Unsupported MVSTATE2 rank-history schema.")
        result = cls(
            entries=tuple(
                TargetMultiViewSelectionEntry.from_dict(dict(item))
                for item in payload.get("entries", ())
            ),
            rungs=tuple(
                TargetMultiViewSelectionRung.from_dict(dict(item))
                for item in payload.get("rungs", ())
            ),
            phase_a_completed_at=(
                None
                if payload.get("phase_a_completed_at") is None
                else int(payload["phase_a_completed_at"])
            ),
        )
        if payload.get("content_digest") != result.content_digest:
            raise TrainingDataInputError("MVSTATE2 rank-history digest mismatch.")
        return result


def encode_target_multi_view_selection_history_v2(
    history: TargetMultiViewSelectionHistoryV2,
    *,
    identity_digest: str,
    selected_order_digest: str,
) -> dict[str, Any]:
    """Bind one history journal to one authenticated MVSTATE2 selected prefix."""

    payload = {
        "schema": MVSTATE2_HISTORY_RECORD_SCHEMA,
        "identity_digest": str(identity_digest),
        "selected_order_digest": str(selected_order_digest),
        "selected_count": int(history.selected_count),
        "history": history.to_dict(),
    }
    return {**payload, "record_digest": digest(payload)}


def decode_target_multi_view_selection_history_v2(
    payload: Mapping[str, Any],
    *,
    expected_identity_digest: str,
    expected_selected_order_digest: str,
    expected_selected_count: int,
) -> TargetMultiViewSelectionHistoryV2:
    """Authenticate a stored journal before allowing replay-free resume."""

    if payload.get("schema") != MVSTATE2_HISTORY_RECORD_SCHEMA:
        raise TrainingDataInputError("Unsupported MVSTATE2 rank-history record schema.")
    record = {key: value for key, value in payload.items() if key != "record_digest"}
    if payload.get("record_digest") != digest(record):
        raise TrainingDataInputError("MVSTATE2 rank-history record digest mismatch.")
    if str(payload.get("identity_digest", "")) != str(expected_identity_digest):
        raise TrainingDataInputError("MVSTATE2 rank history scientific identity mismatch.")
    if str(payload.get("selected_order_digest", "")) != str(expected_selected_order_digest):
        raise TrainingDataInputError("MVSTATE2 rank history selected-prefix identity mismatch.")
    if int(payload.get("selected_count", -1)) != int(expected_selected_count):
        raise TrainingDataInputError("MVSTATE2 rank history selected-count mismatch.")
    history_payload = payload.get("history")
    if not isinstance(history_payload, Mapping):
        raise TrainingDataInputError("MVSTATE2 rank-history payload is invalid.")
    history = TargetMultiViewSelectionHistoryV2.from_dict(history_payload)
    if history.selected_count != int(expected_selected_count):
        raise TrainingDataInputError("MVSTATE2 rank-history cardinality mismatch.")
    return history
