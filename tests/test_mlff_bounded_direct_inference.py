"""Bounded direct EVAL2 execution: the scientific population is not a GPU batch.

The production failure these tests close was a CUDA out-of-memory inside
``run_target_size_direct_boundary_inference``: the exact-``M`` evaluation
population was handed to ``provider.predict_batch`` as one native
derivative-bearing graph batch, so peak VRAM scaled with the boundary's
scientific size rather than with the machine.

Every test here drives the **real** direct-inference owner -- role, boundary
state, evaluation artifact, checkpoint/provider authentication, chunk
orchestration, concatenation, prediction digest, and evidence construction are
all production code.  The only substitution is the per-chunk numerical forward,
which sits strictly below the partition owner and records exactly the widths it
was given, so a test cannot pass while chunking never happens.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

import tests.test_mlff_target_size_execution_p3a as p3a
import tests.test_mlff_target_size_execution_p3c as p3c
import tests.test_mlff_target_size_execution_p3d as p3d
from mdstats.training_data._common import (
    TrainingDataInputError,
    TrainingDataSerializationError,
)
from mdstats.training_data.bounded_inference import (
    execution_batch_width,
    run_bounded_inference,
)
from mdstats.training_data.mace_export import MaceExtxyzPolicy
from mdstats.training_data.protocol import MaceOptimizerPolicy
from mdstats.training_data.target_size_execution import (
    TargetSizePredictionEntry,
    TargetSizePredictionEvidence,
    build_target_size_candidate_trajectory,
    build_target_size_eval2_role,
    build_target_size_screen_schedule,
    evaluate_target_size_boundary,
    run_target_size_direct_boundary_inference,
    target_size_eval2_prediction_digest,
    target_size_population_correlation_blocks,
)
from mdstats.training_data.target_size_execution.context import (
    build_target_size_execution_context,
)
from mdstats.training_data.target_size_execution.evaluation import (
    TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA,
)
from mdstats.training_data.neutral_substrate import (
    build_neutral_split_exclusion_evidence,
)


def _env(tmp_path: Path, *, valid_batch_size: int):
    """A P3 environment whose accepted execution policy bounds EVAL2 batches."""

    manifest, frame_authority, neutral_base, aggregate, common, index = p3a._common(
        tmp_path
    )
    frames, frame_data_by_run, _ = p3a._frame_arrays(tmp_path, manifest)
    schedule = build_target_size_screen_schedule((1, 3, 10))
    optimizer = MaceOptimizerPolicy(
        max_num_epochs=schedule.n3,
        batch_size=4,
        valid_batch_size=int(valid_batch_size),
        device="cpu",
    )
    context = build_target_size_execution_context(
        aggregate.definition, common, schedule, seed_neutral_optimizer_policy=optimizer
    )
    trajectory = build_target_size_candidate_trajectory(
        aggregate.definition,
        context,
        common,
        schedule,
        target_size=aggregate.definition.qualified_candidate_sizes[0],
        optimizer_policy=optimizer,
        optimizer_seed=1,
    )
    return {
        "frame_authority": frame_authority,
        "neutral_base": neutral_base,
        "aggregate": aggregate,
        "common": common,
        "index": index,
        "frames": frames,
        "frame_data_by_run": frame_data_by_run,
        "schedule": schedule,
        "context": context,
        "trajectory": trajectory,
        "optimizer": optimizer,
        "evidence": build_neutral_split_exclusion_evidence(
            frame_authority, neutral_base
        ),
    }


class _RecordingForward:
    """Analytic per-chunk forward that remembers every width it received."""

    def __init__(self, view, *, epsilon: float = 2.5e-3):
        self._view = view
        self._epsilon = epsilon
        self._cursor = 0
        self.widths: list[int] = []
        self.frame_order: list[int] = []

    def __call__(self, provider, atoms_list):
        self.widths.append(len(atoms_list))
        view = self._view
        predictions = []
        for _atoms in atoms_list:
            frame_index = self._cursor % int(view.configuration_count)
            self.frame_order.append(frame_index)
            self._cursor += 1
            start = int(view.force_offsets[frame_index])
            stop = int(view.force_offsets[frame_index + 1])
            stress_3x3 = None
            if bool(view.stress_present[frame_index]):
                flat = np.asarray(
                    view.reference_stresses[frame_index], dtype=np.float64
                )
                stress_3x3 = np.array(
                    [
                        [flat[0], flat[5], flat[4]],
                        [flat[5], flat[1], flat[3]],
                        [flat[4], flat[3], flat[2]],
                    ]
                )
            predictions.append(
                SimpleNamespace(
                    energy_ev=float(view.reference_energies[frame_index]),
                    forces_ev_per_angstrom=np.asarray(
                        view.reference_forces[start:stop], dtype=np.float64
                    )
                    + self._epsilon,
                    stress_ev_per_angstrom3=stress_3x3,
                )
            )
        return predictions


def _direct_inference(tmp_path: Path, *, valid_batch_size: int, boundary: int):
    env = _env(tmp_path, valid_batch_size=valid_batch_size)
    definition = env["aggregate"].definition
    index = env["schedule"].fidelity_epochs.index(boundary)
    evaluation_size = definition.policy.evaluation_sizes[index]
    snapshot = p3d._boundary_snapshot(env, tmp_path, boundary, name="ckpt")
    artifact = p3d._eval_artifact_for(
        env, tmp_path, evaluation_size, name="eval-art"
    )
    materialization = p3d._materialization_for(env, tmp_path)
    role = build_target_size_eval2_role(
        trajectory=env["trajectory"],
        boundary_state=snapshot,
        definition=definition,
        schedule=env["schedule"],
        correlation_blocks=target_size_population_correlation_blocks(
            env["aggregate"], env["evidence"]
        ),
        evaluation_data=artifact,
    )
    view = artifact.build_evaluation_view(tmp_path / "eval-art")
    forward = _RecordingForward(view)
    evidence = run_target_size_direct_boundary_inference(
        trajectory=env["trajectory"],
        materialization=materialization,
        boundary_state=snapshot,
        role=role,
        evaluation_data=artifact,
        canonical_frame_authority=env["frame_authority"],
        definition=definition,
        context=env["context"],
        common=env["common"],
        schedule=env["schedule"],
        optimizer_policy=env["optimizer"],
        extxyz_policy=MaceExtxyzPolicy(),
        frame_catalog=env["frames"],
        frame_data_by_run=env["frame_data_by_run"],
        frame_array_index=env["index"],
        materialization_directory=tmp_path / "materialization",
        snapshot_root=tmp_path / "ckpt_snap",
        evaluation_directory=tmp_path / "eval-art",
        inference_evaluator=forward,
    )
    return env, role, artifact, evidence, forward, evaluation_size


@pytest.mark.parametrize("boundary", [1, 3, 10])
def test_every_device_batch_respects_the_accepted_bound(
    tmp_path: Path, boundary: int
):
    """No forward ever exceeds ``valid_batch_size``, at any exact-M boundary."""

    _env_, _role, _artifact, evidence, forward, evaluation_size = _direct_inference(
        tmp_path, valid_batch_size=2, boundary=boundary
    )
    assert forward.widths, "the bounded forward seam never executed"
    assert max(forward.widths) <= 2
    assert min(forward.widths) >= 1
    assert sum(forward.widths) == evaluation_size
    assert evidence.prediction_count == evaluation_size


def test_population_smaller_than_the_bound_is_one_batch(tmp_path: Path):
    _env_, _role, _artifact, evidence, forward, evaluation_size = _direct_inference(
        tmp_path, valid_batch_size=64, boundary=1
    )
    assert forward.widths == [evaluation_size]
    assert evidence.prediction_count == evaluation_size


def test_non_divisible_population_keeps_exact_order_and_a_short_tail(
    tmp_path: Path,
):
    """``M`` need not be a multiple of the bound; nothing is lost or repeated."""

    _env_, _role, _artifact, evidence, forward, evaluation_size = _direct_inference(
        tmp_path, valid_batch_size=3, boundary=10
    )
    if evaluation_size % 3:
        assert forward.widths[-1] == evaluation_size % 3
    assert forward.frame_order == list(range(evaluation_size))
    assert evidence.prediction_count == evaluation_size


def test_chunked_predictions_equal_the_unchunked_reference(tmp_path: Path):
    """Chunk width is execution realization, never scientific content.

    The concatenated per-chunk predictions must be exactly what one unchunked
    forward over the same ordered population would have produced: same count,
    same order, same payload.  The comparison uses the production prediction
    digest so the harness does not reimplement the evidence it checks.
    """

    import ase.io
    import io as _io

    env, role, artifact, evidence, forward, evaluation_size = _direct_inference(
        tmp_path, valid_batch_size=3, boundary=10
    )
    assert len(forward.widths) > 1, "the population did not exercise several batches"

    raw = (tmp_path / "eval-art" / artifact.relative_path).read_text(encoding="utf-8")
    atoms_list = ase.io.read(_io.StringIO(raw), format="extxyz", index=":")
    reference_forward = _RecordingForward(
        artifact.build_evaluation_view(tmp_path / "eval-art")
    )
    reference = reference_forward(None, atoms_list)
    assert reference_forward.widths == [evaluation_size]

    entries = tuple(
        TargetSizePredictionEntry(
            energy_ev=float(item.energy_ev),
            forces_ev_per_angstrom=np.asarray(
                item.forces_ev_per_angstrom, dtype=np.float64
            ),
            stress_ev_per_angstrom3=(
                None
                if item.stress_ev_per_angstrom3 is None
                else np.asarray(item.stress_ev_per_angstrom3, dtype=np.float64)
            ),
        )
        for item in reference
    )
    assert evidence.prediction_count == evaluation_size
    assert evidence.prediction_payload_digest == target_size_eval2_prediction_digest(
        role, entries
    )


def test_the_accepted_batch_bound_is_execution_policy_identity(tmp_path: Path):
    """`valid_batch_size` is a bound execution identity, not transient pressure.

    Changing it does not touch prepared P1/P2 science, but it does change the
    accepted P3 execution context, so evidence produced under the old bound is
    not silently reusable under the new one.
    """

    narrow = _env(tmp_path / "narrow", valid_batch_size=2)
    wide = _env(tmp_path / "wide", valid_batch_size=16)
    assert (
        narrow["aggregate"].definition.content_digest
        == wide["aggregate"].definition.content_digest
    )
    assert narrow["common"].content_digest == wide["common"].content_digest
    assert narrow["context"].content_digest != wide["context"].content_digest


def test_execution_batch_width_requires_a_positive_accepted_policy():
    assert execution_batch_width(SimpleNamespace(valid_batch_size=8)) == 8
    with pytest.raises(TrainingDataInputError):
        execution_batch_width(SimpleNamespace())
    with pytest.raises(TrainingDataInputError):
        execution_batch_width(SimpleNamespace(valid_batch_size=0))


def test_a_forward_that_answers_for_the_wrong_population_fails_closed():
    """A seam cannot silently stand in for the partition owner it is below."""

    def liar(provider, chunk):
        return ["a", "b", "c"]

    with pytest.raises(TrainingDataInputError):
        run_bounded_inference(object(), [1, 2, 3, 4], batch_width=2, forward=liar)


def test_bounded_inference_uses_the_provider_when_no_seam_is_supplied():
    """Production has no forward override; the real provider sees each chunk."""

    class _Provider:
        def __init__(self) -> None:
            self.widths: list[int] = []

        def predict_batch(self, chunk):
            self.widths.append(len(chunk))
            return [object() for _ in chunk]

    provider = _Provider()
    result = run_bounded_inference(provider, list(range(7)), batch_width=3)
    assert provider.widths == [3, 3, 1]
    assert len(result) == 7


def test_durable_evidence_records_the_population_not_the_device_batch(
    tmp_path: Path,
):
    """`M` is scientific membership; it was never a claim about one forward.

    The runtime defect was repaired at execution, but the durable evidence went
    on recording ``batch_size = M`` -- asserting, for every later reader and
    every replay, that the whole population had been one accelerator batch.
    The field is gone: the deterministic execution partition is `M` together
    with the accepted execution policy's ``valid_batch_size``, and that policy
    is already inside the trajectory identity this evidence binds.
    """

    _env_, _role, _artifact, evidence, forward, evaluation_size = _direct_inference(
        tmp_path, valid_batch_size=3, boundary=10
    )
    assert evaluation_size > 3, "this acceptance needs M > valid_batch_size"
    assert max(forward.widths) <= 3

    payload = evidence.to_dict()
    assert payload["schema"] == TARGET_SIZE_PREDICTION_EVIDENCE_SCHEMA
    assert payload["schema"].endswith(".v2")
    assert "batch_size" not in payload
    assert not hasattr(evidence, "batch_size")
    assert payload["evaluation_size"] == evaluation_size
    assert payload["prediction_count"] == evaluation_size
    # The evidence still authenticates itself exactly.
    assert (
        TargetSizePredictionEvidence.from_dict(payload).content_digest
        == evidence.content_digest
    )


def test_retired_full_batch_prediction_evidence_is_not_current_authority(
    tmp_path: Path,
):
    """A record that still claims `batch_size == M` cannot be read as current."""

    _env_, _role, _artifact, evidence, _forward, evaluation_size = _direct_inference(
        tmp_path, valid_batch_size=3, boundary=10
    )
    retired = dict(evidence.to_dict())
    retired["schema"] = "mdstats.target-size.prediction-evidence.v1"
    retired["batch_size"] = evaluation_size
    retired.pop("content_digest", None)
    with pytest.raises(TrainingDataSerializationError):
        TargetSizePredictionEvidence.from_dict(retired)
