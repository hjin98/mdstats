"""Classify what a selected size still owes before `train-production` spends work.

Three states, and only one of them may train:

``PRODUCT_COMPLETE``
    the exact replayable current decision, its completion, an authenticated
    model publication and a current predecessor reclosure all agree.

``PRODUCT_RECLOSURE``
    the decision and completion are exactly replayable, but the model
    representation and/or the predecessor reclosure is missing, stale, corrupt
    or no longer loadable.  This is a *representation* debt.  Retraining or
    re-running EVAL2 to regenerate a pickle would discard valid scientific
    evidence to fix a serialization problem, so it is explicitly forbidden.

``PRODUCTION_REQUIRED``
    no exact replayable decision exists for the current completion/evidence.
    Only these positions enter the accepted global TRAIN wave.

Classification is an admission hint, never commit authority: every COMPLETE or
RECLOSURE action re-resolves current state under the publication-set lock, and
the pointer commit repeats the upstream validation under the generation
barrier.  A classification taken before another size's TRAIN wave cannot
commit after currentness moved underneath it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .campaign_post_selection import PostSelectionError

PRODUCT_COMPLETE = "PRODUCT_COMPLETE"
PRODUCT_RECLOSURE = "PRODUCT_RECLOSURE"
PRODUCTION_REQUIRED = "PRODUCTION_REQUIRED"


@dataclass(frozen=True, slots=True)
class ProductRecoveryClassification:
    """One selected size's admission state and the parents it already has."""

    state: str
    n_selected: int
    decision: Any | None = None
    model_publication: Any | None = None
    reclosure: Any | None = None
    detail: str = ""

    @property
    def admits_training(self) -> bool:
        return self.state == PRODUCTION_REQUIRED


