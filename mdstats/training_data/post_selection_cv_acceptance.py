"""Target-only cross-validation acceptance for the post-selection method.

The order of operations is the science, and it is fixed:

```text
fresh fold training
 -> checkpoint candidates
 -> mandatory target/replay/physical admissibility
 -> target-only checkpoint selection on the fold's own monitor
 -> freeze representative
 -> outer target evaluation on the held-out fold
 -> fold acceptance
```

A fold whose nonempty candidate set contains no admissible checkpoint has no
representative to freeze and therefore no outer evaluation.  That is still a
completed fold: its verdict is a rejection that names the mandatory
admissibility reasons its candidates actually failed.  An empty candidate set is
missing evidence, never a verdict.

Two separations do the work.  The held-out outer fold is never visible to the
checkpoint-selection owner, so a fold cannot choose the checkpoint that happens
to score well on its own evaluation.  And replay evidence is a *constraint*, not
a score: it can make a checkpoint inadmissible through the TRAIN2 admissibility
policy, but it contributes no weight, bonus, tie-break, or acceptance credit -
ordering among admissible candidates is target-only.

Acceptance is then exact rather than aggregate.  Every required fold of every
required CV seed must pass its configured target-only predicate; a good mean
over folds cannot rescue a failing fold, a missing fold is not a pass, and
cross-fold dispersion stays diagnostic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from ._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
    digest,
    validate_digest,
)
from .campaign_post_selection import PostSelectionError
from .post_selection_cv_plan import PostSelectionCvPlan
from .post_selection_identity import CvValidationPolicyIdentity

#: v2 names the fold outcome explicitly and binds the candidate evidence the
#: outcome was decided from.  v1 records predate the no-admissible outcome, so
#: each of them is a representative-selected fold; they stay readable and
#: re-serialize byte-identically under their own schema.
CV_FOLD_ACCEPTANCE_SCHEMA = "mdstats.post-selection-cv-fold-acceptance.v2"
CV_FOLD_ACCEPTANCE_SCHEMA_V1 = "mdstats.post-selection-cv-fold-acceptance.v1"

CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED = "representative_selected"
CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE = "no_admissible_representative"
CV_FOLD_NO_ADMISSIBLE_REASON = "no_admissible_checkpoint"

CV_SEED_ACCEPTANCE_SCHEMA = "mdstats.post-selection-cv-seed-acceptance.v1"
CV_CAMPAIGN_ACCEPTANCE_SCHEMA = "mdstats.post-selection-cv-campaign-acceptance.v1"

#: Configured acceptance-metric names and the EVAL2 target-metric field each
#: names.  Every entry is target-side; no replay quantity is addressable.
CV_ACCEPTANCE_METRICS: dict[str, str] = {
    "target_force_rmse_ev_per_angstrom": "force_component_rmse_ev_per_angstrom",
    "species_macro_force_rmse_ev_per_angstrom": (
        "species_macro_force_rmse_ev_per_angstrom"
    ),
    "worst_stratum_force_rmse_ev_per_angstrom": (
        "worst_stratum_force_rmse_ev_per_angstrom"
    ),
    "force_error_p95_ev_per_angstrom": "force_error_p95_ev_per_angstrom",
    "force_error_p99_ev_per_angstrom": "force_error_p99_ev_per_angstrom",
    "energy_mae_ev_per_atom": "energy_mae_ev_per_atom",
}


class PostSelectionCvRejectedError(PostSelectionError):
    """The post-selection method failed its cross-validation."""


def cv_acceptance_metric_value(
    metrics: Any, acceptance_metric: str
) -> float:
    """Read the configured target-only acceptance metric from EVAL2 evidence."""

    field = CV_ACCEPTANCE_METRICS.get(str(acceptance_metric))
    if field is None:
        raise TrainingDataInputError(
            f"Unsupported CV acceptance metric {acceptance_metric!r}; the current "
            f"target-only metrics are {sorted(CV_ACCEPTANCE_METRICS)}."
        )
    value = getattr(metrics, field, None)
    if value is None:
        raise PostSelectionError(
            f"The held-out outer evaluation produced no {acceptance_metric!r} value, "
            "so this fold has no acceptance evidence."
        )
    return float(value)


def select_cv_fold_representative(
    candidates: Sequence[Any],
    *,
    selection_policy: Any,
    seed_material_digest: str,
) -> Any | None:
    """Freeze one fold representative from admissible candidates, target-only.

    Both steps are delegated to the current TRAIN2/EVAL2 owners: admissibility
    was already decided per candidate by the checkpoint-admissibility policy
    (which is where replay belongs), and ordering is the accepted target-only
    EVAL2 ordering.  No combined target+replay score exists on this path.

    ``None`` means the candidates exist and every one of them failed mandatory
    admissibility: the fold has no representative, which is a scientific result
    for the fold rather than an execution failure.  No inadmissible candidate is
    ever returned, however it ranks.  An empty candidate set is missing evidence
    and still raises.
    """

    from .eval2 import order_eval2_admissible_candidates

    if not candidates:
        raise PostSelectionError("A CV fold produced no checkpoint candidates.")
    ordered, _comparisons = order_eval2_admissible_candidates(
        candidates,
        policy=selection_policy,
        seed_material_digest=validate_digest(
            str(seed_material_digest), name="seed_material_digest"
        ),
    )
    return ordered[0] if ordered else None


@dataclass(frozen=True, slots=True)
class CvFoldAcceptance:
    """The acceptance record of one exact ``(seed, fold)`` position.

    One record, two lawful outcomes.  A ``representative_selected`` fold binds
    its frozen admissible representative and the held-out outer metric that
    judged it.  A ``no_admissible_representative`` fold binds the candidates
    that all failed mandatory admissibility and carries no representative and
    no outer evidence at all; it is always a rejection.  Mixed states are
    refused at construction rather than normalized.
    """

    cv_plan_digest: str
    run_plan_digest: str
    run_identity: str
    fold_index: int
    cv_seed: int
    representative_candidate_identity: str | None
    representative_checkpoint_record_digest: str | None
    outer_metric_record_digest: str | None
    acceptance_metric: str
    acceptance_maximum: float
    outer_metric_value: float | None
    accepted: bool
    rejection_reasons: tuple[str, ...]
    replay_degradation_ev_per_angstrom: float | None = None
    outcome: str = CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
    #: Content digests of every EVAL2 checkpoint record the outcome was decided
    #: from; the records themselves are durable in the evidence store.
    candidate_record_digests: tuple[str, ...] = ()
    #: Union of the mandatory admissibility reasons across those candidates.
    checkpoint_rejection_reasons: tuple[str, ...] = ()
    serialization_schema: str = field(
        default=CV_FOLD_ACCEPTANCE_SCHEMA, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        for name in ("cv_plan_digest", "run_plan_digest", "run_identity"):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        if self.serialization_schema not in (
            CV_FOLD_ACCEPTANCE_SCHEMA,
            CV_FOLD_ACCEPTANCE_SCHEMA_V1,
        ):
            raise TrainingDataInputError("Unsupported CV fold-acceptance schema.")
        object.__setattr__(self, "fold_index", int(self.fold_index))
        object.__setattr__(self, "cv_seed", int(self.cv_seed))
        object.__setattr__(self, "acceptance_metric", str(self.acceptance_metric))
        object.__setattr__(self, "acceptance_maximum", float(self.acceptance_maximum))
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(sorted({str(v) for v in self.rejection_reasons})),
        )
        if bool(self.accepted) != (len(self.rejection_reasons) == 0):
            raise TrainingDataInputError(
                "CV fold acceptance disagrees with its rejection reasons."
            )
        object.__setattr__(self, "accepted", bool(self.accepted))
        candidates = tuple(
            validate_digest(str(v), name="candidate_record_digest")
            for v in self.candidate_record_digests
        )
        if len(set(candidates)) != len(candidates):
            raise TrainingDataInputError(
                "A CV fold binds the same checkpoint candidate more than once."
            )
        object.__setattr__(self, "candidate_record_digests", tuple(sorted(candidates)))
        object.__setattr__(
            self,
            "checkpoint_rejection_reasons",
            tuple(sorted({str(v) for v in self.checkpoint_rejection_reasons})),
        )
        if self.serialization_schema == CV_FOLD_ACCEPTANCE_SCHEMA_V1:
            if (
                self.outcome != CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
                or candidates
                or self.checkpoint_rejection_reasons
            ):
                raise TrainingDataInputError(
                    "A v1 CV fold acceptance can only record a selected representative."
                )
        elif not candidates:
            raise TrainingDataInputError(
                "A CV fold outcome requires the checkpoint candidates it was decided from."
            )

        if self.outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED:
            identity = str(self.representative_candidate_identity or "").strip()
            if not identity:
                raise TrainingDataInputError(
                    "A fold acceptance requires its frozen representative identity."
                )
            object.__setattr__(self, "representative_candidate_identity", identity)
            for name in ("representative_checkpoint_record_digest", "outer_metric_record_digest"):
                object.__setattr__(
                    self, name, validate_digest(str(getattr(self, name)), name=name)
                )
            if self.outer_metric_value is None:
                raise TrainingDataInputError(
                    "A fold with a representative requires its held-out outer metric."
                )
            object.__setattr__(self, "outer_metric_value", float(self.outer_metric_value))
            if candidates and self.representative_checkpoint_record_digest not in candidates:
                raise TrainingDataInputError(
                    "A fold representative must be one of the fold's checkpoint candidates."
                )
            if self.replay_degradation_ev_per_angstrom is not None:
                object.__setattr__(
                    self,
                    "replay_degradation_ev_per_angstrom",
                    float(self.replay_degradation_ev_per_angstrom),
                )
        elif self.outcome == CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE:
            if any(
                getattr(self, name) is not None
                for name in (
                    "representative_candidate_identity",
                    "representative_checkpoint_record_digest",
                    "outer_metric_record_digest",
                    "outer_metric_value",
                    "replay_degradation_ev_per_angstrom",
                )
            ):
                raise TrainingDataInputError(
                    "A fold without an admissible checkpoint cannot carry representative "
                    "or held-out outer evidence."
                )
            if self.rejection_reasons != (CV_FOLD_NO_ADMISSIBLE_REASON,):
                raise TrainingDataInputError(
                    "A fold without an admissible checkpoint is rejected for exactly that "
                    "reason."
                )
            if not self.checkpoint_rejection_reasons:
                raise TrainingDataInputError(
                    "A fold without an admissible checkpoint must name the mandatory "
                    "admissibility reasons its candidates failed."
                )
        else:
            raise TrainingDataInputError(f"Unsupported CV fold outcome {self.outcome!r}.")

    def _payload(self) -> dict[str, Any]:
        payload = {
            "schema": self.serialization_schema,
            "cv_plan_digest": self.cv_plan_digest,
            "run_plan_digest": self.run_plan_digest,
            "run_identity": self.run_identity,
            "fold_index": self.fold_index,
            "cv_seed": self.cv_seed,
            "representative_candidate_identity": self.representative_candidate_identity,
            "representative_checkpoint_record_digest": (
                self.representative_checkpoint_record_digest
            ),
            "outer_metric_record_digest": self.outer_metric_record_digest,
            "acceptance_metric": self.acceptance_metric,
            "acceptance_maximum": self.acceptance_maximum,
            "outer_metric_value": self.outer_metric_value,
            "accepted": self.accepted,
            "rejection_reasons": list(self.rejection_reasons),
            "replay_degradation_ev_per_angstrom": (
                self.replay_degradation_ev_per_angstrom
            ),
        }
        if self.serialization_schema != CV_FOLD_ACCEPTANCE_SCHEMA_V1:
            payload["outcome"] = self.outcome
            payload["candidate_record_digests"] = list(self.candidate_record_digests)
            payload["checkpoint_rejection_reasons"] = list(
                self.checkpoint_rejection_reasons
            )
        return payload

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CvFoldAcceptance":
        schema = payload.get("schema")
        if schema not in (CV_FOLD_ACCEPTANCE_SCHEMA, CV_FOLD_ACCEPTANCE_SCHEMA_V1):
            raise TrainingDataSerializationError(
                "Unsupported CV fold-acceptance schema."
            )
        current = schema == CV_FOLD_ACCEPTANCE_SCHEMA

        def optional(name: str, kind: Any) -> Any:
            value = payload[name] if current else payload.get(name)
            return None if value is None else kind(value)

        result = cls(
            cv_plan_digest=str(payload["cv_plan_digest"]),
            run_plan_digest=str(payload["run_plan_digest"]),
            run_identity=str(payload["run_identity"]),
            fold_index=int(payload["fold_index"]),
            cv_seed=int(payload["cv_seed"]),
            representative_candidate_identity=optional(
                "representative_candidate_identity", str
            ),
            representative_checkpoint_record_digest=optional(
                "representative_checkpoint_record_digest", str
            ),
            outer_metric_record_digest=optional("outer_metric_record_digest", str),
            acceptance_metric=str(payload["acceptance_metric"]),
            acceptance_maximum=float(payload["acceptance_maximum"]),
            outer_metric_value=optional("outer_metric_value", float),
            accepted=bool(payload["accepted"]),
            rejection_reasons=tuple(str(v) for v in payload["rejection_reasons"]),
            replay_degradation_ev_per_angstrom=(
                None
                if payload.get("replay_degradation_ev_per_angstrom") is None
                else float(payload["replay_degradation_ev_per_angstrom"])
            ),
            outcome=(
                str(payload["outcome"])
                if current
                else CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
            ),
            candidate_record_digests=(
                tuple(str(v) for v in payload["candidate_record_digests"])
                if current
                else ()
            ),
            checkpoint_rejection_reasons=(
                tuple(str(v) for v in payload["checkpoint_rejection_reasons"])
                if current
                else ()
            ),
            serialization_schema=str(schema),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CV fold-acceptance digest mismatch.")
        return result


def build_cv_fold_acceptance(
    *,
    run_plan: Any,
    candidates: Sequence[Any],
    representative: Any | None,
    outer_metrics: Any | None,
    policy: CvValidationPolicyIdentity,
) -> CvFoldAcceptance:
    """Decide one fold from its checkpoint candidates and frozen representative.

    With a representative, the outer evaluation only decides acceptance against
    the configured target-only predicate.  Replay degradation is carried forward
    as a diagnostic; it is not consulted here and cannot turn a target failure
    into a pass.

    Without one, every candidate must have failed mandatory admissibility and
    no outer evidence may exist: the fold is rejected with the union of the
    reasons its candidates actually failed.  Any other combination is an
    impossible state and fails loudly.
    """

    candidates = tuple(candidates)
    if not candidates:
        raise PostSelectionError("A CV fold produced no checkpoint candidates.")
    common = {
        "cv_plan_digest": run_plan.cv_plan_digest,
        "run_plan_digest": run_plan.content_digest,
        "run_identity": run_plan.run_identity,
        "fold_index": run_plan.fold_index,
        "cv_seed": run_plan.optimizer_seed,
        "acceptance_metric": policy.acceptance_metric,
        "acceptance_maximum": policy.acceptance_maximum,
        "candidate_record_digests": tuple(item.content_digest for item in candidates),
        "checkpoint_rejection_reasons": tuple(
            reason for item in candidates for reason in item.rejection_reasons
        ),
    }
    if representative is None:
        if outer_metrics is not None:
            raise PostSelectionError(
                "A CV fold without a representative cannot carry held-out outer "
                "evaluation evidence."
            )
        if any(item.admissible for item in candidates):
            raise PostSelectionError(
                "A CV fold with an admissible checkpoint candidate must freeze a "
                "representative before it can be judged."
            )
        return CvFoldAcceptance(
            **common,
            representative_candidate_identity=None,
            representative_checkpoint_record_digest=None,
            outer_metric_record_digest=None,
            outer_metric_value=None,
            accepted=False,
            rejection_reasons=(CV_FOLD_NO_ADMISSIBLE_REASON,),
            outcome=CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE,
        )
    if not representative.admissible or representative.content_digest not in (
        common["candidate_record_digests"]
    ):
        raise PostSelectionError(
            "A CV fold representative must be an admissible candidate of that fold; "
            "an inadmissible checkpoint is never promoted to a fold representative."
        )
    if outer_metrics is None:
        raise PostSelectionError(
            f"CV fold {run_plan.fold_index} produced no held-out outer evaluation."
        )
    value = cv_acceptance_metric_value(outer_metrics, policy.acceptance_metric)
    reasons: list[str] = []
    if not value <= policy.acceptance_maximum:
        reasons.append("outer_target_metric_above_configured_maximum")
    return CvFoldAcceptance(
        **common,
        representative_candidate_identity=representative.stable_candidate_identity,
        representative_checkpoint_record_digest=representative.content_digest,
        outer_metric_record_digest=outer_metrics.content_digest,
        outer_metric_value=value,
        accepted=not reasons,
        rejection_reasons=tuple(reasons),
        replay_degradation_ev_per_angstrom=(
            representative.replay_degradation_ev_per_angstrom
        ),
    )


@dataclass(frozen=True, slots=True)
class CvSeedAcceptance:
    """Acceptance of one required CV seed/variant across all of its folds."""

    cv_plan_digest: str
    cv_seed: int
    fold_acceptances: tuple[CvFoldAcceptance, ...]
    accepted: bool
    rejection_reasons: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "cv_plan_digest",
            validate_digest(self.cv_plan_digest, name="cv_plan_digest"),
        )
        object.__setattr__(self, "cv_seed", int(self.cv_seed))
        folds = tuple(sorted(self.fold_acceptances, key=lambda item: item.fold_index))
        object.__setattr__(self, "fold_acceptances", folds)
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(sorted({str(v) for v in self.rejection_reasons})),
        )
        if bool(self.accepted) != (len(self.rejection_reasons) == 0):
            raise TrainingDataInputError(
                "CV seed acceptance disagrees with its rejection reasons."
            )
        object.__setattr__(self, "accepted", bool(self.accepted))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CV_SEED_ACCEPTANCE_SCHEMA,
            "cv_plan_digest": self.cv_plan_digest,
            "cv_seed": self.cv_seed,
            "fold_acceptances": [item.to_dict() for item in self.fold_acceptances],
            "accepted": self.accepted,
            "rejection_reasons": list(self.rejection_reasons),
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CvSeedAcceptance":
        if payload.get("schema") != CV_SEED_ACCEPTANCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported CV seed-acceptance schema."
            )
        result = cls(
            cv_plan_digest=str(payload["cv_plan_digest"]),
            cv_seed=int(payload["cv_seed"]),
            fold_acceptances=tuple(
                CvFoldAcceptance.from_dict(item) for item in payload["fold_acceptances"]
            ),
            accepted=bool(payload["accepted"]),
            rejection_reasons=tuple(str(v) for v in payload["rejection_reasons"]),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError("CV seed-acceptance digest mismatch.")
        return result


@dataclass(frozen=True, slots=True)
class CvCampaignAcceptance:
    """Whether the shared method is cross-validated for this exact plan.

    This record is what authorizes final production.  It binds the CV plan, the
    shared method, the CV policy, and the selected binding, so a production run
    can prove it descends from cross-validation of the method it is about to
    execute rather than of some other one.
    """

    cv_plan_digest: str
    method_identity_digest: str
    cv_policy_identity_digest: str
    selected_binding_digest: str
    seed_acceptances: tuple[CvSeedAcceptance, ...]
    accepted: bool
    rejection_reasons: tuple[str, ...]
    cross_fold_dispersion: float | None = None
    dispersion_policy: str = "diagnostic_only"

    def __post_init__(self) -> None:
        for name in (
            "cv_plan_digest",
            "method_identity_digest",
            "cv_policy_identity_digest",
            "selected_binding_digest",
        ):
            object.__setattr__(
                self, name, validate_digest(getattr(self, name), name=name)
            )
        seeds = tuple(sorted(self.seed_acceptances, key=lambda item: item.cv_seed))
        object.__setattr__(self, "seed_acceptances", seeds)
        object.__setattr__(
            self,
            "rejection_reasons",
            tuple(sorted({str(v) for v in self.rejection_reasons})),
        )
        if bool(self.accepted) != (len(self.rejection_reasons) == 0):
            raise TrainingDataInputError(
                "CV campaign acceptance disagrees with its rejection reasons."
            )
        object.__setattr__(self, "accepted", bool(self.accepted))
        if self.cross_fold_dispersion is not None:
            object.__setattr__(
                self, "cross_fold_dispersion", float(self.cross_fold_dispersion)
            )
        if str(self.dispersion_policy) != "diagnostic_only":
            raise PostSelectionError(
                "Cross-fold dispersion is diagnostic-only on the current path."
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": CV_CAMPAIGN_ACCEPTANCE_SCHEMA,
            "cv_plan_digest": self.cv_plan_digest,
            "method_identity_digest": self.method_identity_digest,
            "cv_policy_identity_digest": self.cv_policy_identity_digest,
            "selected_binding_digest": self.selected_binding_digest,
            "seed_acceptances": [item.to_dict() for item in self.seed_acceptances],
            "accepted": self.accepted,
            "rejection_reasons": list(self.rejection_reasons),
            "cross_fold_dispersion": self.cross_fold_dispersion,
            "dispersion_policy": self.dispersion_policy,
        }

    @property
    def content_digest(self) -> str:
        return digest(self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self._payload(), "content_digest": self.content_digest}

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "CvCampaignAcceptance":
        if payload.get("schema") != CV_CAMPAIGN_ACCEPTANCE_SCHEMA:
            raise TrainingDataSerializationError(
                "Unsupported CV campaign-acceptance schema."
            )
        result = cls(
            cv_plan_digest=str(payload["cv_plan_digest"]),
            method_identity_digest=str(payload["method_identity_digest"]),
            cv_policy_identity_digest=str(payload["cv_policy_identity_digest"]),
            selected_binding_digest=str(payload["selected_binding_digest"]),
            seed_acceptances=tuple(
                CvSeedAcceptance.from_dict(item) for item in payload["seed_acceptances"]
            ),
            accepted=bool(payload["accepted"]),
            rejection_reasons=tuple(str(v) for v in payload["rejection_reasons"]),
            cross_fold_dispersion=(
                None
                if payload.get("cross_fold_dispersion") is None
                else float(payload["cross_fold_dispersion"])
            ),
            dispersion_policy=str(payload.get("dispersion_policy", "diagnostic_only")),
        )
        if payload.get("content_digest") not in (None, result.content_digest):
            raise TrainingDataSerializationError(
                "CV campaign-acceptance digest mismatch."
            )
        return result


def _dispersion(values: Sequence[float]) -> float | None:
    if len(values) < 2:
        return None
    mean = sum(values) / len(values)
    variance = sum((value - mean) ** 2 for value in values) / (len(values) - 1)
    return variance**0.5


def accept_post_selection_cv_campaign(
    plan: PostSelectionCvPlan,
    policy: CvValidationPolicyIdentity,
    fold_acceptances: Sequence[CvFoldAcceptance],
) -> CvCampaignAcceptance:
    """Reduce fold outcomes into the one current CV acceptance record.

    The reduction is coverage-first: for each required seed, every configured
    fold must appear exactly once and every one of them must pass.  A duplicate
    fold does not stand in for a missing one, and no average, majority, or
    best-seed rule is representable here.
    """

    for item in fold_acceptances:
        if item.cv_plan_digest != plan.content_digest:
            raise PostSelectionError(
                "A fold acceptance belongs to a different CV plan."
            )
        if item.acceptance_metric != policy.acceptance_metric or (
            item.acceptance_maximum != policy.acceptance_maximum
        ):
            raise PostSelectionError(
                "A fold was judged under a different acceptance predicate than the "
                "current CV policy."
            )

    required_folds = tuple(item.fold_index for item in plan.folds)
    seed_records: list[CvSeedAcceptance] = []
    campaign_reasons: list[str] = []
    for seed in plan.required_cv_seeds:
        present = [item for item in fold_acceptances if item.cv_seed == seed]
        reasons: list[str] = []
        by_fold: dict[int, list[CvFoldAcceptance]] = {}
        for item in present:
            by_fold.setdefault(item.fold_index, []).append(item)
        for fold_index in required_folds:
            occurrences = by_fold.get(fold_index, [])
            if not occurrences:
                reasons.append(f"missing_required_fold_{fold_index}")
            elif len(occurrences) > 1:
                reasons.append(f"duplicate_fold_{fold_index}")
            elif not occurrences[0].accepted:
                # A fold with no admissible checkpoint is present evidence and a
                # completed rejection; only its reason differs.
                reasons.append(
                    f"fold_{fold_index}_failed_target_predicate"
                    if occurrences[0].outcome == CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED
                    else f"fold_{fold_index}_{CV_FOLD_NO_ADMISSIBLE_REASON}"
                )
        unexpected = sorted(set(by_fold) - set(required_folds))
        for fold_index in unexpected:
            reasons.append(f"unexpected_fold_{fold_index}")
        seed_records.append(
            CvSeedAcceptance(
                cv_plan_digest=plan.content_digest,
                cv_seed=seed,
                fold_acceptances=tuple(present),
                accepted=not reasons,
                rejection_reasons=tuple(reasons),
            )
        )
        if reasons:
            campaign_reasons.append(f"cv_seed_{seed}_rejected")

    unexpected_seeds = sorted(
        {item.cv_seed for item in fold_acceptances} - set(plan.required_cv_seeds)
    )
    for seed in unexpected_seeds:
        campaign_reasons.append(f"unexpected_cv_seed_{seed}")

    values = [
        item.outer_metric_value
        for item in fold_acceptances
        if item.outer_metric_value is not None
    ]
    return CvCampaignAcceptance(
        cv_plan_digest=plan.content_digest,
        method_identity_digest=plan.method_identity_digest,
        cv_policy_identity_digest=plan.cv_policy_identity_digest,
        selected_binding_digest=plan.binding.content_digest,
        seed_acceptances=tuple(seed_records),
        accepted=not campaign_reasons,
        rejection_reasons=tuple(campaign_reasons),
        cross_fold_dispersion=_dispersion(values),
    )


def require_cv_acceptance_for_method(
    acceptance: CvCampaignAcceptance,
    *,
    plan: PostSelectionCvPlan,
    method_identity_digest: str,
    selected_binding_digest: str,
) -> None:
    """Fail closed unless this acceptance authorizes the method about to run.

    Cross-validation of one method never authorizes production of another, so
    the method digest, the CV plan, and the selected lineage are all compared
    before any final-production work begins.
    """

    if acceptance.cv_plan_digest != plan.content_digest:
        raise PostSelectionCvRejectedError(
            "The supplied CV acceptance belongs to a different cross-validation plan."
        )
    if acceptance.method_identity_digest != str(method_identity_digest):
        raise PostSelectionCvRejectedError(
            "The accepted cross-validation validated a different training method "
            f"({acceptance.method_identity_digest[:12]}...) than the one final "
            f"production would execute ({str(method_identity_digest)[:12]}...). "
            "Stale CV cannot authorize a changed method."
        )
    if acceptance.cv_policy_identity_digest != plan.cv_policy_identity_digest:
        raise PostSelectionCvRejectedError(
            "The accepted cross-validation validated a different cross-validation policy "
            f"({acceptance.cv_policy_identity_digest[:12]}...) than the CV plan binds "
            f"({plan.cv_policy_identity_digest[:12]}...). "
            "Inconsistent CV policy ancestry cannot authorize production."
        )
    if acceptance.selected_binding_digest != str(selected_binding_digest):
        raise PostSelectionCvRejectedError(
            "The accepted cross-validation descends from a different selected "
            "target-size generation."
        )
    if not acceptance.accepted:
        raise PostSelectionCvRejectedError(
            "The post-selection method is not cross-validation accepted: "
            f"{list(acceptance.rejection_reasons)}. Cross-validation failure is a "
            "methodological result; it never selects another target size, resumes "
            "the target-size screen, or authorizes production anyway."
        )


__all__ = [
    "CV_ACCEPTANCE_METRICS",
    "CV_CAMPAIGN_ACCEPTANCE_SCHEMA",
    "CV_FOLD_ACCEPTANCE_SCHEMA",
    "CV_FOLD_ACCEPTANCE_SCHEMA_V1",
    "CV_FOLD_NO_ADMISSIBLE_REASON",
    "CV_FOLD_OUTCOME_NO_ADMISSIBLE_REPRESENTATIVE",
    "CV_FOLD_OUTCOME_REPRESENTATIVE_SELECTED",
    "CV_SEED_ACCEPTANCE_SCHEMA",
    "CvCampaignAcceptance",
    "CvFoldAcceptance",
    "CvSeedAcceptance",
    "PostSelectionCvRejectedError",
    "accept_post_selection_cv_campaign",
    "build_cv_fold_acceptance",
    "cv_acceptance_metric_value",
    "require_cv_acceptance_for_method",
    "select_cv_fold_representative",
]
