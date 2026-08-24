from __future__ import annotations

import numpy as np
import pytest
from ase import Atoms

from mdstats.training_data.model_features import (
    AtomicModelPrediction,
    StaticMaceInferenceExecutor,
)
from mdstats.training_data._common import TrainingDataInputError


def _atoms(count: int = 9):
    return tuple(
        Atoms("H2", positions=[[0, 0, 0], [0, 0, 0.7 + index * 0.01]])
        for index in range(count)
    )


class _Provider:
    def __init__(self, maximum_batch: int = 100):
        self.maximum_batch = maximum_batch
        self.calls = []

    def predict_batch(self, atoms, *, geometry_identities=None, graph_cache_directory=None):
        self.calls.append((len(atoms), None if geometry_identities is None else tuple(geometry_identities)))
        if len(atoms) > self.maximum_batch:
            raise RuntimeError("CUDA out of memory")
        return tuple(
            AtomicModelPrediction(
                energy_ev=float(value.positions[1, 2]),
                forces_ev_per_angstrom=np.full((2, 3), value.positions[1, 2]),
                stress_ev_per_angstrom3=np.eye(3) * value.positions[1, 2],
            )
            for value in atoms
        )


def test_static_executor_batch_matches_batch_one_reference_and_preserves_order() -> None:
    atoms = _atoms()
    reference = StaticMaceInferenceExecutor(_Provider(), batch_size=1).prediction_channels(atoms)
    provider = _Provider()
    observed = StaticMaceInferenceExecutor(provider, batch_size=4).prediction_channels(
        atoms, geometry_identities=tuple(f"g{index}" for index in range(len(atoms)))
    )
    for channel in reference:
        np.testing.assert_allclose(observed[channel], reference[channel], rtol=0.0, atol=0.0)
    assert provider.calls == [(4, ("g0", "g1", "g2", "g3")), (4, ("g4", "g5", "g6", "g7")), (1, ("g8",))]


def test_static_executor_oom_backoff_is_bounded_and_retains_safe_ceiling() -> None:
    provider = _Provider(maximum_batch=2)
    executor = StaticMaceInferenceExecutor(provider, batch_size=8, maximum_oom_backoffs=4)
    predictions = executor.predict(_atoms())
    assert len(predictions) == 9
    assert executor.oom_backoff_count == 2
    assert executor.learned_safe_batch_size == 2
    assert [size for size, _ in provider.calls] == [8, 4, 2, 2, 2, 2, 1]


def test_static_executor_surfaces_batch_one_oom() -> None:
    executor = StaticMaceInferenceExecutor(_Provider(maximum_batch=0), batch_size=2)
    with pytest.raises(RuntimeError, match="out of memory"):
        executor.predict(_atoms(1))


def test_static_executor_prohibits_concurrent_model_shell_sharing() -> None:
    import threading

    entered = threading.Event()
    release = threading.Event()

    class BlockingProvider(_Provider):
        def predict_batch(self, atoms, **kwargs):
            entered.set()
            release.wait(timeout=2.0)
            return super().predict_batch(atoms, **kwargs)

    executor = StaticMaceInferenceExecutor(BlockingProvider(), batch_size=1)
    worker = threading.Thread(target=lambda: executor.predict(_atoms(1)))
    worker.start()
    assert entered.wait(timeout=1.0)
    with pytest.raises(TrainingDataInputError, match="cannot be shared"):
        executor.predict(_atoms(1))
    release.set()
    worker.join(timeout=2.0)
    assert not worker.is_alive()
