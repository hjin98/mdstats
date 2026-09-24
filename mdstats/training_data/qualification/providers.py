"""Model access for qualification, always through the accepted P5 owner.

Qualification never loads a checkpoint itself.  It asks the same TRAIN2 provider
owner the target-size screen and post-selection evaluation use, so the frozen
representative checkpoint of a published member is authenticated by exactly one
implementation.  The only substitutable seam is the numerical forward, which is
the already accepted P5 inference seam - the owner boundary stays above it.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, Sequence

import numpy as np

from ..post_selection_execution import (
    PostSelectionRunEvidence,
)
from .errors import QualificationError, QualificationLineageError
from .publication import PublishedProductionMember, authenticate_member_bytes
from .stress import stress_of


def _run_evidence(context: Any, member: PublishedProductionMember) -> PostSelectionRunEvidence:
    return context.evidence_store.get(
        member.run_evidence_digest, PostSelectionRunEvidence.from_dict
    )


@contextmanager
def member_provider(context: Any, member: PublishedProductionMember) -> Iterator[Any]:
    """Authenticate one published member's model and release it deterministically.

    The reconstruction itself belongs to the P5 owner and is *called*, not
    reimplemented: qualification checks its own lineage preconditions and then
    hands the exact selected member to the same reconstruction path that
    produces the published product.  Two copies of MACE checkpoint
    authentication is precisely how one of them ends up weaker.
    """

    from ..post_selection_model_products import selected_representative_provider

    authenticate_member_bytes(context, member)
    evidence = _run_evidence(context, member)
    if evidence.representative_checkpoint_sha256 != member.representative_checkpoint_sha256:
        raise QualificationLineageError(
            "Published member evidence does not bind its own representative checkpoint."
        )
    if evidence.training_root_identity != member.run_identity:
        raise QualificationLineageError(
            "Published member does not name the training root its assessment binds."
        )
    with selected_representative_provider(
        context,
        run_identity=member.run_identity,
        checkpoint_relative_path=member.checkpoint_relative_path,
        representative_checkpoint_sha256=member.representative_checkpoint_sha256,
        materialization_digest=evidence.materialization_digest,
        optimizer_seed=member.optimizer_seed,
        # The one substitutable seam remains the accepted P5 numerical forward.
        # It can never be the source of a *published* model, which is why the
        # publication owner passes False unconditionally.
        allow_forward_override=context.inference_evaluator is not None,
    ) as (provider, _evaluated):
        yield provider


def predict_all(context: Any, provider: Any, atoms_list: Sequence[Any]) -> tuple[Any, ...]:
    """Predict through the accepted seam, or through the real provider."""

    if not atoms_list:
        return ()
    evaluator = context.inference_evaluator
    if evaluator is not None:
        predictions = tuple(evaluator(provider, list(atoms_list)))
    else:
        predictions = tuple(provider.predict(atoms) for atoms in atoms_list)
    if len(predictions) != len(atoms_list):
        raise QualificationError(
            "The model forward returned a different number of predictions than "
            "configurations it was given."
        )
    return predictions


def forces_of(prediction: Any) -> np.ndarray:
    return np.asarray(prediction.forces_ev_per_angstrom, dtype=np.float64)


def energy_of(prediction: Any) -> float:
    return float(prediction.energy_ev)


__all__ = ["energy_of", "forces_of", "member_provider", "predict_all", "stress_of"]
