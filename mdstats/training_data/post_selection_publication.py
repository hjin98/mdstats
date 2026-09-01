"""The P5 final-production publication decision: which seeds ship, and why.

Final production trains one run per required seed.  Deciding *which* of those
runs constitute the released product is a predecessor responsibility, not a
qualification one: the decision must be taken from pre-qualification evidence
only, before any downstream physical, calibration, or locked observation
exists.  Otherwise "the committee" would silently become "the members that
happened to survive qualification", which is member selection on release
evidence.

This module is therefore the single owner of that decision.  It ranks nothing
new: it reuses the already-frozen per-seed representative checkpoints and the
accepted target-only EVAL2 ordering that chose them, over the common frozen
``M3`` development evidence.  No target-size statistic, physical score, locked
score, or qualification outcome participates, and there is deliberately no API
that adds, removes, or reorders a member after the decision is published.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import PostSelectionBinding, PostSelectionError

FINAL_PUBLICATION_SEED_EVIDENCE_SCHEMA = (
    "mdstats.post-selection-final-publication-seed-evidence.v1"
)
FINAL_PUBLICATION_DECISION_SCHEMA = (
    "mdstats.post-selection-final-publication-decision.v1"
)

#: Identity of the deterministic decision procedure itself.  Changing how the
#: published member set is derived changes this string, which changes the
#: decision digest and therefore stales every descendant.
FINAL_PUBLICATION_DECISION_POLICY_IDENTITY = (
    "mdstats.p5-final-publication-decision.frozen-representative-eval2-ordering.v1"
)

COMMITTEE_ALL_QUALIFIED = "all_qualified_final_seeds"
COMMITTEE_SINGLE_BEST = "single_best_final_seed"
SUPPORTED_COMMITTEE_POLICIES = (COMMITTEE_ALL_QUALIFIED, COMMITTEE_SINGLE_BEST)


def member_id_for_seed(optimizer_seed: int) -> str:
    return f"seed-{int(optimizer_seed)}"


@dataclass(frozen=True, slots=True)
class FinalPublicationSeedEvidence:
    """One required production seed's exact pre-qualification decision inputs."""

    optimizer_seed: int
    run_identity: str
    run_plan_digest: str
    run_evidence_digest: str
    representative_candidate_identity: str
    representative_checkpoint_sha256: str
    representative_record_digest: str
    monitor_metric_record_digest: str
    checkpoint_relative_path: str
    admissible: bool

    def __post_init__(self) -> None:
        for name in (
            "run_identity",
            "run_plan_digest",
            "run_evidence_digest",
            "representative_checkpoint_sha256",
            "representative_record_digest",
            "monitor_metric_record_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        identity = str(self.representative_candidate_identity).strip()
        if not identity:
            raise TrainingDataInputError(
                "Publication seed evidence requires its frozen representative identity."
            )
        object.__setattr__(self, "representative_candidate_identity", identity)
        relative = str(self.checkpoint_relative_path).strip()
        if not relative or Path(relative).is_absolute():
            raise TrainingDataInputError(
                "A published checkpoint path must be run-root relative."
            )
        object.__setattr__(self, "checkpoint_relative_path", relative)
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        object.__setattr__(self, "admissible", bool(self.admissible))

    @property
    def member_id(self) -> str:
        return member_id_for_seed(self.optimizer_seed)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PUBLICATION_SEED_EVIDENCE_SCHEMA,
            "optimizer_seed": self.optimizer_seed,
            "run_identity": self.run_identity,
            "run_plan_digest": self.run_plan_digest,
            "run_evidence_digest": self.run_evidence_digest,
            "representative_candidate_identity": self.representative_candidate_identity,
            "representative_checkpoint_sha256": self.representative_checkpoint_sha256,
            "representative_record_digest": self.representative_record_digest,
            "monitor_metric_record_digest": self.monitor_metric_record_digest,
            "checkpoint_relative_path": self.checkpoint_relative_path,
            "admissible": self.admissible,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FinalPublicationSeedEvidence":
        if payload.get("schema") != FINAL_PUBLICATION_SEED_EVIDENCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-publication seed-evidence schema."
            )
        result = cls(
            optimizer_seed=int(payload["optimizer_seed"]),
            run_identity=str(payload["run_identity"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            run_evidence_digest=str(payload["run_evidence_digest"]),
            representative_candidate_identity=str(
                payload["representative_candidate_identity"]
            ),
            representative_checkpoint_sha256=str(
                payload["representative_checkpoint_sha256"]
            ),
            representative_record_digest=str(payload["representative_record_digest"]),
            monitor_metric_record_digest=str(payload["monitor_metric_record_digest"]),
            checkpoint_relative_path=str(payload["checkpoint_relative_path"]),
            admissible=bool(payload["admissible"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-publication seed-evidence digest mismatch."
            )
        return result


@dataclass(frozen=True, slots=True)
class FinalProductionPublicationDecision:
    """The immutable pre-qualification decision of the published member set."""

    binding: PostSelectionBinding
    final_plan_digest: str
    final_production_policy_digest: str
    method_identity_digest: str
    cv_plan_digest: str
    cv_authorization_digest: str
    m3_membership_digest: str
    completion_digest: str
    target_head_name: str
    committee_policy: str
    decision_policy_identity: str
    seed_evidence: tuple[FinalPublicationSeedEvidence, ...]
    published_member_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.binding, PostSelectionBinding):
            raise TrainingDataInputError(
                "A final-publication decision requires the authenticated selected binding."
            )
        for name in (
            "final_plan_digest",
            "final_production_policy_digest",
            "method_identity_digest",
            "cv_plan_digest",
            "cv_authorization_digest",
            "m3_membership_digest",
            "completion_digest",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        head = str(self.target_head_name).strip()
        if not head:
            raise TrainingDataInputError(
                "A final-publication decision requires the canonical target head name."
            )
        object.__setattr__(self, "target_head_name", head)
        policy = str(self.committee_policy).strip()
        if policy not in SUPPORTED_COMMITTEE_POLICIES:
            raise PostSelectionError(
                f"Unsupported final-production committee policy {policy!r}."
            )
        object.__setattr__(self, "committee_policy", policy)
        identity = str(self.decision_policy_identity).strip()
        if not identity:
            raise TrainingDataInputError(
                "A final-publication decision requires its decision-policy identity."
            )
        object.__setattr__(self, "decision_policy_identity", identity)
        evidence = tuple(self.seed_evidence)
        if not evidence:
            raise PostSelectionError(
                "A final-publication decision requires every required seed's evidence."
            )
        seeds = [item.optimizer_seed for item in evidence]
        if seeds != sorted(seeds) or len(set(seeds)) != len(seeds):
            raise TrainingDataInputError(
                "Publication seed evidence must be uniquely ordered by production seed."
            )
        object.__setattr__(self, "seed_evidence", evidence)
        members = tuple(str(v) for v in self.published_member_ids)
        if not members or len(set(members)) != len(members):
            raise PostSelectionError(
                "A final publication requires a non-empty unique published member set."
            )
        known = {item.member_id for item in evidence}
        unknown = sorted(set(members) - known)
        if unknown:
            raise PostSelectionError(
                f"Published member(s) {unknown} do not correspond to a required "
                "production seed; publication membership is never invented."
            )
        object.__setattr__(self, "published_member_ids", members)

    def evidence_for(self, member_id: str) -> FinalPublicationSeedEvidence:
        for item in self.seed_evidence:
            if item.member_id == str(member_id):
                return item
        raise PostSelectionError(f"Unknown publication member {member_id!r}.")

    @property
    def published_seed_evidence(self) -> tuple[FinalPublicationSeedEvidence, ...]:
        """The exact decided ordered member set, as evidence records."""

        return tuple(self.evidence_for(member_id) for member_id in self.published_member_ids)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": FINAL_PUBLICATION_DECISION_SCHEMA,
            "binding": self.binding.to_dict(),
            "final_plan_digest": self.final_plan_digest,
            "final_production_policy_digest": self.final_production_policy_digest,
            "method_identity_digest": self.method_identity_digest,
            "cv_plan_digest": self.cv_plan_digest,
            "cv_authorization_digest": self.cv_authorization_digest,
            "m3_membership_digest": self.m3_membership_digest,
            "completion_digest": self.completion_digest,
            "target_head_name": self.target_head_name,
            "committee_policy": self.committee_policy,
            "decision_policy_identity": self.decision_policy_identity,
            "seed_evidence": [item.to_dict() for item in self.seed_evidence],
            "published_member_ids": list(self.published_member_ids),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    @property
    def selected_binding_digest(self) -> str:
        return self.binding.content_digest

    @property
    def member_digest(self) -> str:
        """Identity of the exact ordered published product bytes and head."""

        return digest(
            {
                "schema": "mdstats.post-selection-final-publication-members.v1",
                "target_head_name": self.target_head_name,
                "members": [
                    [item.member_id, item.representative_checkpoint_sha256]
                    for item in self.published_seed_evidence
                ],
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(
        cls, payload: Mapping[str, Any]
    ) -> "FinalProductionPublicationDecision":
        if payload.get("schema") != FINAL_PUBLICATION_DECISION_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported final-publication decision schema."
            )
        result = cls(
            binding=PostSelectionBinding.from_dict(payload["binding"]),
            final_plan_digest=str(payload["final_plan_digest"]),
            final_production_policy_digest=str(payload["final_production_policy_digest"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            cv_plan_digest=str(payload["cv_plan_digest"]),
            cv_authorization_digest=str(payload["cv_authorization_digest"]),
            m3_membership_digest=str(payload["m3_membership_digest"]),
            completion_digest=str(payload["completion_digest"]),
            target_head_name=str(payload["target_head_name"]),
            committee_policy=str(payload["committee_policy"]),
            decision_policy_identity=str(payload["decision_policy_identity"]),
            seed_evidence=tuple(
                FinalPublicationSeedEvidence.from_dict(item)
                for item in payload["seed_evidence"]
            ),
            published_member_ids=tuple(payload["published_member_ids"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "Final-publication decision digest mismatch."
            )
        return result


def _seed_evidence_for_run(context: Any, plan: Any, evidence: Any) -> tuple[
    FinalPublicationSeedEvidence, Any
]:
    """Authenticate one completed seed and return (evidence record, EVAL2 record)."""

    from .campaign_post_selection_runtime import authenticated_run_representative_records
    from .post_selection_execution import (
        DATASET_ROLE_CHECKPOINT_MONITOR,
        PostSelectionMaterialization,
        post_selection_checkpoint_catalog,
        post_selection_eval_role_digest,
    )
    from .post_selection_production import (
        build_final_production_run_plan,
        frozen_m3_development_evidence,
    )

    seed = _seed_for_run(plan, evidence)
    run_plan = build_final_production_run_plan(plan, optimizer_seed=seed)
    if run_plan.content_digest != evidence.run_plan_digest:
        raise PostSelectionError(
            "Final-production run evidence does not bind its own run plan."
        )
    catalog = post_selection_checkpoint_catalog(
        run_plan=run_plan,
        checkpoint_directory=context.run_root(run_plan.run_identity) / "checkpoints",
    )
    record = catalog.checkpoint_by_sha256(evidence.representative_checkpoint_sha256)
    representative, monitor_metrics = authenticated_run_representative_records(
        context, run_plan, evidence
    )
    if (
        representative.stable_candidate_identity != evidence.representative_candidate_identity
        or representative.trajectory_point.checkpoint_sha256
        != evidence.representative_checkpoint_sha256
    ):
        raise PostSelectionError(
            "The durable representative record does not describe the checkpoint the "
            "run evidence published."
        )
    if representative.target_metrics.content_digest != monitor_metrics.content_digest:
        raise PostSelectionError(
            "The durable representative record does not carry its own M3 target "
            "metric record."
        )
    # Re-authenticate the M3 role itself.  A metric digest alone is not enough:
    # it must describe the exact frozen monitor artifact and its ordered frame
    # membership from this run's materialization.
    materialization = context.evidence_store.get(
        evidence.materialization_digest, PostSelectionMaterialization.from_dict
    )
    monitor_artifact = materialization.checkpoint_monitor_artifact
    _m3_size, m3_membership, m3_digest = frozen_m3_development_evidence(
        context.selected
    )
    artifact_membership = tuple(str(value) for value in monitor_artifact.frame_uids)
    if (
        artifact_membership != tuple(m3_membership)
        or str(monitor_artifact.membership_digest)
        != digest({"frame_uids": list(m3_membership)})
        or int(monitor_artifact.configuration_count) != int(_m3_size)
    ):
        raise PostSelectionError(
            "Final-production M3 evidence is not the exact frozen monitor role "
            "authorized by the current predecessor lineage."
        )
    expected_role_digest = post_selection_eval_role_digest(
        run_plan=run_plan,
        dataset_role=DATASET_ROLE_CHECKPOINT_MONITOR,
        artifact=monitor_artifact,
    )
    if monitor_metrics.target_role_digest != expected_role_digest:
        raise PostSelectionError(
            "Final-production M3 metrics are bound to a different evaluation role "
            "than the authenticated checkpoint monitor artifact."
        )
    return (
        FinalPublicationSeedEvidence(
            optimizer_seed=run_plan.optimizer_seed,
            run_identity=run_plan.run_identity,
            run_plan_digest=run_plan.content_digest,
            run_evidence_digest=evidence.content_digest,
            representative_candidate_identity=evidence.representative_candidate_identity,
            representative_checkpoint_sha256=evidence.representative_checkpoint_sha256,
            representative_record_digest=representative.content_digest,
            monitor_metric_record_digest=monitor_metrics.content_digest,
            checkpoint_relative_path=record.relative_path,
            admissible=bool(representative.admissible),
        ),
        representative,
    )


def _seed_for_run(plan: Any, evidence: Any) -> int:
    from .post_selection_production import build_final_production_run_plan

    for seed in plan.required_final_seeds:
        if build_final_production_run_plan(plan, optimizer_seed=seed).run_identity == (
            evidence.run_identity
        ):
            return int(seed)
    raise PostSelectionError(
        "Final-production evidence does not correspond to any required production seed."
    )


def _rank_single_best(
    representatives: Sequence[tuple[FinalPublicationSeedEvidence, Any]],
    *,
    selection_policy: Any,
    seed_material_digest: str,
) -> FinalPublicationSeedEvidence:
    """Choose the first canonical admissible representative across seeds.

    The ordering owner is the accepted target-only EVAL2 ordering that already
    chose each seed's representative, applied over the *common* frozen M3
    development evidence.  Replay evidence contributed admissibility only and
    contributes no ranking weight here either.  Tie material descends from the
    final-production plan identity, so the answer does not depend on process
    order, completion order, or when the decision is taken.
    """

    from .eval2 import order_eval2_admissible_candidates

    admissible = [item for item in representatives if item[1].admissible]
    if not admissible:
        raise PostSelectionError(
            "No required production seed produced an admissible representative, so "
            "there is no publishable single best final seed."
        )
    by_identity = {record.stable_candidate_identity: seed for seed, record in admissible}
    if len(by_identity) != len(admissible):
        raise PostSelectionError(
            "Two production seeds report the same representative candidate identity; "
            "the cross-seed ranking is not well defined."
        )
    ordered, _comparisons = order_eval2_admissible_candidates(
        [record for _seed, record in admissible],
        policy=selection_policy,
        seed_material_digest=validate_digest(
            str(seed_material_digest), name="seed_material_digest"
        ),
    )
    return by_identity[ordered[0].stable_candidate_identity]


def decide_final_production_publication(
    context: Any, completion: Any
) -> FinalProductionPublicationDecision:
    """Freeze the published member set from pre-qualification evidence alone."""

    from .post_selection_production import frozen_m3_development_evidence

    plan = completion.plan
    context.selected.require_binding(plan.binding)
    policy = context.production_policy
    if tuple(plan.required_final_seeds) != tuple(policy.production_seeds):
        raise PostSelectionError(
            "The current final-production plan seed matrix does not match the "
            "configured production policy; no publication can be decided."
        )
    pairs = [_seed_evidence_for_run(context, plan, run) for run in completion.runs]
    pairs.sort(key=lambda item: item[0].optimizer_seed)
    if [item[0].optimizer_seed for item in pairs] != list(plan.required_final_seeds):
        raise PostSelectionError(
            "Final-production completion does not cover exactly the required seed "
            "matrix; publication membership is never decided from a partial run set."
        )
    committee = str(policy.committee_policy)
    if committee == COMMITTEE_ALL_QUALIFIED:
        published = [item[0] for item in pairs if item[0].admissible]
        if not published:
            raise PostSelectionError(
                "No required production seed produced an admissible representative, "
                "so the all-qualified committee would be empty."
            )
        member_ids = tuple(item.member_id for item in published)
    elif committee == COMMITTEE_SINGLE_BEST:
        best = _rank_single_best(
            pairs,
            selection_policy=context.method_policies.checkpoint_selection,
            seed_material_digest=plan.content_digest,
        )
        member_ids = (best.member_id,)
    else:  # pragma: no cover - FinalProductionPolicyIdentity restricts the vocabulary
        raise PostSelectionError(f"Unsupported committee policy {committee!r}.")
    _m3_size, _m3_membership, m3_digest = frozen_m3_development_evidence(context.selected)
    return FinalProductionPublicationDecision(
        binding=plan.binding,
        final_plan_digest=plan.content_digest,
        final_production_policy_digest=plan.final_production_policy_digest,
        method_identity_digest=plan.method_identity_digest,
        cv_plan_digest=plan.cv_plan_digest,
        cv_authorization_digest=plan.cv_authorization_digest,
        m3_membership_digest=m3_digest,
        completion_digest=completion.content_digest,
        target_head_name=str(context.method_policies.target_head_name),
        committee_policy=committee,
        decision_policy_identity=FINAL_PUBLICATION_DECISION_POLICY_IDENTITY,
        seed_evidence=tuple(item[0] for item in pairs),
        published_member_ids=member_ids,
    )


def publish_final_production_publication(
    context: Any, campaign_store: Any, completion: Any
) -> FinalProductionPublicationDecision:
    """Decide and publish the current final publication, idempotently."""

    from .post_selection_store import (
        POINTER_FINAL_PUBLICATION,
        POINTER_PREDECESSOR_RECLOSURE,
        post_selection_publication_barrier,
        publish_current_post_selection_pointer,
    )
    from .post_selection_reclosure import build_predecessor_reclosure

    decision = decide_final_production_publication(context, completion)
    # Object publication and the pointers that make them current share the
    # owner's publication barrier: a storage mutation that could reclaim P5
    # evidence acquires the same barrier, so it can never delete an object
    # inside the window in which no pointer references it yet.
    with post_selection_publication_barrier(
        context.paths, context.selected.binding.campaign_generation
    ):
        context.evidence_store.put(decision)
        # P5/P6 reclosure is a separate immutable predecessor record.  It binds
        # the exact decision and the repaired executable source surface before
        # any P7 descendant can expose the product.
        reclosure = build_predecessor_reclosure(context, decision)
        context.evidence_store.put(reclosure)
        publish_current_post_selection_pointer(
            campaign_store,
            binding=context.selected.binding,
            kind=POINTER_PREDECESSOR_RECLOSURE,
            content_digest=reclosure.content_digest,
        )
        publish_current_post_selection_pointer(
            campaign_store,
            binding=context.selected.binding,
            kind=POINTER_FINAL_PUBLICATION,
            content_digest=decision.content_digest,
        )
    return decision


def resolve_current_final_production_publication(
    context: Any,
) -> FinalProductionPublicationDecision | None:
    """Resolve the current published product through freshly established authority.

    ``None`` means no product has been published yet.  A decision that does not
    bind the currently resolved final plan, policy, method, CV authorization,
    M3 lineage, committee policy, or completion is *not* current: it stays on
    disk as historical evidence and is unreachable as the current product.
    """

    from .campaign_post_selection_runtime import (
        resolve_current_final_production_completion,
    )
    from .post_selection_production import frozen_m3_development_evidence
    from .post_selection_reclosure import (
        resolve_current_predecessor_reclosure,
    )
    from .post_selection_store import (
        POINTER_FINAL_PUBLICATION,
        resolve_current_post_selection_record,
    )

    decision = resolve_current_post_selection_record(
        context.store,
        context.paths,
        context.selected,
        kind=POINTER_FINAL_PUBLICATION,
        deserializer=FinalProductionPublicationDecision.from_dict,
    )
    if decision is None:
        return None
    # A publication without the revision-11 predecessor reclosure is an
    # historical P5 object, even if its old decision digest still parses.
    reclosure = resolve_current_predecessor_reclosure(context, decision=decision)
    if reclosure.final_publication_digest != decision.content_digest:
        raise PostSelectionError(
            "The current P5/P6 predecessor reclosure does not bind the published "
            "final-production decision."
        )
    completion = resolve_current_final_production_completion(context)
    if completion is None:
        raise PostSelectionError(
            "A final publication is current but its final-production completion is "
            "not; the published product cannot be authenticated."
        )
    plan = completion.plan
    mismatches = {
        "final_plan_digest": (decision.final_plan_digest, plan.content_digest),
        "final_production_policy_digest": (
            decision.final_production_policy_digest,
            plan.final_production_policy_digest,
        ),
        "method_identity_digest": (
            decision.method_identity_digest,
            plan.method_identity_digest,
        ),
        "cv_plan_digest": (decision.cv_plan_digest, plan.cv_plan_digest),
        "cv_authorization_digest": (
            decision.cv_authorization_digest,
            plan.cv_authorization_digest,
        ),
        "completion_digest": (decision.completion_digest, completion.content_digest),
        "committee_policy": (
            decision.committee_policy,
            str(context.production_policy.committee_policy),
        ),
        "target_head_name": (
            decision.target_head_name,
            str(context.method_policies.target_head_name),
        ),
        "decision_policy_identity": (
            decision.decision_policy_identity,
            FINAL_PUBLICATION_DECISION_POLICY_IDENTITY,
        ),
    }
    _m3_size, _m3_membership, m3_digest = frozen_m3_development_evidence(context.selected)
    mismatches["m3_membership_digest"] = (decision.m3_membership_digest, m3_digest)
    stale = sorted(name for name, (stored, current) in mismatches.items() if stored != current)
    if stale:
        raise PostSelectionError(
            "The published final production binds retired lineage "
            f"({stale}); it remains historical evidence and is not the current "
            "product. Republish through `train-production`."
        )
    # Finally replay the exact P5 decision procedure over every required run.
    # This authenticates the complete seed evidence and ordered member set; the
    # stored digest is never accepted merely because its parent lineage matches.
    recomputed = decide_final_production_publication(context, completion)
    if recomputed.content_digest != decision.content_digest:
        raise PostSelectionError(
            "The published final-production decision does not reproduce from the "
            "current complete P5 seed evidence; it remains historical and cannot "
            "feed a downstream product."
        )
    return decision


__all__ = [
    "COMMITTEE_ALL_QUALIFIED",
    "COMMITTEE_SINGLE_BEST",
    "FINAL_PUBLICATION_DECISION_POLICY_IDENTITY",
    "FINAL_PUBLICATION_DECISION_SCHEMA",
    "FINAL_PUBLICATION_SEED_EVIDENCE_SCHEMA",
    "SUPPORTED_COMMITTEE_POLICIES",
    "FinalProductionPublicationDecision",
    "FinalPublicationSeedEvidence",
    "decide_final_production_publication",
    "member_id_for_seed",
    "publish_final_production_publication",
    "resolve_current_final_production_publication",
]
