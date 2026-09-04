"""Persistence, restart, and currentness-fenced publication for P5 descendants.

Post-selection evidence is immutable and content-addressed, and there is no
mutable "current post-selection state" anywhere.  Currentness is resolved, not
stored: a current read re-establishes P4 authority through the selected-training
adapter, derives the expected selected binding, and then looks only inside that
binding's namespace.  Evidence from a retired generation may stay on disk as
historical record; it simply is not reachable as current.

That leaves one race worth closing explicitly.  A writer that validated
generation ``g1``, then spent a long time training, must not publish after a
concurrent ``prepare`` has committed ``g2``.  Publication therefore re-checks the
current campaign revision *inside the same serialized CampaignStore
transaction* that makes the pointer visible - a check performed only before the
write would leave exactly that window open.  The expensive work itself runs
outside any campaign lock, under an immutable attempt identity.
"""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import (
    CurrentSelectedTrainingContext,
    PostSelectionBinding,
    PostSelectionError,
    PostSelectionStaleBindingError,
)

POST_SELECTION_ROOT_NAME = "post-selection"

#: Pointer kinds published inside one selected binding's namespace.
POINTER_CV_PLAN = "cv_plan"
POINTER_CV_ACCEPTANCE = "cv_acceptance"
POINTER_FINAL_PLAN = "final_production_plan"
POINTER_PREDECESSOR_RECLOSURE = "p5_p6_predecessor_reclosure"
POINTER_FINAL_PUBLICATION = "final_production_publication"
POINTER_KINDS = (
    POINTER_CV_PLAN,
    POINTER_CV_ACCEPTANCE,
    POINTER_FINAL_PLAN,
    POINTER_PREDECESSOR_RECLOSURE,
    POINTER_FINAL_PUBLICATION,
)


class PostSelectionPublicationConflictError(PostSelectionError):
    """Two different records claim the same immutable post-selection identity."""


