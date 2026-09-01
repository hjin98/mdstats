"""V7-native post-production qualification and immutable release evidence.

This package consumes the accepted P1-P6 product.  It authenticates the frozen
final-production publication through the real predecessor owner, binds the exact
executable, environment, and specification identities that make a qualification
claim meaningful, executes deployment/physical/relaxation/dynamics/calibration
components against that exact product, and - only after an explicit one-shot
activation - the reserved locked interpolation test.

It owns no selection authority of any kind.  A failure here rejects the exact
published product; it never reaches back into target-size selection,
cross-validation acceptance, production training, or publication membership.
"""

from .binding import (
    EvidenceRoleMembership,
    QualificationInputBinding,
    resolve_evidence_role_membership,
)
from .commands import (
    QUALIFICATION_STAGE,
    execute_qualification_activate_locked,
    execute_qualification_run,
    execute_qualification_status,
)
from .components import (
    ALL_COMPONENTS,
    COMPONENT_CALIBRATION,
    COMPONENT_DEPLOYMENT_PARITY,
    COMPONENT_DYNAMICS,
    COMPONENT_LOCKED_TEST,
    COMPONENT_PHYSICAL_PES,
    COMPONENT_RELAXATION,
    NONLOCKED_COMPONENTS,
    ComponentStatus,
    QualificationComponentEvidence,
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
    executable_source_tree_digest,
    resolve_executable_candidate_identity,
)
from .locked import LockedActivationRecord
from ..post_selection_reclosure import (
    PREDECESSOR_RECLOSURE_SCHEMA,
    PredecessorReclosureRecord,
    resolve_current_predecessor_reclosure,
)
from .plan import (
    PhysicalValidationBase,
    PhysicalValidationPlan,
    ProductionQualificationPlan,
    build_physical_validation_plan,
)
from .publication import (
    AuthenticatedFinalPublication,
    PublishedProductionMember,
    resolve_authenticated_final_publication,
)
from .record import (
    ComponentOutcome,
    ProductionQualificationRecord,
    QualificationVerdict,
    ReleaseEvidenceIndex,
)
from .reference import (
    AuthenticatedReferenceBundle,
    PhysicalReferenceRequest,
    ReferenceObservation,
    build_physical_reference_request,
    load_reference_bundle,
    write_reference_bundle,
)
from .runtime import (
    QualificationSession,
    activate_locked_test,
    build_qualification_session,
    resolve_current_locked_activation,
    resolve_current_qualification_plan,
    resolve_current_qualification_verdict,
    resolve_current_release_evidence,
    run_qualification,
)
from .runtime_capability import LammpsRuntimeProbe, probe_lammps_runtime
from .spec import resolve_qualification_spec_identity
from .stress import (
    CANONICAL_STRESS_UNITS,
    CANONICAL_VOIGT_ORDER,
    EXTERNAL_STRESS_PROVENANCE_SCHEMA,
    ExternalStressProvenance,
    canonical_stress_from_virial,
    canonical_stress_tensor,
    canonicalize_external_stress,
    normalize_stress_units,
    stress_of,
)
from .store import (
    QualificationAttemptState,
    QualificationEvidenceStore,
    QualificationRetentionFence,
    build_qualification_retention_fence,
    qualification_root,
)

__all__ = [
    "ALL_COMPONENTS",
    "COMPONENT_CALIBRATION",
    "COMPONENT_DEPLOYMENT_PARITY",
    "COMPONENT_DYNAMICS",
    "COMPONENT_LOCKED_TEST",
    "COMPONENT_PHYSICAL_PES",
    "COMPONENT_RELAXATION",
    "NONLOCKED_COMPONENTS",
    "QUALIFICATION_STAGE",
    "AuthenticatedFinalPublication",
    "AuthenticatedReferenceBundle",
    "ComponentOutcome",
    "ComponentStatus",
    "EnvironmentFingerprint",
    "EvidenceRoleMembership",
    "ExecutableCandidateIdentity",
    "LammpsRuntimeProbe",
    "LockedActivationRecord",
    "PhysicalReferenceRequest",
    "PhysicalValidationBase",
    "PhysicalValidationPlan",
    "PREDECESSOR_RECLOSURE_SCHEMA",
    "PredecessorReclosureRecord",
    "ProductionQualificationPlan",
    "ProductionQualificationRecord",
    "PublishedProductionMember",
    "QualificationActivationError",
    "QualificationAttemptState",
    "QualificationComponentEvidence",
    "QualificationError",
    "QualificationEvidenceStore",
    "QualificationInputBinding",
    "QualificationLineageError",
    "QualificationRetentionFence",
    "QualificationSession",
    "QualificationSpecIdentity",
    "QualificationUnavailableError",
    "QualificationVerdict",
    "ReferenceObservation",
    "ReleaseEvidenceIndex",
    "activate_locked_test",
    "canonical_stress_tensor",
    "canonical_stress_from_virial",
    "canonicalize_external_stress",
    "normalize_stress_units",
    "CANONICAL_STRESS_UNITS",
    "CANONICAL_VOIGT_ORDER",
    "EXTERNAL_STRESS_PROVENANCE_SCHEMA",
    "ExternalStressProvenance",
    "build_physical_reference_request",
    "build_physical_validation_plan",
    "build_qualification_retention_fence",
    "build_qualification_session",
    "capture_environment_fingerprint",
    "execute_qualification_activate_locked",
    "execute_qualification_run",
    "execute_qualification_status",
    "executable_source_tree_digest",
    "load_reference_bundle",
    "probe_lammps_runtime",
    "qualification_root",
    "resolve_authenticated_final_publication",
    "resolve_current_locked_activation",
    "resolve_current_predecessor_reclosure",
    "resolve_current_qualification_plan",
    "resolve_current_qualification_verdict",
    "resolve_current_release_evidence",
    "resolve_evidence_role_membership",
    "resolve_executable_candidate_identity",
    "resolve_qualification_spec_identity",
    "run_qualification",
    "stress_of",
    "write_reference_bundle",
]
