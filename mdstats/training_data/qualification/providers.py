"""Model access for qualification, always through the accepted P5 owner.

Qualification never loads a checkpoint itself.  It asks the same TRAIN2 provider
owner the target-size screen and post-selection evaluation use, so the frozen
representative checkpoint of a published member is authenticated by exactly one
implementation.  The only substitutable seam is the numerical forward, which is
the already accepted P5 inference seam - the owner boundary stays above it.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Sequence

import numpy as np

from ..campaign_post_selection_runtime import POST_SELECTION_EVALUATION_MODEL_STATE
from ..post_selection_execution import (
    PostSelectionMaterialization,
    PostSelectionRunEvidence,
    authenticate_post_selection_provider,
)
from .errors import QualificationError, QualificationLineageError
from .publication import PublishedProductionMember, authenticate_member_bytes


def _run_evidence(context: Any, member: PublishedProductionMember) -> PostSelectionRunEvidence:
    return context.evidence_store.get(
        member.run_evidence_digest, PostSelectionRunEvidence.from_dict
    )


@contextmanager
def member_provider(context: Any, member: PublishedProductionMember) -> Iterator[Any]:
    """Authenticate one published member's model and release it deterministically."""

    from ..train2_runtime import load_train2_runtime_summary

    authenticate_member_bytes(context, member)
    evidence = _run_evidence(context, member)
    if evidence.representative_checkpoint_sha256 != member.representative_checkpoint_sha256:
        raise QualificationLineageError(
            "Published member evidence does not bind its own representative checkpoint."
        )
    materialization = context.evidence_store.get(
        evidence.materialization_digest, PostSelectionMaterialization.from_dict
    )
    run_root = context.run_root(member.run_identity)
    checkpoint_directory = run_root / "checkpoints"
    summary = load_train2_runtime_summary(checkpoint_directory)
    provider, _evaluated = authenticate_post_selection_provider(
        materialization=materialization,
        materialization_directory=run_root / "materialization",
        checkpoint_directory=checkpoint_directory,
        checkpoint_name=Path(member.checkpoint_relative_path).name,
        checkpoint_sha256=member.representative_checkpoint_sha256,
        summary=summary,
        evaluation_model_state=POST_SELECTION_EVALUATION_MODEL_STATE,
        allow_forward_override=context.inference_evaluator is not None,
    )
    try:
        yield provider
    finally:
        _retire(provider)


def _retire(provider: Any) -> None:
    for name in ("retire", "close", "release"):
        method = getattr(provider, name, None)
        if callable(method):
            try:
                method()
            except Exception:
                pass
            return


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


__all__ = ["energy_of", "forces_of", "member_provider", "predict_all"]
