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

from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, Iterable, Iterator, Mapping, Sequence
import json
import errno
import logging
import stat
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

#: Close failures that arrive behind a primary product failure are logged
#: rather than raised, so they stay visible without displacing the failure
#: that carries this action's mutation truth.
_LOGGER = logging.getLogger(__name__)

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
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise TrainingDataSerializationError(
                f"Qualification object {path!s} is not readable JSON."
            ) from exc
        if not isinstance(payload, Mapping):
            raise TrainingDataSerializationError(
                f"Qualification object {path!s} must contain a JSON object."
            )
        try:
            record = deserializer(payload)
            record_digest = str(record.content_digest)
        except (
            AttributeError,
            KeyError,
            TypeError,
            ValueError,
            TrainingDataInputError,
            TrainingDataSerializationError,
            QualificationError,
        ) as exc:
            raise TrainingDataSerializationError(
                f"Qualification object {path!s} cannot be deserialized."
            ) from exc
        if record_digest != str(content_digest):
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


#: Owner-local publication barrier for one generation's P7 evidence.
PUBLICATION_BARRIER_NAME = ".publication-barrier"


@contextmanager
def qualification_publication_barrier(paths: Any, generation: int | str) -> Iterator[None]:
    """Serialize this generation's qualification object-then-pointer window.

    Same contract as the P5 barrier: the publisher and any storage mutation
    that could touch this generation's P7 evidence acquire it, so a storage
    operation can never observe the window half-open.
    """

    from ..target_size_execution import artifact_publication_lock

    root = qualification_root(paths, generation)
    root.mkdir(parents=True, exist_ok=True)
    with artifact_publication_lock(root / PUBLICATION_BARRIER_NAME):
        yield


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


def _qualification_verdict_value(record: Any) -> str:
    value = getattr(record, "verdict", "")
    return str(getattr(value, "value", value))


def _expected_attempt_identity(binding_digest: str) -> str:
    return digest(
        {
            "schema": "mdstats.qualification-attempt-identity.v1",
            "binding": str(binding_digest),
        }
    )


def _authenticate_resource_observation(
    store: QualificationEvidenceStore,
    record: Any,
    *,
    binding: Any = None,
    authority_record: Any | None = None,
) -> Any:
    """Dereference and authenticate the resource object named by ``record``.

    Resource observations are intentionally immutable descendants rather than
    part of the scientific verdict.  At the public boundary, however, a
    terminal/release claim is not complete unless its measured attempt history
    is present and belongs to the same exact qualification binding.
    """

    from .resource_observation import QualificationResourceObservation

    resource_digest = getattr(record, "resource_observation_digest", None)
    if resource_digest is None:
        raise QualificationLineageError(
            "A terminal/release qualification object does not name its immutable "
            "resource observation."
        )
    authority = authority_record if authority_record is not None else record
    expected_binding = (
        getattr(binding, "content_digest", None)
        or getattr(authority, "binding_digest", None)
    )
    if expected_binding is None:
        raise QualificationLineageError(
            "The qualification resource observation belongs to a different binding."
        )
    expected_attempt = getattr(binding, "attempt_identity", None)
    if expected_attempt is None:
        expected_attempt = _expected_attempt_identity(str(expected_binding))
    expected_scope = getattr(binding, "resource_scope_digest", None)
    if expected_scope is None:
        expected_scope = getattr(authority, "resource_scope_digest", None)
    if expected_scope is None:
        raise QualificationLineageError(
            "The qualification resource observation belongs to a different resource scope."
        )

    # The pointer names the newest cumulative observation, but the attempt
    # history is a content-addressed predecessor chain. Authenticate every
    # link so a terminal record cannot hide a missing, substituted, cyclic, or
    # scope-drifting earlier resume segment behind a valid tail.
    current = str(resource_digest)
    seen: set[str] = set()
    latest = None
    while current:
        if current in seen:
            raise QualificationLineageError(
                "The qualification resource-observation predecessor chain is cyclic."
            )
        seen.add(current)
        try:
            observation = store.get(
                current, QualificationResourceObservation.from_dict
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TrainingDataInputError,
            TrainingDataSerializationError,
        ) as exc:
            raise QualificationLineageError(
                "The qualification resource observation chain is missing or corrupt; "
                "the terminal/release view is not current."
            ) from exc
        if observation.binding_digest != str(expected_binding):
            raise QualificationLineageError(
                "The qualification resource observation belongs to a different binding."
            )
        if observation.attempt_identity != str(expected_attempt):
            raise QualificationLineageError(
                "The qualification resource observation belongs to a different attempt."
            )
        if observation.resource_scope_digest != str(expected_scope):
            raise QualificationLineageError(
                "The qualification resource observation belongs to a different resource scope."
            )
        material = dict(observation.resource_scope_material)
        if not material or digest(material) != observation.resource_scope_digest:
            raise QualificationLineageError(
                "The qualification resource observation has no authenticated stable "
                "resource-scope material."
            )
        if latest is None:
            latest = observation
        predecessor = observation.previous_observation_digest
        current = "" if predecessor is None else str(predecessor)
    return latest


def _authenticate_release_index_record(
    store: QualificationEvidenceStore,
    index: Any,
    *,
    binding: Any = None,
    expected_plan_digest: str | None = None,
) -> Any:
    """Resolve the single terminal-record authority behind a release index."""

    from .record import ProductionQualificationRecord

    terminal_digest = getattr(index, "qualification_record_digest", None)
    if terminal_digest is None:
        raise QualificationLineageError(
            "A release-evidence index does not name its qualification record."
        )
    try:
        terminal = store.get(
            str(terminal_digest), ProductionQualificationRecord.from_dict
        )
    except (OSError, ValueError, KeyError, TrainingDataInputError, TrainingDataSerializationError) as exc:
        raise QualificationLineageError(
            "The release-evidence index names a missing or corrupt qualification record."
        ) from exc
    if binding is not None and not qualification_record_is_current(
        terminal, binding, require_extended=True
    ):
        raise QualificationLineageError(
            "The release-evidence index names a qualification record that is not "
            "current for the authenticated binding."
        )
    if expected_plan_digest is not None and terminal.plan_digest != str(expected_plan_digest):
        raise QualificationLineageError(
            "The release-evidence index names a qualification record from a different plan."
        )
    if _qualification_verdict_value(index) != _qualification_verdict_value(terminal):
        raise QualificationLineageError(
            "The release-evidence index verdict disagrees with its qualification record."
        )
    for attribute in (
        "selected_binding_digest",
        "publication_digest",
        "publication_member_digest",
        "executable_digest",
        "specification_digest",
        "environment_digest",
        "plan_digest",
        "locked_activation_digest",
        "resource_scope_digest",
        "predecessor_reclosure_digest",
        "predecessor_executable_tree_digest",
        "resource_observation_digest",
    ):
        if getattr(index, attribute, None) != getattr(terminal, attribute, None):
            raise QualificationLineageError(
                "The release-evidence index disagrees with its qualification record "
                f"for {attribute}."
            )
    indexed_components = tuple(sorted(getattr(index, "component_evidence_digests", ())))
    terminal_components = tuple(
        sorted(
            outcome.evidence_digest
            for outcome in getattr(terminal, "components", ())
            if str(
                getattr(
                    getattr(outcome, "status", None),
                    "value",
                    getattr(outcome, "status", ""),
                )
            )
            != "waiting_for_reference"
        )
    )
    if indexed_components != terminal_components:
        raise QualificationLineageError(
            "The release-evidence index component graph disagrees with its "
            "qualification record."
        )
    return terminal


def resolve_current_qualification_record(
    campaign_store: Any,
    paths: Any,
    context: Any,
    *,
    kind: str,
    deserializer: Callable[[Mapping[str, Any]], Any],
    binding: Any = None,
    expected_plan_digest: str | None = None,
    qualification_session: Any = None,
) -> Any | None:
    """Locate a published P7 record and validate it against current authority.

    The campaign-store pointer is a *locator*, nothing more.  Selected-binding
    scoping alone would let a terminal verdict published under an older
    qualification specification, executable, environment, or product keep
    answering as "current" until something happened to overwrite the pointer -
    which is exactly the failure mode where a stale ``release_qualified`` is
    reported for a product that no longer exists.  So when the caller supplies
    the freshly resolved :class:`QualificationInputBinding`, every located
    object must reauthenticate against it; a mismatch is historical, not
    current, and is reported as ``None``.
    """

    selected = context.binding if hasattr(context, "binding") else context
    pointer = read_current_qualification_pointer(campaign_store, binding=selected, kind=kind)
    if pointer is None:
        return None
    store = open_qualification_store(paths, selected)
    record = store.get(pointer, deserializer)
    bound = getattr(record, "selected_binding_digest", None)
    if bound is not None and str(bound) != selected.content_digest:
        raise PostSelectionStaleBindingError(
            "A published qualification record binds a different selected generation "
            "than the current authenticated selection."
        )
    if binding is not None and not qualification_record_is_current(
        record, binding, require_extended=True
    ):
        return None
    # Qualification records and release indexes carry ``plan_digest`` and must
    # be checked against the freshly rebuilt plan.  Activation and plan
    # objects are themselves part of this resolver's public surface but do not
    # carry a nested plan digest; their exact binding is the applicable fence.
    if expected_plan_digest is not None and hasattr(record, "plan_digest"):
        plan_value = getattr(record, "plan_digest", None)
        if plan_value is None or str(plan_value) != str(expected_plan_digest):
            return None
        nested_binding = getattr(record, "binding", None)
        if (
            nested_binding is not None
            and binding is not None
            and getattr(nested_binding, "content_digest", None) != binding.content_digest
        ):
            return None
    terminal_record = None
    if kind == POINTER_RELEASE_EVIDENCE:
        terminal_record = _authenticate_release_index_record(
            store,
            record,
            binding=binding,
            expected_plan_digest=expected_plan_digest,
        )
    verdict_is_terminal = _qualification_verdict_value(record) in {
        "rejected",
        "release_qualified",
    }
    if kind == POINTER_RELEASE_EVIDENCE or verdict_is_terminal:
        _authenticate_resource_observation(
            store,
            record,
            binding=binding,
            authority_record=terminal_record,
        )
    # A current terminal/release index is only as sound as every immutable
    # component object it names.  Resolve those objects now so pointer/file
    # presence can never masquerade as current evidence after corruption.
    component_digests = list(getattr(record, "component_evidence_digests", ()))
    # Waiting-for-reference outcomes are intentionally not stored as evidence
    # objects; they are a durable record of the current absence of evidence,
    # not reusable component results.  Only terminal component outcomes can be
    # dereferenced from the immutable object store.
    component_digests.extend(
        str(getattr(item, "evidence_digest"))
        for item in getattr(record, "components", ())
        if getattr(item, "evidence_digest", None) is not None
        and str(getattr(getattr(item, "status", None), "value", getattr(item, "status", "")))
        != "waiting_for_reference"
    )
    component_evidence: list[Any] = []
    if component_digests:
        from .components import QualificationComponentEvidence

        for component_digest in sorted(set(component_digests)):
            evidence = store.get(component_digest, QualificationComponentEvidence.from_dict)
            if binding is not None and not qualification_record_is_current(evidence, binding):
                return None
            component_evidence.append(evidence)

    if qualification_session is not None:
        # A component's binding digest is not enough to identify reference
        # evidence: the same product can receive a new authenticated bundle
        # under the same P5/P6 publication.  Re-establish the bundle at the
        # public exposure boundary and make every reference-dependent evidence
        # object prove that it consumed this exact bundle.  A waiting record is
        # current only while the requested bundle is still absent; once it is
        # supplied, the old waiting observation is historical until ``run``
        # recomputes the dependent components.
        reference_components = {"physical_pes", "relaxation", "dynamics"}
        bundle = qualification_session.authenticated_reference_bundle()
        outcomes = tuple(getattr(record, "components", ()))
        if bundle is not None:
            if any(
                str(getattr(outcome, "component", "")) in reference_components
                and str(
                    getattr(
                        getattr(outcome, "status", None),
                        "value",
                        getattr(outcome, "status", ""),
                    )
                )
                == "waiting_for_reference"
                for outcome in outcomes
            ) or (
                str(
                    getattr(
                        getattr(record, "verdict", None),
                        "value",
                        getattr(record, "verdict", ""),
                    )
                )
                == "waiting_for_reference"
                and not component_evidence
            ):
                return None
        for evidence in component_evidence:
            if evidence.component not in reference_components:
                continue
            expected_input = qualification_session.component_input_digest(
                evidence.component, bundle
            )
            if evidence.component_input_digest != expected_input:
                return None
            payload_bundle = evidence.payload.get("reference_bundle_digest")
            expected_bundle = None if bundle is None else bundle.content_digest
            if payload_bundle != expected_bundle:
                return None
    if binding is not None and getattr(record, "resource_scope_digest", None) is not None:
        if str(record.resource_scope_digest) != str(getattr(binding, "resource_scope_digest", None)):
            return None
    return record