def replayable_decision_candidate(context: Any) -> Any | None:
    """The pointed decision, re-derived from current evidence, reclosure aside.

    This implementation changes the importable P5/P6 source surface, so every
    pre-existing predecessor reclosure is stale by construction.  The strict
    public resolver correctly refuses such a decision, and applying that rule
    to *migration* would mean a completed, scientifically valid campaign could
    only obtain its new product by retraining - which is the defect this cycle
    exists to remove.

    The bypass is narrow and one-directional: only stale predecessor
    executable-tree currentness is waived.  Selected binding, final plan, CV
    plan/acceptance, method, common monitor, committee policy, completion,
    decision-policy identity and the full committee replay are all still
    required exactly, and the strict public/P7 resolvers keep the reclosure
    requirement.
    """

    from .campaign_post_selection_runtime import (
        resolve_current_final_production_completion,
    )
    from .post_selection_publication import (
        FINAL_PUBLICATION_DECISION_POLICY_IDENTITY,
        FinalProductionPublicationDecision,
        decide_final_production_publication,
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
    completion = resolve_current_final_production_completion(context)
    if completion is None:
        return None
    plan = completion.plan
    expected = {
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
        "common_monitor_record_digest": (
            decision.common_monitor_record_digest,
            plan.common_monitor_record_digest,
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
    if any(stored != current for stored, current in expected.values()):
        return None
    recomputed = decide_final_production_publication(context, completion)
    if recomputed.content_digest != decision.content_digest:
        return None
    return decision


def model_publication_candidate(context: Any, decision: Any) -> Any | None:
    """The pointed model publication, bound to an exactly replayed decision.

    Loaded without declaring it publicly current: it must bind the exact
    decision/member set and every member's bytes must authenticate through the
    shared descriptor owner.  Whether those bytes are still *loadable* is a
    separate question the caller asks only when the runtime or predecessor
    boundary actually changed.
    """

    from .post_selection_model_products import (
        authenticate_model_publication_artifacts,
        resolve_current_final_production_model_publication,
    )

    try:
        record = resolve_current_final_production_model_publication(context, decision)
    except PostSelectionError:
        return None
    if record is None:
        return None
    try:
        authenticate_model_publication_artifacts(context, record)
    except Exception:  # noqa: BLE001 - unauthenticated bytes are not a candidate
        return None
    return record


def current_reclosure_candidate(context: Any, decision: Any) -> Any | None:
    """The pointed predecessor reclosure when it is fully current for ``decision``."""

    from .post_selection_reclosure import (
        PredecessorReclosureRecord,
        validate_predecessor_reclosure,
    )
    from .post_selection_store import (
        POINTER_PREDECESSOR_RECLOSURE,
        resolve_current_post_selection_record,
    )

    try:
        record = resolve_current_post_selection_record(
            context.store,
            context.paths,
            context.selected,
            kind=POINTER_PREDECESSOR_RECLOSURE,
            deserializer=PredecessorReclosureRecord.from_dict,
        )
    except PostSelectionError:
        return None
    if record is None:
        return None
    try:
        validate_predecessor_reclosure(record, context, decision)
    except PostSelectionError:
        return None
    return record


def classify_product_recovery(context: Any) -> ProductRecoveryClassification:
    """Decide what this selected size still owes, before any expensive work."""

    n_selected = int(context.selected.n_selected)
    try:
        decision = replayable_decision_candidate(context)
    except PostSelectionError as exc:
        return ProductRecoveryClassification(
            state=PRODUCTION_REQUIRED, n_selected=n_selected, detail=str(exc)
        )
    if decision is None:
        return ProductRecoveryClassification(
            state=PRODUCTION_REQUIRED,
            n_selected=n_selected,
            detail="no exact replayable final-production decision is current",
        )
    record = model_publication_candidate(context, decision)
    reclosure = current_reclosure_candidate(context, decision)
    if record is None or reclosure is None:
        missing = []
        if record is None:
            missing.append("model publication")
        if reclosure is None:
            missing.append("predecessor reclosure")
        return ProductRecoveryClassification(
            state=PRODUCT_RECLOSURE,
            n_selected=n_selected,
            decision=decision,
            model_publication=record,
            reclosure=reclosure,
            detail=f"representation reclosure required: {', '.join(missing)} is not current",
        )
    return ProductRecoveryClassification(
        state=PRODUCT_COMPLETE,
        n_selected=n_selected,
        decision=decision,
        model_publication=record,
        reclosure=reclosure,
        detail="decision, completion, model publication and predecessor reclosure agree",
    )


def reclose_product_representation(
    context: Any, classification: ProductRecoveryClassification
) -> tuple[Any, Any, Any]:
    """Repair representation and/or reclosure with zero TRAIN2 and zero EVAL2.

    Each descendant is repaired from its own authority.  When only the
    predecessor reclosure is stale, the still-valid model bytes are reused
    unchanged - reserializing them would churn the model-artifact-set digest
    and needlessly invalidate deployment evidence.  When only the
    representation is stale, the exact current predecessor-reclosure object is
    preserved, which is what keeps ``QualificationInputBinding`` and therefore
    the P7 attempt identity unchanged across a representation-only successor.
    """

    from .post_selection_model_products import (
        ModelRepresentationIncompatible,
        current_runtime_compatibility_established,
        model_publication_set_lock,
        prove_existing_representation_reusable,
        publish_final_production_model_products,
    )

    with model_publication_set_lock(context, classification.decision):
        # Re-resolve under the lock: a classification is a hint, and the state
        # it saw may have advanced while another size trained.
        decision = replayable_decision_candidate(context)
        if decision is None or decision.content_digest != (
            classification.decision.content_digest
        ):
            raise PostSelectionError(
                f"N={classification.n_selected}: the final-production decision changed "
                "after recovery classification; no stale reclosure was committed."
            )
        record = model_publication_candidate(context, decision)
        reclosure = current_reclosure_candidate(context, decision)
        if record is not None:
            # Byte/SHA equality cannot answer "does this still load here?".
            # When the recorded serializer/runtime no longer proves the current
            # loader, or the predecessor executable changed (which is exactly
            # the case whenever reclosure is stale), the producer owes a real
            # load plus provider-equivalence proof before reusing the bytes.
            if not current_runtime_compatibility_established(record) or reclosure is None:
                try:
                    prove_existing_representation_reusable(context, record, decision)
                except ModelRepresentationIncompatible as exc:
                    print(
                        f"[P5 reclosure] N={classification.n_selected}: the existing "
                        f"published representation is no longer usable ({exc}); a fresh "
                        "successor representation is published from the same selected "
                        "checkpoint with zero TRAIN2/EVAL2",
                        flush=True,
                    )
                    record = None
        published, reclosed = publish_final_production_model_products(
            context,
            context.store,
            decision,
            existing_reclosure=reclosure,
            existing_model_publication=record,
        )
    return decision, published, reclosed


__all__ = [
    "PRODUCTION_REQUIRED",
    "PRODUCT_COMPLETE",
    "PRODUCT_RECLOSURE",
    "ProductRecoveryClassification",
    "classify_product_recovery",
    "current_reclosure_candidate",
    "model_publication_candidate",
    "reclose_product_representation",
    "replayable_decision_candidate",
]
