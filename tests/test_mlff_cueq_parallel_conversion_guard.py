from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import threading
import time

from mdstats.training_data import model_features


def test_accelerator_graph_rewrites_are_serialized_across_inference_threads() -> None:
    state_lock = threading.Lock()
    active = 0
    peak = 0

    def unsafe_conversion(value: int) -> int:
        nonlocal active, peak
        with state_lock:
            active += 1
            peak = max(peak, active)
            # Reproduce the failure class observed when two FX traces overlap.
            if active > 1:
                active -= 1
                raise NameError("module is not installed as a submodule")
        try:
            time.sleep(0.02)
            return value
        finally:
            with state_lock:
                active -= 1

    module = SimpleNamespace(
        run_e3nn_to_cueq=unsafe_conversion,
        run_e3nn_to_oeq=None,
        run_e3nn_to_hybrid=None,
    )
    model_features._install_thread_safe_mace_accelerator_conversion(module)
    wrapped = module.run_e3nn_to_cueq
    assert wrapped is not unsafe_conversion
    assert wrapped._mdstats_fx_serialized is True

    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(wrapped, range(8)))

    assert results == list(range(8))
    assert peak == 1


def test_accelerator_graph_rewrite_install_is_idempotent() -> None:
    calls: list[int] = []

    def convert(value: int) -> int:
        calls.append(value)
        return value

    module = SimpleNamespace(
        run_e3nn_to_cueq=convert,
        run_e3nn_to_oeq=None,
        run_e3nn_to_hybrid=None,
    )
    model_features._install_thread_safe_mace_accelerator_conversion(module)
    first = module.run_e3nn_to_cueq
    model_features._install_thread_safe_mace_accelerator_conversion(module)
    assert module.run_e3nn_to_cueq is first
    assert first(3) == 3
    assert calls == [3]