#: Identity fields a current P7 record must reproduce, when it carries them.
_CURRENT_BINDING_FIELDS = (
    ("binding_digest", "content_digest"),
    ("publication_digest", "publication_digest"),
    ("publication_member_digest", "publication_member_digest"),
    ("selected_binding_digest", "selected_binding_digest"),
)


def qualification_record_is_current(
    record: Any, binding: Any, *, require_extended: bool = False
) -> bool:
    """Does this published record describe the exact current P7 binding?

    Only the fields a record actually carries are compared, so one predicate
    serves the plan, the terminal record, the release index, and the locked
    activation without inventing fields for any of them.
    """

    for attribute, expected in _CURRENT_BINDING_FIELDS:
        stored = getattr(record, attribute, None)
        if stored is not None and str(stored) != str(getattr(binding, expected)):
            return False
    # Activation and plan objects are also resolved through this helper, but
    # their schemas intentionally do not carry the predecessor/resource fields
    # of a terminal qualification record.  Strict extended-field currentness
    # applies only to the record/index schemas that actually define
    # ``plan_digest``; their binding digest still fences every other object.
    strict_extended = require_extended and hasattr(record, "plan_digest")
    for attribute, expected in (
        ("specification_digest", binding.specification.content_digest),
        ("environment_digest", binding.environment.content_digest),
        ("executable_digest", binding.executable.content_digest),
        ("resource_scope_digest", getattr(binding, "resource_scope_digest", None)),
        (
            "predecessor_reclosure_digest",
            getattr(binding, "predecessor_reclosure_digest", None),
        ),
        (
            "predecessor_executable_tree_digest",
            getattr(binding, "predecessor_executable_tree_digest", None),
        ),
    ):
        stored = getattr(record, attribute, None)
        if strict_extended:
            if (stored is None) != (expected is None):
                return False
            if stored is not None and str(stored) != str(expected):
                return False
        elif stored is not None and str(stored) != str(expected):
            return False
    return True


# ---------------------------------------------------------------------------
# One-shot locked disclosure history
# ---------------------------------------------------------------------------

LOCKED_REVEAL_DIRECTORY = "locked-reveals"


def locked_reveal_path(paths: Any, binding: PostSelectionBinding, cohort_identity: str) -> Path:
    identity = validate_digest(str(cohort_identity), name="cohort_identity")
    # Disclosure is a fact about the reserved cohort, not a generation-scoped
    # verdict.  Keeping the immutable history beside all generation roots means
    # a new publication or target-size generation cannot make the same reserved
    # cohort appear unseen.
    root = qualification_root(paths, binding.campaign_generation).parent / LOCKED_REVEAL_DIRECTORY
    root.mkdir(parents=True, exist_ok=True)
    return root / f"{identity}.json"


def record_locked_reveal(
    paths: Any,
    binding: PostSelectionBinding,
    *,
    cohort_identity: str,
    activation_digest: str,
) -> Mapping[str, Any]:
    """Append-only proof that this exact locked cohort has been opened.

    Disclosure is a fact about the world, not about the current product
    binding.  It is therefore recorded outside the currentness-fenced pointer
    graph: a later specification, executable, environment, or publication
    change may make a *verdict* historical, but it can never make a revealed
    cohort unseen again.
    """

    from ..target_size_execution import publish_immutable_json_create_or_verify

    payload = {
        "schema": "mdstats.qualification-locked-reveal.v1",
        "cohort_generation_identity": validate_digest(
            str(cohort_identity), name="cohort_identity"
        ),
        "activation_digest": validate_digest(
            str(activation_digest), name="activation_digest"
        ),
    }
    path = locked_reveal_path(paths, binding, cohort_identity)
    publish_immutable_json_create_or_verify(
        path, payload, deserializer=lambda value: _RevealRecord(value)
    )
    return payload


