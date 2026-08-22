"""Direct fixed-universe MVQUAL authority for the v5 target-size workflow.

This authority scores only authenticated REPAIR2 prefixes.  It deliberately has
no TARGET-DATA2C ladder, migration, rescue, or same-N legacy comparison input.
MVQUAL remains the sole hard eligibility gate; the downstream target-size study
only consumes ``mv_qualified_sizes`` and does not reimplement qualification.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from ._target_multi_view_scoring import (
    TargetMultiViewSelectorTelemetry,
    _MVQUAL_STRICT_EDGE_LIMIT,
    _mvqual_score_job,
    _qualification_provenance_codes,
)
from .target_size_study import FIXED_TARGET_SIZES
from .target_coverage import target_coverage_role_domain_view

TARGET_MULTI_VIEW_QUALIFICATION_V2_VERSION = (
    "mdstats.target-data2c.mvqual2.fixed-eight.2026-08.v1"
)
TARGET_MULTI_VIEW_QUALIFICATION_V2_POLICY_SCHEMA = (
    "mdstats.target-multi-view-qualification-policy.v2"
)
TARGET_MULTI_VIEW_QUALIFICATION_V2_RUNG_SCHEMA = (
    "mdstats.target-multi-view-qualification-rung.v2"
)
TARGET_MULTI_VIEW_QUALIFICATION_V2_DOMAIN_SCHEMA = (
    "mdstats.target-multi-view-qualification-domain.v2"
)
TARGET_MULTI_VIEW_QUALIFICATION_V2_PLAN_SCHEMA = (
    "mdstats.target-multi-view-qualification-plan.v2"
)

OUTCOME_QUALIFIED = "fixed_universe_qualified"
OUTCOME_NO_QUALIFIED_SIZES = "no_qualified_sizes_within_fixed_universe"


def _assert_monotone_qualification(
    states: Sequence[tuple[int, bool, bool]], *, scope: str
) -> None:
    """Require FAIL* -> PASS* across the materializable nested-prefix population."""

    passed = False
    for size, materializable, qualified in states:
        if not materializable:
            continue
        if qualified:
            passed = True
        elif passed:
            raise TrainingDataInputError(
                f"MVQUAL2 monotonic qualification invariant violated for {scope}: "
                f"a larger materializable prefix n{size} failed after a smaller prefix passed."
            )


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationPolicyV2:
    coverage_threshold: float = 0.95
    candidate_sizes: tuple[int, ...] = FIXED_TARGET_SIZES
    capacity_ceiling: int = FIXED_TARGET_SIZES[-1]
    authority_version: str = TARGET_MULTI_VIEW_QUALIFICATION_V2_VERSION

    def __post_init__(self) -> None:
        threshold = float(self.coverage_threshold)
        sizes = tuple(int(v) for v in self.candidate_sizes)
        ceiling = int(self.capacity_ceiling)
        if not 0.0 < threshold <= 1.0:
            raise TrainingDataInputError("MVQUAL2 coverage threshold must lie in (0, 1].")
        if sizes != FIXED_TARGET_SIZES or ceiling != FIXED_TARGET_SIZES[-1]:
            raise TrainingDataInputError(
                "MVQUAL2 freezes the production universe at 128..16384 powers of two."
            )
        if self.authority_version != TARGET_MULTI_VIEW_QUALIFICATION_V2_VERSION:
            raise TrainingDataInputError("Unsupported MVQUAL2 authority version.")
        object.__setattr__(self, "coverage_threshold", threshold)
        object.__setattr__(self, "candidate_sizes", sizes)
        object.__setattr__(self, "capacity_ceiling", ceiling)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_V2_POLICY_SCHEMA,
            "coverage_threshold": self.coverage_threshold,
            "candidate_sizes": list(self.candidate_sizes),
            "capacity_ceiling": self.capacity_ceiling,
            "authority_version": self.authority_version,
        }

    @property
    def policy_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "policy_digest": self.policy_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationPolicyV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_V2_POLICY_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVQUAL2 policy schema.")
        result = cls(
            coverage_threshold=float(payload["coverage_threshold"]),
            candidate_sizes=tuple(int(v) for v in payload["candidate_sizes"]),
            capacity_ceiling=int(payload["capacity_ceiling"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("policy_digest") not in (None, result.policy_digest):
            raise TrainingDataSerializationError("MVQUAL2 policy digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationRungV2:
    target_size: int
    materializable: bool
    coverage_passed: bool
    hard_obligations_passed: bool
    qualified: bool
    coverage_report_digest: str | None
    telemetry: TargetMultiViewSelectorTelemetry | None
    unsatisfied_obligation_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        size = int(self.target_size)
        if size not in FIXED_TARGET_SIZES:
            raise TrainingDataInputError("MVQUAL2 rung lies outside the fixed universe.")
        if self.qualified != bool(
            self.materializable and self.coverage_passed and self.hard_obligations_passed
        ):
            raise TrainingDataInputError("MVQUAL2 rung qualification state is inconsistent.")
        report_digest = self.coverage_report_digest
        if self.materializable:
            if report_digest is None or self.telemetry is None:
                raise TrainingDataInputError(
                    "Materializable MVQUAL2 rungs require independent score evidence."
                )
            report_digest = validate_digest(report_digest, name="coverage_report_digest")
        elif report_digest is not None or self.telemetry is not None:
            raise TrainingDataInputError(
                "Unavailable MVQUAL2 rungs cannot carry fabricated score evidence."
            )
        object.__setattr__(self, "target_size", size)
        object.__setattr__(self, "coverage_report_digest", report_digest)
        object.__setattr__(
            self,
            "unsatisfied_obligation_ids",
            tuple(sorted(set(str(v) for v in self.unsatisfied_obligation_ids))),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_V2_RUNG_SCHEMA,
            "target_size": self.target_size,
            "materializable": self.materializable,
            "coverage_passed": self.coverage_passed,
            "hard_obligations_passed": self.hard_obligations_passed,
            "qualified": self.qualified,
            "coverage_report_digest": self.coverage_report_digest,
            "telemetry": None if self.telemetry is None else self.telemetry.to_dict(),
            "unsatisfied_obligation_ids": list(self.unsatisfied_obligation_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationRungV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_V2_RUNG_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVQUAL2 rung schema.")
        telemetry_payload = payload.get("telemetry")
        result = cls(
            target_size=int(payload["target_size"]),
            materializable=bool(payload["materializable"]),
            coverage_passed=bool(payload["coverage_passed"]),
            hard_obligations_passed=bool(payload["hard_obligations_passed"]),
            qualified=bool(payload["qualified"]),
            coverage_report_digest=(
                None
                if payload.get("coverage_report_digest") is None
                else str(payload["coverage_report_digest"])
            ),
            telemetry=(
                None
                if telemetry_payload is None
                else TargetMultiViewSelectorTelemetry.from_dict(telemetry_payload)
            ),
            unsatisfied_obligation_ids=tuple(
                str(v) for v in payload.get("unsatisfied_obligation_ids", ())
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVQUAL2 rung digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationDomainPlanV2:
    label_domain_id: str
    reference_domain_digest: str
    sparse_domain_digest: str
    repair_domain_digest: str
    rungs: tuple[TargetMultiViewQualificationRungV2, ...]
    _rung_by_size: dict[int, TargetMultiViewQualificationRungV2] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        rungs = tuple(sorted(self.rungs, key=lambda item: item.target_size))
        if tuple(v.target_size for v in rungs) != FIXED_TARGET_SIZES:
            raise TrainingDataInputError(
                "Each MVQUAL2 domain must report the complete fixed target-size universe."
            )
        _assert_monotone_qualification(
            tuple((v.target_size, v.materializable, v.qualified) for v in rungs),
            scope=f"domain {self.label_domain_id!r}",
        )
        object.__setattr__(self, "rungs", rungs)
        object.__setattr__(self, "_rung_by_size", {v.target_size: v for v in rungs})

    def rung(self, target_size: int) -> TargetMultiViewQualificationRungV2:
        return self._rung_by_size[int(target_size)]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_V2_DOMAIN_SCHEMA,
            "label_domain_id": self.label_domain_id,
            "reference_domain_digest": validate_digest(
                self.reference_domain_digest, name="reference_domain_digest"
            ),
            "sparse_domain_digest": validate_digest(
                self.sparse_domain_digest, name="sparse_domain_digest"
            ),
            "repair_domain_digest": validate_digest(
                self.repair_domain_digest, name="repair_domain_digest"
            ),
            "rungs": [v.to_dict() for v in self.rungs],
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "TargetMultiViewQualificationDomainPlanV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_V2_DOMAIN_SCHEMA:
            raise TrainingDataSerializationError("Unsupported MVQUAL2 domain schema.")
        result = cls(
            label_domain_id=str(payload["label_domain_id"]),
            reference_domain_digest=str(payload["reference_domain_digest"]),
            sparse_domain_digest=str(payload["sparse_domain_digest"]),
            repair_domain_digest=str(payload["repair_domain_digest"]),
            rungs=tuple(
                TargetMultiViewQualificationRungV2.from_dict(v)
                for v in payload["rungs"]
            ),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVQUAL2 domain digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class TargetMultiViewQualificationPlanV2:
    dataset_id: str
    target_coverage_reference_digest: str
    target_coverage_sparse_index_digest: str
    target_coverage_feasibility_digest: str
    target_data_role_freeze_digest: str
    target_multi_view_repair_digest: str
    policy: TargetMultiViewQualificationPolicyV2
    domains: tuple[TargetMultiViewQualificationDomainPlanV2, ...]
    mv_qualified_sizes: tuple[int, ...]
    outcome: str
    authority_version: str = TARGET_MULTI_VIEW_QUALIFICATION_V2_VERSION
    _domain_by_id: dict[str, TargetMultiViewQualificationDomainPlanV2] = field(
        default_factory=dict, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        domains = tuple(sorted(self.domains, key=lambda item: item.label_domain_id))
        if not domains or len({v.label_domain_id for v in domains}) != len(domains):
            raise TrainingDataInputError("MVQUAL2 requires unique nonempty domains.")
        qualified = tuple(sorted(set(int(v) for v in self.mv_qualified_sizes)))
        if any(v not in FIXED_TARGET_SIZES for v in qualified):
            raise TrainingDataInputError("MVQUAL2 qualified size lies outside the fixed universe.")
        derived = tuple(
            size
            for size in FIXED_TARGET_SIZES
            if all(domain.rung(size).qualified for domain in domains)
        )
        if qualified != derived:
            raise TrainingDataInputError("MVQUAL2 global qualification contradicts domain evidence.")
        _assert_monotone_qualification(
            tuple(
                (
                    size,
                    all(domain.rung(size).materializable for domain in domains),
                    size in qualified,
                )
                for size in FIXED_TARGET_SIZES
            ),
            scope="global intersection",
        )
        expected_outcome = OUTCOME_QUALIFIED if qualified else OUTCOME_NO_QUALIFIED_SIZES
        if self.outcome != expected_outcome:
            raise TrainingDataInputError("MVQUAL2 outcome contradicts qualification evidence.")
        if self.authority_version != TARGET_MULTI_VIEW_QUALIFICATION_V2_VERSION:
            raise TrainingDataInputError("Unsupported MVQUAL2 authority version.")
        for name in (
            "target_coverage_reference_digest",
            "target_coverage_sparse_index_digest",
            "target_coverage_feasibility_digest",
            "target_data_role_freeze_digest",
            "target_multi_view_repair_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        object.__setattr__(self, "domains", domains)
        object.__setattr__(self, "mv_qualified_sizes", qualified)
        object.__setattr__(self, "_domain_by_id", {v.label_domain_id: v for v in domains})

    def domain(self, label_domain_id: str) -> TargetMultiViewQualificationDomainPlanV2:
        return self._domain_by_id[str(label_domain_id)]

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": TARGET_MULTI_VIEW_QUALIFICATION_V2_PLAN_SCHEMA,
            "dataset_id": self.dataset_id,
            "target_coverage_reference_digest": self.target_coverage_reference_digest,
            "target_coverage_sparse_index_digest": self.target_coverage_sparse_index_digest,
            "target_coverage_feasibility_digest": self.target_coverage_feasibility_digest,
            "target_data_role_freeze_digest": self.target_data_role_freeze_digest,
            "target_multi_view_repair_digest": self.target_multi_view_repair_digest,
            "policy": self.policy.to_dict(),
            "domains": [v.to_dict() for v in self.domains],
            "mv_qualified_sizes": list(self.mv_qualified_sizes),
            "outcome": self.outcome,
            "authority_version": self.authority_version,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "TargetMultiViewQualificationPlanV2":
        if payload.get("schema") != TARGET_MULTI_VIEW_QUALIFICATION_V2_PLAN_SCHEMA:
            raise TrainingDataSerializationError(
                "Legacy MVQUAL state is not restart-compatible with the v5 fixed-universe authority."
            )
        result = cls(
            dataset_id=str(payload["dataset_id"]),
            target_coverage_reference_digest=str(payload["target_coverage_reference_digest"]),
            target_coverage_sparse_index_digest=str(payload["target_coverage_sparse_index_digest"]),
            target_coverage_feasibility_digest=str(payload["target_coverage_feasibility_digest"]),
            target_data_role_freeze_digest=str(payload["target_data_role_freeze_digest"]),
            target_multi_view_repair_digest=str(payload["target_multi_view_repair_digest"]),
            policy=TargetMultiViewQualificationPolicyV2.from_dict(payload["policy"]),
            domains=tuple(
                TargetMultiViewQualificationDomainPlanV2.from_dict(v)
                for v in payload["domains"]
            ),
            mv_qualified_sizes=tuple(int(v) for v in payload["mv_qualified_sizes"]),
            outcome=str(payload["outcome"]),
            authority_version=str(payload["authority_version"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("MVQUAL2 plan digest mismatch.")
        return result


def _report_digest(report: Any) -> str:
    value = getattr(report, "content_digest", None)
    if value is not None:
        return validate_digest(str(value), name="coverage_report_digest")
    to_dict = getattr(report, "to_dict", None)
    if not callable(to_dict):
        raise TrainingDataInputError("MVQUAL2 coverage report is not content-addressable.")
    return digest(to_dict())


def build_target_multi_view_qualification_plan_v2(
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_coverage_feasibility: Any,
    target_data_role_freeze: Any,
    target_multi_view_repair: Any,
    *,
    policy: TargetMultiViewQualificationPolicyV2 | None = None,
    coverage_query_workers: int = 1,
    scoring_workers: int = 1,
    sparse_max_edges: int = _MVQUAL_STRICT_EDGE_LIMIT,
    progress_callback: Any = None,
) -> TargetMultiViewQualificationPlanV2:
    """Qualify every materializable fixed REPAIR2 prefix independently."""

    policy = policy or TargetMultiViewQualificationPolicyV2(
        coverage_threshold=float(target_coverage_reference.policy.coverage_threshold)
    )
    query_workers = int(coverage_query_workers)
    requested_workers = int(scoring_workers)
    if query_workers < 1 or requested_workers < 1:
        raise TrainingDataInputError("MVQUAL2 worker counts must be positive.")
    if int(sparse_max_edges) < 1:
        raise TrainingDataInputError("MVQUAL2 sparse edge limit must be positive.")
    dataset_ids = {
        target_coverage_reference.dataset_id,
        target_coverage_sparse_index.dataset_id,
        target_coverage_feasibility.dataset_id,
        target_multi_view_repair.dataset_id,
    }
    if len(dataset_ids) != 1:
        raise TrainingDataInputError("MVQUAL2 dataset identity mismatch.")
    if target_coverage_sparse_index.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("MVQUAL2 MVIDX/reference lineage mismatch.")
    if target_coverage_feasibility.target_coverage_reference_digest != target_coverage_reference.content_digest:
        raise TrainingDataInputError("MVQUAL2 FEAS/reference lineage mismatch.")
    if target_coverage_feasibility.target_data_role_freeze_digest != target_data_role_freeze.content_digest:
        raise TrainingDataInputError("MVQUAL2 FEAS/DATA2A lineage mismatch.")
    if (
        target_multi_view_repair.target_coverage_reference_digest
        != target_coverage_reference.content_digest
        or target_multi_view_repair.target_coverage_sparse_index_digest
        != target_coverage_sparse_index.content_digest
    ):
        raise TrainingDataInputError("MVQUAL2 REPAIR2 lineage mismatch.")
    if abs(policy.coverage_threshold - float(target_coverage_reference.policy.coverage_threshold)) > 5e-15:
        raise TrainingDataInputError("MVQUAL2 threshold differs from TARGET-DATA2B authority.")

    jobs: list[tuple[str, int, Sequence[str], Any, Any, dict[str, int], Any, Any]] = []
    unavailable: dict[tuple[str, int], TargetMultiViewQualificationRungV2] = {}
    domain_meta: dict[str, tuple[Any, Any, Any]] = {}
    for reference_domain in target_coverage_reference.domains:
        label = reference_domain.label_domain_id
        sparse_domain = target_coverage_sparse_index.domain(label)
        repair_domain = target_multi_view_repair.domain(label)
        role_domain = target_coverage_role_domain_view(target_data_role_freeze, reference_domain)
        uid_to_index, run_codes, condition_codes = _qualification_provenance_codes(
            reference_domain, role_domain
        )
        domain_meta[label] = (reference_domain, sparse_domain, repair_domain)
        master = tuple(str(v) for v in repair_domain.repaired_master_order)
        for size in FIXED_TARGET_SIZES:
            if len(master) < size:
                unavailable[(label, size)] = TargetMultiViewQualificationRungV2(
                    target_size=size,
                    materializable=False,
                    coverage_passed=False,
                    hard_obligations_passed=False,
                    qualified=False,
                    coverage_report_digest=None,
                    telemetry=None,
                    unsatisfied_obligation_ids=(),
                )
                continue
            jobs.append(
                (
                    label,
                    size,
                    master[:size],
                    reference_domain,
                    sparse_domain,
                    uid_to_index,
                    run_codes,
                    condition_codes,
                )
            )

    effective_workers = max(1, min(requested_workers, len(jobs) or 1))
    inner_query_workers = query_workers if effective_workers == 1 else 1

    def evaluate(job: tuple[str, int, Sequence[str], Any, Any, dict[str, int], Any, Any]):
        label, size, selected, reference_domain, sparse_domain, uid_to_index, run_codes, condition_codes = job
        result = _mvqual_score_job(
            target_coverage_reference,
            reference_domain,
            sparse_domain,
            label=label,
            selector="mv",
            target_size=size,
            selected_uids=selected,
            uid_to_index=uid_to_index,
            run_codes=run_codes,
            condition_codes=condition_codes,
            query_workers=inner_query_workers,
            sparse_max_edges=int(sparse_max_edges),
        )
        return label, size, result

    results: dict[tuple[str, int], Any] = {}
    if effective_workers == 1:
        for job in jobs:
            label, size, result = evaluate(job)
            results[(label, size)] = result
            if progress_callback is not None:
                progress_callback(f"status=rung; domain={label}; target_size={size}; pass={result.report.passed and result.hard_state[0]}")
    else:
        with ThreadPoolExecutor(max_workers=effective_workers, thread_name_prefix="mdstats-mvqual2") as pool:
            futures = {pool.submit(evaluate, job): (job[0], job[1]) for job in jobs}
            for future in as_completed(futures):
                label, size, result = future.result()
                results[(label, size)] = result
        if progress_callback is not None:
            for label, size, *_ in jobs:
                result = results[(label, size)]
                progress_callback(f"status=rung; domain={label}; target_size={size}; pass={result.report.passed and result.hard_state[0]}")

    domains: list[TargetMultiViewQualificationDomainPlanV2] = []
    for label in sorted(domain_meta):
        reference_domain, sparse_domain, repair_domain = domain_meta[label]
        rungs: list[TargetMultiViewQualificationRungV2] = []
        for size in FIXED_TARGET_SIZES:
            if (label, size) in unavailable:
                rungs.append(unavailable[(label, size)])
                continue
            result = results[(label, size)]
            coverage_passed = bool(result.report.passed)
            hard_passed, unsatisfied = result.hard_state
            rungs.append(
                TargetMultiViewQualificationRungV2(
                    target_size=size,
                    materializable=True,
                    coverage_passed=coverage_passed,
                    hard_obligations_passed=bool(hard_passed),
                    qualified=bool(coverage_passed and hard_passed),
                    coverage_report_digest=_report_digest(result.report),
                    telemetry=result.telemetry,
                    unsatisfied_obligation_ids=tuple(str(v) for v in unsatisfied),
                )
            )
        domains.append(
            TargetMultiViewQualificationDomainPlanV2(
                label_domain_id=label,
                reference_domain_digest=reference_domain.content_digest,
                sparse_domain_digest=sparse_domain.content_digest,
                repair_domain_digest=repair_domain.content_digest,
                rungs=tuple(rungs),
            )
        )

    qualified = tuple(
        size for size in FIXED_TARGET_SIZES if all(domain.rung(size).qualified for domain in domains)
    )
    return TargetMultiViewQualificationPlanV2(
        dataset_id=target_coverage_reference.dataset_id,
        target_coverage_reference_digest=target_coverage_reference.content_digest,
        target_coverage_sparse_index_digest=target_coverage_sparse_index.content_digest,
        target_coverage_feasibility_digest=target_coverage_feasibility.content_digest,
        target_data_role_freeze_digest=target_data_role_freeze.content_digest,
        target_multi_view_repair_digest=target_multi_view_repair.content_digest,
        policy=policy,
        domains=tuple(domains),
        mv_qualified_sizes=qualified,
        outcome=(OUTCOME_QUALIFIED if qualified else OUTCOME_NO_QUALIFIED_SIZES),
    )


def validate_target_multi_view_qualification_authority_v2(
    plan: TargetMultiViewQualificationPlanV2,
    *,
    target_coverage_reference: Any,
    target_coverage_sparse_index: Any,
    target_coverage_feasibility: Any,
    target_data_role_freeze: Any,
    target_multi_view_repair: Any,
    policy: TargetMultiViewQualificationPolicyV2 | None = None,
) -> None:
    """Validate current MVQUAL2 lineage without replaying expensive scores."""

    policy = policy or TargetMultiViewQualificationPolicyV2(
        coverage_threshold=float(target_coverage_reference.policy.coverage_threshold)
    )
    expected = (
        target_coverage_reference.content_digest,
        target_coverage_sparse_index.content_digest,
        target_coverage_feasibility.content_digest,
        target_data_role_freeze.content_digest,
        target_multi_view_repair.content_digest,
    )
    observed = (
        plan.target_coverage_reference_digest,
        plan.target_coverage_sparse_index_digest,
        plan.target_coverage_feasibility_digest,
        plan.target_data_role_freeze_digest,
        plan.target_multi_view_repair_digest,
    )
    if expected != observed or plan.dataset_id != target_coverage_reference.dataset_id:
        raise TrainingDataInputError("MVQUAL2 lineage changed.")
    if plan.policy.policy_digest != policy.policy_digest:
        raise TrainingDataInputError("MVQUAL2 policy changed.")
    if tuple(plan.mv_qualified_sizes) != tuple(
        size
        for size in FIXED_TARGET_SIZES
        if all(domain.rung(size).qualified for domain in plan.domains)
    ):
        raise TrainingDataInputError("MVQUAL2 qualification evidence is inconsistent.")
