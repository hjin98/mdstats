"""Bounded direct model evaluation.

A scientific evaluation population and an accelerator batch are different
things.  Direct EVAL2 owners used to hand the entire exact-``M`` population to
``provider.predict_batch(...)``, which builds one native derivative-bearing
graph batch and moves it to the device in a single allocation.  Peak VRAM then
scaled with the scientific question rather than with the machine, and the
observed production failure was a CUDA out-of-memory on a boundary whose
population simply did not fit.

The repair is an explicit execution-realization boundary in front of native
graph/device materialization: the exact ordered population is partitioned into
deterministic contiguous chunks, each no wider than the accepted execution
policy, and the per-chunk results are concatenated back in exact role order.
Membership, order, model state, dtype/device, requested observables, and the
downstream reduction are untouched -- chunk width is not a scientific knob and
never changes what is evaluated.

The batch bound is the already accepted ``MaceOptimizerPolicy.valid_batch_size``
of the candidate's execution policy.  It is positive, serialized, and already
part of execution-policy identity, so no second evaluation-batch configuration
is introduced to express the same thing twice.
"""

from __future__ import annotations

from typing import Any, Callable, Sequence

from ._common import TrainingDataInputError

__all__ = [
    "execution_batch_width",
    "run_bounded_inference",
]


def execution_batch_width(optimizer_policy: Any) -> int:
    """The accepted device-batch bound for one direct evaluation role."""

    width = getattr(optimizer_policy, "valid_batch_size", None)
    if width is None:
        raise TrainingDataInputError(
            "Direct evaluation requires the accepted optimizer policy that owns "
            "`valid_batch_size`; there is no separate evaluation batch policy."
        )
    width = int(width)
    if width < 1:
        raise TrainingDataInputError(
            "The accepted execution policy must declare a positive "
            f"`valid_batch_size`; got {width}."
        )
    return width


def run_bounded_inference(
    provider: Any,
    atoms_list: Sequence[Any],
    *,
    batch_width: int,
    forward: Callable[[Any, Sequence[Any]], Sequence[Any]] | None = None,
) -> list[Any]:
    """Evaluate ``atoms_list`` in exact order through bounded device batches.

    ``forward`` is the accepted numerical seam and sits strictly *below* this
    partition owner: it receives one chunk at a time, exactly as the real
    provider does, so a test double cannot silently stand in for the chunking
    decision it is supposed to exercise.

    The same authenticated ``provider`` -- and therefore the same model state --
    evaluates every chunk of one role.
    """

    if batch_width < 1:
        raise TrainingDataInputError(
            "Bounded direct inference requires a positive device-batch width."
        )
    call = forward if forward is not None else (lambda p, chunk: p.predict_batch(chunk))
    predictions: list[Any] = []
    total = len(atoms_list)
    for start in range(0, total, batch_width):
        chunk = list(atoms_list[start : start + batch_width])
        produced = call(provider, chunk)
        if len(produced) != len(chunk):
            raise TrainingDataInputError(
                "Bounded direct inference received "
                f"{len(produced)} prediction(s) for a {len(chunk)}-frame device "
                "batch; the evaluated population and its predictions must "
                "correspond one to one."
            )
        predictions.extend(produced)
    if len(predictions) != total:
        raise TrainingDataInputError(
            "Bounded direct inference produced "
            f"{len(predictions)} prediction(s) for {total} evaluated frame(s)."
        )
    return predictions