class _RevealRecord:
    """Deserializer shim for the create-or-verify reveal record."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)


def read_locked_reveal(
    paths: Any, binding: PostSelectionBinding, cohort_identity: str
) -> Mapping[str, Any] | None:
    path = locked_reveal_path(paths, binding, cohort_identity)
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise QualificationLineageError(
            f"The locked disclosure record at {path!s} is corrupt; a one-shot "
            "history is never reconstructed by guessing."
        ) from exc
    if payload.get("schema") != "mdstats.qualification-locked-reveal.v1":
        raise QualificationLineageError(
            "A locked disclosure record has an unsupported schema."
        )
    if str(payload.get("cohort_generation_identity")) != str(cohort_identity):
        raise QualificationLineageError(
            "A locked disclosure record describes a different cohort generation."
        )
    try:
        validate_digest(str(payload["cohort_generation_identity"]), name="cohort_identity")
        validate_digest(str(payload["activation_digest"]), name="activation_digest")
    except (KeyError, TrainingDataInputError) as exc:
        raise QualificationLineageError(
            "A locked disclosure record is missing authenticated identity fields."
        ) from exc
    return payload


def _qualification_internal_root(workspace_or_paths: Any) -> Path:
    internal = (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )
    return internal.resolve() / QUALIFICATION_ROOT_NAME


def _locked_activation_from_path(path: Path) -> Any:
    from .locked import LockedActivationRecord

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        activation = LockedActivationRecord.from_dict(payload)
    except (OSError, ValueError, KeyError, TrainingDataInputError, TrainingDataSerializationError) as exc:
        raise QualificationLineageError(
            f"Locked activation object {path!s} is corrupt; disclosure history "
            "is never reconstructed by guessing."
        ) from exc
    if activation.content_digest != path.stem:
        raise QualificationLineageError(
            f"Locked activation object {path!s} is stored under the wrong digest."
        )
    return activation


def find_locked_activation(
    workspace_or_paths: Any,
    activation_digest: str,
) -> Any | None:
    """Find one authenticated activation across all generation object stores."""

    value = validate_digest(str(activation_digest), name="activation_digest")
    root = _qualification_internal_root(workspace_or_paths)
    matches = sorted(root.glob(f"g*/objects/{value[:2]}/{value}.json"))
    if not matches:
        return None
    activations = [_locked_activation_from_path(path) for path in matches]
    first = activations[0]
    if any(item.to_dict() != first.to_dict() for item in activations[1:]):
        raise QualificationLineageError(
            "The same locked activation digest resolves to conflicting immutable objects."
        )
    return first


def find_locked_activation_for_role(
    workspace_or_paths: Any,
    locked_role_digest: str,
) -> Any | None:
    """Find a prior activation for the same reserved role, including legacy roots."""

    role = validate_digest(str(locked_role_digest), name="locked_role_digest")
    root = _qualification_internal_root(workspace_or_paths)
    matches: list[Any] = []
    for path in sorted(root.glob("g*/objects/*/*.json")):
        # Only locked activation objects carry this exact schema.  Other
        # immutable evidence is not inspected as a substitute authority.
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise QualificationLineageError(
                f"Qualification object {path!s} is corrupt."
            ) from exc
        if payload.get("schema") != "mdstats.qualification-locked-activation.v1":
            continue
        activation = _locked_activation_from_path(path)
        if activation.locked_role_digest == role:
            matches.append(activation)
    if not matches:
        return None
    first = matches[0]
    if any(item.content_digest != first.content_digest for item in matches[1:]):
        raise QualificationLineageError(
            "Multiple immutable locked activations claim the same reserved role; "
            "the one-shot history is inconsistent."
        )
    return first


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


#: Released-attempt topology proof for one finished attempt's own scratch tree.
#:
#: Attempt-local bulk - the exported deployment, the per-component evidence - is
#: disposable once the attempt is released, but "beneath the attempt directory"
#: is containment, not authorship.  A downstream consumer that wants to reclaim
#: that bulk needs this owner to say which nodes it actually produced, so that
#: anything else present withholds authority instead of being deleted with it.
#:
#: The v3 proof is bound to the exact released state it was published for. It is
#: written *before* that state, so the released state is the commit point: a
#: crash after the proof grants nothing, because the current state's identity
#: will not match the one the proof binds.  An aborted attempt that legally
#: reopens as active invalidates its own release proof for free, for the same
#: reason.
ATTEMPT_MEMBER_MANIFEST_FILENAME = "attempt-members.json"
ATTEMPT_MEMBER_MANIFEST_SCHEMA = "mdstats.qualification-attempt-members.v3"

#: The superseded development record.  It carries no self identity and no state
#: binding, so it is diagnosable but grants no consequential authority; a tree
#: holding only that record is conservatively retained.
ATTEMPT_MEMBER_MANIFEST_SCHEMA_V2 = "mdstats.qualification-attempt-members.v2"

#: Attempt-root infrastructure this owner writes beside its records.  These are
#: never members and never make an attempt tree look uncertified.
ATTEMPT_INFRASTRUCTURE_NAMES: frozenset[str] = frozenset(
    {
        ATTEMPT_STATE_FILENAME,
        ATTEMPT_MEMBER_MANIFEST_FILENAME,
        f".{ATTEMPT_STATE_FILENAME}.lock",
        f".{ATTEMPT_MEMBER_MANIFEST_FILENAME}.lock",
    }
)


def attempt_state_lock_at(attempt_directory: str | os.PathLike[str]):
    """The exact per-attempt state lock this owner mutates attempt state under.

    Storage takes the same lock, so an aborted attempt cannot reopen as active
    while a storage operation is removing what it treats as released scratch.
    """

    from ..target_size_execution import artifact_publication_lock

    return artifact_publication_lock(Path(attempt_directory) / ATTEMPT_STATE_FILENAME)


def attempt_member_manifest_path(attempt_directory: str | os.PathLike[str]) -> Path:
    return Path(attempt_directory) / ATTEMPT_MEMBER_MANIFEST_FILENAME


def _observe_attempt_nodes(root: Path) -> list[dict[str, str]]:
    """Every node present under one attempt root, classified with no-follow.

    Symlinks and special objects are observed rather than skipped: dropping them
    would let a symlink substituted at a recorded name vanish from the
    comparison instead of contradicting the proof.
    """

    from ..storage.owners import NODE_ABSENT, NODE_DIRECTORY, observed_node_kind

    nodes: list[dict[str, str]] = []
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            entries = sorted(os.scandir(current), key=lambda item: item.name)
        except OSError:
            continue
        for entry in entries:
            path = Path(entry.path)
            relative = path.relative_to(root)
            if relative.parts[0] in ATTEMPT_INFRASTRUCTURE_NAMES:
                continue
            if len(relative.parts) == 1 and relative.name.endswith(".lock"):
                # Advisory locks this owner's publication primitive leaves beside
                # its own top-level records.
                continue
            kind = observed_node_kind(path)
            if kind == NODE_ABSENT:
                continue
            nodes.append({"path": relative.as_posix(), "kind": kind})
            if kind == NODE_DIRECTORY:
                stack.append(path)
    return sorted(nodes, key=lambda item: item["path"])


def _attempt_owned_nodes(root: Path) -> list[dict[str, str]]:
    """The nodes this owner records as its own: plain files and directories."""

    return [
        item
        for item in _observe_attempt_nodes(root)
        if item["kind"] in ("file", "directory")
    ]


def _sealed_attempt_proof(payload: dict[str, Any]) -> dict[str, Any]:
    body = {key: value for key, value in payload.items() if key != "content_digest"}
    return {**body, "content_digest": digest(body)}


def read_attempt_member_proof(
    attempt_directory: str | os.PathLike[str],
) -> tuple[dict[str, Any] | None, str]:
    """Validate one released-attempt topology proof, or say why it grants nothing.

    This is the single validating reader. It opens the record with the strict
    no-follow reader, re-derives the record's own digest, and checks every field
    that could otherwise be used to widen ownership: the attempt root it claims,
    canonical unique node paths with supported kinds, self-consistent parent
    topology, and the counts. A proof that fails any of it returns ``None``; it
    never degrades into a guessed member set.
    """

    from ..storage.owners import NODE_FILE, observed_node_kind, read_owner_record_bytes

    root = Path(attempt_directory)
    path = attempt_member_manifest_path(root)
    if observed_node_kind(path) != NODE_FILE:
        return None, (
            "the released-attempt proof is missing or is not a plain regular file"
        )
    raw = read_owner_record_bytes(path)
    if raw is None:
        return None, "the released-attempt proof could not be read as a regular file"
    return validate_attempt_member_proof_bytes(raw)


def validate_attempt_member_proof_bytes(
    raw: bytes,
) -> tuple[dict[str, Any] | None, str]:
    """Validate proof *bytes*, wherever they were read from.

    The rules that decide whether a record grants authority live here, so the
    descriptor-relative storage reader and the diagnostic path reader can never
    drift into two different notions of a valid proof.
    """

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return None, "the released-attempt proof is not valid JSON"
    if not isinstance(payload, Mapping):
        return None, "the released-attempt proof is not an object"
    schema = payload.get("schema")
    if schema == ATTEMPT_MEMBER_MANIFEST_SCHEMA_V2:
        return None, (
            "the attempt carries only the superseded v2 development record, which is "
            "diagnosable but grants no consequential authority"
        )
    if schema != ATTEMPT_MEMBER_MANIFEST_SCHEMA:
        return None, "the released-attempt proof carries an unsupported schema"
    body = {key: value for key, value in dict(payload).items() if key != "content_digest"}
    if str(payload.get("content_digest", "")) != digest(body):
        return None, (
            "the released-attempt proof does not authenticate against its own "
            "recorded identity"
        )
    recorded_root = str(payload.get("attempt_root", ""))
    if "/" not in recorded_root:
        return None, (
            "the released-attempt proof carries only a bare attempt name rather than "
            "the generation-scoped root locator; it is diagnosable but grants no "
            "destructive authority"
        )
    if str(payload.get("released_state", "")) not in (ATTEMPT_TERMINAL, ATTEMPT_ABORTED):
        return None, "the released-attempt proof names no released state"
    for field in ("attempt_identity", "binding_digest", "publication_digest", "state_digest"):
        if len(str(payload.get(field, ""))) != 64:
            return None, f"the released-attempt proof carries no usable {field}"
    raw_nodes = payload.get("nodes", ())
    if not isinstance(raw_nodes, Sequence) or isinstance(raw_nodes, (str, bytes)):
        return None, "the released-attempt proof records no usable node set"
    nodes: list[dict[str, str]] = []
    seen: set[str] = set()
    directories: set[str] = set()
    for item in raw_nodes:
        if not isinstance(item, Mapping):
            return None, "the released-attempt proof contains a malformed node entry"
        relative = str(item.get("path", ""))
        kind = str(item.get("kind", ""))
        if kind not in ("file", "directory"):
            return None, f"the released-attempt proof records an unsupported kind: {kind!r}"
        parts = tuple(relative.split("/")) if relative else ()
        if (
            not parts
            or relative.startswith("/")
            or any(part in ("", ".", "..") for part in parts)
            or parts[0] in ATTEMPT_INFRASTRUCTURE_NAMES
        ):
            return None, (
                f"the released-attempt proof records a non-canonical path: {relative!r}"
            )
        if relative in seen:
            return None, f"the released-attempt proof records a duplicate node: {relative!r}"
        seen.add(relative)
        if kind == "directory":
            directories.add(relative)
        nodes.append({"path": relative, "kind": kind})
    for item in nodes:
        parent = "/".join(item["path"].split("/")[:-1])
        if parent and parent not in directories:
            return None, (
                f"the released-attempt proof records {item['path']!r} without its "
                "parent directory; the topology is not self-consistent"
            )
    try:
        node_count = int(payload["node_count"])
        file_count = int(payload["file_count"])
        directory_count = int(payload["directory_count"])
    except (KeyError, TypeError, ValueError):
        return None, "the released-attempt proof carries an unusable node accounting"
    if (
        node_count != len(nodes)
        or file_count != sum(1 for item in nodes if item["kind"] == "file")
        or directory_count != len(directories)
    ):
        return None, "the released-attempt proof node accounting is self-inconsistent"
    return {**dict(payload), "nodes": nodes}, "released-attempt proof authenticated"


def publish_attempt_member_proof(
    attempt_directory: str | os.PathLike[str],
    state: "QualificationAttemptState",
    *,
    campaign_generation: int,
) -> Path:
    """Freeze the typed node set this owner produced, bound to one released state.

    Published *before* the released state it binds, so the state remains the
    commit point: a crash in between leaves a proof whose bound state identity
    matches nothing current, which grants no authority at all.

    The root it binds is the **generation-scoped** locator, taken from the
    owner's authoritative ``PostSelectionBinding.campaign_generation`` rather
    than from whatever parent pathname happens to contain the file. Scratch
    belongs to one generation namespace, so a whole attempt copied under another
    generation must not look like that generation's owned scratch.
    """

    root = Path(attempt_directory)
    nodes = _attempt_owned_nodes(root)
    payload = _sealed_attempt_proof(
        {
            "schema": ATTEMPT_MEMBER_MANIFEST_SCHEMA,
            "attempt_root": released_attempt_root_locator(
                campaign_generation, state.attempt_identity
            ),
            "attempt_identity": state.attempt_identity,
            "binding_digest": state.binding_digest,
            "publication_digest": state.publication_digest,
            "released_state": state.state,
            "state_digest": state.content_digest,
            "nodes": nodes,
            "node_count": len(nodes),
            "file_count": sum(1 for item in nodes if item["kind"] == "file"),
            "directory_count": sum(1 for item in nodes if item["kind"] == "directory"),
        }
    )
    destination = attempt_member_manifest_path(root)
    _atomic_write_json(destination, payload)
    return destination


def validate_bound_attempt_proof(
    attempt_directory: str | os.PathLike[str],
    state: "QualificationAttemptState",
) -> tuple[dict[str, Any] | None, str]:
    """The retained v3 proof, proven to bind *this* exact released state.

    Self-consistency is not enough. The proof redundantly carries the binding
    and publication digests, and a record that authenticates against its own
    digest while naming a different binding is contradictory metadata, not
    authority. Every field that ties the proof to the state is checked here so
    no consumer has to remember to.
    """

    from ..storage.owners import NODE_DIRECTORY, observed_node_kind

    root = Path(attempt_directory)
    if observed_node_kind(root) != NODE_DIRECTORY:
        return None, f"{root} is not a plain directory"
    proof, why = read_attempt_member_proof(root)
    if proof is None:
        return None, why
    # The root binding is recomputed from the namespace this attempt actually
    # lives in, not read back out of the record. A whole attempt copied under
    # another generation stays internally consistent; what it is not is bound to
    # the generation it now sits in.
    generation = parse_canonical_generation(root.parent.parent.name)
    if root.parent.name != "attempts" or generation is None:
        return None, (
            "the attempt does not live in a canonical generation-scoped "
            "qualification namespace"
        )
    bound, why = _proof_binds_state(proof, state, generation, root.name)
    if not bound:
        return None, why
    return proof, why


#: The descriptor-relative primitives this owner's mutation boundary is built
#: from.  `shutil.rmtree(..., dir_fd=...)` does not exist on the supported
#: Python floor (>=3.10), so the recursion below is written from the `os`
#: primitives that do, rather than raising the floor to avoid writing it.
_DIR_FD_MUTATION_PRIMITIVES = ("O_NOFOLLOW", "O_DIRECTORY")


#: Owned by ``storage.trust`` alongside the primitive it guards; bound at
#: the bottom of this module for the circular-import reason given there.


class SpentCapabilityError(RuntimeError):
    """A closed or invalidated attempt capability was used again.

    Not a refusal to be recorded and moved past: reaching here means a caller
    tried to spend authority the owner has already withdrawn, and the only safe
    answer is to stop before touching the filesystem at all.
    """


@dataclass
class ReleasedAttemptSession:
    """A live, descriptor-bound capability over one released P7 attempt.

    Everything that authorizes a destructive action on this attempt - the
    authenticated state, the validated released proof, the generation-scoped
    root binding, and the exact typed topology - was established *on the open
    descriptor this object holds*, and the mutation happens through that same
    descriptor. A certification made on a descriptor that was then closed is a
    memory of authority, not authority: between the close and the next open the
    name can mean something else, and only the identity check would notice.

    The capability is ephemeral and one-way. It lives for one apply invocation
    under the already-held storage/P5/P7 locks; once closed or invalidated it
    can never be spent again. That guard is checked *before* any syscall that
    would use the stored descriptor, because the integer is not an identity -
    the kernel is free to hand the same number to the next thing that opens a
    file, and a stale capability must not be able to ride it.
    """

    attempt_fd: int
    attempt_root: Path
    generation: int
    state: "QualificationAttemptState"
    proof: Mapping[str, Any]
    certified_nodes: tuple[tuple[str, str], ...]
    root_identity: Mapping[str, int]
    release_authority: str
    closed: bool = False
    #: Why the capability was withdrawn, when it was. A contradiction found at
    #: one member's mutation boundary is evidence about the whole attempt, so
    #: the remaining planned members of that attempt inherit this refusal
    #: instead of spending a premise the owner just saw fail.
    invalidation_reason: str = ""
    _recorded: Mapping[str, str] | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        # Materialized once. Rebuilding this per planned member would re-walk
        # the whole proof for every top-level target - O(N*M) for no gain, since
        # the proof was authenticated once on this descriptor and cannot change
        # under a live session.
        object.__setattr__(
            self,
            "_recorded",
            MappingProxyType({path: kind for path, kind in self.certified_nodes}),
        )

    @property
    def recorded(self) -> Mapping[str, str]:
        """The authenticated proof's typed nodes, read-only.

        Handed out as a view rather than a copy: a caller that could add an
        entry here would be widening the certified set after authentication,
        which is exactly the authority the session exists to bound.
        """

        assert self._recorded is not None
        return self._recorded

    @property
    def live(self) -> bool:
        return not self.closed and not self.invalidation_reason

    def require_live(self) -> None:
        """Refuse to act at all if this capability has been spent."""

        if self.closed:
            raise SpentCapabilityError(
                "this released-attempt capability was closed; its descriptor number "
                "may now belong to something else entirely"
            )
        if self.invalidation_reason:
            raise SpentCapabilityError(
                f"this released-attempt capability was invalidated: "
                f"{self.invalidation_reason}"
            )

    def invalidate(self, reason: str) -> None:
        """Withdraw the capability and close its descriptor, once.

        The withdrawal is recorded and the descriptor released before anything
        can fail, so the capability is unspendable from here on whatever the
        kernel says about the close. A close failure is then raised to the
        caller, because only the caller knows whether a primary product failure
        is already in flight and therefore whether this is the failure that
        should be reported or secondary evidence behind one. Deciding that here
        by inspecting the ambient exception state would make a genuine
        close-only failure invisible whenever anything else happened to be
        propagating.
        """

        if not self.invalidation_reason:
            self.invalidation_reason = reason or "withdrawn"
        self.close()

    def close(self) -> None:
        """Spend this capability, once and irreversibly.

        The session is marked closed and the descriptor number cleared *before*
        the kernel close, so a close that fails cannot leave a session that
        still looks live holding a descriptor number the kernel may reissue.
        """

        if not self.closed:
            self.closed = True
            fd = self.attempt_fd
            self.attempt_fd = -1
            if fd >= 0:
                os.close(fd)

    def __enter__(self) -> "ReleasedAttemptSession":
        return self

    def __exit__(self, *_exc: Any) -> None:
        self.close()


def open_released_attempt_session(
    paths: Any,
    attempt_root: str | os.PathLike[str],
    *,
    expected_root_identity: Mapping[str, int] | None,
    expected_release_authority: str = "",
) -> tuple["ReleasedAttemptSession | None", "MutationOutcomeT"]:
    """Acquire the live authority a released-attempt mutation must hold.

    Strict reacquisition, then state, proof, root binding and typed topology are
    all established on the descriptor that is returned still open - so the
    authority the caller mutates under is the authority it just verified, not a
    snapshot of one taken earlier somewhere else.

    ``expected_root_identity`` and ``expected_release_authority`` are the plan's
    constraints. They narrow what this session may be used for; they never
    supply the authority themselves.
    """

    from ..storage.outcome import refused_no_change

    if not dir_fd_mutation_supported():
        return None, refused_no_change(
            "this platform does not provide the no-follow directory-descriptor "
            "primitives this owner's authority boundary is built on, so released "
            "scratch is retained rather than removed by pathname"
        )
    root = Path(attempt_root)
    generation = parse_canonical_generation(root.parent.parent.name)
    attempt_fd, why = open_attempt_namespace(paths, root)
    if attempt_fd is None or generation is None:
        namespace_refusal = refused_no_change(
            f"the attempt namespace is unresolved: {why}"
        )
        if attempt_fd is not None:
            # The namespace/generation refusal is already decided; releasing the
            # descriptor cannot be allowed to replace it with an `OSError`.
            release_descriptor_behind(attempt_fd, root, namespace_refusal)
        return None, namespace_refusal

    # The outcome is materialized first, the descriptor is ranked and released
    # second, and only then does this function return. A `finally: os.close(...)`
    # around the returns below would let a close failure cancel an owner,
    # root-identity, release-authority, state/proof or topology refusal that had
    # already been decided - the one classification the caller records.
    try:
        session, outcome = _authenticate_released_attempt(
            paths,
            root,
            attempt_fd,
            generation,
            expected_root_identity=expected_root_identity,
            expected_release_authority=expected_release_authority,
        )
    except BaseException as exc:
        release_descriptor_behind(attempt_fd, root, exc)
        raise
    if session is None:
        release_descriptor_behind(attempt_fd, root, outcome)
        return None, outcome
    # Ownership transferred exactly once: from here the session owns the
    # descriptor and this acquisition never closes it.
    return session, outcome


def release_descriptor_behind(
    handle: int, display: Any, primary: Any
) -> None:
    """Close one still-owned descriptor once, behind an already-decided primary.

    Every failed acquisition path releases what it acquired, and exactly once.
    A close that fails while a namespace, root-identity, release-authority,
    state/proof, topology or authentication refusal is already decided is
    secondary evidence: raising it would replace the classification the caller
    records and, on a mutating path, the mutation truth that travels with it.
    """

    try:
        os.close(handle)
    except OSError:
        _LOGGER.warning(
            "qualification: releasing the attempt descriptor for %s failed while "
            "a primary outcome (%s) was already decided; the primary outcome is "
            "preserved",
            display,
            getattr(primary, "detail", primary),
        )


def _authenticate_released_attempt(
    paths: Any,
    root: Path,
    attempt_fd: int,
    generation: int,
    *,
    expected_root_identity: Mapping[str, int] | None,
    expected_release_authority: str,
) -> tuple["ReleasedAttemptSession | None", "MutationOutcomeT"]:
    """Decide this acquisition's outcome without ever closing the descriptor.

    Separating the decision from the release is what makes the ranking in
    :func:`open_released_attempt_session` possible: this returns either a live
    session that has taken ownership of ``attempt_fd`` or a refusal that the
    caller records, and it never competes with either by closing.
    """

    from ..storage.outcome import refused_no_change

    identity = _descriptor_identity(attempt_fd)
    if expected_root_identity is not None and (
        int(identity["device"]) != int(expected_root_identity["device"])
        or int(identity["inode"]) != int(expected_root_identity["inode"])
    ):
        return None, refused_no_change(
            "the attempt root is a different filesystem object than the one this "
            "action was authorized against; nothing was removed"
        )
    authority = _authenticate_attempt_from_descriptor(root, attempt_fd, generation)
    if authority.state is None:
        return None, refused_no_change(
            f"the released attempt state is no longer authentic: {authority.reason}"
        )
    certified, certify_why, nodes, proof = _certify_attempt_from_descriptor(
        attempt_fd, root, generation, authority.state
    )
    if not certified or proof is None:
        return None, refused_no_change(
            f"the released attempt is no longer certified: {certify_why}"
        )
    release_authority = released_authority_identity(
        generation,
        authority.state.attempt_identity,
        authority.state.content_digest,
        str(proof["content_digest"]),
    )
    if expected_release_authority and release_authority != expected_release_authority:
        return None, refused_no_change(
            "the released authority behind this attempt changed after planning; "
            "the state and proof now confer a different release, so the plan no "
            "longer authorizes it"
        )
    session = ReleasedAttemptSession(
        attempt_fd=attempt_fd,
        attempt_root=root,
        generation=generation,
        state=authority.state,
        proof=proof,
        certified_nodes=nodes,
        root_identity=identity,
        release_authority=release_authority,
    )
    return session, refused_no_change("authenticated")


#: The bounded filesystem-identity dimensions the storage plan already
#: revalidates a target on.  The final P7 boundary observes the same ones, no
#: fewer: if plan revalidation later strengthens its identity, this must not
#: silently become the weaker of the two checks.
TARGET_IDENTITY_DIMENSIONS = ("kind", "device", "inode", "size_bytes", "mtime_ns")


def _observed_target_identity(entry_stat: os.stat_result) -> dict[str, Any]:
    """The plan's identity dimensions, from a no-follow descriptor-relative stat."""

    mode = entry_stat.st_mode
    if stat.S_ISLNK(mode):
        kind = "symlink"
    elif stat.S_ISREG(mode):
        kind = "file"
    elif stat.S_ISDIR(mode):
        kind = "directory"
    else:
        kind = "other"
    return {
        "kind": kind,
        "device": int(entry_stat.st_dev),
        "inode": int(entry_stat.st_ino),
        "size_bytes": int(entry_stat.st_size),
        "mtime_ns": int(entry_stat.st_mtime_ns),
    }


