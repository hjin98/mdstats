"""Authenticated P5/P6 predecessor reclosure for the final publication.

Revision-11 qualification may consume the final-production publication only
after the repaired predecessor has re-established the publication decision and
the executable source that produced it.  This record is deliberately a small
P5/P6 audit object: it does not select members, duplicate run evidence, or
expose any P7 state.  Its source-tree digest is the authoritative executable
identity; Git values are retained only as useful audit metadata because a
working tree can contain a valid, uncommitted repair.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping
import hashlib
import subprocess

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import PostSelectionError


PREDECESSOR_RECLOSURE_SCHEMA = "mdstats.p5-p6-predecessor-reclosure.v1"


def _package_root() -> Path:
    import mdstats

    return Path(mdstats.__file__).resolve().parent


def predecessor_executable_source_tree_digest(
    root: str | Path | None = None,
) -> str:
    """Digest the current importable P5/P6 source surface.

    Qualification source is intentionally excluded.  A P7 implementation
    repair therefore does not rewrite the predecessor identity, while a change
    to the publication, training, persistence, or execution owners does.
    """

    package = _package_root() if root is None else Path(root).resolve()
    entries: list[tuple[str, str]] = []
    for path in sorted(package.rglob("*.py")):
        relative = path.relative_to(package)
        if "qualification" in relative.parts:
            continue
        if any(part in {"__pycache__", ".git", ".pytest_cache", ".mypy_cache"} for part in relative.parts):
            continue
        entries.append((relative.as_posix(), hashlib.sha256(path.read_bytes()).hexdigest()))
    if not entries:
        raise PostSelectionError(
            "No importable P5/P6 predecessor source was found; reclosure cannot be authenticated."
        )
    return digest({"schema": PREDECESSOR_RECLOSURE_SCHEMA, "source_tree": entries})


def _git_identity(root: Path) -> tuple[str | None, str | None]:
    def _run(*argv: str) -> str | None:
        try:
            result = subprocess.run(
                argv,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30.0,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return None
        if result.returncode != 0:
            return None
        value = result.stdout.strip()
        return value or None

    return _run("git", "rev-parse", "HEAD"), _run("git", "rev-parse", "HEAD^{tree}")


@dataclass(frozen=True, slots=True)
class PredecessorReclosureRecord:
    """One immutable P5/P6 reclosure and rebind identity."""

    selected_binding_digest: str
    final_publication_digest: str
    final_plan_digest: str
    publication_member_digest: str
    decision_policy_identity: str
    executable_source_tree_digest: str
    executable_git_commit: str | None
    executable_git_tree: str | None
    published_at: str

    def __post_init__(self) -> None:
        for name in (
            "selected_binding_digest",
            "final_publication_digest",
            "final_plan_digest",
            "publication_member_digest",
            "executable_source_tree_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        for name in ("decision_policy_identity", "published_at"):
            value = str(getattr(self, name)).strip()
            if not value:
                raise TrainingDataInputError(f"Predecessor reclosure requires {name}.")
            object.__setattr__(self, name, value)
        for name in ("executable_git_commit", "executable_git_tree"):
            value = getattr(self, name)
            object.__setattr__(self, name, None if value is None else str(value).strip() or None)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": PREDECESSOR_RECLOSURE_SCHEMA,
            "selected_binding_digest": self.selected_binding_digest,
            "final_publication_digest": self.final_publication_digest,
            "final_plan_digest": self.final_plan_digest,
            "publication_member_digest": self.publication_member_digest,
            "decision_policy_identity": self.decision_policy_identity,
            "executable_source_tree_digest": self.executable_source_tree_digest,
            "executable_git_commit": self.executable_git_commit,
            "executable_git_tree": self.executable_git_tree,
            "published_at": self.published_at,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PredecessorReclosureRecord":
        if payload.get("schema") != PREDECESSOR_RECLOSURE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported P5/P6 predecessor-reclosure schema."
            )
        result = cls(
            selected_binding_digest=str(payload["selected_binding_digest"]),
            final_publication_digest=str(payload["final_publication_digest"]),
            final_plan_digest=str(payload["final_plan_digest"]),
            publication_member_digest=str(payload["publication_member_digest"]),
            decision_policy_identity=str(payload["decision_policy_identity"]),
            executable_source_tree_digest=str(payload["executable_source_tree_digest"]),
            executable_git_commit=(
                None if payload.get("executable_git_commit") is None else str(payload["executable_git_commit"])
            ),
            executable_git_tree=(
                None if payload.get("executable_git_tree") is None else str(payload["executable_git_tree"])
            ),
            published_at=str(payload["published_at"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("P5/P6 predecessor-reclosure digest mismatch.")
        return result


def build_predecessor_reclosure(context: Any, decision: Any) -> PredecessorReclosureRecord:
    """Build the reclosure from the exact P5 decision and current P5/P6 source."""

    root = _package_root().parent
    commit, tree = _git_identity(root)
    return PredecessorReclosureRecord(
        selected_binding_digest=decision.binding.content_digest,
        final_publication_digest=decision.content_digest,
        final_plan_digest=decision.final_plan_digest,
        publication_member_digest=decision.member_digest,
        decision_policy_identity=decision.decision_policy_identity,
        executable_source_tree_digest=predecessor_executable_source_tree_digest(),
        executable_git_commit=commit,
        executable_git_tree=tree,
        published_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )


def validate_predecessor_reclosure(
    record: PredecessorReclosureRecord,
    context: Any,
    decision: Any,
) -> None:
    """Re-establish the full predecessor reclosure at an exposure boundary."""

    mismatches: dict[str, tuple[Any, Any]] = {
        "selected_binding_digest": (
            record.selected_binding_digest,
            decision.binding.content_digest,
        ),
        "final_publication_digest": (record.final_publication_digest, decision.content_digest),
        "final_plan_digest": (record.final_plan_digest, decision.final_plan_digest),
        "publication_member_digest": (record.publication_member_digest, decision.member_digest),
        "decision_policy_identity": (
            record.decision_policy_identity,
            decision.decision_policy_identity,
        ),
        "executable_source_tree_digest": (
            record.executable_source_tree_digest,
            predecessor_executable_source_tree_digest(),
        ),
    }
    stale = sorted(name for name, (stored, current) in mismatches.items() if stored != current)
    if stale:
        raise PostSelectionError(
            "The P5/P6 predecessor reclosure is stale or no longer binds the current "
            f"publication ({stale}); it remains historical evidence and cannot feed P7."
        )


def resolve_current_predecessor_reclosure(
    context: Any,
    decision: Any | None = None,
) -> PredecessorReclosureRecord:
    """Resolve and authenticate the current reclosure pointer."""

    from .post_selection_store import (
        POINTER_PREDECESSOR_RECLOSURE,
        resolve_current_post_selection_record,
    )

    if decision is None:
        from .post_selection_publication import resolve_current_final_production_publication

        decision = resolve_current_final_production_publication(context)
    if decision is None:
        raise PostSelectionError("No current final-production publication exists for predecessor reclosure.")
    record = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_PREDECESSOR_RECLOSURE,
        deserializer=PredecessorReclosureRecord.from_dict,
    )
    if record is None:
        raise PostSelectionError(
            "The final-production publication predates the required P5/P6 predecessor "
            "reclosure; it is historical and cannot be exposed to P7. Republish it "
            "through the repaired production owner."
        )
    validate_predecessor_reclosure(record, context, decision)
    return record


__all__ = [
    "PREDECESSOR_RECLOSURE_SCHEMA",
    "PredecessorReclosureRecord",
    "build_predecessor_reclosure",
    "predecessor_executable_source_tree_digest",
    "resolve_current_predecessor_reclosure",
    "validate_predecessor_reclosure",
]
