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
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping
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


#: Membership record for one finished attempt's own scratch tree.
#:
#: Attempt-local bulk - the exported deployment, the per-component evidence - is
#: disposable once the attempt is terminal, but "beneath the attempt directory"
#: is containment, not authorship.  A downstream consumer that wants to reclaim
#: that bulk needs this owner to say which descendants it actually produced, so
#: that anything else present withholds authority instead of being deleted with
#: it.  The record is written exactly when the attempt reaches a terminal or
#: aborted state, which is the moment P7 stops writing into the tree.
ATTEMPT_MEMBER_MANIFEST_FILENAME = "attempt-members.json"
ATTEMPT_MEMBER_MANIFEST_SCHEMA = "mdstats.qualification-attempt-members.v1"

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


def _attempt_relative_files(root: Path) -> list[str]:
    """Every regular file under one attempt root, as sorted relative paths."""

    members: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        relative = path.relative_to(root)
        if relative.parts[0] in ATTEMPT_INFRASTRUCTURE_NAMES:
            continue
        if len(relative.parts) == 1 and relative.name.endswith(".lock"):
            # Advisory locks this owner's publication primitive leaves beside
            # its own top-level records.
            continue
        members.append(relative.as_posix())
    return members


def record_attempt_members(attempt_directory: str | os.PathLike[str]) -> Path:
    """Freeze the exact member set this owner produced under one attempt root."""

    root = Path(attempt_directory)
    destination = root / ATTEMPT_MEMBER_MANIFEST_FILENAME
    members = _attempt_relative_files(root)
    _atomic_write_json(
        destination,
        {
            "schema": ATTEMPT_MEMBER_MANIFEST_SCHEMA,
            "attempt_root": root.name,
            "members": members,
            "member_count": len(members),
        },
    )
    return destination


def recorded_attempt_members(
    attempt_directory: str | os.PathLike[str],
) -> tuple[str, ...]:
    """The member set this owner recorded for one attempt root, or empty."""

    path = Path(attempt_directory) / ATTEMPT_MEMBER_MANIFEST_FILENAME
    if not path.is_file():
        return ()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ()
    if payload.get("schema") != ATTEMPT_MEMBER_MANIFEST_SCHEMA:
        return ()
    return tuple(sorted(str(item) for item in payload.get("members", ())))


def certify_closed_attempt_member(
    attempt_directory: str | os.PathLike[str], member_name: str
) -> tuple[bool, str, tuple[str, ...]]:
    """Whether P7 certifies every descendant of one attempt-local member.

    Returns the certification, a truthful detail, and the recorded member paths
    relative to ``member_name`` itself, which is what a consumer needs in order
    to act on exactly those files and nothing else.
    """

    root = Path(attempt_directory)
    member = root / member_name
    recorded = recorded_attempt_members(root)
    if not recorded:
        return False, (
            "the attempt recorded no member manifest, so this owner cannot certify "
            "which descendants it produced"
        ), ()
    prefix = f"{member_name}/"
    inside = tuple(
        item[len(prefix) :] for item in recorded if item.startswith(prefix)
    )
    if not member.is_dir() or member.is_symlink():
        return False, f"{member} is not a plain directory", ()
    observed = {
        path.relative_to(member).as_posix()
        for path in member.rglob("*")
        if path.is_file() and not path.is_symlink()
    }
    extra = sorted(observed - set(inside))
    if extra:
        return False, (
            f"attempt member contains descendant(s) P7 did not write: {extra[:5]}"
        ), ()
    # A recorded member that is absent has legitimately left the tree; the
    # guarantee is that nothing foreign is present, not that nothing is gone.
    return True, (
        "released attempt-local member whose descendants all belong to the set P7 "
        "recorded when the attempt became terminal"
    ), inside


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
        # than changing timestamps or downgrading it to aborted.
        if existing.state == ATTEMPT_TERMINAL:
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
        # moment at which its membership can be recorded truthfully. Recording
        # it before the state write keeps the manifest a precondition of the
        # released state rather than a promise made after it.
        record_attempt_members(state_path.parent)
        _atomic_write_json(state_path, state.to_dict())
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
    generation_roots = (
        tuple(sorted(path for path in root.glob("g*") if path.is_dir()))
        if root.is_dir()
        else ()
    )
    reveal_root = root / LOCKED_REVEAL_DIRECTORY
    roots = generation_roots + ((reveal_root,) if reveal_root.is_dir() else ())
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
    "ATTEMPT_INFRASTRUCTURE_NAMES",
    "ATTEMPT_MEMBER_MANIFEST_FILENAME",
    "ATTEMPT_MEMBER_MANIFEST_SCHEMA",
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
    "certify_closed_attempt_member",
    "record_attempt_members",
    "recorded_attempt_members",
    "attempt_state_path",
    "build_qualification_retention_fence",
    "find_locked_activation",
    "find_locked_activation_for_role",
    "iter_attempt_states",
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