def remove_released_attempt_member(
    session: "ReleasedAttemptSession",
    member_name: str,
    *,
    expected_kind: str = "",
    planned_identity: Mapping[str, Any],
) -> "MutationOutcomeT":
    """Remove one proof-certified released member through a live session.

    The member and everything beneath it are opened, unlinked, and removed
    relative to the session's descriptor. No ancestor is ever named again after
    the session authenticated it.

    ``planned_identity`` is the filesystem identity the immutable plan bound to
    this exact target, and it is **required**. It is compared here, immediately
    before the mutation and through the retained descriptor, because ordinary
    plan revalidation happened earlier and by pathname: an object swapped in
    afterwards under the same name and kind would otherwise inherit the plan's
    permission to delete it. Making the comparison optional would make the
    boundary a convention every future caller could forget; a missing or
    incomplete identity is refused before anything is observed or removed.

    The guarantee is descriptor-pinned owner ancestry plus no-follow fd-relative
    mutation under the supported-owner locks. It is deliberately *not* a claim
    that the kernel unlinks a directory entry only if its inode still matches an
    earlier observation - POSIX offers no such primitive, and pretending
    otherwise would misdescribe the boundary. Only the irreducible race after
    this final check is outside it.
    """

    from ..storage.outcome import already_absent, refused_no_change, removed

    # Before any syscall: a spent capability may hold a descriptor number the
    # kernel has since reissued to something else.
    session.require_live()

    # Also before any syscall: without the plan's full identity there is nothing
    # to compare the target against, so there is no authority to act on it.
    missing = [
        key
        for key in TARGET_IDENTITY_DIMENSIONS
        if key not in (planned_identity or {})
    ]
    if missing:
        return refused_no_change(
            "the plan-bound target identity is incomplete "
            f"({', '.join(missing)} absent), so this action was not authorized "
            "against any specific object; nothing was removed"
        )

    attempt_fd = session.attempt_fd
    recorded = session.recorded
    if expected_kind and recorded.get(member_name) != expected_kind:
        return refused_no_change(
            f"this owner now records {recorded.get(member_name)!r} at that name, not "
            f"the {expected_kind!r} the plan targeted"
        )
    try:
        entry_stat = os.stat(member_name, dir_fd=attempt_fd, follow_symlinks=False)
    except FileNotFoundError:
        # Monotonic absence: an earlier action in this cleanup, or an interrupted
        # prior one, already removed it. Terminally satisfied, but this execution
        # reclaimed nothing and must not claim the planned bytes.
        return already_absent("the certified member was already gone")
    except OSError as exc:
        return refused_no_change(f"the certified member could not be observed: {exc}")

    observed = _observed_target_identity(entry_stat)
    differing = [
        key
        for key in TARGET_IDENTITY_DIMENSIONS
        if observed[key] != planned_identity[key]
    ]
    if differing:
        return refused_no_change(
            "the target is no longer the object this action was planned against "
            f"({', '.join(differing)} differ); nothing was removed"
        )

    if stat.S_ISREG(entry_stat.st_mode):
        if recorded.get(member_name) != "file":
            return refused_no_change("this owner did not record a file at that name")
        size = int(entry_stat.st_size)
        _unlink_certified_file(attempt_fd, member_name)
        # The entry is gone from here on: any failure below is partial mutation,
        # never a refusal that claims nothing happened.
        _fsync_after_mutation(attempt_fd, removed_bytes=size, what=member_name)
        return removed("removed relative to the authenticated attempt directory")
    if not stat.S_ISDIR(entry_stat.st_mode):
        return refused_no_change(
            "the certified member is neither a plain file nor a plain directory; "
            "it is retained"
        )
    if recorded.get(member_name) != "directory":
        return refused_no_change("this owner did not record a directory at that name")
    outcome = _remove_certified_directory(
        attempt_fd,
        member_name,
        session.attempt_root / member_name,
        recorded,
        f"{member_name}/",
        seen=set(),
    )
    # Gated on mutation, never on the byte total: a recursion that unlinked a
    # zero-byte file or removed an empty directory changed the namespace and
    # owes the same durability step as one that freed a gigabyte.
    if outcome.mutated:
        _fsync_after_mutation(
            attempt_fd,
            removed_bytes=int(outcome.removed_bytes or 0),
            what=member_name,
        )
    return outcome


def _fsync_after_mutation(handle: int, *, removed_bytes: int, what: str) -> None:
    """Persist a directory-entry removal, or say exactly what was already lost.

    ``removed_bytes`` names entries whose removal has already happened in the
    live namespace. If the fsync that was meant to make that durable fails, the
    action is not ``removed`` - but neither is it a no-op, and the executor has
    to be told which of the two it is before the failure propagates.
    """

    from ..storage.outcome import PartialMutationError, partial_change_refused

    try:
        os.fsync(handle)
    except OSError as exc:
        raise PartialMutationError(
            partial_change_refused(
                f"{what} was removed but the removal could not be made durable: {exc}",
                removed_bytes=removed_bytes,
            ),
            exc,
        ) from exc


def _unlink_certified_file(parent_fd: int, name: str) -> None:
    """Unlink one certified regular file relative to its authenticated parent.

    The single destructive transition for a top-level released file, kept
    separate for the same reason the directory recursion is: this is the exact
    point where the owner's authority becomes a syscall, and it names only the
    entry - never an ancestor.
    """

    os.unlink(name, dir_fd=parent_fd)


def _remove_certified_directory(
    parent_fd: int,
    name: str,
    display: Path,
    recorded: Mapping[str, str],
    prefix: str,
    *,
    seen: set[tuple[int, int]] | None = None,
    ledger: "MutationLedgerT | None" = None,
) -> "MutationOutcomeT":
    """Recursively remove one certified directory, descriptor-relative.

    Depth-first, entering each child through a no-follow open on the descriptor
    of the parent that was just authenticated. Anything the proof did not record
    with this exact kind - and anything on the far side of a mount boundary -
    stops the removal instead of widening it, and the partially emptied
    container is retained rather than forced.

    Stopping part-way is a real outcome, not a failure to report: by the time a
    contradiction appears, earlier certified children of this container may
    already be unlinked. The ledger answers two *different* questions - whether
    anything was destroyed, and how many bytes that accounted for - because they
    genuinely come apart. Unlinking a zero-byte file, removing an empty
    directory, or dropping one more hard link to an already-counted inode all
    change the namespace while crediting nothing. Deciding "did this mutate?"
    from the byte total would report those as no change, and would also skip the
    durability step the caller owes for entries that really went.

    ``seen`` carries ``(device, inode)`` across the whole action so a file with
    several hard links is counted once, matching the planner's own tree metric.
    """

    from ..storage.outcome import MutationLedger, already_absent
    from ..storage.trust import verify_opened_directory_trust

    if ledger is None:
        ledger = MutationLedger()
    if seen is not None:
        # Callers that pre-seed the dedup set keep it authoritative.
        ledger.adopt_seen(seen)

    try:
        handle = _open_directory_nofollow(name, dir_fd=parent_fd)
    except FileNotFoundError:
        return already_absent("already gone")
    except NamespaceAmbiguity as exc:
        return ledger.stop(f"{display}: {exc}")

    # From here there is exactly one way out: whatever the descent decides, the
    # descriptor is closed once on the way. Returning from inside the walk is
    # how a bounded contradiction loop leaks one descriptor per contradiction.
    primary: BaseException | None = None
    outcome: "MutationOutcomeT | None" = None
    try:
        crossed, detail = verify_opened_directory_trust(parent_fd, handle, display)
        if crossed:
            outcome = ledger.stop(detail)
        else:
            outcome = _empty_and_remove_certified_directory(
                handle, parent_fd, name, display, recorded, prefix, ledger
            )
    except BaseException as exc:  # noqa: BLE001 - re-raised after the close
        primary = exc
    primary = _close_owner_descriptor(handle, display, ledger, primary)
    if primary is not None:
        raise primary
    assert outcome is not None
    return outcome


