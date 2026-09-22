"""One read-only owner for "is this size's usable product current?".

Observation is not a weaker version of execution here; it is a different
question answered from strictly less. It consumes one already-captured
``campaign_owner_snapshot()`` mapping plus the immutable objects that mapping
names, and nothing else: no later live pointer read, no filesystem or evidence
creation, no configuration re-derivation, and - decisively - no MACE
reconstruction. A command that describes a campaign must not be able to change
it, and must not need a GPU to answer.

The one expensive thing it does do is authenticate every current published
model's confined bytes: recorded size and streaming SHA-256 through the shared
descriptor owner. The member count is bounded by the frozen committee, and a
cheap COMPLETE that turns out to name corrupted bytes is worse than a slightly
slower honest one. It still never ``torch.load``s the pickle, so what it
reports is durable byte currentness - not a claim that some arbitrary changed
local loader can consume it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

PRODUCT_STATE_ABSENT = "absent"
PRODUCT_STATE_WAITING = "waiting"
PRODUCT_STATE_BLOCKED = "blocked"
PRODUCT_STATE_COMPLETE = "complete"


@dataclass(frozen=True, slots=True)
class ProductObservation:
    """What one coherent snapshot says about one selected size's product."""

    state: str
    message: str
    decision: Any | None = None
    model_publication: Any | None = None
    reclosure: Any | None = None
    loader_compatibility_advisory: str = ""

    @property
    def complete(self) -> bool:
        return self.state == PRODUCT_STATE_COMPLETE

    @property
    def model_artifact_set_digest(self) -> str | None:
        if self.model_publication is None:
            return None
        return str(self.model_publication.model_artifact_set_digest)


def _authenticated(store: Any, content_digest: str, deserializer: Any) -> Any | None:
    try:
        return store.get(content_digest, deserializer)
    except Exception:  # noqa: BLE001 - every failure is one blocked observation
        return None


def _short(value: Any) -> str:
    text = "" if value is None else str(value)
    return f"{text[:12]}..." if text else "unbound"


def required_final_seed_locators(
    binding: Any, decision: Any, store: Any
) -> tuple[dict[str, str], str | None]:
    """The exact canonical position key/value pairs this decision requires.

    Derived from the *decision-named immutable run evidence*, not by searching
    captured rows for a matching digest.  A historical or otherwise different
    assessment position that happens to hold the same ``run_evidence_digest``
    is a different position, and value membership cannot tell them apart -
    which is precisely how a stale decision would survive a parent advance.

    The canonical digest and the binding-scoped key both come from the existing
    owners; no second position/policy-key algorithm is introduced here.
    """

    from .post_selection_execution import PostSelectionRunEvidence
    from .post_selection_store import (
        ASSESSMENT_ROLE_FINAL_SEED,
        POINTER_ASSESSMENT_POSITION,
        assessment_position_digest,
        post_selection_pointer_key,
    )

    expected: dict[str, str] = {}
    for evidence in decision.seed_evidence:
        record = _authenticated(
            store, evidence.run_evidence_digest, PostSelectionRunEvidence.from_dict
        )
        if record is None:
            return {}, (
                "the final decision names run evidence "
                f"{_short(evidence.run_evidence_digest)} that is missing, unreadable "
                "or does not reproduce its own identity"
            )
        if (
            str(getattr(record, "run_role", "")) != "final_production"
            or record.selected_binding_digest != binding.content_digest
            or int(record.optimizer_seed) != int(evidence.optimizer_seed)
            or str(record.content_digest) != str(evidence.run_evidence_digest)
        ):
            return {}, (
                f"the run evidence named for seed {evidence.optimizer_seed} is not "
                "that seed's final-production assessment under this binding"
            )
        position = assessment_position_digest(
            assessment_role=ASSESSMENT_ROLE_FINAL_SEED,
            assessment_position_policy_digest=(
                record.assessment_position_policy_digest
            ),
            training_trajectory_identity=record.training_trajectory_identity,
            optimizer_seed=record.optimizer_seed,
            fold_index=None,
        )
        key = post_selection_pointer_key(
            binding, POINTER_ASSESSMENT_POSITION, position
        )
        expected[key] = str(evidence.run_evidence_digest)
    return expected, None


