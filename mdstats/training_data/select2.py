"""SELECT2 physics-qualified lexicographic production selection.

SELECT2 is intentionally a *selection* authority, not another scoring model.  It
consumes final-development EVAL2 representatives and the completed
DEPLOY->PES->RELAX->DYN qualification chain.  Physical evidence has pass/fail
authority only.  Once a candidate is physically eligible, ordering is delegated
to the exact EVAL2 target-only practical-equivalence/bootstrap policy; replay and
rollout metrics never receive positive ranking credit.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Mapping, Sequence
import math

from ._common import TrainingDataInputError, TrainingDataSerializationError, digest, validate_digest
from .eval2 import (
    Eval2BootstrapComparison,
    Eval2CheckpointRecord,
    Eval2RunRecord,
    order_eval2_admissible_candidates,
)
from .train2_policy import CheckpointSelectionPolicy

SELECT2_VERSION = "0.20.176a0"
SELECT2_CANDIDATE_SCHEMA = "mdstats.select2-candidate.v1"
SELECT2_SELECTION_SCHEMA = "mdstats.select2-selection.v2"
SELECT2_FROZEN_CANDIDATE_SCHEMA = "mdstats.select2-frozen-candidate.v1"


def _check_record_digest(payload: Mapping[str, Any], value: str, *, name: str) -> None:
    stored = payload.get("content_digest")
    if stored not in (None, value):
        raise TrainingDataSerializationError(f"{name} content digest mismatch.")


@dataclass(frozen=True, slots=True)
class Select2CandidateRecord:
    """One final-development seed representative entering SELECT2.

    The entire selected EVAL2 checkpoint record is embedded so target ranking can
    be reconstructed without consulting mutable campaign files.  Physical-chain
    digests are nullable because failed candidates must remain visible in the
    immutable decision record rather than disappearing from provenance.
    """

    run_plan_digest: str
    run_id: str
    optimizer_seed: int
    eval2_run_record_digest: str
    selected_checkpoint: Eval2CheckpointRecord
    deploy_verify_run_digest: str | None
    pes_verify_run_digest: str | None
    relax_verify_run_digest: str | None
    dyn_verify_run_digest: str | None
    physical_qualified: bool
    failure_reasons: tuple[str, ...]
    target_only_model_path: str | None = None
    target_only_model_sha256: str | None = None
    mliap_artifact_path: str | None = None
    mliap_artifact_sha256: str | None = None
    serialization_schema: str = field(default=SELECT2_CANDIDATE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != SELECT2_CANDIDATE_SCHEMA:
            raise TrainingDataInputError("Unsupported SELECT2 candidate schema.")
        object.__setattr__(self, "run_plan_digest", validate_digest(self.run_plan_digest, name="run_plan_digest"))
        object.__setattr__(self, "eval2_run_record_digest", validate_digest(self.eval2_run_record_digest, name="eval2_run_record_digest"))
        if not str(self.run_id).strip():
            raise TrainingDataInputError("SELECT2 candidate requires run_id.")
        if int(self.optimizer_seed) < 0:
            raise TrainingDataInputError("SELECT2 optimizer seed must be nonnegative.")
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        for name in (
            "deploy_verify_run_digest", "pes_verify_run_digest",
            "relax_verify_run_digest", "dyn_verify_run_digest",
        ):
            value = getattr(self, name)
            if value is not None:
                object.__setattr__(self, name, validate_digest(value, name=name))
        reasons = tuple(sorted(set(str(v).strip() for v in self.failure_reasons if str(v).strip())))
        object.__setattr__(self, "failure_reasons", reasons)
        if bool(self.physical_qualified) != (len(reasons) == 0):
            raise TrainingDataInputError("SELECT2 physical-qualified flag disagrees with failure reasons.")
        if not self.selected_checkpoint.admissible:
            raise TrainingDataInputError("SELECT2 cannot admit an EVAL2-inadmissible checkpoint representative.")
        if self.physical_qualified:
            if any(getattr(self, name) is None for name in (
                "deploy_verify_run_digest", "pes_verify_run_digest",
                "relax_verify_run_digest", "dyn_verify_run_digest",
            )):
                raise TrainingDataInputError("Physically qualified SELECT2 candidate requires the complete verification chain.")
            for path_name, sha_name in (
                ("target_only_model_path", "target_only_model_sha256"),
                ("mliap_artifact_path", "mliap_artifact_sha256"),
            ):
                path_value = getattr(self, path_name)
                sha_value = getattr(self, sha_name)
                if path_value in (None, "") or sha_value is None:
                    raise TrainingDataInputError("Physically qualified SELECT2 candidate requires deployment artifact identities.")
                object.__setattr__(self, sha_name, validate_digest(sha_value, name=sha_name))
        else:
            # Deployment identities are retained when available, but a failed
            # candidate may legitimately have been eliminated before later gates.
            for sha_name in ("target_only_model_sha256", "mliap_artifact_sha256"):
                sha_value = getattr(self, sha_name)
                if sha_value is not None:
                    object.__setattr__(self, sha_name, validate_digest(sha_value, name=sha_name))

    @property
    def stable_candidate_identity(self) -> str:
        return f"run:{self.run_plan_digest}:seed:{self.optimizer_seed}:checkpoint:{self.selected_checkpoint.trajectory_point.checkpoint_sha256}"

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "optimizer_seed": self.optimizer_seed,
            "eval2_run_record_digest": self.eval2_run_record_digest,
            "selected_checkpoint": self.selected_checkpoint.to_dict(),
            "deploy_verify_run_digest": self.deploy_verify_run_digest,
            "pes_verify_run_digest": self.pes_verify_run_digest,
            "relax_verify_run_digest": self.relax_verify_run_digest,
            "dyn_verify_run_digest": self.dyn_verify_run_digest,
            "physical_qualified": self.physical_qualified,
            "failure_reasons": list(self.failure_reasons),
            "target_only_model_path": self.target_only_model_path,
            "target_only_model_sha256": self.target_only_model_sha256,
            "mliap_artifact_path": self.mliap_artifact_path,
            "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "stable_candidate_identity": self.stable_candidate_identity,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Select2CandidateRecord":
        if payload.get("schema") != SELECT2_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SELECT2 candidate schema.")
        result = cls(
            run_plan_digest=str(payload["run_plan_digest"]),
            run_id=str(payload["run_id"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            eval2_run_record_digest=str(payload["eval2_run_record_digest"]),
            selected_checkpoint=Eval2CheckpointRecord.from_dict(payload["selected_checkpoint"]),
            deploy_verify_run_digest=None if payload.get("deploy_verify_run_digest") is None else str(payload["deploy_verify_run_digest"]),
            pes_verify_run_digest=None if payload.get("pes_verify_run_digest") is None else str(payload["pes_verify_run_digest"]),
            relax_verify_run_digest=None if payload.get("relax_verify_run_digest") is None else str(payload["relax_verify_run_digest"]),
            dyn_verify_run_digest=None if payload.get("dyn_verify_run_digest") is None else str(payload["dyn_verify_run_digest"]),
            physical_qualified=bool(payload["physical_qualified"]),
            failure_reasons=tuple(str(v) for v in payload.get("failure_reasons", ())),
            target_only_model_path=None if payload.get("target_only_model_path") is None else str(payload["target_only_model_path"]),
            target_only_model_sha256=None if payload.get("target_only_model_sha256") is None else str(payload["target_only_model_sha256"]),
            mliap_artifact_path=None if payload.get("mliap_artifact_path") is None else str(payload["mliap_artifact_path"]),
            mliap_artifact_sha256=None if payload.get("mliap_artifact_sha256") is None else str(payload["mliap_artifact_sha256"]),
        )
        _check_record_digest(payload, result.content_digest, name="SELECT2 candidate")
        return result


@dataclass(frozen=True, slots=True)
class Select2SelectionRecord:
    """Immutable target-first decision across physically qualified production seeds."""

    campaign_plan_digest: str
    target_size_study_digest: str
    dyn_verify_campaign_digest: str
    selection_policy: CheckpointSelectionPolicy
    candidates: tuple[Select2CandidateRecord, ...]
    static_order_run_plan_digests: tuple[str, ...]
    qualified_order_run_plan_digests: tuple[str, ...]
    bootstrap_comparisons: tuple[Eval2BootstrapComparison, ...]
    selected_run_plan_digest: str | None
    fallback_count: int
    outcome: str
    decision_reason: str
    serialization_schema: str = field(default=SELECT2_SELECTION_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != SELECT2_SELECTION_SCHEMA:
            raise TrainingDataInputError("Unsupported SELECT2 selection schema.")
        for name in ("campaign_plan_digest", "target_size_study_digest", "dyn_verify_campaign_digest"):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        candidates = tuple(sorted(self.candidates, key=lambda v: (v.optimizer_seed, v.run_id, v.run_plan_digest)))
        if not candidates or len({v.run_plan_digest for v in candidates}) != len(candidates):
            raise TrainingDataInputError("SELECT2 requires unique final-development seed candidates.")
        object.__setattr__(self, "candidates", candidates)
        lookup = {v.run_plan_digest: v for v in candidates}
        static_order = tuple(validate_digest(v, name="static_order_run_plan_digest") for v in self.static_order_run_plan_digests)
        if len(static_order) != len(candidates) or len(set(static_order)) != len(static_order) or set(static_order) != set(lookup):
            raise TrainingDataInputError("SELECT2 static target order must contain every candidate exactly once.")
        order = tuple(validate_digest(v, name="qualified_order_run_plan_digest") for v in self.qualified_order_run_plan_digests)
        expected_order = tuple(v for v in static_order if lookup[v].physical_qualified)
        if order != expected_order:
            raise TrainingDataInputError("SELECT2 qualified order must be the physical-pass filter of the frozen static order.")
        object.__setattr__(self, "static_order_run_plan_digests", static_order)
        object.__setattr__(self, "qualified_order_run_plan_digests", order)
        fallback_count = int(self.fallback_count)
        if fallback_count < 0:
            raise TrainingDataInputError("SELECT2 fallback count cannot be negative.")
        object.__setattr__(self, "fallback_count", fallback_count)
        if self.outcome not in {"selected", "no_physically_qualified_candidate"}:
            raise TrainingDataInputError("Unsupported SELECT2 outcome.")
        if self.outcome == "selected":
            if self.selected_run_plan_digest is None or not order or self.selected_run_plan_digest != order[0]:
                raise TrainingDataInputError("SELECT2 selected outcome must identify the first physically qualified candidate in frozen static order.")
            if fallback_count != static_order.index(self.selected_run_plan_digest):
                raise TrainingDataInputError("SELECT2 fallback count disagrees with the frozen static order.")
        elif self.selected_run_plan_digest is not None or order or fallback_count != len(static_order):
            raise TrainingDataInputError("SELECT2 no-qualified outcome must exhaust the frozen static order.")
        if not str(self.decision_reason).strip():
            raise TrainingDataInputError("SELECT2 requires an explicit decision reason.")

    @property
    def selected_candidate(self) -> Select2CandidateRecord | None:
        if self.selected_run_plan_digest is None:
            return None
        return next(v for v in self.candidates if v.run_plan_digest == self.selected_run_plan_digest)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "target_size_study_digest": self.target_size_study_digest,
            "dyn_verify_campaign_digest": self.dyn_verify_campaign_digest,
            "selection_policy": self.selection_policy.to_dict(),
            "candidates": [v.to_dict() for v in self.candidates],
            "static_order_run_plan_digests": list(self.static_order_run_plan_digests),
            "qualified_order_run_plan_digests": list(self.qualified_order_run_plan_digests),
            "bootstrap_comparisons": [v.to_dict() for v in self.bootstrap_comparisons],
            "selected_run_plan_digest": self.selected_run_plan_digest,
            "fallback_count": self.fallback_count,
            "outcome": self.outcome,
            "decision_reason": self.decision_reason,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Select2SelectionRecord":
        if payload.get("schema") != SELECT2_SELECTION_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SELECT2 selection schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            target_size_study_digest=str(payload["target_size_study_digest"]),
            dyn_verify_campaign_digest=str(payload["dyn_verify_campaign_digest"]),
            selection_policy=CheckpointSelectionPolicy.from_dict(payload["selection_policy"]),
            candidates=tuple(Select2CandidateRecord.from_dict(v) for v in payload["candidates"]),
            static_order_run_plan_digests=tuple(str(v) for v in payload.get("static_order_run_plan_digests", ())),
            qualified_order_run_plan_digests=tuple(str(v) for v in payload.get("qualified_order_run_plan_digests", ())),
            bootstrap_comparisons=tuple(Eval2BootstrapComparison.from_dict(v) for v in payload.get("bootstrap_comparisons", ())),
            selected_run_plan_digest=None if payload.get("selected_run_plan_digest") is None else str(payload["selected_run_plan_digest"]),
            fallback_count=int(payload.get("fallback_count", 0)),
            outcome=str(payload["outcome"]),
            decision_reason=str(payload["decision_reason"]),
        )
        _check_record_digest(payload, result.content_digest, name="SELECT2 selection")
        return result


@dataclass(frozen=True, slots=True)
class Select2FrozenCandidateRecord:
    """Pre-locked-test frozen candidate bytes selected by SELECT2.

    This record intentionally does not claim locked-test success or final post-test
    publication.  It freezes the candidate *before* locked evidence is activated,
    ensuring that the locked test has zero selection authority.
    """

    campaign_plan_digest: str
    selection_record_digest: str
    selected_candidate_digest: str
    run_plan_digest: str
    run_id: str
    optimizer_seed: int
    checkpoint_sha256: str
    checkpoint_epoch: int
    target_model_path: str
    target_model_sha256: str
    mliap_artifact_path: str
    mliap_artifact_sha256: str
    frozen_at_utc: str
    serialization_schema: str = field(default=SELECT2_FROZEN_CANDIDATE_SCHEMA, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.serialization_schema != SELECT2_FROZEN_CANDIDATE_SCHEMA:
            raise TrainingDataInputError("Unsupported SELECT2 frozen-candidate schema.")
        for name in (
            "campaign_plan_digest", "selection_record_digest", "selected_candidate_digest",
            "run_plan_digest", "checkpoint_sha256", "target_model_sha256", "mliap_artifact_sha256",
        ):
            object.__setattr__(self, name, validate_digest(getattr(self, name), name=name))
        if not str(self.run_id).strip() or not str(self.target_model_path).strip() or not str(self.mliap_artifact_path).strip():
            raise TrainingDataInputError("SELECT2 frozen candidate requires run and artifact paths.")
        if int(self.optimizer_seed) < 0 or int(self.checkpoint_epoch) < 0:
            raise TrainingDataInputError("SELECT2 frozen candidate seed/epoch must be nonnegative.")
        object.__setattr__(self, "optimizer_seed", int(self.optimizer_seed))
        object.__setattr__(self, "checkpoint_epoch", int(self.checkpoint_epoch))
        if not str(self.frozen_at_utc).strip():
            raise TrainingDataInputError("SELECT2 frozen candidate requires a freeze timestamp.")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": self.serialization_schema,
            "campaign_plan_digest": self.campaign_plan_digest,
            "selection_record_digest": self.selection_record_digest,
            "selected_candidate_digest": self.selected_candidate_digest,
            "run_plan_digest": self.run_plan_digest,
            "run_id": self.run_id,
            "optimizer_seed": self.optimizer_seed,
            "checkpoint_sha256": self.checkpoint_sha256,
            "checkpoint_epoch": self.checkpoint_epoch,
            "target_model_path": self.target_model_path,
            "target_model_sha256": self.target_model_sha256,
            "mliap_artifact_path": self.mliap_artifact_path,
            "mliap_artifact_sha256": self.mliap_artifact_sha256,
            "frozen_at_utc": self.frozen_at_utc,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Select2FrozenCandidateRecord":
        if payload.get("schema") != SELECT2_FROZEN_CANDIDATE_SCHEMA:
            raise TrainingDataSerializationError("Unsupported SELECT2 frozen-candidate schema.")
        result = cls(
            campaign_plan_digest=str(payload["campaign_plan_digest"]),
            selection_record_digest=str(payload["selection_record_digest"]),
            selected_candidate_digest=str(payload["selected_candidate_digest"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            run_id=str(payload["run_id"]),
            optimizer_seed=int(payload["optimizer_seed"]),
            checkpoint_sha256=str(payload["checkpoint_sha256"]),
            checkpoint_epoch=int(payload["checkpoint_epoch"]),
            target_model_path=str(payload["target_model_path"]),
            target_model_sha256=str(payload["target_model_sha256"]),
            mliap_artifact_path=str(payload["mliap_artifact_path"]),
            mliap_artifact_sha256=str(payload["mliap_artifact_sha256"]),
            frozen_at_utc=str(payload["frozen_at_utc"]),
        )
        _check_record_digest(payload, result.content_digest, name="SELECT2 frozen candidate")
        return result


def build_select2_selection(
    *,
    campaign_plan_digest: str,
    target_size_study_digest: str,
    dyn_verify_campaign_digest: str,
    selection_policy: CheckpointSelectionPolicy,
    candidates: Sequence[Select2CandidateRecord],
) -> Select2SelectionRecord:
    """Build the immutable physics-gated, target-only SELECT2 decision."""

    items = tuple(candidates)
    if not items:
        raise TrainingDataInputError("SELECT2 requires at least one production seed candidate.")

    ranking_checkpoints = tuple(
        replace(
            v.selected_checkpoint,
            trajectory_point=replace(
                v.selected_checkpoint.trajectory_point,
                stable_candidate_identity=v.stable_candidate_identity,
            ),
        )
        for v in items
    )
    checkpoint_to_candidate = {cp.stable_candidate_identity: candidate for cp, candidate in zip(ranking_checkpoints, items)}
    ordered_checkpoints, comparisons = order_eval2_admissible_candidates(
        ranking_checkpoints,
        policy=selection_policy,
        seed_material_digest=digest({
            "schema": "mdstats.select2-bootstrap-seed-material.v1",
            "campaign_plan_digest": campaign_plan_digest,
            "target_size_study_digest": target_size_study_digest,
            "dyn_verify_campaign_digest": dyn_verify_campaign_digest,
            "selection_policy_digest": selection_policy.policy_digest,
        }),
    )
    static_order = tuple(
        checkpoint_to_candidate[checkpoint.stable_candidate_identity].run_plan_digest
        for checkpoint in ordered_checkpoints
    )
    by_run = {v.run_plan_digest: v for v in items}
    qualified_order = tuple(v for v in static_order if by_run[v].physical_qualified)
    if not qualified_order:
        return Select2SelectionRecord(
            campaign_plan_digest=campaign_plan_digest,
            target_size_study_digest=target_size_study_digest,
            dyn_verify_campaign_digest=dyn_verify_campaign_digest,
            selection_policy=selection_policy,
            candidates=items,
            static_order_run_plan_digests=static_order,
            qualified_order_run_plan_digests=(),
            bootstrap_comparisons=comparisons,
            selected_run_plan_digest=None,
            fallback_count=len(static_order),
            outcome="no_physically_qualified_candidate",
            decision_reason="All frozen target-ranked final-development seed candidates failed DEPLOY/PES/RELAX/DYN qualification.",
        )

    winner = by_run[qualified_order[0]]
    fallback_count = static_order.index(winner.run_plan_digest)
    reason = (
        f"Selected seed {winner.optimizer_seed} after {fallback_count} higher-ranked physical failure(s); "
        "the candidate order was frozen from EVAL2 target evidence before DEPLOY/PES/RELAX/DYN pass/fail was applied."
    )
    return Select2SelectionRecord(
        campaign_plan_digest=campaign_plan_digest,
        target_size_study_digest=target_size_study_digest,
        dyn_verify_campaign_digest=dyn_verify_campaign_digest,
        selection_policy=selection_policy,
        candidates=items,
        static_order_run_plan_digests=static_order,
        qualified_order_run_plan_digests=qualified_order,
        bootstrap_comparisons=comparisons,
        selected_run_plan_digest=winner.run_plan_digest,
        fallback_count=fallback_count,
        outcome="selected",
        decision_reason=reason,
    )



__all__ = [
    "SELECT2_VERSION",
    "SELECT2_CANDIDATE_SCHEMA",
    "SELECT2_SELECTION_SCHEMA",
    "SELECT2_FROZEN_CANDIDATE_SCHEMA",
    "Select2CandidateRecord",
    "Select2SelectionRecord",
    "Select2FrozenCandidateRecord",
    "build_select2_selection",
]