def _close_owner_descriptor(
    handle: int,
    display: Path,
    ledger: "MutationLedgerT",
    primary: BaseException | None,
) -> BaseException | None:
    """Close one owner descriptor once, without displacing a primary failure.

    A close failure after this action already destroyed something is real
    evidence, but it is not the evidence the audit needs most: the primary
    failure carries what was removed. So it is logged and subordinated there,
    and only becomes the outcome when nothing else failed.
    """

    try:
        os.close(handle)
    except OSError as exc:
        if primary is not None:
            _LOGGER.warning(
                "qualification: closing the descriptor for %s failed after a "
                "primary failure (%s); the primary failure is preserved",
                display,
                exc,
            )
            return primary
        return ledger.failure(exc, f"{display} descriptor close failed: {exc}")
    return primary


def _empty_and_remove_certified_directory(
    handle: int,
    parent_fd: int,
    name: str,
    display: Path,
    recorded: Mapping[str, str],
    prefix: str,
    ledger: "MutationLedgerT",
) -> "MutationOutcomeT":
    """Empty one authenticated certified directory and then spend it.

    The descriptor stays open across the final ``rmdir`` on purpose: ``rmdir``
    names an entry, and the entry is compared against this still-open
    descriptor immediately before the syscall so a directory substituted after
    authentication is refused rather than removed.
    """

    from ..storage.outcome import removed as removed_outcome
    from ..storage.trust import (
        crosses_mount_boundary_at,
        verify_final_directory_identity,
    )

    def stop(detail: str) -> "MutationOutcomeT":
        return ledger.stop(detail)

    try:
        entries = sorted(os.scandir(handle), key=lambda item: item.name)
    except OSError as exc:
        return stop(f"{display} could not be enumerated: {exc}")
    for entry in entries:
        child_relative = f"{prefix}{entry.name}"
        child_display = display / entry.name
        expected = recorded.get(child_relative)
        try:
            is_sym = entry.is_symlink()
            is_dir = entry.is_dir(follow_symlinks=False)
            is_file = entry.is_file(follow_symlinks=False)
        except OSError as exc:
            return stop(f"{child_display} could not be observed: {exc}")
        if is_sym:
            return stop(f"{child_display} is a symlink; the container is retained")
        if is_dir:
            if expected != "directory":
                return stop(
                    f"{child_display} is a directory this owner did not record"
                    if expected is None
                    else f"{child_display} was recorded as a {expected}"
                )
            crossed, detail = crosses_mount_boundary_at(
                handle, entry.name, child_display
            )
            if crossed:
                return stop(detail)
            nested = _remove_certified_directory(
                handle,
                entry.name,
                child_display,
                recorded,
                f"{child_relative}/",
                ledger=ledger,
            )
            if not nested.succeeded:
                return stop(nested.detail)
            continue
        if not is_file:
            return stop(
                f"{child_display} is a special node; the container is retained"
            )
        if expected != "file":
            return stop(
                f"{child_display} is a file this owner did not record"
                if expected is None
                else f"{child_display} was recorded as a {expected}"
            )
        # Measured before the unlink, because afterwards there is nothing
        # left to measure - but credited only once the entry has actually
        # gone, so a failed unlink cannot inflate the figure.
        #
        # An unmeasurable file is *retained*. Deleting it and crediting zero
        # would put bytes beyond recovery that this action can never account
        # for, and if nothing else had been removed yet the outcome would
        # even read as "nothing changed".
        try:
            child_stat = entry.stat(follow_symlinks=False)
        except OSError as exc:
            return stop(f"{child_display} could not be measured: {exc}")
        try:
            _unlink_certified_file(handle, entry.name)
        except OSError as exc:
            return stop(f"{child_display} could not be removed: {exc}")
        ledger.credit(
            int(child_stat.st_size),
            (int(child_stat.st_dev), int(child_stat.st_ino)),
        )
    try:
        os.fsync(handle)
    except OSError as exc:
        raise ledger.failure(
            exc,
            f"{display} was emptied but the removal could not be made durable: {exc}",
        ) from exc
    same, why = verify_final_directory_identity(parent_fd, name, handle, display)
    if not same:
        return stop(why)
    try:
        os.rmdir(name, dir_fd=parent_fd)
    except OSError as exc:
        return stop(f"{display} could not be removed: {exc}")
    # An emptied directory that is now gone is a destructive transition even
    # though a directory entry credits no bytes under the planner's metric.
    ledger.note_mutation()
    return removed_outcome("removed", removed_bytes=ledger.removed_bytes)


def authorize_released_attempt_member(
    paths: Any,
    attempt_root: str | os.PathLike[str],
    member_name: str,
    *,
    expected_root_identity: Mapping[str, int] | None,
    certified_nodes: Sequence[Mapping[str, str]],
) -> tuple[tuple[Path, ...], tuple[tuple[Path, str], ...]]:
    """Authorize one released-attempt member through the continuous descent.

    This exists because typed node *names* do not say which directory they were
    certified beneath. Handing them to a generic pathname walk would re-enter
    exactly the resolution the strict P7 acquisition just closed, one level
    later: the certification would have been done on one directory and the
    removal on whatever now answers to that name.

    So the attempt namespace is re-acquired no-follow from the accepted campaign
    parent, the attempt root's ``(device, inode)`` is required to be the one the
    certification observed, and the member subtree is walked descriptor-relative
    from there. Nested mounts, symlinks, special nodes, and unrecorded or
    wrong-kind nodes reduce authority exactly as they do elsewhere.
    """

    from ..storage.inventory import AuthorizedPath
    from ..storage.trust import crosses_mount_boundary

    root = Path(attempt_root)
    member_path = root / member_name
    refused: list[tuple[Path, str]] = []
    attempt_fd, why = open_attempt_namespace(paths, root)
    if attempt_fd is None:
        return (), ((member_path, f"the attempt namespace is unresolved: {why}"),)
    try:
        identity = _descriptor_identity(attempt_fd)
        if expected_root_identity is not None and (
            int(identity["device"]) != int(expected_root_identity["device"])
            or int(identity["inode"]) != int(expected_root_identity["inode"])
        ):
            return (), (
                (
                    root,
                    "the attempt root is a different filesystem object than the one "
                    "this certification was performed on",
                ),
            )
        recorded = {item["path"]: item["kind"] for item in certified_nodes}
        try:
            member_fd = _open_directory_nofollow(member_name, dir_fd=attempt_fd)
        except FileNotFoundError:
            return (), ()
        except NamespaceAmbiguity as exc:
            return (), ((member_path, str(exc)),)
        try:
            members: list[Path] = []
            stack: list[tuple[int, str]] = [(member_fd, "")]
            owned: list[int] = []
            try:
                while stack:
                    handle, relative = stack.pop()
                    try:
                        entries = sorted(
                            os.scandir(handle), key=lambda item: item.name
                        )
                    except OSError as exc:
                        refused.append(
                            (
                                member_path / relative if relative else member_path,
                                f"could not be enumerated: {exc}",
                            )
                        )
                        continue
                    for entry in entries:
                        child_relative = (
                            f"{relative}/{entry.name}" if relative else entry.name
                        )
                        child_path = member_path / child_relative
                        crossed, detail = crosses_mount_boundary(root, child_path)
                        if crossed:
                            refused.append((child_path, detail))
                            continue
                        expected_kind = recorded.get(child_relative)
                        if entry.is_symlink():
                            refused.append(
                                (child_path, "symlink members are never collected")
                            )
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if expected_kind != "directory":
                                refused.append(
                                    (
                                        child_path,
                                        "a directory this owner did not record"
                                        if expected_kind is None
                                        else f"the owner recorded a {expected_kind} here",
                                    )
                                )
                                continue
                            try:
                                child_fd = _open_directory_nofollow(
                                    entry.name, dir_fd=handle
                                )
                            except (FileNotFoundError, NamespaceAmbiguity) as exc:
                                refused.append((child_path, f"{exc}"))
                                continue
                            owned.append(child_fd)
                            stack.append((child_fd, child_relative))
                            continue
                        if not entry.is_file(follow_symlinks=False):
                            refused.append(
                                (child_path, "a special node is never an owned member")
                            )
                            continue
                        if expected_kind != "file":
                            refused.append(
                                (
                                    child_path,
                                    "a file this owner did not record"
                                    if expected_kind is None
                                    else f"the owner recorded a {expected_kind} here",
                                )
                            )
                            continue
                        members.append(AuthorizedPath.create(child_path, "file"))
            finally:
                # This resolver is planning, not mutation, but its descriptors
                # are acquired the same way and released under the same
                # doctrine: exactly once, behind the authorization result it has
                # already decided, so a close failure never becomes the answer.
                for handle in owned:
                    release_descriptor_behind(handle, member_path, "authorization")
            return tuple(sorted(members)), tuple(refused)
        finally:
            release_descriptor_behind(member_fd, member_path, "authorization")
    finally:
        release_descriptor_behind(attempt_fd, root, "authorization")




def read_attempt_state_at(
    attempt_directory: str | os.PathLike[str],
) -> "QualificationAttemptState | None":
    """The authenticated state at one attempt root, or ``None``.

    A thin projection of :func:`authenticate_attempt_state` - the single strict
    authority - so that no storage-facing consumer can reach a weaker answer.
    """

    return authenticate_attempt_state(attempt_directory).state


def read_attempt_state(
    paths: Any, binding: PostSelectionBinding, attempt_identity: str
) -> QualificationAttemptState | None:
    from ..storage.owners import NODE_FILE, observed_node_kind, read_owner_record_bytes

    path = attempt_state_path(paths, binding, attempt_identity)
    if observed_node_kind(path) != NODE_FILE:
        if path.exists() or path.is_symlink():
            raise QualificationLineageError(
                f"Qualification attempt state at {path!s} is not a plain regular "
                "file; a qualification attempt never resumes from a substituted "
                "object."
            )
        return None
    raw = read_owner_record_bytes(path)
    if raw is None:
        raise QualificationLineageError(
            f"Qualification attempt state at {path!s} could not be read as a plain "
            "regular file."
        )
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
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

    from ..target_size_execution import artifact_publication_lock

    attempt_value = validate_digest(str(attempt_identity), name="attempt_identity")
    publication_value = validate_digest(str(publication_digest), name="publication_digest")
    binding_value = validate_digest(str(binding_digest), name="binding_digest")
    resolved = tuple(str(Path(value).resolve()) for value in referenced_paths)
    state_path = attempt_state_path(paths, binding, attempt_value)
    # The read/merge/write sequence is one owner transaction.  Without this
    # lock, two independent workers can each read the old reference set and
    # silently lose the other's retention path.
    with artifact_publication_lock(state_path):
        existing = read_attempt_state(paths, binding, attempt_value)
        if existing is not None:
            if existing.publication_digest != publication_value:
                raise QualificationLineageError(
                    "An existing qualification attempt with this identity references a "
                    "different publication; the attempt identity is not authentic."
                )
            if existing.binding_digest != binding_value:
                raise QualificationLineageError(
                    "An existing qualification attempt with this identity references a "
                    "different qualification binding."
                )
            # A terminal state is monotonic.  A late retry cannot reopen it and
            # reintroduce retention references after release.
            if existing.state == ATTEMPT_TERMINAL:
                return existing
        opened_at = existing.opened_at if existing is not None else _utc_now()
        merged = tuple(sorted(set(resolved) | set(existing.referenced_paths if existing else ())))
        state = QualificationAttemptState(
            attempt_identity=attempt_value,
            binding_digest=binding_value,
            publication_digest=publication_value,
            state=ATTEMPT_ACTIVE,
            referenced_paths=merged,
            opened_at=opened_at,
            updated_at=_utc_now(),
            detail=detail,
        )
        _atomic_write_json(state_path, state.to_dict())
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

    from ..target_size_execution import artifact_publication_lock

    attempt_value = validate_digest(str(attempt_identity), name="attempt_identity")
    state_path = attempt_state_path(paths, binding, attempt_value)
    with artifact_publication_lock(state_path):
        existing = read_attempt_state(paths, binding, attempt_value)
        if existing is None:
            return None
        # Terminal completion is immutable, including its released reference
        # set.  Duplicate completion calls return the existing state rather
        # than changing timestamps or downgrading it to aborted - but they still
        # have to prove the retained proof is intact. Returning a bare success
        # while the topology proof that authorizes reclamation has been lost
        # would report the owner as healthy and leave the terminal scratch
        # permanently unreclaimable with nothing said about it. The proof is
        # verified, never rebuilt: rescanning a tree storage may already have
        # depleted or something may have tampered with is exactly how foreign
        # content would get absorbed into ownership.
        if existing.state == ATTEMPT_TERMINAL:
            proof, why = validate_bound_attempt_proof(state_path.parent, existing)
            if proof is None:
                raise QualificationLineageError(
                    f"Repeated terminal release of qualification attempt "
                    f"{existing.attempt_identity[:12]}... cannot validate its retained "
                    f"released-attempt proof: {why}. The attempt and its scratch are "
                    "retained; the proof is never rebuilt from the current tree."
                )
            return existing
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
        # The attempt stops being written exactly here, so this is the one
        # moment at which its topology can be recorded truthfully. The proof is
        # published first and binds the state it is being published for, which
        # makes the state write the commit point: a crash in between leaves a
        # proof bound to a state that is not current, and therefore grants
        # nothing at all.
        publish_attempt_member_proof(
            state_path.parent,
            state,
            campaign_generation=int(binding.campaign_generation),
        )
        _atomic_write_json(state_path, state.to_dict())
        return state