def observe_current_product(
    paths: Any, binding: Any, pointers: Mapping[str, str | None]
) -> ProductObservation:
    """Resolve one size's product state from one captured coherent snapshot."""

    from .model_artifact_trust import ModelArtifactTrustError, authenticate_model_artifact
    from .post_selection_model_products import current_runtime_compatibility_established
    from .post_selection_model_publication import FinalProductionModelPublication
    from .post_selection_publication import FinalProductionPublicationDecision
    from .post_selection_reclosure import (
        PredecessorReclosureRecord,
        predecessor_executable_source_tree_digest,
    )
    from .post_selection_store import (
        POINTER_CV_ACCEPTANCE,
        POINTER_CV_PLAN,
        POINTER_FINAL_MODEL_PUBLICATION,
        POINTER_FINAL_PLAN,
        POINTER_FINAL_PUBLICATION,
        POINTER_PREDECESSOR_RECLOSURE,
        open_post_selection_store,
    )
    from .post_selection_model_publication import (
        validate_model_publication_against_decision,
    )

    prefix = f"post_selection:{binding.content_digest}:"
    publication_digest = pointers.get(prefix + POINTER_FINAL_PUBLICATION)
    if publication_digest is None:
        return ProductObservation(
            PRODUCT_STATE_ABSENT, "no final-production publication is current"
        )
    store = open_post_selection_store(paths, binding, create=False)
    decision = _authenticated(
        store, publication_digest, FinalProductionPublicationDecision.from_dict
    )
    if decision is None:
        return ProductObservation(
            PRODUCT_STATE_BLOCKED,
            "the current final-production publication pointer names an object that "
            f"is missing, unreadable, or does not reproduce its own identity "
            f"({_short(publication_digest)})",
        )

    # The decision must descend from the parents that are current *now*, in
    # this same captured instant.  Pointer presence at the decision row alone
    # is never sufficient.
    parents = {
        "final-production plan": (
            pointers.get(prefix + POINTER_FINAL_PLAN),
            decision.final_plan_digest,
        ),
        "CV plan": (pointers.get(prefix + POINTER_CV_PLAN), decision.cv_plan_digest),
        "CV acceptance": (
            pointers.get(prefix + POINTER_CV_ACCEPTANCE),
            decision.cv_authorization_digest,
        ),
    }
    drifted = sorted(
        name for name, (current, bound) in parents.items() if current != bound
    )
    if drifted:
        return ProductObservation(
            PRODUCT_STATE_WAITING,
            "the current final-production publication descends from retired "
            f"{drifted}; it is historical evidence and a fresh publication is "
            "required",
            decision=decision,
        )
    expected_positions, failure = required_final_seed_locators(binding, decision, store)
    if failure is not None:
        return ProductObservation(PRODUCT_STATE_BLOCKED, failure, decision=decision)
    for key, value in sorted(expected_positions.items()):
        observed = pointers.get(key)
        if observed != value:
            return ProductObservation(
                PRODUCT_STATE_WAITING,
                "a required final-seed assessment position has advanced past the "
                "current final-production publication; the publication is historical "
                "and `train-production` must republish",
                decision=decision,
            )

    model_digest = pointers.get(prefix + POINTER_FINAL_MODEL_PUBLICATION)
    if model_digest is None:
        return ProductObservation(
            PRODUCT_STATE_WAITING,
            "the final-production decision is current but no usable full model has "
            "been published for it; rerun `train-production` to reclose the product "
            "representation (no retraining or re-evaluation is performed)",
            decision=decision,
        )
    record = _authenticated(
        store, model_digest, FinalProductionModelPublication.from_dict
    )
    if record is None:
        return ProductObservation(
            PRODUCT_STATE_BLOCKED,
            "the current model-publication pointer names an object that is missing, "
            f"unreadable, or does not reproduce its own identity ({_short(model_digest)})",
            decision=decision,
        )
    try:
        validate_model_publication_against_decision(record, decision)
    except Exception as exc:  # noqa: BLE001 - one blocked observation
        return ProductObservation(
            PRODUCT_STATE_BLOCKED, str(exc), decision=decision, model_publication=record
        )
    models_root = Path(paths.models)
    for member in record.members:
        try:
            authenticate_model_artifact(
                models_root,
                member.model_relative_path,
                expected_sha256=member.model_sha256,
                expected_size_bytes=member.model_size_bytes,
            )
        except ModelArtifactTrustError as exc:
            return ProductObservation(
                PRODUCT_STATE_BLOCKED,
                f"published model for {member.member_id} is not authentic: {exc}",
                decision=decision,
                model_publication=record,
            )
        except OSError as exc:
            return ProductObservation(
                PRODUCT_STATE_BLOCKED,
                f"published model for {member.member_id} is unreadable: {exc}",
                decision=decision,
                model_publication=record,
            )

    reclosure_digest = pointers.get(prefix + POINTER_PREDECESSOR_RECLOSURE)
    if reclosure_digest is None:
        return ProductObservation(
            PRODUCT_STATE_WAITING,
            "the published product has no current P5/P6 predecessor reclosure; rerun "
            "`train-production` to reclose it",
            decision=decision,
            model_publication=record,
        )
    reclosure = _authenticated(
        store, reclosure_digest, PredecessorReclosureRecord.from_dict
    )
    if reclosure is None:
        return ProductObservation(
            PRODUCT_STATE_BLOCKED,
            "the current predecessor-reclosure pointer names an object that is "
            f"missing, unreadable, or does not reproduce its own identity "
            f"({_short(reclosure_digest)})",
            decision=decision,
            model_publication=record,
        )
    reclosure_mismatch = {
        "selected_binding_digest": (
            reclosure.selected_binding_digest,
            decision.binding.content_digest,
        ),
        "final_publication_digest": (
            reclosure.final_publication_digest,
            decision.content_digest,
        ),
        "final_plan_digest": (reclosure.final_plan_digest, decision.final_plan_digest),
        "publication_member_digest": (
            reclosure.publication_member_digest,
            decision.member_digest,
        ),
        "decision_policy_identity": (
            reclosure.decision_policy_identity,
            decision.decision_policy_identity,
        ),
    }
    stale = sorted(
        name for name, (stored, current) in reclosure_mismatch.items() if stored != current
    )
    if stale:
        return ProductObservation(
            PRODUCT_STATE_WAITING,
            f"the current predecessor reclosure does not bind this publication ({stale})",
            decision=decision,
            model_publication=record,
            reclosure=reclosure,
        )
    try:
        current_tree = predecessor_executable_source_tree_digest()
    except Exception:  # noqa: BLE001 - unreadable source is a blocked observation
        current_tree = None
    if current_tree is not None and (
        reclosure.executable_source_tree_digest != current_tree
    ):
        return ProductObservation(
            PRODUCT_STATE_WAITING,
            "the predecessor executable source changed since this product was "
            "reclosed; rerun `train-production` to reclose it (no retraining or "
            "re-evaluation is performed)",
            decision=decision,
            model_publication=record,
            reclosure=reclosure,
        )

    advisory = ""
    if not current_runtime_compatibility_established(record):
        # Status never deserializes the pickle, so it must not claim a changed
        # loader was tested.  It reports exactly what it knows: durable bytes
        # are current, loader compatibility is unverified until a consequential
        # consumer or `train-production` proves it.
        advisory = (
            "the recorded serialization runtime differs from the current supported "
            "loader surface; loader compatibility is unverified until a "
            "consequential consumer or `train-production` proves it"
        )
    return ProductObservation(
        PRODUCT_STATE_COMPLETE,
        "the selected representative checkpoint(s) are published as authenticated "
        f"full MACE model(s) on target head `{record.target_head_name}` "
        f"({len(record.members)} member(s))",
        decision=decision,
        model_publication=record,
        reclosure=reclosure,
        loader_compatibility_advisory=advisory,
    )


__all__ = [
    "PRODUCT_STATE_ABSENT",
    "PRODUCT_STATE_BLOCKED",
    "PRODUCT_STATE_COMPLETE",
    "PRODUCT_STATE_WAITING",
    "ProductObservation",
    "observe_current_product",
    "required_final_seed_locators",
]
