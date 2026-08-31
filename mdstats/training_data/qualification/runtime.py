"""The one qualification owner: plan, run, resume, activate, and record.

Qualification is deliberately a single coordinating owner over immutable typed
component evidence, not a second training lifecycle.  It resolves the accepted
predecessor product through P4/P5, freezes one descendant binding, pins the
exact artifacts it needs, executes only what is missing, and reduces the typed
component outcomes into exactly one terminal release verdict.

Nothing in this module can change ``N_selected``, ``T_selected``, CV acceptance,
production membership, or the published member set: it holds a read-only
publication view and there is no code path from a qualification failure back
into selection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
import hashlib
import json

import numpy as np

from .._common import TrainingDataInputError, digest
from ..campaign_post_selection import PostSelectionError
from .binding import (
    EvidenceRoleMembership,
    QualificationInputBinding,
    resolve_evidence_role_membership,
)
from .components import (
    ALL_COMPONENTS,
    COMPONENT_CALIBRATION,
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_DYNAMICS,
    COMPONENT_LOCKED_TEST,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
    ComponentStatus,
    QualificationComponentEvidence,
    build_component_evidence,
)
from .deployment import (
    DeployedEvaluation,
    default_deployment_exporter,
    default_mliap_artifact_builder,
    qualify_deployment_parity,
)
from .errors import (
    QualificationActivationError,
    QualificationError,
    QualificationLineageError,
    QualificationUnavailableError,
)
from .identity import (
    EnvironmentFingerprint,
    ExecutableCandidateIdentity,
    QualificationSpecIdentity,
    capture_environment_fingerprint,
    resolve_executable_candidate_identity,
)
from .locked import (
    LockedActivationRecord,
    build_locked_activation,
    qualify_locked_test,
)
from .plan import ProductionQualificationPlan, build_physical_validation_plan
from .publication import (
    AuthenticatedFinalPublication,
    PublishedProductionMember,
    checkpoint_path_for_member,
    resolve_authenticated_final_publication,
)
from .record import (
    ComponentOutcome,
    ProductionQualificationRecord,
    QualificationVerdict,
    ReleaseEvidenceIndex,
    derive_verdict,
    utc_now,
)
from .reference import (
    PhysicalReferenceRequest,
    build_physical_reference_request,
    load_reference_bundle,
    publish_reference_request,
)
from .runtime_capability import deployed_static_evaluation, execute_lammps_request, write_lammps_data
from .spec import enabled_components, resolve_qualification_spec_identity
from .store import (
    QualificationEvidenceStore,
    POINTER_LOCKED_ACTIVATION,
    POINTER_QUALIFICATION_PLAN,
    POINTER_QUALIFICATION_RECORD,
    POINTER_RELEASE_EVIDENCE,
    acquire_attempt_reference,
    attempt_root,
    open_qualification_store,
    publish_current_qualification_pointer,
    release_attempt_reference,
    resolve_current_qualification_record,
)

#: The independently accepted P1-P6 baseline this qualification descends from.
#: These are audit anchors recorded in release evidence; executable currentness
#: is decided by the source-tree identity, never by a branch head.
ACCEPTED_PREDECESSOR_EXECUTABLE_COMMIT = "f55d59b28c9db890dcb6a3c167a067ef5f37e8a2"
ACCEPTED_PREDECESSOR_EXECUTABLE_TREE = "e9a6d5f9d1a798f07dab88bd56dafcc73fe0e491"
ACCEPTED_PREDECESSOR_EVIDENCE_COMMIT = "82371ecdab5f981255d0853a11477596be2623d3"

COMPONENT_POSITION_DIRECTORY = "components"

DEFAULT_REFERENCE_PROTOCOL = "external-reference-protocol-unset"


def _reference_root(cfg: Mapping[str, Any], paths: Any) -> Path:
    section = cfg.get("qualification", {}) if isinstance(cfg, Mapping) else {}
    reference = section.get("reference", {}) if isinstance(section, Mapping) else {}
    configured = reference.get("root") if isinstance(reference, Mapping) else None
    if configured:
        candidate = Path(str(configured))
        return candidate if candidate.is_absolute() else (Path(paths.config_dir) / candidate)
    return Path(paths.workspace) / "qualification-references"


def _reference_protocol(cfg: Mapping[str, Any]) -> str:
    section = cfg.get("qualification", {}) if isinstance(cfg, Mapping) else {}
    reference = section.get("reference", {}) if isinstance(section, Mapping) else {}
    if isinstance(reference, Mapping) and reference.get("protocol"):
        return str(reference["protocol"])
    return DEFAULT_REFERENCE_PROTOCOL


@dataclass
class QualificationSession:
    """One resolved qualification invocation over one frozen product."""

    context: Any
    publication: AuthenticatedFinalPublication
    binding: QualificationInputBinding
    plan: ProductionQualificationPlan
    store: QualificationEvidenceStore
    attempt_root: Path
    reference_root: Path
    reference_request: PhysicalReferenceRequest
    deployment_exporter: Callable[..., Any] = default_deployment_exporter
    mliap_builder: Callable[..., Path] = default_mliap_artifact_builder
    deployed_evaluator: Callable[..., DeployedEvaluation] | None = None
    dynamics_runner: Callable[..., Mapping[str, Any]] | None = None
    case_workers: int = 1
    _deployment_cache: dict[str, tuple[Path, str]] = field(default_factory=dict, repr=False)

    # -- artifact plumbing ---------------------------------------------------
    def deployed_artifact(self, member: PublishedProductionMember) -> tuple[Path, str]:
        """Build (once per attempt) the exact artifact the runtime executes."""

        if member.member_id in self._deployment_cache:
            return self._deployment_cache[member.member_id]
        root = self.attempt_root / "deployment" / member.member_id
        root.mkdir(parents=True, exist_ok=True)
        source = checkpoint_path_for_member(self.context, member)
        artifact = self.deployment_exporter(
            source,
            root,
            deployment_dtype=self.binding.environment.default_dtype,
            target_head=None,
        )
        deployment_path = root / str(getattr(artifact, "deployment_relative_path", "deployment.model"))
        mliap_path = root / "deployment-mliap.pt"
        self.mliap_builder(deployment_path, mliap_path, head=None)
        sha = hashlib.sha256(mliap_path.read_bytes()).hexdigest()
        self._deployment_cache[member.member_id] = (mliap_path, sha)
        return mliap_path, sha

    def _element_types(self, atoms: Any) -> tuple[str, ...]:
        from ase.data import chemical_symbols

        return tuple(
            chemical_symbols[int(number)]
            for number in sorted({int(v) for v in atoms.get_atomic_numbers()})
        )

    def evaluate_deployed(
        self, member: PublishedProductionMember, atoms_list: Sequence[Any]
    ) -> DeployedEvaluation:
        if self.deployed_evaluator is not None:
            return self.deployed_evaluator(self, member, list(atoms_list))
        artifact_path, sha = self.deployed_artifact(member)
        energies: list[float] = []
        forces: list[np.ndarray] = []
        root = self.attempt_root / "deployed" / member.member_id
        for index, atoms in enumerate(atoms_list):
            energy, force = deployed_static_evaluation(
                atoms,
                artifact_path=artifact_path,
                element_types=self._element_types(atoms),
                working_directory=root / f"probe-{index}",
            )
            energies.append(energy)
            forces.append(force)
        return DeployedEvaluation(
            energies_ev=tuple(energies),
            forces_ev_per_angstrom=tuple(forces),
            artifact_sha256=sha,
            runtime_identity=self.binding.environment.content_digest,
        )

    def run_deployed_dynamics(
        self,
        member: PublishedProductionMember,
        atoms: Any,
        *,
        temperature_kelvin: float,
        velocity_seed: int,
        case_identity: str,
    ) -> Mapping[str, Any]:
        if self.dynamics_runner is not None:
            return self.dynamics_runner(
                self,
                member,
                atoms,
                temperature_kelvin=temperature_kelvin,
                velocity_seed=velocity_seed,
                case_identity=case_identity,
            )
        policy = self.binding.specification.component_policy(COMPONENT_DYNAMICS)
        artifact_path, _sha = self.deployed_artifact(member)
        root = self.attempt_root / "dynamics" / case_identity
        root.mkdir(parents=True, exist_ok=True)
        data_path = root / "case.data"
        elements = self._element_types(atoms)
        write_lammps_data(atoms, data_path, specorder=elements)
        return execute_lammps_request(
            {
                "mode": "dynamics",
                "data_path": str(data_path),
                "artifact_path": str(artifact_path),
                "element_types": list(elements),
                "periodic": bool(np.all(np.asarray(atoms.get_pbc(), dtype=bool))),
                "timestep_femtoseconds": float(policy["timestep_femtoseconds"]),
                "temperature_kelvin": float(temperature_kelvin),
                "velocity_seed": int(velocity_seed),
                "thermostat_damping_femtoseconds": float(policy["thermostat_damping_femtoseconds"]),
                "warmup_steps": int(policy["warmup_steps"]),
                "propagation_steps": int(policy["propagation_steps"]),
                "sample_interval_steps": int(policy["sample_interval_steps"]),
            },
            working_directory=root,
        )

    def map_cases(
        self, function: Callable[[Any], tuple[str, Any]], cases: Sequence[Any]
    ) -> dict[str, Any]:
        """Execute independent cases serially or with bounded concurrency.

        The result is keyed by case identity and therefore identical regardless
        of completion order: concurrency is a scheduling choice with no
        scientific content.
        """

        from ..resources import available_cpu_threads

        # Concurrency is bounded by the campaign's existing resource owner
        # rather than by a qualification-private policy.
        workers = max(1, min(int(self.case_workers), int(available_cpu_threads())))
        if workers == 1 or len(cases) <= 1:
            return dict(function(case) for case in cases)
        from concurrent.futures import ThreadPoolExecutor

        with ThreadPoolExecutor(max_workers=min(workers, len(cases))) as pool:
            return dict(pool.map(function, cases))

    # -- component position records -----------------------------------------
    def _position_path(self, component: str) -> Path:
        root = self.attempt_root / COMPONENT_POSITION_DIRECTORY
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{component}.json"

    def completed_component(self, component: str) -> QualificationComponentEvidence | None:
        path = self._position_path(component)
        if not path.is_file():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        evidence = self.store.get(
            str(payload["evidence_digest"]), QualificationComponentEvidence.from_dict
        )
        if evidence.binding_digest != self.binding.content_digest:
            raise QualificationLineageError(
                "Stored component evidence belongs to a different qualification identity."
            )
        return evidence

    def record_component(self, evidence: QualificationComponentEvidence) -> QualificationComponentEvidence:
        from ..target_size_execution import publish_immutable_json_create_or_verify

        self.store.put(evidence)
        publish_immutable_json_create_or_verify(
            self._position_path(evidence.component),
            {
                "component": evidence.component,
                "binding_digest": self.binding.content_digest,
                "evidence_digest": evidence.content_digest,
            },
            deserializer=lambda payload: _PositionRecord(payload),
        )
        return evidence


class _PositionRecord:
    """Minimal deserializer shim for the create-or-verify position record."""

    def __init__(self, payload: Mapping[str, Any]) -> None:
        self._payload = dict(payload)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._payload)


# ---------------------------------------------------------------------------
# Session construction
# ---------------------------------------------------------------------------


def build_qualification_session(
    cfg: Mapping[str, Any],
    paths: Any,
    campaign_store: Any,
    *,
    inference_evaluator: Any = None,
    trainer: Any = None,
    deployment_exporter: Callable[..., Any] | None = None,
    mliap_builder: Callable[..., Path] | None = None,
    deployed_evaluator: Callable[..., DeployedEvaluation] | None = None,
    dynamics_runner: Callable[..., Mapping[str, Any]] | None = None,
    case_workers: int = 1,
) -> QualificationSession | None:
    """Resolve the current product and freeze one qualification identity.

    ``None`` means the predecessor has not published a final production yet.
    """

    from ..campaign_post_selection_runtime import build_post_selection_context

    context = build_post_selection_context(
        cfg, paths, campaign_store, trainer=trainer, inference_evaluator=inference_evaluator
    )
    publication = resolve_authenticated_final_publication(context)
    if publication is None:
        return None
    specification = resolve_qualification_spec_identity(cfg)
    environment = capture_environment_fingerprint(
        default_dtype=str(context.method_policies.common_training.default_dtype),
        device=str(context.method_policies.device),
    )
    executable = resolve_executable_candidate_identity()
    evidence_roles = resolve_evidence_role_membership(context)
    binding = QualificationInputBinding(
        selected_binding_digest=context.selected.binding.content_digest,
        publication_digest=publication.content_digest,
        publication_member_digest=publication.member_digest,
        executable=executable,
        environment=environment,
        specification=specification,
        evidence_roles=evidence_roles,
    )
    physical_plan = build_physical_validation_plan(
        context, evidence_roles=evidence_roles, specification=specification
    )
    plan = ProductionQualificationPlan(
        binding=binding,
        physical_plan=physical_plan,
        planned_components=enabled_components(specification),
    )
    root = attempt_root(paths, context.selected.binding, binding.attempt_identity)
    reference_root = _reference_root(cfg, paths) / physical_plan.content_digest[:16]
    request = build_physical_reference_request(
        context,
        physical_plan,
        protocol_identity=_reference_protocol(cfg),
        include_relaxed=(
            COMPONENT_RELAXATION in specification.required_components
            or COMPONENT_RELAXATION in specification.optional_components
        ),
    )
    return QualificationSession(
        context=context,
        publication=publication,
        binding=binding,
        plan=plan,
        store=open_qualification_store(paths, context.selected.binding),
        attempt_root=root,
        reference_root=reference_root,
        reference_request=request,
        deployment_exporter=deployment_exporter or default_deployment_exporter,
        mliap_builder=mliap_builder or default_mliap_artifact_builder,
        deployed_evaluator=deployed_evaluator,
        dynamics_runner=dynamics_runner,
        case_workers=case_workers,
    )


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _waiting_evidence(session: QualificationSession, component: str, detail: str) -> QualificationComponentEvidence:
    return build_component_evidence(
        component=component,
        binding=session.binding,
        status=ComponentStatus.WAITING_FOR_REFERENCE,
        reason_code="external_reference_not_supplied",
        detail=detail,
        metrics={"requested_geometry_count": len(session.reference_request.geometries)},
        payload={
            "reference_request_digest": session.reference_request.content_digest,
            "reference_protocol_identity": session.reference_request.protocol_identity,
            "reference_request_path": str(session.reference_root),
        },
    )


def execute_nonlocked_components(
    session: QualificationSession,
) -> tuple[QualificationComponentEvidence, ...]:
    """Run or resume every planned nonlocked component, in dependency order."""

    from .calibration import qualify_calibration
    from .dynamics import qualify_dynamics
    from .physical import qualify_physical_pes
    from .relaxation import qualify_relaxation

    publish_reference_request(session.reference_root, session.reference_request)
    bundle = load_reference_bundle(session.reference_root, session.reference_request)
    results: list[QualificationComponentEvidence] = []
    for component in session.plan.planned_components:
        existing = session.completed_component(component)
        if existing is not None:
            results.append(existing)
            continue
        if component == COMPONENT_DEPLOYMENT_PARITY:
            evidence = qualify_deployment_parity(session)
        elif component == COMPONENT_PHYSICAL_PES:
            evidence = (
                qualify_physical_pes(session, bundle)
                if bundle is not None
                else _waiting_evidence(
                    session,
                    component,
                    "Local PES qualification is waiting for the external reference "
                    f"bundle requested under {session.reference_root!s}.",
                )
            )
        elif component == COMPONENT_RELAXATION:
            evidence = (
                qualify_relaxation(session, bundle)
                if bundle is not None
                else _waiting_evidence(
                    session,
                    component,
                    "Relaxation qualification is waiting for matched external "
                    f"reference relaxations requested under {session.reference_root!s}.",
                )
            )
        elif component == COMPONENT_DYNAMICS:
            evidence = qualify_dynamics(session)
        elif component == COMPONENT_CALIBRATION:
            evidence = qualify_calibration(session)
        else:  # pragma: no cover - enabled_components filters the vocabulary
            raise QualificationError(f"Unsupported qualification component {component!r}.")
        if evidence.status is ComponentStatus.WAITING_FOR_REFERENCE:
            # Waiting is not durable evidence: it is the absence of evidence, and
            # persisting it would make a later supplied reference unreachable.
            results.append(evidence)
            continue
        results.append(session.record_component(evidence))
    return tuple(results)


def _locked_required(session: QualificationSession) -> bool:
    policy = session.binding.specification.component_policy(COMPONENT_LOCKED_TEST)
    return bool(policy["enabled"])


def build_qualification_record(
    session: QualificationSession,
    components: Sequence[QualificationComponentEvidence],
    *,
    locked_activation: LockedActivationRecord | None,
) -> ProductionQualificationRecord:
    outcomes = tuple(
        ComponentOutcome.of(evidence)
        for evidence in components
        if evidence.status is not ComponentStatus.WAITING_FOR_REFERENCE
    ) + tuple(
        ComponentOutcome(
            component=evidence.component,
            status=evidence.status,
            reason_code=evidence.reason_code,
            evidence_digest=evidence.content_digest,
        )
        for evidence in components
        if evidence.status is ComponentStatus.WAITING_FOR_REFERENCE
    )
    verdict, reason = derive_verdict(
        specification=session.binding.specification,
        components=outcomes,
        locked_required=_locked_required(session),
    )
    return ProductionQualificationRecord(
        selected_binding_digest=session.binding.selected_binding_digest,
        binding_digest=session.binding.content_digest,
        publication_digest=session.binding.publication_digest,
        publication_member_digest=session.binding.publication_member_digest,
        plan_digest=session.plan.content_digest,
        specification_digest=session.binding.specification.content_digest,
        environment_digest=session.binding.environment.content_digest,
        executable_digest=session.binding.executable.content_digest,
        predecessor_executable_commit=ACCEPTED_PREDECESSOR_EXECUTABLE_COMMIT,
        predecessor_evidence_commit=ACCEPTED_PREDECESSOR_EVIDENCE_COMMIT,
        components=outcomes,
        locked_activation_digest=(
            None if locked_activation is None else locked_activation.content_digest
        ),
        verdict=verdict,
        reason_code=reason,
        recorded_at=utc_now(),
    )


def publish_qualification_record(
    session: QualificationSession,
    campaign_store: Any,
    paths: Any,
    record: ProductionQualificationRecord,
) -> ProductionQualificationRecord:
    session.store.put(record)
    publish_current_qualification_pointer(
        campaign_store,
        binding=session.context.selected.binding,
        kind=POINTER_QUALIFICATION_RECORD,
        content_digest=record.content_digest,
    )
    session.store.put(session.plan)
    publish_current_qualification_pointer(
        campaign_store,
        binding=session.context.selected.binding,
        kind=POINTER_QUALIFICATION_PLAN,
        content_digest=session.plan.content_digest,
    )
    return record


def publish_release_evidence(
    session: QualificationSession,
    campaign_store: Any,
    record: ProductionQualificationRecord,
    components: Sequence[QualificationComponentEvidence],
) -> ReleaseEvidenceIndex:
    index = ReleaseEvidenceIndex(
        qualification_record_digest=record.content_digest,
        selected_binding_digest=record.selected_binding_digest,
        publication_digest=record.publication_digest,
        publication_member_digest=record.publication_member_digest,
        executable_digest=record.executable_digest,
        specification_digest=record.specification_digest,
        environment_digest=record.environment_digest,
        plan_digest=record.plan_digest,
        component_evidence_digests=tuple(
            evidence.content_digest
            for evidence in components
            if evidence.status is not ComponentStatus.WAITING_FOR_REFERENCE
        ),
        locked_activation_digest=record.locked_activation_digest,
        verdict=record.verdict,
        published_at=utc_now(),
    )
    session.store.put(index)
    publish_current_qualification_pointer(
        campaign_store,
        binding=session.context.selected.binding,
        kind=POINTER_RELEASE_EVIDENCE,
        content_digest=index.content_digest,
    )
    return index


def resolve_current_locked_activation(
    campaign_store: Any, paths: Any, context: Any
) -> LockedActivationRecord | None:
    return resolve_current_qualification_record(
        campaign_store,
        paths,
        context.selected,
        kind=POINTER_LOCKED_ACTIVATION,
        deserializer=LockedActivationRecord.from_dict,
    )


def resolve_current_qualification_verdict(
    campaign_store: Any, paths: Any, context: Any
) -> ProductionQualificationRecord | None:
    return resolve_current_qualification_record(
        campaign_store,
        paths,
        context.selected,
        kind=POINTER_QUALIFICATION_RECORD,
        deserializer=ProductionQualificationRecord.from_dict,
    )


def run_qualification(
    session: QualificationSession, campaign_store: Any, paths: Any
) -> tuple[ProductionQualificationRecord, tuple[QualificationComponentEvidence, ...]]:
    """Execute/resume nonlocked qualification and publish the current record."""

    referenced = [str(checkpoint_path_for_member(session.context, member)) for member in session.publication.members]
    acquire_attempt_reference(
        paths,
        session.context.selected.binding,
        attempt_identity=session.binding.attempt_identity,
        publication_digest=session.binding.publication_digest,
        binding_digest=session.binding.content_digest,
        referenced_paths=referenced,
        detail="nonlocked qualification in progress",
    )
    released = False
    try:
        components = execute_nonlocked_components(session)
        existing_activation = resolve_current_locked_activation(campaign_store, paths, session.context)
        locked_evidence: tuple[QualificationComponentEvidence, ...] = ()
        if existing_activation is not None:
            locked = session.completed_component(COMPONENT_LOCKED_TEST)
            if locked is not None:
                locked_evidence = (locked,)
        record = build_qualification_record(
            session, tuple(components) + locked_evidence, locked_activation=existing_activation
        )
        publish_qualification_record(session, campaign_store, paths, record)
        publish_release_evidence(session, campaign_store, record, tuple(components) + locked_evidence)
        if record.verdict.is_terminal:
            release_attempt_reference(
                paths,
                session.context.selected.binding,
                attempt_identity=session.binding.attempt_identity,
                terminal=True,
                detail=f"terminal verdict {record.verdict.value}",
            )
            released = True
        return record, tuple(components) + locked_evidence
    except BaseException:
        if not released:
            release_attempt_reference(
                paths,
                session.context.selected.binding,
                attempt_identity=session.binding.attempt_identity,
                terminal=False,
                detail="qualification attempt aborted",
            )
        raise


def activate_locked_test(
    session: QualificationSession, campaign_store: Any, paths: Any
) -> tuple[ProductionQualificationRecord, QualificationComponentEvidence]:
    """The only path that opens locked evidence. It is one-shot, by construction."""

    if not _locked_required(session):
        raise QualificationActivationError(
            "The frozen qualification policy disables the locked interpolation test; "
            "there is nothing to activate."
        )
    existing = resolve_current_locked_activation(campaign_store, paths, session.context)
    activation = build_locked_activation(session, prerequisite_component_digests=())
    if existing is not None:
        if existing.cohort_generation_identity == activation.cohort_generation_identity:
            raise QualificationActivationError(
                "The locked interpolation test has already been activated for this "
                "exact publication and locked cohort. A revealed cohort is never a "
                "fresh locked test again."
            )
        raise QualificationActivationError(
            "A locked activation exists for a different product generation; resolve "
            "the current publication before activating a new locked test."
        )

    components = execute_nonlocked_components(session)
    blocking = [
        evidence
        for evidence in components
        if evidence.component in session.binding.specification.required_components
        and not evidence.status.is_terminal_success
    ]
    if blocking:
        raise QualificationActivationError(
            "Locked activation requires every mandatory nonlocked component to have "
            "completed successfully first; currently blocked by "
            f"{[item.component for item in blocking]}."
        )
    activation = build_locked_activation(
        session,
        prerequisite_component_digests=tuple(evidence.content_digest for evidence in components),
    )
    session.store.put(activation)
    publish_current_qualification_pointer(
        campaign_store,
        binding=session.context.selected.binding,
        kind=POINTER_LOCKED_ACTIVATION,
        content_digest=activation.content_digest,
    )
    locked_evidence = session.record_component(qualify_locked_test(session, activation))
    record = build_qualification_record(
        session, tuple(components) + (locked_evidence,), locked_activation=activation
    )
    publish_qualification_record(session, campaign_store, paths, record)
    publish_release_evidence(
        session, campaign_store, record, tuple(components) + (locked_evidence,)
    )
    release_attempt_reference(
        paths,
        session.context.selected.binding,
        attempt_identity=session.binding.attempt_identity,
        terminal=True,
        detail=f"terminal verdict {record.verdict.value}",
    )
    return record, locked_evidence


__all__ = [
    "ACCEPTED_PREDECESSOR_EVIDENCE_COMMIT",
    "ACCEPTED_PREDECESSOR_EXECUTABLE_COMMIT",
    "ACCEPTED_PREDECESSOR_EXECUTABLE_TREE",
    "QualificationSession",
    "activate_locked_test",
    "build_qualification_record",
    "build_qualification_session",
    "execute_nonlocked_components",
    "publish_qualification_record",
    "publish_release_evidence",
    "resolve_current_locked_activation",
    "resolve_current_qualification_verdict",
    "run_qualification",
]