def iter_attempt_states(workspace_or_paths: Any) -> tuple[QualificationAttemptState, ...]:
    """Every attempt state this owner can authenticate."""

    states, _unreadable = iter_attempt_state_census(workspace_or_paths)
    return states


#: Both are owned by ``storage.trust`` and bound at the bottom of this module.
#: The storage package initializes this one, so binding them up here would be a
#: circular import; by the end of the file this module is complete and the
#: import resolves normally.  Declared here so readers meet them in place.
NamespaceAmbiguity: type[RuntimeError]


#: Errors that mean "this name is simply not there".  Everything else - a
#: symlink loop, a non-directory component, a permission or stale-handle
#: failure, an I/O error - means the component exists or its status is unknown,
#: which is unresolved authority rather than absence.  Collapsing the two is how
#: a substituted qualification family would silently become "no attempts".
_ABSENT_ERRNOS = frozenset({errno.ENOENT})

#: The typed node vocabulary this owner shares with the storage owner.
NODE_SYMLINK_NAME = "symlink"

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ..storage.outcome import MutationLedger as MutationLedgerT
    from ..storage.outcome import MutationOutcome as MutationOutcomeT
else:  # pragma: no cover - the alias is only a name for signatures
    MutationOutcomeT = "MutationOutcome"
    MutationLedgerT = "MutationLedger"


#: The one no-follow directory acquisition, owned by ``storage.trust``.  The P7
#: descent and the storage executor's recursions share it deliberately: two
#: copies of a trust primitive is how one of them ends up weaker than the other.
#: Bound at the bottom of this module, for the reason given above.


def _read_regular_file_nofollow(name: str, *, dir_fd: int) -> bytes | None:
    """Read one regular file relative to an authenticated directory identity."""

    flags = (
        os.O_RDONLY
        | os.O_NOFOLLOW
        # Non-blocking for the same reason as the directory open: a planted
        # FIFO must be refused, not waited on.
        | getattr(os, "O_NONBLOCK", 0)
        | getattr(os, "O_CLOEXEC", 0)
    )
    try:
        handle = os.open(name, flags, dir_fd=dir_fd)
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise NamespaceAmbiguity(
            f"{name!r} could not be opened as a plain regular file ({exc.strerror})"
        ) from exc
    try:
        if not stat.S_ISREG(os.fstat(handle).st_mode):
            raise NamespaceAmbiguity(f"{name!r} is not a plain regular file")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(handle, 1 << 20)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    except OSError as exc:
        raise NamespaceAmbiguity(
            f"{name!r} could not be read ({exc.strerror})"
        ) from exc
    finally:
        os.close(handle)


def _descriptor_identity(handle: int) -> dict[str, int]:
    stats = os.fstat(handle)
    return {"device": int(stats.st_dev), "inode": int(stats.st_ino)}


def released_authority_identity(
    generation: int,
    attempt_identity: str,
    state_digest: str,
    proof_digest: str,
) -> str:
    """The exact released authority a destructive action was planned against.

    Root inode, generation-scoped locator, and typed topology already constrain
    *where* an action may act and *what* it may touch. None of them notice a
    state and proof that were both resealed to a different, equally valid
    released authority while exposing the same member names and kinds - so a
    plan made against the old authority would still authorize the new one.

    This value closes that: it is derived from the two owner records that
    actually confer the release, and it rides the existing owner-state binding
    into the plan. It is computed on demand and never persisted.
    """

    return digest(
        {
            "schema": "mdstats.qualification-released-authority.v1",
            "generation": int(generation),
            "attempt_identity": str(attempt_identity),
            "state_digest": str(state_digest),
            "proof_digest": str(proof_digest),
        }
    )


def canonical_generation_name(generation: int) -> str:
    return f"g{int(generation)}"


def parse_canonical_generation(name: str) -> int | None:
    """The generation a reserved ``g*`` namespace names, or ``None``.

    The spelling has to be the exact one the owner produces. ``g01`` is not an
    alias for ``g1``; it is a malformed reserved entry, and treating it as a
    second place to look for state would be one more namespace to attack.
    """

    if not name.startswith("g"):
        return None
    digits = name[1:]
    if not digits.isdigit():
        return None
    value = int(digits)
    return value if canonical_generation_name(value) == name else None


def released_attempt_root_locator(generation: int, attempt_identity: str) -> str:
    """The canonical, workspace-portable identity of one attempt's scratch root.

    Scratch belongs to *one* generation namespace, not to every
    ``qualification/g*/attempts/<same name>`` path, and an absolute path is not
    durable identity because relocating or restoring a campaign must not change
    what P7 owns.
    """

    return f"{canonical_generation_name(generation)}/attempts/{attempt_identity}"


@dataclass(frozen=True, slots=True)
class GenerationFacts:
    """What the strict descent authenticated about one generation namespace."""

    generation: int
    root: Path
    has_objects: bool


@dataclass(frozen=True, slots=True)
class QualificationNamespaceSnapshot:
    """One strict, descriptor-bound answer for the whole P7 storage surface.

    Storage asks this once and builds every P7 view from it. The alternative -
    asking for attempt state here and re-listing generations and attempts by
    pathname there - is two namespace resolutions with a window in between, and
    the second one would happily enumerate whatever a substituted ancestor now
    points at.
    """

    generations: tuple[GenerationFacts, ...] = ()
    authorities: tuple[AttemptStateAuthority, ...] = ()


@dataclass(frozen=True, slots=True)
class AttemptStateAuthority:
    """The single strict, root-bound answer about one P7 attempt.

    Either an authenticated state that provably belongs to the attempt root it
    was read from, or an explicit unresolved result naming the root and the
    reason. There is deliberately no third answer and no second reader: a
    permissive parser beside this one could classify an attempt as released
    while the owner graph is simultaneously reporting it as unknown, and the two
    contradictory views would race to decide whether external P5 checkpoints
    stay protected.

    ``root_identity`` is the attempt directory's ``(device, inode)`` as observed
    through the authenticated descriptor. It is what lets a later consequential
    step prove it is acting on the same directory that was certified, rather
    than on whatever now answers to that name.
    """

    attempt_root: Path
    state: "QualificationAttemptState | None" = None
    reason: str = ""
    generation: int | None = None
    root_identity: Mapping[str, int] | None = None
    #: ``(name, kind)`` for every non-infrastructure top-level entry, observed
    #: relative to the authenticated attempt descriptor.  The storage owner
    #: builds its member views from this instead of listing the directory again
    #: by pathname, which would be a second namespace resolution.
    top_level_nodes: tuple[tuple[str, str], ...] = ()
    #: Whether a released-attempt proof record is present at all.  Bounded
    #: reporting says so without parsing the O(node-count) proof.
    proof_present: bool = False
    #: Exact certification, filled in only when the caller asked for it.
    certified: bool = False
    certification_reason: str = ""
    certified_nodes: tuple[tuple[str, str], ...] = ()
    #: The derived identity of the exact released authority - state digest plus
    #: proof digest, bound to this generation and attempt. A plan carries it so
    #: a resealed-but-still-valid authority cannot inherit the old plan's
    #: permission to delete.
    release_authority: str = ""

    @property
    def resolved(self) -> bool:
        return self.state is not None

    @property
    def root_locator(self) -> str:
        """The canonical generation-scoped locator of this attempt's scratch."""

        if self.generation is None:
            return ""
        return released_attempt_root_locator(self.generation, self.attempt_root.name)


def _authenticate_state_bytes(
    attempt_root: Path, raw: bytes, *, generation: int | None, identity: Mapping[str, int] | None
) -> AttemptStateAuthority:
    """Authenticate one attempt's state payload against the root it came from.

    Four things must agree before this state may release anything, and each one
    closes a distinct hole:

    * the persisted ``content_digest`` is present and recomputes exactly. The
      generic deserializer tolerates its absence for compatibility, but a record
      that can release external P5 protection may not be authenticated by a
      digest this process just invented for it;
    * ``state.attempt_identity`` equals the directory name, so a digest-valid
      state copied over another attempt is not accepted as that attempt's;
    * ``state.attempt_identity`` equals the canonical identity derived from
      ``state.binding_digest``. The directory name is not independent semantic
      authority: P7 derives attempt identity from the qualification binding, and
      a state whose binding says it belongs elsewhere is not this attempt's
      state no matter what it is filed under.

    Reconstruction is **total over expected persisted-record corruption**. A
    syntactically valid object missing a required field, or carrying a wrong
    container type, is unresolved authority - never an exception escaping the
    owner boundary, because the retention fence consults this while an
    observational `storage report` is still being built and that report is
    exactly what has to keep working.
    """

    def _unresolved(reason: str) -> AttemptStateAuthority:
        return AttemptStateAuthority(
            attempt_root, None, reason, generation=generation, root_identity=identity
        )

    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        return _unresolved(f"attempt state is unusable: {exc}")
    if not isinstance(payload, Mapping):
        return _unresolved("attempt state is not an object")
    recorded_digest = payload.get("content_digest")
    if not recorded_digest:
        return _unresolved(
            "attempt state carries no persisted content digest, so nothing "
            "authenticates it"
        )
    try:
        state = QualificationAttemptState.from_dict(payload)
    except (
        KeyError,
        TypeError,
        ValueError,
        TrainingDataSerializationError,
        TrainingDataInputError,
    ) as exc:
        return _unresolved(f"attempt state is unusable: {exc!r}")
    if str(recorded_digest) != state.content_digest:
        return _unresolved(
            "attempt state does not authenticate against its own digest"
        )
    if state.attempt_identity != attempt_root.name:
        return _unresolved(
            "attempt state belongs to a different attempt identity than the "
            "directory it was read from"
        )
    if state.attempt_identity != _expected_attempt_identity(state.binding_digest):
        return _unresolved(
            "attempt identity is not the canonical identity of the qualification "
            "binding this state names; the directory name is not independent "
            "authority"
        )
    return AttemptStateAuthority(
        attempt_root,
        state,
        "attempt state authenticated",
        generation=generation,
        root_identity=identity,
    )


def _authenticate_attempt_from_descriptor(
    attempt_root: Path, attempt_fd: int, generation: int
) -> AttemptStateAuthority:
    identity = _descriptor_identity(attempt_fd)
    try:
        raw = _read_regular_file_nofollow(ATTEMPT_STATE_FILENAME, dir_fd=attempt_fd)
    except NamespaceAmbiguity as exc:
        return AttemptStateAuthority(
            attempt_root, None, str(exc), generation=generation, root_identity=identity
        )
    if raw is None:
        return AttemptStateAuthority(
            attempt_root,
            None,
            "attempt state is missing",
            generation=generation,
            root_identity=identity,
        )
    return _authenticate_state_bytes(
        attempt_root, raw, generation=generation, identity=identity
    )


