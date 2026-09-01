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
import os
import shutil
import threading

import numpy as np

from .._common import TrainingDataInputError, TrainingDataSerializationError, digest
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
    reference_request_path,
)
from .runtime_capability import (
    deployed_static_observation,
    execute_lammps_request,
    write_lammps_data,
)
from .resource_scope import resource_scope_digest, resource_scope_payload
from .spec import enabled_components, resolve_qualification_spec_identity
from .store import (
    _atomic_write_json,
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

COMPONENT_POSITION_DIRECTORY = "components"

_DEPLOYMENT_RECEIPT_SCHEMA = "mdstats.qualification-deployment-receipt.v1"


def _callable_identity(function: Callable[..., Any]) -> str:
    """Stable identity of an injected owner/seam, for artifact identity."""

    module = getattr(function, "__module__", "?")
    name = getattr(function, "__qualname__", getattr(function, "__name__", repr(function)))
    return f"{module}.{name}"

DEFAULT_REFERENCE_PROTOCOL = "external-reference-protocol-unset"

_REFERENCE_DEPENDENT_COMPONENTS = frozenset(
    {COMPONENT_PHYSICAL_PES, COMPONENT_RELAXATION, COMPONENT_DYNAMICS}
)


def _config_table(cfg: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = cfg.get(name, {}) if isinstance(cfg, Mapping) else {}
    return value if isinstance(value, Mapping) else {}


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


def _require_explicit_reference_protocol(
    cfg: Mapping[str, Any], specification: QualificationSpecIdentity
) -> str:
    protocol = _reference_protocol(cfg).strip()
    needs_reference = bool(
        _REFERENCE_DEPENDENT_COMPONENTS
        & (set(specification.required_components) | set(specification.optional_components))
    )
    if needs_reference and (
        not protocol or protocol == DEFAULT_REFERENCE_PROTOCOL
        or protocol.lower() in {"unset", "none", "placeholder"}
    ):
        raise QualificationError(
            "Required production reference qualification needs an explicit, non-"
            "placeholder [qualification.reference].protocol identity before the "
            "reference request is published."
        )
    return protocol


def _qualification_resource_scope(
    cfg: Mapping[str, Any], *, device: str, requested_workers: int
) -> tuple[Any, Any, str]:
    """Resolve P7 execution resources through the campaign resource owner."""

    from ..resources import build_stage_resource_scope, detect_system_resources

    performance = cfg.get("performance", {})
    if not isinstance(performance, Mapping):
        performance = {}
    resources = detect_system_resources(
        cpu_fraction=float(performance.get("cpu_fraction", 0.9)),
        ram_fraction=float(performance.get("ram_fraction", 0.8)),
        gpu_memory_fraction=float(performance.get("gpu_memory_fraction", 0.9)),
        device=str(device),
    )
    requested = int(requested_workers)
    if requested < 0:
        raise TrainingDataInputError("qualification case_workers must be zero or positive")
    # ``case_workers`` is an execution-only scheduling cap.  It must not enter
    # the authenticated qualification binding: otherwise a rerun with a
    # different harmless concurrency setting would make the same scientific
    # record unreachable as current.  The stage scope records the stable
    # machine allocation/budget; ``map_cases`` applies the per-invocation
    # requested cap when it resolves the actual pool size.
    python_workers = int(resources.cpu_threads_budget)
    scope = build_stage_resource_scope(
        resources,
        stage_name="post-production-qualification",
        python_workers=max(1, python_workers),
        structural_workers=1,
        tree_workers=1,
        blas_threads=1,
        native_openmp_threads=1,
        pytorch_cpu_workers=1,
        gpu_jobs=1 if bool(resources.gpu.available) else 0,
    )
    return resources, scope, resource_scope_digest(resources, scope)


@dataclass
class QualificationSession:
    """One resolved qualification invocation over one frozen product."""

    context: Any
    publication: AuthenticatedFinalPublication
    predecessor_reclosure: Any
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
    resources: Any | None = None
    resource_scope: Any | None = None
    resource_scope_material: Mapping[str, Any] | None = None
    _deployment_cache: dict[str, tuple[Path, str]] = field(default_factory=dict, repr=False)
    #: Overrides the runtime stress-reporting fact when a bounded seam, rather
    #: than the real runtime, provides deployed observations.
    deployed_stress_supported: bool | None = None
    minimum_free_disk_gib: float = 20.0
    _stress_capabilities: dict[str, Any] = field(default_factory=dict, repr=False)
    _resource_recorder: Any = field(default=None, repr=False)
    _resource_recorder_lock: Any = field(
        default_factory=threading.RLock, init=False, repr=False
    )

    @property
    def resource_recorder(self) -> Any:
        """Accumulates what this attempt actually cost, lazily and once."""

        from .resource_observation import (
            QualificationResourceObservation,
            ResourceObservationRecorder,
            read_resource_observation_pointer,
        )

        if self._resource_recorder is None:
            with self._resource_recorder_lock:
                if self._resource_recorder is None:
                    previous_digest = read_resource_observation_pointer(self.attempt_root)
                    previous = (
                        None
                        if previous_digest is None
                        else self.store.get(
                            previous_digest, QualificationResourceObservation.from_dict
                        )
                    )
                    self._resource_recorder = ResourceObservationRecorder(
                        binding_digest=self.binding.content_digest,
                        attempt_identity=self.binding.attempt_identity,
                        resource_scope_digest=self.binding.resource_scope_digest,
                        workspace=Path(self.context.paths.workspace),
                        attempt_root=self.attempt_root,
                        minimum_free_disk_gib=float(self.minimum_free_disk_gib),
                        device=str(self.context.method_policies.device),
                        runtime_identity_digest=self.binding.environment.content_digest,
                        resource_scope_material=(
                            {}
                            if self.resource_scope_material is None
                            else self.resource_scope_material
                        ),
                        previous_observation=previous,
                        previous_observation_digest=previous_digest,
                    )
                    self._resource_recorder.sample_filesystem("start")
        return self._resource_recorder

    # -- artifact plumbing ---------------------------------------------------
    def deployment_identity(self, member: PublishedProductionMember) -> str:
        """What makes two deployed artifacts the same product, exactly.

        The canonical target head is part of the identity: an artifact exported
        from the replay or foundation head is a different product, not the same
        product serialized differently.
        """

        return digest(
            {
                "schema": "mdstats.qualification-deployment-identity.v1",
                "publication_digest": self.binding.publication_digest,
                "member_id": member.member_id,
                "representative_checkpoint_sha256": member.representative_checkpoint_sha256,
                "target_head_name": member.target_head_name,
                "resource_scope_digest": self.binding.resource_scope_digest,
                "deployment_dtype": self.binding.environment.default_dtype,
                "exporter": _callable_identity(self.deployment_exporter),
                "mliap_builder": _callable_identity(self.mliap_builder),
            }
        )

    def _deployment_root(self, member: PublishedProductionMember) -> Path:
        return self.attempt_root / "deployment" / self.deployment_identity(member)[:16]

    def deployed_artifact(self, member: PublishedProductionMember) -> tuple[Path, str]:
        """Return the exact deployed artifact this member's product executes.

        Construction is create-once under an advisory per-artifact lock, so two
        concurrent dynamics cases for the same member converge on one artifact
        rather than racing to write the same path. Reuse - including after a
        process restart with an empty in-memory cache - is authenticated from
        the durable receipt and the artifact bytes, never from a cache hit: a
        full PyTorch model pickle is not byte-deterministic, so identity has to
        be carried by the receipt rather than inferred from the bytes.
        """

        from ..target_size_execution import artifact_publication_lock

        identity = self.deployment_identity(member)
        cached = self._deployment_cache.get(identity)
        if cached is not None and self._authenticated_artifact(cached[0], cached[1]):
            return cached
        root = self._deployment_root(member)
        self._require_component_disk_reserve(COMPONENT_DEPLOYMENT_PARITY)
        root.mkdir(parents=True, exist_ok=True)
        mliap_path = root / "deployment-mliap.pt"
        receipt_path = root / "deployment-receipt.json"
        with artifact_publication_lock(mliap_path):
            existing = self._reuse_published_artifact(member, identity, mliap_path, receipt_path)
            if existing is not None:
                self._deployment_cache[identity] = existing
                return existing
            sha = self._build_deployment_artifact(member, root, mliap_path)
            _atomic_write_json(
                receipt_path,
                {
                    "schema": _DEPLOYMENT_RECEIPT_SCHEMA,
                    "deployment_identity": identity,
                    "member_id": member.member_id,
                    "representative_checkpoint_sha256": member.representative_checkpoint_sha256,
                    "target_head_name": member.target_head_name,
                    "resource_scope_digest": self.binding.resource_scope_digest,
                    "deployment_dtype": self.binding.environment.default_dtype,
                    "artifact_sha256": sha,
                },
            )
        result = (mliap_path, sha)
        self._deployment_cache[identity] = result
        return result

    def _reuse_published_artifact(
        self,
        member: PublishedProductionMember,
        identity: str,
        mliap_path: Path,
        receipt_path: Path,
    ) -> tuple[Path, str] | None:
        if not (mliap_path.is_file() and receipt_path.is_file()):
            return None
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except ValueError as exc:
            raise QualificationLineageError(
                f"The deployed-artifact receipt at {receipt_path!s} is corrupt."
            ) from exc
        expected = {
            "schema": _DEPLOYMENT_RECEIPT_SCHEMA,
            "deployment_identity": identity,
            "member_id": member.member_id,
            "representative_checkpoint_sha256": member.representative_checkpoint_sha256,
            "target_head_name": member.target_head_name,
            "resource_scope_digest": self.binding.resource_scope_digest,
            "deployment_dtype": self.binding.environment.default_dtype,
        }
        for key, value in expected.items():
            if str(receipt.get(key)) != str(value):
                raise QualificationLineageError(
                    "A published deployed artifact binds a different "
                    f"{key}; it is not this product's artifact."
                )
        sha = str(receipt.get("artifact_sha256", ""))
        if not self._authenticated_artifact(mliap_path, sha):
            raise QualificationLineageError(
                "The deployed artifact bytes changed after publication; "
                "qualification never executes a mutated artifact."
            )
        return mliap_path, sha

    @staticmethod
    def _authenticated_artifact(path: Path, sha: str) -> bool:
        if not path.is_file() or not sha:
            return False
        return hashlib.sha256(path.read_bytes()).hexdigest() == sha

    def _build_deployment_artifact(
        self, member: PublishedProductionMember, root: Path, mliap_path: Path
    ) -> str:
        """Export and convert into scratch, then place the artifact atomically."""

        scratch = root / f".build-{os.getpid()}"
        if scratch.exists():
            shutil.rmtree(scratch, ignore_errors=True)
        scratch.mkdir(parents=True, exist_ok=True)
        try:
            source = checkpoint_path_for_member(self.context, member)
            artifact = self.deployment_exporter(
                source,
                scratch,
                deployment_dtype=self.binding.environment.default_dtype,
                target_head=member.target_head_name,
            )
            deployment_path = scratch / str(
                getattr(artifact, "deployment_relative_path", "deployment.model")
            )
            staged = scratch / "deployment-mliap.pt"
            self.mliap_builder(deployment_path, staged, head=member.target_head_name)
            if not staged.is_file():
                raise QualificationError(
                    "The ML-IAP builder did not produce a deployed artifact."
                )
            sha = hashlib.sha256(staged.read_bytes()).hexdigest()
            os.replace(staged, mliap_path)
            return sha
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

    def _element_types(self, atoms: Any) -> tuple[str, ...]:
        from ase.data import chemical_symbols

        return tuple(
            chemical_symbols[int(number)]
            for number in sorted({int(v) for v in atoms.get_atomic_numbers()})
        )

    def _runtime_launch_options(self) -> dict[str, Any]:
        """Translate the authenticated resource assignment for the worker."""

        gpu = getattr(self.resources, "gpu", None)
        available = bool(getattr(gpu, "available", False))
        selected = getattr(gpu, "selected_device", None)
        device = str(self.context.method_policies.device)
        if selected is None and device.startswith("cuda:"):
            try:
                selected = int(device.split(":", 1)[1])
            except ValueError as exc:
                raise QualificationLineageError(
                    f"The authenticated resource policy has an invalid device {device!r}."
                ) from exc
        gpu_jobs = int(getattr(self.resource_scope, "gpu_jobs", 0) or 0)
        return {
            # This is the allocation actually granted to the stage, not a
            # universal one-GPU assumption.  The worker receives no KOKKOS
            # accelerator flags when the authenticated scope is CPU-only.
            "kokkos_gpu_count": max(0, gpu_jobs) if available else 0,
            "selected_cuda_device": selected if available else None,
        }

    def required_incremental_headroom_bytes(self, component: str) -> int:
        """Return a bounded owner-local write allowance for one component.

        Qualification does not become a global storage scheduler. It reserves
        only enough room for output this attempt can estimate: fixed scratch
        plus two copies of authenticated publication checkpoints for runtime
        and artifact work.
        """

        base = 64 * 1024 * 1024
        if str(component) not in {
            COMPONENT_DEPLOYMENT_PARITY,
            COMPONENT_DYNAMICS,
            COMPONENT_PHYSICAL_PES,
            COMPONENT_RELAXATION,
            COMPONENT_CALIBRATION,
            COMPONENT_LOCKED_TEST,
        }:
            return base
        checkpoint_bytes = 0
        for member in self.publication.members:
            try:
                checkpoint_bytes += max(
                    0,
                    int(checkpoint_path_for_member(self.context, member).stat().st_size),
                )
            except OSError:
                # The retention fence reports a missing checkpoint separately;
                # keep the fixed allowance for this owner-local admission.
                continue
        return max(base, 2 * checkpoint_bytes + base)

    def _require_component_disk_reserve(self, component: str) -> float:
        return self.resource_recorder.require_disk_reserve(
            f"qualification component {component}",
            required_incremental_headroom_bytes=self.required_incremental_headroom_bytes(
                component
            ),
        )

    def evaluate_deployed(
        self,
        member: PublishedProductionMember,
        atoms_list: Sequence[Any],
        *,
        stress_capability: Any | None = None,
    ) -> DeployedEvaluation:
        if self.deployed_evaluator is not None:
            return self.deployed_evaluator(self, member, list(atoms_list))
        artifact_path, sha = self.deployed_artifact(member)
        # Reading stress is worth the extra thermo work only when the resolved
        # capability says this product's stress is comparable through the
        # deployed runtime.  The capability is already resolved by the time the
        # component asks for observations.
        capability = stress_capability
        if capability is None:
            # Standalone owner callers still need the exact member/cohort claim;
            # a cache-key lookup by member id would either miss the digest-keyed
            # cache or accidentally select a decision for another geometry.
            capability = self.stress_capability(
                atoms_list,
                member=member,
                component=COMPONENT_DEPLOYMENT_PARITY,
                claim_kind="deployment",
            )
        include_stress = bool(capability is not None and capability.deployed_comparable)
        energies: list[float] = []
        forces: list[np.ndarray] = []
        stresses: list[np.ndarray | None] = []
        cells: list[np.ndarray] = []
        pbc_values: list[tuple[bool, bool, bool]] = []
        runtime_evidence: list[Mapping[str, Any]] = []
        root = self.attempt_root / "deployed" / member.member_id
        for index, atoms in enumerate(atoms_list):
            observation = deployed_static_observation(
                atoms,
                artifact_path=artifact_path,
                element_types=self._element_types(atoms),
                working_directory=root / f"probe-{index}",
                include_stress=include_stress,
                **self._runtime_launch_options(),
            )
            energies.append(observation.energy)
            forces.append(observation.forces)
            stresses.append(observation.stress)
            cells.append(observation.cell_angstrom)
            pbc_values.append(observation.pbc)
            runtime_evidence.append(observation.runtime_evidence)
        return DeployedEvaluation(
            energies_ev=tuple(energies),
            forces_ev_per_angstrom=tuple(forces),
            artifact_sha256=sha,
            runtime_identity=self.binding.environment.content_digest,
            stresses_ev_per_angstrom3=tuple(stresses),
            cells_angstrom=tuple(cells),
            pbc=tuple(pbc_values),
            runtime_evidence=tuple(runtime_evidence),
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
        capability = self._deployment_stress_capability(member.member_id, atoms)
        artifact_path, _sha = self.deployed_artifact(member)
        root = self.attempt_root / "dynamics" / case_identity
        self._require_component_disk_reserve(COMPONENT_DYNAMICS)
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
                "pbc": [bool(value) for value in np.asarray(atoms.get_pbc(), dtype=bool)],
                "timestep_femtoseconds": float(policy["timestep_femtoseconds"]),
                "temperature_kelvin": float(temperature_kelvin),
                "velocity_seed": int(velocity_seed),
                "thermostat_damping_femtoseconds": float(policy["thermostat_damping_femtoseconds"]),
                "warmup_steps": int(policy["warmup_steps"]),
                "propagation_steps": int(policy["propagation_steps"]),
                "sample_interval_steps": int(policy["sample_interval_steps"]),
                "include_stress": bool(
                    capability is not None and capability.deployed_comparable
                ),
                **self._runtime_launch_options(),
            },
            working_directory=root,
        )

    def stress_capability(
        self,
        atoms_list: Sequence[Any],
        *,
        probe: Sequence[str] = (),
        member: PublishedProductionMember | None = None,
        component: str = COMPONENT_DEPLOYMENT_PARITY,
        claim_kind: str | None = None,
        reference_stress_available: bool | None = None,
        geometry_or_cohort_digest: str | None = None,
        reference_stress_available_by_geometry: Sequence[bool] | None = None,
    ) -> Any:
        """Resolve one immutable stress claim for one member/cohort.

        A session may execute several components and several published members;
        none of those decisions share a mutable singleton.  Omitting ``member``
        is only permitted for the historical one-member convenience API and is
        rejected for a committee so evidence cannot accidentally inherit member
        zero's capability.
        """

        from .providers import member_provider, predict_all, stress_of
        from .runtime_capability import probe_lammps_runtime
        from .stress_capability import resolve_stress_capability

        members = tuple(self.publication.members)
        if member is None:
            if len(members) != 1:
                raise QualificationError(
                    "Stress capability is claim-scoped; a multi-member publication "
                    "must resolve each exact publication member explicitly."
                )
            selected_member = members[0]
        else:
            selected_member = member
            if selected_member.member_id not in {item.member_id for item in members}:
                raise QualificationLineageError(
                    "Stress capability was requested for a member outside the "
                    "authenticated publication."
                )
        atoms = list(atoms_list)
        policy = self.binding.specification.component_policy(str(component))
        geometry_digest = geometry_or_cohort_digest or digest(
            {
                "schema": "mdstats.qualification-stress-geometry.v1",
                "geometries": [
                    {
                        "numbers": [int(value) for value in item.get_atomic_numbers()],
                        "positions": np.asarray(
                            item.get_positions(), dtype=np.float64
                        ).tolist(),
                        "cell": np.asarray(item.get_cell(), dtype=np.float64).tolist(),
                        "pbc": [bool(value) for value in item.get_pbc()],
                    }
                    for item in atoms
                ],
            }
        )
        if (claim_kind or component) == "deployment":
            runtime_reports = bool(
                self.deployed_stress_supported
                if self.deployed_stress_supported is not None
                else True
            )
        else:
            # Physical/reference claims are scientifically independent of the
            # deployment runtime. Their evidence availability is supplied by
            # the authenticated bundle; probing LAMMPS here would let an
            # unrelated runtime outage leak into the physical capability cache.
            runtime_reports = True
        cache_key = digest(
            {
                "component": str(component),
                "claim_kind": str(claim_kind or component),
                "member_id": selected_member.member_id,
                "geometry_or_cohort_digest": geometry_digest,
                "reference_stress_available": reference_stress_available,
                "reference_stress_available_by_geometry": (
                    None
                    if reference_stress_available_by_geometry is None
                    else list(reference_stress_available_by_geometry)
                ),
                "runtime_reports_stress": runtime_reports,
                "component_stress_policy": dict(policy),
            }
        )
        cached = self._stress_capabilities.get(cache_key)
        if cached is not None:
            return cached
        with member_provider(self.context, selected_member) as provider:
            predictions = predict_all(self.context, provider, atoms)
        decision = resolve_stress_capability(
            self.context,
            policy=policy,
            probe_atoms=atoms,
            probe_stresses=[stress_of(item) for item in predictions],
            runtime_reports_stress=runtime_reports,
            reference_frame_uids=tuple(probe)
            + tuple(base.frame_uid for base in self.plan.physical_plan.bases),
            reference_stress_available=reference_stress_available,
            reference_stress_available_by_geometry=reference_stress_available_by_geometry,
            qualification_binding_digest=self.binding.content_digest,
            component=str(component),
            claim_kind=str(claim_kind or component),
            member_id=selected_member.member_id,
            geometry_or_cohort_digest=geometry_digest,
        )
        self._stress_capabilities[cache_key] = decision
        return decision

    def _deployment_stress_capability(
        self, member_id: str, atoms: Any | None = None
    ) -> Any | None:
        """Return the exact deployment claim for one member/geometry.

        Dynamics may visit a geometry outside the bounded deployment probe
        cohort. Selecting an arbitrary cached member decision would reuse a
        different geometry claim, so an exact atom is required for a new
        lookup. The optional legacy form returns no decision rather than
        leaking a singleton into another claim.
        """

        if atoms is None:
            return None
        member = next(
            (item for item in self.publication.members if item.member_id == str(member_id)),
            None,
        )
        if member is None:
            raise QualificationLineageError(
                "Dynamics requested deployment stress for a member outside the publication."
            )
        return self.stress_capability(
            [atoms],
            member=member,
            component=COMPONENT_DEPLOYMENT_PARITY,
            claim_kind="deployment",
        )

    def _resolve_physical_reference_request_stress(
        self, request: PhysicalReferenceRequest
    ) -> PhysicalReferenceRequest:
        """Add the exact physical stress claim geometries to a new request.

        The request is created before an external bundle exists, so the
        candidate-independent geometry enumeration alone cannot know whether a
        published member actually exposes a trained stress channel.  Resolve
        that product fact once for every member here and union only the exact
        applicable geometries.  Later sessions reuse the immutable published
        request and therefore do not rerun model forwards merely to inspect
        currentness.
        """

        from dataclasses import replace

        from .providers import member_provider, predict_all, stress_of
        from .reference import RELAXED_MODE
        from .stress_capability import resolve_stress_capability

        (
            claim_geometries,
            claim_frames,
            _exact_reference,
            _exact_reference_by_geometry,
            claim_geometry_digest,
        ) = self._physical_stress_inputs(None)
        request_geometries = tuple(
            item for item in request.geometries if item.mode != RELAXED_MODE
        )
        if len(request_geometries) != len(claim_geometries):
            raise QualificationLineageError(
                "The physical reference request geometry order does not match the "
                "authenticated physical stress claim cohort."
            )
        policy = self.binding.specification.component_policy(COMPONENT_PHYSICAL_PES)
        required = [False] * len(claim_geometries)
        for member in self.publication.members:
            with member_provider(self.context, member) as provider:
                predictions = predict_all(self.context, provider, claim_geometries)
            decision = resolve_stress_capability(
                self.context,
                policy=policy,
                probe_atoms=claim_geometries,
                probe_stresses=[stress_of(item) for item in predictions],
                runtime_reports_stress=True,
                reference_frame_uids=tuple(claim_frames)
                + tuple(base.frame_uid for base in self.plan.physical_plan.bases),
                qualification_binding_digest=self.binding.content_digest,
                component=COMPONENT_PHYSICAL_PES,
                claim_kind="physical",
                member_id=member.member_id,
                geometry_or_cohort_digest=claim_geometry_digest,
            )
            if len(decision.geometry_applicability) != len(required):
                raise QualificationLineageError(
                    "The physical stress capability did not preserve exact claim "
                    "geometry cardinality."
                )
            for index, applicable in enumerate(decision.geometry_applicability):
                required[index] = bool(required[index] or applicable)
        stress_ids = tuple(
            item.geometry_identity
            for item, applicable in zip(request_geometries, required, strict=True)
            if applicable
        )
        return replace(
            request,
            stress_required_geometry_identities=stress_ids,
        )

    def _physical_stress_inputs(
        self, bundle: Any | None
    ) -> tuple[list[Any], tuple[str, ...], bool, tuple[bool, ...], str]:
        from .geometry import atoms_for_frame, displaced_atoms, strained_atoms
        from .reference import BASE_MODE, geometry_identity, mode_name, strain_mode_name

        geometries: list[Any] = []
        identities: list[str] = []
        frames: list[str] = []
        for base in self.plan.physical_plan.bases:
            frames.append(base.frame_uid)
            atoms = atoms_for_frame(self.context, base.frame_uid)
            geometries.append(atoms)
            identities.append(
                geometry_identity(atoms, frame_uid=base.frame_uid, mode=BASE_MODE)
            )
            for atom_index, axis, amplitude in base.modes():
                moved = displaced_atoms(
                    atoms, atom_index=atom_index, axis=axis, amplitude=amplitude
                )
                geometries.append(moved)
                identities.append(
                    geometry_identity(
                        moved,
                        frame_uid=base.frame_uid,
                        mode=mode_name(atom_index, axis, amplitude),
                    )
                )
            for magnitude in self.plan.physical_plan.strain_magnitudes:
                strained = strained_atoms(atoms, magnitude)
                geometries.append(strained)
                identities.append(
                    geometry_identity(
                        strained,
                        frame_uid=base.frame_uid,
                        mode=strain_mode_name(magnitude),
                    )
                )
        exact_reference_by_geometry = tuple(
            bool(
                bundle is not None
                and bundle.observations.get(identity) is not None
                and bundle.observations[identity].stress is not None
                and bundle.observations[identity].stress_provenance is not None
                and bundle.observations[identity].stress_provenance.source_declared
            )
            for identity in identities
        )
        exact_reference = bool(exact_reference_by_geometry and all(exact_reference_by_geometry))
        geometry_digest = digest(
            {
                "schema": "mdstats.qualification-physical-stress-cohort.v1",
                "geometry_identities": list(identities),
            }
        )
        return (
            geometries,
            tuple(frames),
            exact_reference,
            exact_reference_by_geometry,
            geometry_digest,
        )

    def stress_capability_digest(self, component: str, bundle: Any | None) -> str | None:
        """Resolve and digest every stress decision consumed by a component."""

        if str(component) == COMPONENT_DEPLOYMENT_PARITY:
            from .deployment import probe_cohort
            from .geometry import atoms_for_frame

            policy = self.binding.specification.component_policy(component)
            cohort = probe_cohort(
                self.context, count=int(policy["probe_configuration_count"])
            )
            atoms = [atoms_for_frame(self.context, uid) for uid in cohort]
            geometry_digest = digest(
                {
                    "schema": "mdstats.qualification-deployment-stress-cohort.v1",
                    "frame_uids": list(cohort),
                    "geometries": [
                        {
                            "numbers": [int(value) for value in item.get_atomic_numbers()],
                            "positions": np.asarray(
                                item.get_positions(), dtype=np.float64
                            ).tolist(),
                            "cell": np.asarray(item.get_cell(), dtype=np.float64).tolist(),
                            "pbc": [bool(value) for value in item.get_pbc()],
                        }
                        for item in atoms
                    ],
                }
            )
            decisions = [
                self.stress_capability(
                    atoms,
                    probe=cohort,
                    member=member,
                    component=component,
                    claim_kind="deployment",
                    geometry_or_cohort_digest=geometry_digest,
                )
                for member in self.publication.members
            ]
        elif str(component) == COMPONENT_PHYSICAL_PES:
            (
                atoms,
                frames,
                exact_reference,
                exact_reference_by_geometry,
                geometry_digest,
            ) = self._physical_stress_inputs(bundle)
            decisions = [
                self.stress_capability(
                    atoms,
                    probe=frames,
                    member=member,
                    component=component,
                    claim_kind="physical",
                    reference_stress_available=exact_reference,
                    reference_stress_available_by_geometry=exact_reference_by_geometry,
                    geometry_or_cohort_digest=geometry_digest,
                )
                for member in self.publication.members
            ]
        else:
            return None
        return digest(
            {
                "schema": "mdstats.qualification-stress-capability-set.v1",
                "component": str(component),
                "decisions": [
                    item.to_dict()
                    for item in sorted(decisions, key=lambda value: value.member_id or "")
                ],
            }
        )

    def resolved_case_workers(self, task_count: int) -> int:
        """Worker count for *task_count* cases, through the accepted owner.

        Exposed so acceptance can prove that resource pressure reduces
        concurrency without touching any scientific identity.
        """

        from ..resources import resolve_worker_count

        if self.resources is None or self.resource_scope is None:
            raise QualificationError(
                "Qualification case execution has no accepted resource scope."
            )
        return int(
            resolve_worker_count(
                task_count=int(task_count),
                resources=self.resources,
                requested=int(self.case_workers),
                estimated_bytes_per_worker=64 * 1024 * 1024,
                maximum_workers=int(self.resource_scope.python_workers),
            )
        )

    def authenticated_reference_bundle(self) -> Any | None:
        """The authenticated external bundle for this attempt's frozen request."""

        return load_reference_bundle(self.reference_root, self.reference_request)

    def map_cases(
        self, function: Callable[[Any], tuple[str, Any]], cases: Sequence[Any]
    ) -> dict[str, Any]:
        """Execute independent cases serially or with bounded concurrency.

        The result is keyed by case identity and therefore identical regardless
        of completion order: concurrency is a scheduling choice with no
        scientific content.
        """

        from ..resources import resolve_worker_count, stage_resource_scope

        if self.resources is None or self.resource_scope is None:
            raise QualificationError(
                "Qualification case execution has no accepted resource scope."
            )
        workers = resolve_worker_count(
            task_count=len(cases),
            resources=self.resources,
            requested=int(self.case_workers),
            # The estimate is deliberately conservative for the lossless raw
            # dynamics observations retained by the reducer.  It affects only
            # scheduling; it never changes a scientific input or threshold.
            estimated_bytes_per_worker=64 * 1024 * 1024,
            maximum_workers=int(self.resource_scope.python_workers),
        )
        if workers == 1 or len(cases) <= 1:
            with stage_resource_scope(self.resource_scope):
                return dict(function(case) for case in cases)
        from concurrent.futures import ThreadPoolExecutor

        # The scope's nested native-thread limits are applied around the whole
        # pool, so every case observes the same accepted BLAS/OpenMP budget.
        with stage_resource_scope(self.resource_scope):
            with ThreadPoolExecutor(max_workers=min(workers, len(cases))) as pool:
                return dict(pool.map(function, cases))

    # -- component position records -----------------------------------------
    def _position_path(self, component: str) -> Path:
        root = self.attempt_root / COMPONENT_POSITION_DIRECTORY
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{component}.json"

    def _position_object_path(self, component: str, component_input_digest: str) -> Path:
        from .._common import validate_digest

        identity = validate_digest(component_input_digest, name="component_input_digest")
        root = self.attempt_root / COMPONENT_POSITION_DIRECTORY / str(component)
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{identity}.json"

    def component_input_digest(
        self,
        component: str,
        bundle: Any | None,
        *,
        extra: Mapping[str, Any] | None = None,
        capability_digest: str | None = None,
    ) -> str:
        """Identity of the exact inputs consumed by one component.

        Reference-dependent evidence is deliberately a descendant of the
        authenticated bundle, while deployment/calibration remain reusable when
        a new external bundle arrives for the same product.
        """

        component_name = str(component)
        payload: dict[str, Any] = {
            "schema": "mdstats.qualification-component-input.v1",
            "component": component_name,
            "binding_digest": self.binding.content_digest,
            "plan_digest": self.plan.content_digest,
            # Only components that consume external observations depend on the
            # request/bundle identity.  Deployment and calibration evidence is
            # deliberately reusable when a missing reference bundle arrives
            # later; otherwise the waiting-to-qualified transition would
            # spuriously re-execute model-only work.
            "reference_request_digest": (
                self.reference_request.content_digest
                if component_name in _REFERENCE_DEPENDENT_COMPONENTS
                else None
            ),
            "reference_bundle_digest": (
                None
                if bundle is None or component_name not in _REFERENCE_DEPENDENT_COMPONENTS
                else str(bundle.content_digest)
            ),
        }
        if component_name in _REFERENCE_DEPENDENT_COMPONENTS and bundle is not None:
            payload["reference_geometry_identities"] = sorted(
                str(key) for key in bundle.observations
            )
        if component_name in {
            COMPONENT_DEPLOYMENT_PARITY,
            COMPONENT_PHYSICAL_PES,
        }:
            resolved_capability_digest = capability_digest or self._cached_capability_digest(
                component_name
            )
            if resolved_capability_digest is None:
                # A completed component already stores the exact capability set
                # that produced it. Reuse that authenticated set for identity
                # lookup instead of running a second numerical model forward.
                # The deployment runtime portion is re-probed by
                # _stored_capability_digest, so a changed runtime cannot make
                # old stress-bearing evidence current.
                resolved_capability_digest = self._stored_capability_digest(
                    component_name
                )
            if resolved_capability_digest is None:
                # No durable capability evidence exists yet, so this is a new
                # component identity and the claim-scoped owner must resolve
                # every member/geometry decision before execution.
                resolved_capability_digest = self.stress_capability_digest(
                    component_name, bundle
                )
            payload["stress_capability_digest"] = resolved_capability_digest
        if extra:
            payload["extra"] = dict(extra)
        return digest(payload)

    @staticmethod
    def _capability_set_digest_from_payload(
        component: str, payload: Mapping[str, Any]
    ) -> str | None:
        """Recover the authenticated claim-set digest from stored evidence."""

        stored = payload.get("stress_capability_set_digest")
        if stored is not None:
            try:
                from .._common import validate_digest

                return validate_digest(str(stored), name="stress_capability_set_digest")
            except (TypeError, ValueError):
                return None
        decisions = payload.get("stress_capabilities")
        if not isinstance(decisions, Mapping) or not decisions:
            return None
        normalized: list[Mapping[str, Any]] = []
        for decision in decisions.values():
            if not isinstance(decision, Mapping):
                return None
            normalized.append(decision)
        normalized.sort(key=lambda value: str(value.get("member_id", "")))
        return digest(
            {
                "schema": "mdstats.qualification-stress-capability-set.v1",
                "component": str(component),
                "decisions": normalized,
            }
        )

    def _stored_capability_digest(self, component: str) -> str | None:
        """Use stored capability evidence for identity without re-running E/F."""

        existing = self.completed_component(component, None)
        if existing is None:
            return None
        payload = existing.payload
        value = self._capability_set_digest_from_payload(component, payload)
        if value is None:
            return None
        if str(component) == COMPONENT_DEPLOYMENT_PARITY:
            decisions = payload.get("stress_capabilities")
            if not isinstance(decisions, Mapping) or not decisions:
                return None
            if self.deployed_stress_supported is not None:
                if any(
                    not isinstance(decision, Mapping)
                    or bool(decision.get("runtime_reports_stress")) != self.deployed_stress_supported
                    for decision in decisions.values()
                ):
                    return None
        return value

    def _cached_capability_digest(self, component: str) -> str | None:
        """Digest a complete in-memory claim set without another model forward."""

        decisions = [
            value
            for value in self._stress_capabilities.values()
            if getattr(value, "component", None) == str(component)
        ]
        members = tuple(self.publication.members)
        if len(decisions) != len(members):
            return None
        by_member = {str(getattr(value, "member_id", "")): value for value in decisions}
        if set(by_member) != {str(member.member_id) for member in members}:
            return None
        return digest(
            {
                "schema": "mdstats.qualification-stress-capability-set.v1",
                "component": str(component),
                "decisions": [
                    by_member[str(member.member_id)].to_dict()
                    for member in sorted(members, key=lambda item: item.member_id)
                ],
            }
        )

    def completed_component(
        self, component: str, expected_input_digest: str | None = None
    ) -> QualificationComponentEvidence | None:
        path = self._position_path(component)
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise QualificationLineageError(
                f"Qualification component position {path!s} is corrupt."
            ) from exc
        object_path = None
        if payload.get("position_object"):
            relative = Path(str(payload["position_object"]))
            if relative.is_absolute() or ".." in relative.parts:
                raise QualificationLineageError(
                    "Qualification component position points outside its attempt root."
                )
            object_path = self.attempt_root / relative
            if not object_path.is_file():
                raise QualificationLineageError(
                    "Qualification component position refers to a missing immutable "
                    "position object."
                )
            try:
                object_payload = json.loads(object_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise QualificationLineageError(
                    f"Qualification component position object {object_path!s} is corrupt."
                ) from exc
            if digest(object_payload) != str(payload.get("position_object_digest")):
                raise QualificationLineageError(
                    "Qualification component position locator does not authenticate "
                    "its immutable position object."
                )
            payload = object_payload
        input_digest = payload.get("component_input_digest")
        if expected_input_digest is not None and str(input_digest) != str(expected_input_digest):
            return None
        evidence = self.store.get(
            str(payload["evidence_digest"]), QualificationComponentEvidence.from_dict
        )
        if evidence.binding_digest != self.binding.content_digest:
            raise QualificationLineageError(
                "Stored component evidence belongs to a different qualification identity."
            )
        if expected_input_digest is not None and evidence.component_input_digest != str(
            expected_input_digest
        ):
            return None
        if input_digest is not None and evidence.component_input_digest != str(input_digest):
            raise QualificationLineageError(
                "Qualification component position and evidence input identities differ."
            )
        return evidence

    def record_component(self, evidence: QualificationComponentEvidence) -> QualificationComponentEvidence:
        from ..target_size_execution import (
            publish_immutable_json_create_or_verify,
            publish_mutable_json_atomic,
        )

        self.store.put(evidence)
        if evidence.component_input_digest is None:
            raise QualificationLineageError(
                "Durable component evidence must bind its exact component inputs."
            )
        position_payload = {
            "schema": "mdstats.qualification-component-position.v1",
            "component": evidence.component,
            "binding_digest": self.binding.content_digest,
            "component_input_digest": evidence.component_input_digest,
            "evidence_digest": evidence.content_digest,
        }
        object_path = self._position_object_path(
            evidence.component, evidence.component_input_digest
        )
        published = publish_immutable_json_create_or_verify(
            object_path,
            position_payload,
            deserializer=lambda payload: _PositionRecord(payload),
        )
        relative = object_path.relative_to(self.attempt_root)
        locator = {
            "schema": "mdstats.qualification-component-position-locator.v1",
            "component": evidence.component,
            "binding_digest": self.binding.content_digest,
            "component_input_digest": evidence.component_input_digest,
            "evidence_digest": evidence.content_digest,
            "position_object": str(relative),
            "position_object_digest": digest(position_payload),
        }
        if published is None:  # pragma: no cover - the helper always returns an object
            raise QualificationLineageError("Component position publication returned no record.")
        publish_mutable_json_atomic(self._position_path(evidence.component), locator)
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
    deployed_stress_supported: bool | None = None,
) -> QualificationSession | None:
    """Resolve the current product and freeze one qualification identity.

    ``None`` means the predecessor has not published a final production yet.
    """

    from ..campaign_post_selection_runtime import build_post_selection_context

    context = build_post_selection_context(
        cfg,
        paths,
        campaign_store,
        trainer=trainer,
        inference_evaluator=inference_evaluator,
        qualification_case_workers=case_workers,
    )
    publication = resolve_authenticated_final_publication(context)
    if publication is None:
        return None
    from ..post_selection_reclosure import resolve_current_predecessor_reclosure

    predecessor_reclosure = resolve_current_predecessor_reclosure(context)
    specification = resolve_qualification_spec_identity(cfg)
    environment = capture_environment_fingerprint(
        default_dtype=str(context.method_policies.common_training.default_dtype),
        device=str(context.method_policies.device),
    )
    resources, resource_scope, resource_digest = _qualification_resource_scope(
        cfg,
        device=str(context.method_policies.device),
        requested_workers=case_workers,
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
        resource_scope_digest=resource_digest,
        predecessor_reclosure_digest=predecessor_reclosure.content_digest,
        predecessor_executable_tree_digest=predecessor_reclosure.executable_source_tree_digest,
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
    protocol = _require_explicit_reference_protocol(cfg, specification)
    request = build_physical_reference_request(
        context,
        physical_plan,
        protocol_identity=protocol,
        include_relaxed=(
            COMPONENT_RELAXATION in specification.required_components
            or COMPONENT_RELAXATION in specification.optional_components
            or COMPONENT_DYNAMICS in specification.required_components
            or COMPONENT_DYNAMICS in specification.optional_components
        ),
        stress_required=False,
    )
    request_path = reference_request_path(reference_root)
    persisted_request = None
    if request_path.is_file():
        try:
            persisted_request = PhysicalReferenceRequest.from_dict(
                json.loads(request_path.read_text(encoding="utf-8"))
            )
        except (
            OSError,
            ValueError,
            KeyError,
            TypeError,
            AttributeError,
            TrainingDataInputError,
            TrainingDataSerializationError,
            QualificationError,
            QualificationLineageError,
        ) as exc:
            raise QualificationLineageError(
                f"The persisted physical reference request {request_path!s} is corrupt."
            ) from exc
        if (
            persisted_request.protocol_identity != request.protocol_identity
            or persisted_request.physical_plan_digest != request.physical_plan_digest
            or persisted_request.geometries != request.geometries
        ):
            raise QualificationLineageError(
                "The persisted physical reference request does not match the current "
                "authenticated physical plan/protocol."
            )
        request = persisted_request
    session = QualificationSession(
        context=context,
        publication=publication,
        predecessor_reclosure=predecessor_reclosure,
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
        resources=resources,
        resource_scope=resource_scope,
        resource_scope_material=resource_scope_payload(resources, resource_scope),
        # The campaign already declares a free-disk reserve for expensive
        # execution; qualification reuses that policy rather than inventing one.
        minimum_free_disk_gib=float(
            _config_table(cfg, "execution").get("minimum_free_disk_gib", 20.0)
        ),
        deployed_stress_supported=deployed_stress_supported,
    )
    if persisted_request is None:
        session.reference_request = session._resolve_physical_reference_request_stress(
            request
        )
    return session


# ---------------------------------------------------------------------------
# Execution
# ---------------------------------------------------------------------------


def _utc_stamp() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
        component_input_digest=session.component_input_digest(component, None),
    )


def execute_nonlocked_components(
    session: QualificationSession,
) -> tuple[QualificationComponentEvidence, ...]:
    """Run or resume every planned nonlocked component, in dependency order."""

    from .calibration import qualify_calibration
    from .dynamics import qualify_dynamics
    from .physical import qualify_physical_pes
    from .relaxation import qualify_relaxation

    import time

    publish_reference_request(session.reference_root, session.reference_request)
    bundle = load_reference_bundle(session.reference_root, session.reference_request)
    recorder = session.resource_recorder
    results: list[QualificationComponentEvidence] = []
    for component in session.plan.planned_components:
        expected_input_digest = session.component_input_digest(component, bundle)
        existing = session.completed_component(component, expected_input_digest)
        if existing is not None:
            results.append(existing)
            recorder.record_component(
                component, started=_utc_stamp(), elapsed=0.0, reused=True
            )
            continue
        # Materializing deployment artifacts and dynamics scratch is the point
        # where this attempt starts consuming the workspace, so the campaign's
        # existing free-disk reserve is checked here rather than after the fact.
        session._require_component_disk_reserve(component)
        component_started = _utc_stamp()
        component_clock = time.monotonic()
        try:
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
                evidence = (
                    qualify_dynamics(session, bundle)
                    if bundle is not None
                    else _waiting_evidence(
                        session,
                        component,
                        "Dynamics qualification is waiting for authenticated reference-"
                        f"relaxed geometries requested under {session.reference_root!s}.",
                    )
                )
            elif component == COMPONENT_CALIBRATION:
                evidence = qualify_calibration(session)
            else:  # pragma: no cover - enabled_components filters the vocabulary
                raise QualificationError(f"Unsupported qualification component {component!r}.")
        finally:
            # A failed operational/runtime owner is still part of the attempt's
            # measured history.  It must not become scientific evidence, but a
            # later resume must not silently erase the time already spent.
            recorder.record_component(
                component,
                started=component_started,
                elapsed=time.monotonic() - component_clock,
                reused=False,
            )
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
    resource_observation: Any = None,
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
        predecessor_executable_commit=(
            session.predecessor_reclosure.executable_git_commit
            or session.predecessor_reclosure.executable_source_tree_digest
        ),
        predecessor_evidence_commit=session.predecessor_reclosure.content_digest,
        components=outcomes,
        locked_activation_digest=(
            None if locked_activation is None else locked_activation.content_digest
        ),
        verdict=verdict,
        reason_code=reason,
        recorded_at=utc_now(),
        resource_scope_digest=session.binding.resource_scope_digest,
        predecessor_reclosure_digest=session.binding.predecessor_reclosure_digest,
        predecessor_executable_tree_digest=session.binding.predecessor_executable_tree_digest,
        resource_observation_digest=(
            None if resource_observation is None else resource_observation.content_digest
        ),
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


def publish_resource_observation(session: QualificationSession) -> Any:
    """Freeze what this attempt actually cost, as immutable release evidence."""

    from .resource_observation import publish_resource_observation_pointer

    observation = session.resource_recorder.finish()
    session.store.put(observation)
    # The object is immutable; this tiny attempt-local locator is the only
    # mutable state used to resume the same attempt after a process restart.
    # Publish it only after the object store has acknowledged the object, then
    # advance the in-memory recorder so a later invocation aggregates from the
    # exact bytes just published rather than starting a parallel measurement.
    publish_resource_observation_pointer(session.attempt_root, observation=observation)
    session.resource_recorder.mark_published(observation)
    return observation


def _publish_resource_observation_best_effort(session: QualificationSession) -> None:
    """Retain partial attempt measurements when an invocation aborts.

    Operational/runtime failures must preserve the work already performed so a
    later resume cannot silently erase it.  The original qualification failure
    remains authoritative; a failure in this diagnostic persistence path is
    deliberately swallowed rather than replacing the more useful exception.
    """

    if session._resource_recorder is None:
        return
    try:
        publish_resource_observation(session)
    except BaseException:
        pass


def publish_release_evidence(
    session: QualificationSession,
    campaign_store: Any,
    record: ProductionQualificationRecord,
    components: Sequence[QualificationComponentEvidence],
    *,
    resource_observation: Any = None,
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
        resource_scope_digest=record.resource_scope_digest,
        predecessor_reclosure_digest=record.predecessor_reclosure_digest,
        predecessor_executable_tree_digest=record.predecessor_executable_tree_digest,
        resource_observation_digest=(
            None if resource_observation is None else resource_observation.content_digest
        ),
    )
    session.store.put(index)
    publish_current_qualification_pointer(
        campaign_store,
        binding=session.context.selected.binding,
        kind=POINTER_RELEASE_EVIDENCE,
        content_digest=index.content_digest,
    )
    return index


def _fresh_current_qualification_session(
    campaign_store: Any,
    paths: Any,
    context: Any,
    *,
    binding: Any = None,
) -> QualificationSession | None:
    """Re-establish all P4/P5/P7 identities at the public exposure boundary."""

    if not hasattr(context, "cfg") or not hasattr(context, "selected"):
        raise QualificationError(
            "Current qualification resolution requires a full post-selection context, "
            "not a selected-binding locator alone."
        )
    # The context carries only a scheduling value, never volatile free-memory
    # state.  Rebuilding the session re-resolves publication, executable source,
    # environment, resource scope, policy, roles, and the candidate-independent
    # physical plan before any pointer is exposed.
    current = build_qualification_session(
        context.cfg,
        paths,
        campaign_store,
        trainer=getattr(context, "trainer", None),
        inference_evaluator=getattr(context, "inference_evaluator", None),
        case_workers=int(getattr(context, "qualification_case_workers", 1)),
    )
    if current is None:
        return None
    # The caller's object may belong to an older exposure.  The rebuilt session
    # is the authoritative identity used for both pointer lookup and dependent
    # reference-bundle authentication below.
    return current


def resolve_current_locked_activation(
    campaign_store: Any, paths: Any, context: Any, *, binding: Any = None
) -> LockedActivationRecord | None:
    """The activation that is current for *binding*, if any.

    Locked disclosure history is deliberately not resolved here: see
    :func:`locked_cohort_already_revealed`, which answers the one-shot question
    from immutable history regardless of what the current binding is.
    """

    current = _fresh_current_qualification_session(campaign_store, paths, context, binding=binding)
    if current is None:
        return None
    return resolve_current_qualification_record(
        campaign_store,
        paths,
        current.context.selected,
        kind=POINTER_LOCKED_ACTIVATION,
        deserializer=LockedActivationRecord.from_dict,
        binding=current.binding,
        expected_plan_digest=current.plan.content_digest,
        qualification_session=current,
    )


def resolve_current_qualification_verdict(
    campaign_store: Any, paths: Any, context: Any, *, binding: Any = None
) -> ProductionQualificationRecord | None:
    current = _fresh_current_qualification_session(campaign_store, paths, context, binding=binding)
    if current is None:
        return None
    return resolve_current_qualification_record(
        campaign_store,
        paths,
        current.context.selected,
        kind=POINTER_QUALIFICATION_RECORD,
        deserializer=ProductionQualificationRecord.from_dict,
        binding=current.binding,
        expected_plan_digest=current.plan.content_digest,
        qualification_session=current,
    )


def resolve_current_release_evidence(
    campaign_store: Any, paths: Any, context: Any, *, binding: Any = None
) -> ReleaseEvidenceIndex | None:
    current = _fresh_current_qualification_session(campaign_store, paths, context, binding=binding)
    if current is None:
        return None
    return resolve_current_qualification_record(
        campaign_store,
        paths,
        current.context.selected,
        kind=POINTER_RELEASE_EVIDENCE,
        deserializer=ReleaseEvidenceIndex.from_dict,
        binding=current.binding,
        expected_plan_digest=current.plan.content_digest,
        qualification_session=current,
    )


def resolve_current_qualification_plan(
    campaign_store: Any, paths: Any, context: Any, *, binding: Any = None
) -> ProductionQualificationPlan | None:
    current = _fresh_current_qualification_session(campaign_store, paths, context, binding=binding)
    if current is None:
        return None
    return resolve_current_qualification_record(
        campaign_store,
        paths,
        current.context.selected,
        kind=POINTER_QUALIFICATION_PLAN,
        deserializer=ProductionQualificationPlan.from_dict,
        binding=current.binding,
        expected_plan_digest=current.plan.content_digest,
        qualification_session=current,
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
    resource_published = False
    try:
        components = execute_nonlocked_components(session)
        existing_activation = locked_cohort_already_revealed(session, paths)
        activation_for_record = existing_activation
        locked_evidence: tuple[QualificationComponentEvidence, ...] = ()
        if (
            existing_activation is not None
            and existing_activation.binding_digest == session.binding.content_digest
        ):
            locked = session.completed_component(
                COMPONENT_LOCKED_TEST,
                session.component_input_digest(
                    COMPONENT_LOCKED_TEST,
                    None,
                    extra={"activation_digest": existing_activation.content_digest},
                ),
            )
            if locked is not None:
                locked_evidence = (locked,)
                session.resource_recorder.record_component(
                    COMPONENT_LOCKED_TEST,
                    started=_utc_stamp(),
                    elapsed=0.0,
                    reused=True,
                )
        elif existing_activation is not None:
            # The role has already been disclosed for another product.  It is
            # historical one-shot state, not a component object belonging to
            # this new binding, so never attach it to the new record.
            activation_for_record = None
        observation = publish_resource_observation(session)
        resource_published = True
        record = build_qualification_record(
            session,
            tuple(components) + locked_evidence,
            locked_activation=activation_for_record,
            resource_observation=observation,
        )
        publish_qualification_record(session, campaign_store, paths, record)
        publish_release_evidence(
            session,
            campaign_store,
            record,
            tuple(components) + locked_evidence,
            resource_observation=observation,
        )
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
        if not resource_published:
            _publish_resource_observation_best_effort(session)
        if not released:
            release_attempt_reference(
                paths,
                session.context.selected.binding,
                attempt_identity=session.binding.attempt_identity,
                terminal=False,
                detail="qualification attempt aborted",
            )
        raise


def locked_cohort_already_revealed(
    session: QualificationSession, paths: Any
) -> LockedActivationRecord | None:
    """The activation that already opened this exact cohort, from history.

    This deliberately reads immutable disclosure history rather than the
    currentness-fenced pointer: a specification, executable, environment, or
    publication change can make a *verdict* historical, but it must never make
    a revealed cohort fresh again.
    """

    from .store import (
        find_locked_activation,
        find_locked_activation_for_role,
        read_locked_reveal,
    )

    candidate = build_locked_activation(session, prerequisite_component_digests=())
    reveal = read_locked_reveal(
        paths, session.context.selected.binding, candidate.cohort_generation_identity
    )
    activation = None
    if reveal is not None:
        activation = find_locked_activation(paths, str(reveal["activation_digest"]))
        if activation is None:
            raise QualificationLineageError(
                "This locked cohort is recorded as revealed but its activation record is "
                "missing from the release-evidence store. The disclosure stands; the "
                "evidence must be restored before the test can be completed."
            )
        if activation.locked_role_digest != candidate.locked_role_digest:
            raise QualificationLineageError(
                "The locked disclosure record and activation disagree about the "
                "reserved evidence role."
            )
    # A crash after activation object publication but before the reveal pointer
    # is durable is still an opened cohort.  The role scan also recognizes
    # pre-revision activations whose old product-dependent cohort hash is no
    # longer reproducible.
    role_activation = find_locked_activation_for_role(
        paths, candidate.locked_role_digest
    )
    if activation is not None and role_activation is not None:
        if activation.content_digest != role_activation.content_digest:
            raise QualificationLineageError(
                "Locked disclosure history contains conflicting activations for "
                "the same reserved role."
            )
    return activation or role_activation


def activate_locked_test(
    session: QualificationSession, campaign_store: Any, paths: Any
) -> tuple[ProductionQualificationRecord, QualificationComponentEvidence]:
    """The only path that opens locked evidence. One-shot, and crash-resumable.

    Activation is an irreversible *open* event, not proof that the evaluation
    finished. Treating it as proof made a crash between publishing the
    activation and publishing the locked result unrecoverable: the cohort was
    permanently marked revealed and every later attempt refused to finish the
    test it had already opened. So the two facts are separated - the cohort was
    opened, and the locked result is complete - and a resume converges on the
    single already-published activation identity without reopening anything.
    """

    from .store import record_locked_reveal
    import time

    if not _locked_required(session):
        raise QualificationActivationError(
            "The frozen qualification policy disables the locked interpolation test; "
            "there is nothing to activate."
        )

    # The retention reference is acquired before any prerequisite work, so an
    # interruption inside the activation path cannot leave the exact artifacts
    # this attempt still needs reclaimable.
    referenced = [
        str(checkpoint_path_for_member(session.context, member))
        for member in session.publication.members
    ]
    acquire_attempt_reference(
        paths,
        session.context.selected.binding,
        attempt_identity=session.binding.attempt_identity,
        publication_digest=session.binding.publication_digest,
        binding_digest=session.binding.content_digest,
        referenced_paths=referenced,
        detail="locked activation in progress",
    )

    released = False
    resource_published = False
    try:
        existing = locked_cohort_already_revealed(session, paths)
        if existing is not None:
            activation = existing
            if activation.binding_digest != session.binding.content_digest:
                raise QualificationActivationError(
                    "This locked cohort has already been activated under a different product or "
                    "policy identity. The disclosure is permanent: the same cohort "
                    "cannot be reused as a fresh locked test for the current product."
                )
            locked_evidence = session.completed_component(
                COMPONENT_LOCKED_TEST,
                session.component_input_digest(
                    COMPONENT_LOCKED_TEST,
                    None,
                    extra={"activation_digest": activation.content_digest},
                ),
            )
            if locked_evidence is not None:
                terminal = resolve_current_qualification_verdict(
                    campaign_store, paths, session.context, binding=session.binding
                )
                release = resolve_current_release_evidence(
                    campaign_store, paths, session.context, binding=session.binding
                )
                # "Already completed" means the terminal record *and* the
                # release index both describe this activation.  A release index
                # published by an earlier nonlocked run is not evidence that the
                # locked test finished.
                if (
                    terminal is not None
                    and release is not None
                    and terminal.locked_activation_digest == activation.content_digest
                    and release.locked_activation_digest == activation.content_digest
                ):
                    release_attempt_reference(
                        paths,
                        session.context.selected.binding,
                        attempt_identity=session.binding.attempt_identity,
                        terminal=True,
                        detail="duplicate terminal locked activation",
                    )
                    released = True
                    raise QualificationActivationError(
                        "The locked interpolation test has already been activated and "
                        "completed for this exact publication and locked cohort. A "
                        "revealed cohort is never a fresh locked test again."
                    )
        else:
            activation = None

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

        # Opening or resuming the locked owner may materialize durable
        # activation/evidence state, so apply the same reserve-plus-headroom
        # admission before either path is entered.
        session._require_component_disk_reserve(COMPONENT_LOCKED_TEST)

        if activation is None:
            activation = build_locked_activation(
                session,
                prerequisite_component_digests=tuple(
                    evidence.content_digest for evidence in components
                ),
            )
            session.store.put(activation)
            # History first: if the process dies immediately after this line the
            # cohort is correctly known to be open, and the resume path above
            # finishes the exact test rather than opening a second one.
            record_locked_reveal(
                paths,
                session.context.selected.binding,
                cohort_identity=activation.cohort_generation_identity,
                activation_digest=activation.content_digest,
            )
        # Also repairs the durable reveal/pointer after a crash between the
        # activation object and either publication step.  Both operations are
        # create-or-verify/idempotent and never open the cohort twice.
        if activation.binding_digest != session.binding.content_digest:
            raise QualificationActivationError(
                "This locked cohort has already been activated under a different product or "
                "policy identity. The disclosure is permanent: the same cohort "
                "cannot be reused as a fresh locked test for the current product."
            )
        session.store.put(activation)
        record_locked_reveal(
            paths,
            session.context.selected.binding,
            cohort_identity=activation.cohort_generation_identity,
            activation_digest=activation.content_digest,
        )
        publish_current_qualification_pointer(
            campaign_store,
            binding=session.context.selected.binding,
            kind=POINTER_LOCKED_ACTIVATION,
            content_digest=activation.content_digest,
        )

        locked_evidence = session.completed_component(
            COMPONENT_LOCKED_TEST,
            session.component_input_digest(
                COMPONENT_LOCKED_TEST,
                None,
                extra={"activation_digest": activation.content_digest},
            ),
        )
        if locked_evidence is None:
            locked_started = _utc_stamp()
            locked_clock = time.monotonic()
            try:
                locked_evidence = session.record_component(
                    qualify_locked_test(session, activation)
                )
            finally:
                session.resource_recorder.record_component(
                    COMPONENT_LOCKED_TEST,
                    started=locked_started,
                    elapsed=time.monotonic() - locked_clock,
                    reused=False,
                )
        else:
            session.resource_recorder.record_component(
                COMPONENT_LOCKED_TEST,
                started=_utc_stamp(),
                elapsed=0.0,
                reused=True,
            )
        observation = publish_resource_observation(session)
        resource_published = True
        record = build_qualification_record(
            session,
            tuple(components) + (locked_evidence,),
            locked_activation=activation,
            resource_observation=observation,
        )
        publish_qualification_record(session, campaign_store, paths, record)
        publish_release_evidence(
            session,
            campaign_store,
            record,
            tuple(components) + (locked_evidence,),
            resource_observation=observation,
        )
        release_attempt_reference(
            paths,
            session.context.selected.binding,
            attempt_identity=session.binding.attempt_identity,
            terminal=True,
            detail=f"terminal verdict {record.verdict.value}",
        )
        released = True
        return record, locked_evidence
    except BaseException:
        if not resource_published:
            _publish_resource_observation_best_effort(session)
        if not released:
            release_attempt_reference(
                paths,
                session.context.selected.binding,
                attempt_identity=session.binding.attempt_identity,
                terminal=False,
                detail="locked activation aborted",
            )
        raise


__all__ = [
    "QualificationSession",
    "activate_locked_test",
    "build_qualification_record",
    "build_qualification_session",
    "execute_nonlocked_components",
    "publish_qualification_record",
    "publish_release_evidence",
    "locked_cohort_already_revealed",
    "resolve_current_locked_activation",
    "resolve_current_qualification_plan",
    "resolve_current_qualification_verdict",
    "resolve_current_release_evidence",
    "run_qualification",
]
