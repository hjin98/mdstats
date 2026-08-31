"""One canonical P7 persistence boundary, readable by a future storage owner.

Everything durable that qualification produces lives under a single
generation-scoped root, and every lifecycle fact a storage subsystem could want
is answerable through this owner rather than by reading filenames:

``objects/``     immutable, content-addressed, create-once release evidence.
``attempts/``    attempt-local state and bulk scratch, keyed by an immutable
                 attempt identity rather than by a mutable directory name.

Currentness is never persisted here as a second truth: it is re-established
through the P4/P5 owners and published as a fenced pointer in the campaign
store, exactly as the accepted P5 descendants do.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
import json
import os
import tempfile
import time

from .._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ..campaign_post_selection import (
    PostSelectionBinding,
    PostSelectionStaleBindingError,
)
from ..post_selection_store import PostSelectionPublicationConflictError
from .errors import QualificationError, QualificationLineageError

QUALIFICATION_ROOT_NAME = "qualification"
QUALIFICATION_ATTEMPT_STATE_SCHEMA = "mdstats.qualification-attempt-state.v1"

#: Pointer kinds published inside one selected binding's P7 namespace.
POINTER_QUALIFICATION_PLAN = "qualification_plan"
POINTER_QUALIFICATION_RECORD = "qualification_record"
POINTER_LOCKED_ACTIVATION = "locked_activation"
POINTER_RELEASE_EVIDENCE = "release_evidence"
POINTER_KINDS = (
    POINTER_QUALIFICATION_PLAN,
    POINTER_QUALIFICATION_RECORD,
    POINTER_LOCKED_ACTIVATION,
    POINTER_RELEASE_EVIDENCE,
)

ATTEMPT_ACTIVE = "active"
ATTEMPT_TERMINAL = "terminal"
ATTEMPT_ABORTED = "aborted"
_ATTEMPT_STATES = (ATTEMPT_ACTIVE, ATTEMPT_TERMINAL, ATTEMPT_ABORTED)


def qualification_root(workspace_or_paths: Any, generation: int | str) -> Path:
    """Campaign-owned root for one target-size generation's P7 evidence."""

    internal = (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )
    return internal.resolve() / QUALIFICATION_ROOT_NAME / f"g{int(generation)}"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            json.dump(payload, stream, sort_keys=True, separators=(",", ":"))
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


@dataclass(frozen=True, slots=True)
class QualificationEvidenceStore:
    """Create-once/validate-existing object store for P7 release evidence."""

    root: Path

    def object_path(self, content_digest: str) -> Path:
        value = validate_digest(str(content_digest), name="content_digest")
        return self.root / "objects" / value[:2] / f"{value}.json"

    def has(self, content_digest: str) -> bool:
        return self.object_path(content_digest).is_file()

    def put(self, record: Any) -> str:
        payload = record.to_dict()
        content_digest = str(record.content_digest)
        if payload.get("content_digest") not in (None, content_digest):
            raise PostSelectionPublicationConflictError(
                "Record payload digest disagrees with its content digest."
            )
        path = self.object_path(content_digest)
        if path.is_file():
            existing = json.loads(path.read_text(encoding="utf-8"))
            if existing != payload:
                raise PostSelectionPublicationConflictError(
                    f"Immutable qualification object {content_digest[:12]}... already "
                    "exists with different content; release evidence is never "
                    "rewritten in place."
                )
            return content_digest
        _atomic_write_json(path, payload)
        return content_digest

    def get(self, content_digest: str, deserializer: Callable[[Mapping[str, Any]], Any]) -> Any:
        path = self.object_path(content_digest)
        if not path.is_file():
            raise QualificationLineageError(
                f"Qualification object {str(content_digest)[:12]}... is missing from "
                "the campaign-owned release-evidence store."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = deserializer(payload)
        if str(record.content_digest) != str(content_digest):
            raise TrainingDataSerializationError(
                "Stored qualification object does not reproduce its content digest."
            )
        return record

    def find(
        self, content_digest: str, deserializer: Callable[[Mapping[str, Any]], Any]
    ) -> Any | None:
        return (
            self.get(content_digest, deserializer)
            if self.has(content_digest)
            else None
        )


def open_qualification_store(paths: Any, binding: PostSelectionBinding) -> QualificationEvidenceStore:
    root = qualification_root(paths, binding.campaign_generation)
    root.mkdir(parents=True, exist_ok=True)
    return QualificationEvidenceStore(root=root)


def attempt_root(paths: Any, binding: PostSelectionBinding, attempt_identity: str) -> Path:
    """Attempt-local root derived from the immutable attempt identity."""

    identity = validate_digest(str(attempt_identity), name="attempt_identity")
    root = qualification_root(paths, binding.campaign_generation) / "attempts" / identity
    root.mkdir(parents=True, exist_ok=True)
    return root


def _pointer_key(binding: PostSelectionBinding, kind: str) -> str:
    if kind not in POINTER_KINDS:
        raise TrainingDataInputError(f"Unknown qualification pointer kind {kind!r}.")
    return f"qualification:{binding.content_digest}:{kind}"


def publish_current_qualification_pointer(
    campaign_store: Any,
    *,
    binding: PostSelectionBinding,
    kind: str,
    content_digest: str,
) -> None:
    """Make one qualification record current under the same commit-time fence.

    The P5 fence is reused verbatim in spirit: the generation comparison and
    the pointer write share one serialized transaction, so a long qualification
    run that finishes after a newer ``prepare`` cannot publish stale evidence as
    current.
    """

    from ..campaign_target_size_state import _load_head

    key = _pointer_key(binding, kind)
    value = validate_digest(str(content_digest), name="content_digest")
    with campaign_store.exclusive_transaction() as db:
        revision = _load_head(db)
        if revision is None:
            raise PostSelectionStaleBindingError(
                "The campaign has no target-size state; no qualification result can "
                "be published as current."
            )
        state = revision.state
        if (
            state.generation != binding.campaign_generation
            or revision.state_revision != binding.campaign_state_revision
        ):
            raise PostSelectionStaleBindingError(
                "A newer target-size campaign revision became current while this "
                "qualification work was running. The stale qualification stays "
                "available as historical evidence but is never published as current."
            )
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if row is not None and str(row[0]) == value:
            return
        db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, value))