def _observe_attempt_nodes_from_descriptor(
    attempt_fd: int, attempt_root: Path
) -> tuple[tuple[dict[str, str], ...] | None, str]:
    """Every non-infrastructure descendant, observed from the attempt descriptor.

    Nothing here re-resolves a pathname. Each directory is entered through a
    no-follow open relative to the parent descriptor that was already
    authenticated, so the typed node set this returns is provably the one that
    lives under the attempt root the caller holds open - not the one under
    whatever answers to that name now.

    Symlinks and special nodes are reported as themselves so the caller can
    refuse them; a nested mount is reported as an unowned node because a
    descriptor-safe descent still does not make a foreign filesystem ours.
    """

    from ..storage.owners import crosses_mount_boundary_at

    observed: list[dict[str, str]] = []
    stack: list[tuple[int, str, bool]] = [(attempt_fd, "", False)]
    owned: list[int] = []
    try:
        while stack:
            handle, relative, _ = stack.pop()
            try:
                entries = sorted(os.scandir(handle), key=lambda item: item.name)
            except OSError as exc:
                return None, (
                    f"{attempt_root / relative if relative else attempt_root} could "
                    f"not be enumerated: {exc}"
                )
            for entry in entries:
                if not relative and (
                    entry.name in ATTEMPT_INFRASTRUCTURE_NAMES
                    # Advisory locks this owner's publication primitive leaves
                    # beside its own top-level records.
                    or entry.name.endswith(".lock")
                ):
                    continue
                child = f"{relative}/{entry.name}" if relative else entry.name
                if entry.is_symlink():
                    observed.append({"path": child, "kind": "symlink"})
                    continue
                if entry.is_dir(follow_symlinks=False):
                    crossed, _detail = crosses_mount_boundary_at(
                        handle, entry.name, attempt_root / child
                    )
                    if crossed:
                        observed.append({"path": child, "kind": "mount"})
                        continue
                    observed.append({"path": child, "kind": "directory"})
                    try:
                        child_fd = _open_directory_nofollow(entry.name, dir_fd=handle)
                    except FileNotFoundError:
                        continue
                    except NamespaceAmbiguity as exc:
                        return None, f"{attempt_root / child}: {exc}"
                    owned.append(child_fd)
                    stack.append((child_fd, child, False))
                    continue
                if entry.is_file(follow_symlinks=False):
                    observed.append({"path": child, "kind": "file"})
                    continue
                observed.append({"path": child, "kind": "special"})
    finally:
        for handle in owned:
            os.close(handle)
    return tuple(sorted(observed, key=lambda item: item["path"])), "observed"


def _certify_attempt_from_descriptor(
    attempt_fd: int,
    attempt_root: Path,
    generation: int,
    state: "QualificationAttemptState",
) -> tuple[bool, str, tuple[tuple[str, str], ...], Mapping[str, Any] | None]:
    """Exact released-attempt certification, entirely from the open attempt.

    The proof is read relative to ``attempt_fd`` and the generation-scoped root
    locator is recomputed from ``generation``, which came from the authenticated
    descent - not from ``root.parent.parent.name``, which would be an
    independent name lookup and therefore a second authority.
    """

    try:
        raw = _read_regular_file_nofollow(
            ATTEMPT_MEMBER_MANIFEST_FILENAME, dir_fd=attempt_fd
        )
    except NamespaceAmbiguity as exc:
        return False, f"the released-attempt proof could not be read: {exc}", (), None
    if raw is None:
        return False, "the released-attempt proof is missing", (), None
    proof, why = validate_attempt_member_proof_bytes(raw)
    if proof is None:
        return False, why, (), None
    bound, why = _proof_binds_state(proof, state, generation, attempt_root.name)
    if not bound:
        return False, why, (), None

    observed, observe_why = _observe_attempt_nodes_from_descriptor(
        attempt_fd, attempt_root
    )
    if observed is None:
        return False, observe_why, (), None
    # The proof is an *upper bound* on what P7 authored, not a requirement that
    # every recorded node still exists: an earlier action in this cleanup, or an
    # interrupted prior one, legitimately shrinks the live tree. So every
    # observed node must be recorded with the exact kind, and recorded nodes that
    # are gone are simply gone.
    recorded = {item["path"]: item["kind"] for item in proof["nodes"]}
    contradictions: list[str] = []
    for item in observed:
        expected = recorded.get(item["path"])
        if expected is None:
            contradictions.append(f"{item['path']} ({item['kind']} P7 did not write)")
        elif expected != item["kind"]:
            contradictions.append(
                f"{item['path']} (recorded {expected}, found {item['kind']})"
            )
    if contradictions:
        return (
            False,
            (
                "released attempt contains descendant(s) P7 did not write: "
                f"{contradictions[:5]}"
            ),
            (),
            proof,
        )
    return (
        True,
        (
            "released attempt whose nodes all belong to the typed set P7 recorded "
            f"when it became {state.state}"
        ),
        tuple(sorted((item["path"], item["kind"]) for item in proof["nodes"])),
        proof,
    )


def _proof_binds_state(
    proof: Mapping[str, Any],
    state: "QualificationAttemptState",
    generation: int,
    attempt_name: str,
) -> tuple[bool, str]:
    """Every cross-field relation that ties a proof to one released state."""

    expected_locator = released_attempt_root_locator(generation, attempt_name)
    if str(proof["attempt_root"]) != expected_locator:
        return False, (
            "the released-attempt proof binds root "
            f"{proof['attempt_root']!r} but this scratch lives at "
            f"{expected_locator!r}; it was copied rather than published here"
        )
    if str(proof["state_digest"]) != state.content_digest:
        return False, (
            "the released-attempt proof binds a different attempt state than the one "
            "currently published; it grants no authority"
        )
    if str(proof["attempt_identity"]) != state.attempt_identity:
        return False, "the released-attempt proof binds a different attempt"
    if str(proof["released_state"]) != state.state:
        return False, (
            "the released-attempt proof was published for a different released state"
        )
    if str(proof["binding_digest"]) != state.binding_digest:
        return False, (
            "the released-attempt proof binds a different qualification binding than "
            "the state it claims to certify"
        )
    if str(proof["publication_digest"]) != state.publication_digest:
        return False, (
            "the released-attempt proof binds a different publication than the state "
            "it claims to certify"
        )
    return True, "released-attempt proof authenticated against its bound state"


def open_attempt_namespace(
    paths: Any, attempt_root: str | os.PathLike[str]
) -> tuple[int | None, str]:
    """Re-acquire one attempt directory through the continuous no-follow descent.

    Returns an open descriptor for the authenticated attempt root, or ``None``
    with a reason. The caller owns closing it. This is what a consequential step
    uses to prove it is still acting on the directory that was certified, rather
    than trusting a pathname a moment later.
    """

    root = Path(attempt_root)
    generation = parse_canonical_generation(root.parent.parent.name)
    if root.parent.name != "attempts" or generation is None:
        return None, f"{root} is not a canonical P7 attempt namespace path"
    internal = _internal_root(paths)
    family_fd = None
    generation_fd = None
    attempts_fd = None
    try:
        internal_fd = _open_directory_nofollow(str(internal))
    except (FileNotFoundError, NamespaceAmbiguity) as exc:
        return None, f"campaign internal root is unavailable: {exc}"
    outcome: str = "authenticated"
    try:
        family_fd = _open_directory_nofollow(QUALIFICATION_ROOT_NAME, dir_fd=internal_fd)
        generation_fd = _open_directory_nofollow(root.parent.parent.name, dir_fd=family_fd)
        attempts_fd = _open_directory_nofollow("attempts", dir_fd=generation_fd)
        return _open_directory_nofollow(root.name, dir_fd=attempts_fd), "authenticated"
    except FileNotFoundError:
        outcome = "the attempt namespace no longer exists"
        return None, outcome
    except NamespaceAmbiguity as exc:
        outcome = str(exc)
        return None, outcome
    finally:
        # The ancestors are scaffolding for one descent: each is released
        # exactly once, and a close failure here is secondary to whatever this
        # acquisition already decided - the authenticated attempt descriptor it
        # is handing back, or the namespace refusal the caller will record.
        for handle in (attempts_fd, generation_fd, family_fd, internal_fd):
            if handle is not None:
                release_descriptor_behind(handle, root, outcome)


def _internal_root(workspace_or_paths: Any) -> Path:
    return (
        Path(workspace_or_paths.internal)
        if hasattr(workspace_or_paths, "internal")
        else Path(workspace_or_paths) / ".mdstats"
    )


def authenticate_attempt_state(
    attempt_root: str | os.PathLike[str],
) -> AttemptStateAuthority:
    """Authenticate the state at one attempt root, by path.

    Kept for callers that already hold an attempt root and are not walking the
    namespace. The descent below it is still no-follow, but a caller that needs
    the *continuous* guarantee should use :func:`iter_attempt_state_authorities`
    or :func:`open_attempt_namespace`.
    """

    root = Path(attempt_root)
    generation = parse_canonical_generation(root.parent.parent.name)
    try:
        attempt_fd = _open_directory_nofollow(str(root))
    except FileNotFoundError:
        return AttemptStateAuthority(root, None, "attempt root is missing")
    except NamespaceAmbiguity as exc:
        return AttemptStateAuthority(root, None, str(exc))
    try:
        return _authenticate_attempt_from_descriptor(root, attempt_fd, generation)
    finally:
        os.close(attempt_fd)


def observe_qualification_namespace(
    workspace_or_paths: Any, *, certify: bool = False
) -> QualificationNamespaceSnapshot:
    """The one strict P7 storage-facing namespace observation.

    The descent is **continuous and descriptor-relative** from the accepted
    campaign internal root: qualification family, canonical ``g<generation>``,
    the literal ``attempts`` container, then each attempt directory. Every hop
    is opened with ``O_DIRECTORY|O_NOFOLLOW`` relative to the descriptor of the
    parent that was already authenticated, so an ancestor replaced between two
    steps cannot be traversed. A pre-check followed by a fresh path lookup would
    be two resolutions with a window in between; this is one.

    Everything storage needs comes back from this single pass - generation
    facts, attempt state, top-level scratch topology, and (when ``certify`` is
    set) the exact released-attempt proof and its certified node set. Rebuilding
    any of it afterwards from ``Path``/``iterdir``/``glob`` would reopen exactly
    the resolution this closed, one level later.

    Enumeration is by actual attempt *directory*, not by state file: an attempt
    directory with no state at all is precisely the case whose external
    references are unknown, and a state-file glob would not see it.

    Absence and ambiguity are different answers. A genuinely absent family or
    ``attempts`` container is ordinary "nothing here"; a present component that
    cannot be authenticated - substituted, wrong kind, unreadable, stale - is
    unresolved authority.
    """

    internal = _internal_root(workspace_or_paths)
    family = internal / QUALIFICATION_ROOT_NAME
    try:
        internal_fd = _open_directory_nofollow(str(internal))
    except FileNotFoundError:
        return QualificationNamespaceSnapshot()
    except NamespaceAmbiguity as exc:
        return QualificationNamespaceSnapshot(
            authorities=(
                AttemptStateAuthority(internal, None, f"campaign internal root: {exc}"),
            )
        )
    generations: list[GenerationFacts] = []
    results: list[AttemptStateAuthority] = []
    try:
        try:
            family_fd = _open_directory_nofollow(
                QUALIFICATION_ROOT_NAME, dir_fd=internal_fd
            )
        except FileNotFoundError:
            return QualificationNamespaceSnapshot()
        except NamespaceAmbiguity as exc:
            return QualificationNamespaceSnapshot(
                authorities=(
                    AttemptStateAuthority(
                        family, None, f"qualification family root: {exc}"
                    ),
                )
            )
        try:
            try:
                entries = sorted(os.scandir(family_fd), key=lambda item: item.name)
            except OSError as exc:
                return QualificationNamespaceSnapshot(
                    authorities=(
                        AttemptStateAuthority(
                            family,
                            None,
                            f"qualification family root could not be enumerated: {exc}",
                        ),
                    )
                )
            for entry in entries:
                if not entry.name.startswith("g"):
                    continue
                generation_root = family / entry.name
                generation = parse_canonical_generation(entry.name)
                if generation is None:
                    results.append(
                        AttemptStateAuthority(
                            generation_root,
                            None,
                            "reserved generation namespace does not use the owner's "
                            "canonical spelling; it is an integrity problem, not "
                            "another place to look for state",
                        )
                    )
                    continue
                facts, authorities = _observe_generation(
                    family_fd, family, entry.name, generation, certify
                )
                if facts is not None:
                    generations.append(facts)
                results.extend(authorities)
        finally:
            os.close(family_fd)
    finally:
        os.close(internal_fd)
    return QualificationNamespaceSnapshot(
        generations=tuple(generations), authorities=tuple(results)
    )