def post_selection_root(workspace_or_paths: Any, generation: int | str) -> Path:
    """Campaign-owned root for one target-size generation's downstream evidence."""

    internal = (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )
    return internal.resolve() / POST_SELECTION_ROOT_NAME / f"g{int(generation)}"


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=path.name, suffix=".tmp", dir=path.parent
    )
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
class PostSelectionEvidenceStore:
    """Content-addressed object store for one generation's P5 descendants.

    Writing is create-once: an object whose digest already exists is verified
    rather than replaced, so a repeated publication of the same logical record
    is idempotent while genuinely conflicting bytes fail closed.
    """

    root: Path

    def object_path(self, content_digest: str) -> Path:
        value = validate_digest(str(content_digest), name="content_digest")
        return self.root / "objects" / value[:2] / f"{value}.json"

    def has(self, content_digest: str) -> bool:
        return self.object_path(content_digest).is_file()

    def put(self, record: Any) -> str:
        """Publish one immutable record and return its content digest."""

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
                    f"Immutable post-selection object {content_digest[:12]}... already "
                    "exists with different content; post-selection evidence is never "
                    "rewritten in place."
                )
            return content_digest
        _atomic_write_json(path, payload)
        return content_digest

    def get(self, content_digest: str, deserializer: Callable[[Mapping[str, Any]], Any]) -> Any:
        path = self.object_path(content_digest)
        if not path.is_file():
            raise PostSelectionError(
                f"Post-selection object {str(content_digest)[:12]}... is missing from "
                "the campaign-owned evidence store."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        record = deserializer(payload)
        if str(record.content_digest) != str(content_digest):
            raise TrainingDataSerializationError(
                "Stored post-selection object does not reproduce its content digest."
            )
        return record


def open_post_selection_store(
    paths: Any, binding: PostSelectionBinding, *, create: bool = True
) -> PostSelectionEvidenceStore:
    """Open the evidence store for one authenticated selected binding.

    ``create=False`` is the observational open.  Consequential execution may
    bring a generation's evidence root into existence; describing a campaign
    must not, because a root created by a read makes "no evidence" and "an
    empty evidence store" indistinguishable afterwards.
    """

    root = post_selection_root(paths, binding.campaign_generation)
    if create:
        root.mkdir(parents=True, exist_ok=True)
    return PostSelectionEvidenceStore(root=root)


#: Name of the owner-local publication barrier guarding the object-then-pointer
#: window for one generation's P5 evidence.
PUBLICATION_BARRIER_NAME = ".publication-barrier"


@contextmanager
def post_selection_publication_barrier(
    paths: Any, generation: int | str
) -> Iterator[None]:
    """Serialize this generation's object-then-pointer publication.

    Publishing an immutable object and publishing the CampaignStore pointer
    that makes it current are deliberately separate transactions, so there is a
    legitimate window in which the object exists and nothing references it.  A
    reclaiming storage operation that only took a snapshot could delete the
    object inside that window and still let the pointer publication succeed.

    Both the publisher and any storage mutation that could touch this
    generation's evidence acquire this barrier, so the window is never observed
    half-open by a mutator.  It is an advisory file lock, so a crashed holder is
    released by the kernel and never deadlocks the campaign.
    """

    from .target_size_execution.persistence import artifact_publication_lock

    root = post_selection_root(paths, generation)
    root.mkdir(parents=True, exist_ok=True)
    with artifact_publication_lock(root / PUBLICATION_BARRIER_NAME):
        yield


def _pointer_key(binding: PostSelectionBinding, kind: str) -> str:
    if kind not in POINTER_KINDS:
        raise TrainingDataInputError(f"Unknown post-selection pointer kind {kind!r}.")
    return f"post_selection:{binding.content_digest}:{kind}"


def _current_campaign_revision(db: Any) -> Any:
    from .campaign_target_size_state import _load_head

    return _load_head(db)


def publish_current_post_selection_pointer(
    campaign_store: Any,
    *,
    binding: PostSelectionBinding,
    kind: str,
    content_digest: str,
) -> None:
    """Make one record current, under a commit-time stale-generation fence.

    The comparison and the write share one ``BEGIN IMMEDIATE`` transaction, so a
    writer holding a legitimate but superseded ``g1`` binding loses the race
    deterministically: it raises and leaves every current-facing row untouched.
    Republishing the same digest under a still-current binding is idempotent.
    """

    key = _pointer_key(binding, kind)
    value = validate_digest(str(content_digest), name="content_digest")
    with campaign_store.exclusive_transaction() as db:
        revision = _current_campaign_revision(db)
        if revision is None:
            raise PostSelectionStaleBindingError(
                "The campaign has no target-size state; no post-selection result can "
                "be published as current."
            )
        state = revision.state
        if (
            state.generation != binding.campaign_generation
            or revision.state_revision != binding.campaign_state_revision
        ):
            raise PostSelectionStaleBindingError(
                "A newer target-size campaign revision became current while this "
                f"post-selection work was running (binding generation "
                f"{binding.campaign_generation} revision "
                f"{binding.campaign_state_revision[:12]}...; current generation "
                f"{state.generation} revision {revision.state_revision[:12]}...). "
                "The stale result stays available as historical evidence but is "
                "never published as current."
            )
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if row is not None and str(row[0]) == value:
            return
        db.execute(
            "INSERT OR REPLACE INTO meta(key,value) VALUES (?,?)", (key, value)
        )


def read_current_post_selection_pointer(
    campaign_store: Any, *, binding: PostSelectionBinding, kind: str
) -> str | None:
    """Return the digest currently published for this binding, if any."""

    key = _pointer_key(binding, kind)
    with campaign_store._connect() as db:  # noqa: SLF001 - store owns its pool
        row = db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return None if row is None else str(row[0])


def resolve_current_post_selection_record(
    campaign_store: Any,
    paths: Any,
    context: CurrentSelectedTrainingContext,
    *,
    kind: str,
    deserializer: Callable[[Mapping[str, Any]], Any],
) -> Any | None:
    """Resolve a current descendant through freshly established P4 authority.

    The caller has already re-authenticated the current selection to obtain
    ``context``.  Pointers live inside that binding's namespace, so a retired
    generation's pointer is not merely rejected here - it is not reachable, and
    the record's own bound lineage is re-checked as well.
    """

    pointer = read_current_post_selection_pointer(
        campaign_store, binding=context.binding, kind=kind
    )
    if pointer is None:
        return None
    store = open_post_selection_store(paths, context.binding)
    record = store.get(pointer, deserializer)
    bound = getattr(record, "binding", None)
    if isinstance(bound, PostSelectionBinding):
        context.require_binding(bound)
    else:
        bound_digest = getattr(record, "selected_binding_digest", None)
        if bound_digest is not None and str(bound_digest) != (
            context.binding.content_digest
        ):
            raise PostSelectionStaleBindingError(
                "A published post-selection record binds a different selected "
                "generation than the current authenticated selection."
            )
    return record


__all__ = [
    "POINTER_CV_ACCEPTANCE",
    "POINTER_CV_PLAN",
    "POINTER_FINAL_PLAN",
    "POINTER_FINAL_PUBLICATION",
    "POINTER_PREDECESSOR_RECLOSURE",
    "POINTER_KINDS",
    "POST_SELECTION_ROOT_NAME",
    "PUBLICATION_BARRIER_NAME",
    "PostSelectionEvidenceStore",
    "PostSelectionPublicationConflictError",
    "post_selection_publication_barrier",
    "open_post_selection_store",
    "post_selection_root",
    "publish_current_post_selection_pointer",
    "read_current_post_selection_pointer",
    "resolve_current_post_selection_record",
]