def read_current_qualification_pointer(
    campaign_store: Any, *, binding: PostSelectionBinding, kind: str
) -> str | None:
    key = _pointer_key(binding, kind)
    with campaign_store._connect() as db:  # noqa: SLF001 - store owns its pool
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def resolve_current_qualification_record(
    campaign_store: Any,
    paths: Any,
    context: Any,
    *,
    kind: str,
    deserializer: Callable[[Mapping[str, Any]], Any],
) -> Any | None:
    """Resolve a current P7 descendant through freshly established authority."""

    binding = context.binding if hasattr(context, "binding") else context
    pointer = read_current_qualification_pointer(campaign_store, binding=binding, kind=kind)
    if pointer is None:
        return None
    store = open_qualification_store(paths, binding)
    record = store.get(pointer, deserializer)
    bound = getattr(record, "selected_binding_digest", None)
    if bound is not None and str(bound) != binding.content_digest:
        raise PostSelectionStaleBindingError(
            "A published qualification record binds a different selected generation "
            "than the current authenticated selection."
        )
    return record


# ---------------------------------------------------------------------------
# Attempt state and the minimal active-artifact retention reference
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class QualificationAttemptState:
    """Owner-readable attempt state, including the active artifact reference.

    This is coordination metadata, not a storage policy: it says only "this
    exact, already authoritative artifact is actively referenced by this
    qualification attempt".  It grants no scientific currentness, owns no cache,
    and cannot make a stale publication current.
    """

    attempt_identity: str
    binding_digest: str
    publication_digest: str
    state: str
    referenced_paths: tuple[str, ...]
    opened_at: str
    updated_at: str
    detail: str = ""

    def __post_init__(self) -> None:
        for name in ("attempt_identity", "binding_digest", "publication_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        state = str(self.state)
        if state not in _ATTEMPT_STATES:
            raise TrainingDataInputError(f"Unknown qualification attempt state {state!r}.")
        object.__setattr__(self, "state", state)
        paths = tuple(sorted({str(v) for v in self.referenced_paths}))
        for value in paths:
            if not Path(value).is_absolute():
                raise TrainingDataInputError(
                    "A qualification retention reference must name an absolute path."
                )
        object.__setattr__(self, "referenced_paths", paths)
        object.__setattr__(self, "detail", str(self.detail))

    @property
    def is_active(self) -> bool:
        return self.state == ATTEMPT_ACTIVE

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": QUALIFICATION_ATTEMPT_STATE_SCHEMA,
            "attempt_identity": self.attempt_identity,
            "binding_digest": self.binding_digest,
            "publication_digest": self.publication_digest,
            "state": self.state,
            "referenced_paths": list(self.referenced_paths),
            "opened_at": self.opened_at,
            "updated_at": self.updated_at,
            "detail": self.detail,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "QualificationAttemptState":
        if payload.get("schema") != QUALIFICATION_ATTEMPT_STATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported qualification attempt-state schema.")
        result = cls(
            attempt_identity=str(payload["attempt_identity"]),
            binding_digest=str(payload["binding_digest"]),
            publication_digest=str(payload["publication_digest"]),
            state=str(payload["state"]),
            referenced_paths=tuple(payload.get("referenced_paths", ())),
            opened_at=str(payload["opened_at"]),
            updated_at=str(payload["updated_at"]),
            detail=str(payload.get("detail", "")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("Qualification attempt-state digest mismatch.")
        return result


ATTEMPT_STATE_FILENAME = "attempt-state.json"


def attempt_state_path(paths: Any, binding: PostSelectionBinding, attempt_identity: str) -> Path:
    return attempt_root(paths, binding, attempt_identity) / ATTEMPT_STATE_FILENAME


def read_attempt_state(
    paths: Any, binding: PostSelectionBinding, attempt_identity: str
) -> QualificationAttemptState | None:
    path = attempt_state_path(paths, binding, attempt_identity)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise QualificationLineageError(
            f"Qualification attempt state at {path!s} is corrupt; a qualification "
            "attempt never resumes from unreadable state."
        ) from exc
    state = QualificationAttemptState.from_dict(payload)
    if state.attempt_identity != validate_digest(str(attempt_identity), name="attempt_identity"):
        raise QualificationLineageError(
            "Stored qualification attempt state belongs to a different attempt identity."
        )
    return state


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def acquire_attempt_reference(
    paths: Any,
    binding: PostSelectionBinding,
    *,
    attempt_identity: str,
    publication_digest: str,
    binding_digest: str,
    referenced_paths: Iterable[str | os.PathLike[str]],
    detail: str = "",
) -> QualificationAttemptState:
    """Open or reopen an attempt and pin its exact required artifacts.

    Reopening is idempotent and reconstructs the reference from the durable
    attempt state, so a process death does not silently unpin artifacts an
    interrupted qualification still needs.
    """

    resolved = tuple(str(Path(value).resolve()) for value in referenced_paths)
    existing = read_attempt_state(paths, binding, attempt_identity)
    opened_at = existing.opened_at if existing is not None else _utc_now()
    if existing is not None and existing.publication_digest != validate_digest(
        str(publication_digest), name="publication_digest"
    ):
        raise QualificationLineageError(
            "An existing qualification attempt with this identity references a "
            "different publication; the attempt identity is not authentic."
        )
    merged = tuple(sorted(set(resolved) | set(existing.referenced_paths if existing else ())))
    state = QualificationAttemptState(
        attempt_identity=attempt_identity,
        binding_digest=binding_digest,
        publication_digest=publication_digest,
        state=ATTEMPT_ACTIVE,
        referenced_paths=merged,
        opened_at=opened_at,
        updated_at=_utc_now(),
        detail=detail,
    )
    _atomic_write_json(attempt_state_path(paths, binding, attempt_identity), state.to_dict())
    return state


def release_attempt_reference(
    paths: Any,
    binding: PostSelectionBinding,
    *,
    attempt_identity: str,
    terminal: bool = True,
    detail: str = "",
) -> QualificationAttemptState | None:
    """Release the retention reference on terminal completion or explicit abort."""

    existing = read_attempt_state(paths, binding, attempt_identity)
    if existing is None:
        return None
    state = QualificationAttemptState(
        attempt_identity=existing.attempt_identity,
        binding_digest=existing.binding_digest,
        publication_digest=existing.publication_digest,
        state=ATTEMPT_TERMINAL if terminal else ATTEMPT_ABORTED,
        referenced_paths=(),
        opened_at=existing.opened_at,
        updated_at=_utc_now(),
        detail=detail or existing.detail,
    )
    _atomic_write_json(attempt_state_path(paths, binding, attempt_identity), state.to_dict())
    return state


def iter_attempt_states(workspace_or_paths: Any) -> tuple[QualificationAttemptState, ...]:
    """Every attempt state under every qualification generation root."""

    internal = (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )
    root = internal.resolve() / QUALIFICATION_ROOT_NAME
    if not root.is_dir():
        return ()
    states: list[QualificationAttemptState] = []
    for path in sorted(root.glob(f"g*/attempts/*/{ATTEMPT_STATE_FILENAME}")):
        try:
            states.append(QualificationAttemptState.from_dict(json.loads(path.read_text(encoding="utf-8"))))
        except (OSError, ValueError, TrainingDataSerializationError, TrainingDataInputError):
            # An unreadable attempt record is exactly when guessing is unsafe.
            # The fence below treats the whole qualification root as protected,
            # so an unclassifiable attempt cannot be reclaimed by accident.
            continue
    return tuple(states)


@dataclass
class QualificationRetentionFence:
    """Deletion-authority reduction for durable P7 evidence and active attempts.

    Two different things are protected for two different reasons.  Durable
    qualification evidence is *release* evidence and is never reconstructible
    scratch, so the object store is protected outright.  Artifacts an active
    attempt still references are protected because reclaiming them mid-run would
    invalidate an expensive qualification that is still legitimately in flight.
    Terminal and aborted attempts protect nothing beyond the evidence itself.
    """

    qualification_roots: tuple[Path, ...]
    referenced_paths: frozenset[str]

    @property
    def is_active(self) -> bool:
        return bool(self.qualification_roots or self.referenced_paths)

    def protects(self, path: str | os.PathLike[str]) -> tuple[bool, str]:
        candidate = Path(os.path.abspath(os.fspath(path)))
        for value in self.referenced_paths:
            referenced = Path(value)
            if candidate == referenced or _is_within(referenced, candidate) or _is_within(
                candidate, referenced
            ):
                return True, (
                    "artifact is actively referenced by an in-flight P7 qualification attempt"
                )
        for root in self.qualification_roots:
            if candidate != root and _is_within(candidate, root):
                # Deleting an ancestor of the evidence root would remove it.
                return True, (
                    "path contains the campaign-owned P7 qualification evidence root"
                )
            if _is_within(root, candidate):
                relative = candidate.relative_to(root)
                if not relative.parts or relative.parts[0] != "attempts":
                    return True, (
                        "durable P7 qualification/release evidence is never "
                        "reconstructible scratch"
                    )
                # Attempt-local scratch of a released attempt is disposable.
                return False, ""
        return False, ""


def _is_within(root: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False


def build_qualification_retention_fence(workspace_or_paths: Any) -> QualificationRetentionFence:
    """Reconstruct the fence from durable owner state, never from filenames."""

    internal = (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )
    root = internal.resolve() / QUALIFICATION_ROOT_NAME
    roots = tuple(sorted(path for path in root.glob("g*") if path.is_dir())) if root.is_dir() else ()
    referenced: set[str] = set()
    for state in iter_attempt_states(workspace_or_paths):
        if state.is_active:
            referenced.update(state.referenced_paths)
    return QualificationRetentionFence(
        qualification_roots=roots, referenced_paths=frozenset(referenced)
    )


__all__ = [
    "ATTEMPT_ABORTED",
    "ATTEMPT_ACTIVE",
    "ATTEMPT_STATE_FILENAME",
    "ATTEMPT_TERMINAL",
    "POINTER_KINDS",
    "POINTER_LOCKED_ACTIVATION",
    "POINTER_QUALIFICATION_PLAN",
    "POINTER_QUALIFICATION_RECORD",
    "POINTER_RELEASE_EVIDENCE",
    "QUALIFICATION_ATTEMPT_STATE_SCHEMA",
    "QUALIFICATION_ROOT_NAME",
    "QualificationAttemptState",
    "QualificationEvidenceStore",
    "QualificationRetentionFence",
    "acquire_attempt_reference",
    "attempt_root",
    "attempt_state_path",
    "build_qualification_retention_fence",
    "iter_attempt_states",
    "open_qualification_store",
    "publish_current_qualification_pointer",
    "qualification_root",
    "read_attempt_state",
    "read_current_qualification_pointer",
    "release_attempt_reference",
    "resolve_current_qualification_record",
]