def iter_attempt_state_authorities(
    workspace_or_paths: Any,
) -> tuple[AttemptStateAuthority, ...]:
    """Strictly authenticate every attempt in the P7 owner namespace."""

    return observe_qualification_namespace(workspace_or_paths).authorities


def _observe_generation(
    family_fd: int, family: Path, name: str, generation: int, certify: bool
) -> tuple[GenerationFacts | None, list[AttemptStateAuthority]]:
    generation_root = family / name
    try:
        generation_fd = _open_directory_nofollow(name, dir_fd=family_fd)
    except FileNotFoundError:
        # Enumerated a moment ago and gone now: the namespace changed while it
        # was being observed, which is not the same as never having been there.
        return None, [
            AttemptStateAuthority(
                generation_root,
                None,
                "generation namespace disappeared between enumeration and "
                "authentication; the namespace changed during observation",
            )
        ]
    except NamespaceAmbiguity as exc:
        return None, [
            AttemptStateAuthority(
                generation_root, None, f"generation namespace: {exc}"
            )
        ]
    results: list[AttemptStateAuthority] = []
    attempts_root = generation_root / "attempts"
    try:
        has_objects = _child_is_directory(generation_fd, "objects")
        facts = GenerationFacts(
            generation=generation, root=generation_root, has_objects=has_objects
        )
        try:
            attempts_fd = _open_directory_nofollow("attempts", dir_fd=generation_fd)
        except FileNotFoundError:
            return facts, results
        except NamespaceAmbiguity as exc:
            return facts, [
                AttemptStateAuthority(
                    attempts_root, None, f"attempts container: {exc}"
                )
            ]
        try:
            try:
                attempts = sorted(os.scandir(attempts_fd), key=lambda item: item.name)
            except OSError as exc:
                return facts, [
                    AttemptStateAuthority(
                        attempts_root,
                        None,
                        f"attempts container could not be enumerated: {exc}",
                    )
                ]
            for attempt in attempts:
                attempt_root = attempts_root / attempt.name
                try:
                    attempt_fd = _open_directory_nofollow(
                        attempt.name, dir_fd=attempts_fd
                    )
                except FileNotFoundError:
                    results.append(
                        AttemptStateAuthority(
                            attempt_root,
                            None,
                            "attempt directory disappeared between enumeration and "
                            "authentication; the namespace changed during observation",
                            generation=generation,
                        )
                    )
                    continue
                except NamespaceAmbiguity as exc:
                    results.append(
                        AttemptStateAuthority(
                            attempt_root, None, str(exc), generation=generation
                        )
                    )
                    continue
                try:
                    results.append(
                        _observe_attempt(
                            attempt_root, attempt_fd, generation, certify
                        )
                    )
                finally:
                    os.close(attempt_fd)
        finally:
            os.close(attempts_fd)
        return facts, results
    finally:
        os.close(generation_fd)


def _child_is_directory(parent_fd: int, name: str) -> bool:
    """Whether ``name`` is a plain directory under an authenticated parent."""

    try:
        handle = _open_directory_nofollow(name, dir_fd=parent_fd)
    except (FileNotFoundError, NamespaceAmbiguity):
        return False
    os.close(handle)
    return True


def _observe_attempt(
    attempt_root: Path, attempt_fd: int, generation: int, certify: bool
) -> AttemptStateAuthority:
    """Authenticate one attempt and collect everything storage needs from it."""

    authority = _authenticate_attempt_from_descriptor(
        attempt_root, attempt_fd, generation
    )
    top_level: list[tuple[str, str]] = []
    proof_present = False
    try:
        entries = sorted(os.scandir(attempt_fd), key=lambda item: item.name)
    except OSError:
        entries = []
    for entry in entries:
        if entry.name == ATTEMPT_MEMBER_MANIFEST_FILENAME:
            proof_present = not entry.is_symlink() and entry.is_file(
                follow_symlinks=False
            )
        if entry.name in ATTEMPT_INFRASTRUCTURE_NAMES or entry.name.endswith(".lock"):
            continue
        if entry.is_symlink():
            kind = NODE_SYMLINK_NAME
        elif entry.is_dir(follow_symlinks=False):
            kind = "directory"
        elif entry.is_file(follow_symlinks=False):
            kind = "file"
        else:
            kind = "special"
        top_level.append((entry.name, kind))
    authority = replace(
        authority,
        top_level_nodes=tuple(sorted(top_level)),
        proof_present=proof_present,
    )
    if not certify or authority.state is None:
        return authority
    certified, why, nodes, proof = _certify_attempt_from_descriptor(
        attempt_fd, attempt_root, generation, authority.state
    )
    return replace(
        authority,
        certified=certified,
        certification_reason=why,
        certified_nodes=nodes,
        release_authority=(
            released_authority_identity(
                generation,
                authority.state.attempt_identity,
                authority.state.content_digest,
                str(proof["content_digest"]),
            )
            if certified and proof is not None
            else ""
        ),
    )


def iter_attempt_state_census(
    workspace_or_paths: Any,
) -> tuple[tuple[QualificationAttemptState, ...], tuple[tuple[str, str], ...]]:
    """``(states, unresolved)`` derived from the one strict authority above."""

    authorities = iter_attempt_state_authorities(workspace_or_paths)
    states = tuple(item.state for item in authorities if item.state is not None)
    unresolved = tuple(
        (str(item.attempt_root), item.reason) for item in authorities if not item.resolved
    )
    return states, unresolved


@dataclass
class QualificationRetentionFence:
    """Deletion-authority reduction for durable P7 evidence and active attempts.

    Two different things are protected for two different reasons.  Durable
    qualification evidence is *release* evidence and is never reconstructible
    scratch, so the object store is protected outright.  Artifacts an active
    attempt still references are protected because reclaiming them mid-run would
    invalidate an expensive qualification that is still legitimately in flight.
    Terminal and aborted attempts protect nothing beyond the evidence itself.

    There is a third, deliberately blunt state. When *any* attempt state cannot
    be strictly authenticated, the set of artifacts an attempt may have been
    pinning is unknown - and those references routinely name P5 publication
    checkpoints far outside the P7 tree. Protecting only the qualification
    family would therefore leave the very asset whose identity is unknown
    authorizable, so the fence denies destructive authorization for every
    campaign-managed path until the state is repaired. It is a reduction only:
    it never grants ownership or deletion authority to anything.
    """

    qualification_roots: tuple[Path, ...]
    referenced_paths: frozenset[str]
    #: True while some attempt state could not be authenticated.
    ambiguous_attempt_state: bool = False
    #: A bounded, truthful account of why, for reporting.
    ambiguity_reasons: tuple[str, ...] = ()

    @property
    def is_active(self) -> bool:
        return bool(
            self.qualification_roots
            or self.referenced_paths
            or self.ambiguous_attempt_state
        )

    def protects(self, path: str | os.PathLike[str]) -> tuple[bool, str]:
        candidate = Path(os.path.abspath(os.fspath(path)))
        if self.ambiguous_attempt_state:
            reason = self.ambiguity_reasons[0] if self.ambiguity_reasons else "unknown"
            return True, (
                "a P7 qualification attempt state cannot be authenticated, so the "
                "artifacts it may still reference are unknown and no campaign-managed "
                f"path is destructively authorized until it is repaired ({reason})"
            )
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

    internal = _internal_root(workspace_or_paths)
    root = internal.resolve() / QUALIFICATION_ROOT_NAME
    # The fence is a *reduction*, so it has to survive a family root it cannot
    # even look at. An unreadable or substituted root is exactly the case where
    # nothing may be authorized, and a raised OSError here would instead take
    # the whole observational path - including `storage report` - down with it.
    unreadable: list[str] = []
    try:
        generation_roots = (
            tuple(sorted(path for path in root.glob("g*") if path.is_dir()))
            if root.is_dir()
            else ()
        )
        reveal_root = root / LOCKED_REVEAL_DIRECTORY
        roots = generation_roots + ((reveal_root,) if reveal_root.is_dir() else ())
    except OSError as exc:
        roots = (root,)
        unreadable.append(f"{root}: qualification family root is unreadable ({exc})")
    referenced: set[str] = set()
    states, unresolved = iter_attempt_state_census(workspace_or_paths)
    unresolved = tuple(unresolved) + tuple(
        (str(root), reason.split(": ", 1)[-1]) for reason in unreadable
    )
    for state in states:
        if state.is_active:
            referenced.update(state.referenced_paths)
    # Defense in depth for the same ambiguity the owner graph reports, and it
    # has to be *workspace-wide*. The references an unauthenticated attempt
    # would have named are exactly what cannot be recovered, and they commonly
    # point at P5 publication checkpoints far outside the P7 tree - so widening
    # only to `.mdstats/qualification` would leave the very asset whose identity
    # is unknown authorizable. The fence only ever denies; it grants nothing.
    return QualificationRetentionFence(
        qualification_roots=roots,
        referenced_paths=frozenset(referenced),
        ambiguous_attempt_state=bool(unresolved),
        ambiguity_reasons=tuple(
            f"{path}: {reason}" for path, reason in unresolved[:5]
        ),
    )


__all__ = [
    "ATTEMPT_ABORTED",
    "ATTEMPT_ACTIVE",
    "ATTEMPT_INFRASTRUCTURE_NAMES",
    "ATTEMPT_MEMBER_MANIFEST_FILENAME",
    "ATTEMPT_MEMBER_MANIFEST_SCHEMA",
    "ATTEMPT_MEMBER_MANIFEST_SCHEMA_V2",
    "ATTEMPT_STATE_FILENAME",
    "ATTEMPT_TERMINAL",
    "POINTER_KINDS",
    "POINTER_LOCKED_ACTIVATION",
    "PUBLICATION_BARRIER_NAME",
    "POINTER_QUALIFICATION_PLAN",
    "POINTER_QUALIFICATION_RECORD",
    "POINTER_RELEASE_EVIDENCE",
    "QUALIFICATION_ATTEMPT_STATE_SCHEMA",
    "QUALIFICATION_ROOT_NAME",
    "QualificationAttemptState",
    "QualificationEvidenceStore",
    "LOCKED_REVEAL_DIRECTORY",
    "QualificationRetentionFence",
    "acquire_attempt_reference",
    "attempt_root",
    "attempt_state_lock_at",
    "attempt_state_path",
    "build_qualification_retention_fence",
    "find_locked_activation",
    "find_locked_activation_for_role",
    "AttemptStateAuthority",
    "authenticate_attempt_state",
    "ReleasedAttemptSession",
    "SpentCapabilityError",
    "open_released_attempt_session",
    "released_authority_identity",
    "remove_released_attempt_member",
    "dir_fd_mutation_supported",
    "authorize_released_attempt_member",
    "canonical_generation_name",
    "open_attempt_namespace",
    "parse_canonical_generation",
    "released_attempt_root_locator",
    "observe_qualification_namespace",
    "QualificationNamespaceSnapshot",
    "GenerationFacts",
    "validate_attempt_member_proof_bytes",
    "iter_attempt_state_authorities",
    "iter_attempt_state_census",
    "iter_attempt_states",
    "publish_attempt_member_proof",
    "read_attempt_member_proof",
    "read_attempt_state_at",
    "validate_bound_attempt_proof",
    "open_qualification_store",
    "publish_current_qualification_pointer",
    "qualification_record_is_current",
    "qualification_publication_barrier",
    "qualification_root",
    "read_attempt_state",
    "read_current_qualification_pointer",
    "read_locked_reveal",
    "record_locked_reveal",
    "release_attempt_reference",
    "resolve_current_qualification_record",
]


# Owned by ``storage.trust`` so the P7 descent and the storage executor's
# recursions cannot drift apart.  Imported here, at the end, because the storage
# package initializes this module: by now this one is complete.
from ..storage.trust import (  # noqa: E402
    NamespaceAmbiguity,
    dir_fd_mutation_supported,
    open_directory_nofollow as _open_directory_nofollow,
)
