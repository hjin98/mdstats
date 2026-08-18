from __future__ import annotations

import io
import json
import os
from pathlib import Path
import pickle
import tempfile
import time
import warnings

import numpy as np

from mdstats.training_data._array_pickle import dump_with_array_references, load_with_array_references


def timed(call, repeats: int = 3) -> float:
    samples = []
    for _ in range(repeats):
        start = time.perf_counter()
        call()
        samples.append(time.perf_counter() - start)
    return float(np.median(samples))


def worker_transport_benchmark(root: Path) -> dict[str, float | int | bool]:
    source = root / "frame-array.npy"
    array = np.arange(8_000_000, dtype=np.float64).reshape(2_000_000, 4)
    np.save(source, array, allow_pickle=False)
    mapped = np.load(source, mmap_mode="r", allow_pickle=False)
    task = {"positions": mapped, "slice": mapped[100:200]}

    standard_path = root / "standard.pkl"
    reference_path = root / "reference.pkl"
    refs = root / "refs"

    def standard_write() -> None:
        with standard_path.open("wb") as handle:
            pickle.dump(task, handle, protocol=5)

    def reference_write() -> None:
        with reference_path.open("wb") as handle:
            dump_with_array_references(task, handle, array_directory=refs)

    standard_seconds = timed(standard_write, repeats=2)
    reference_seconds = timed(reference_write, repeats=3)
    with reference_path.open("rb") as handle:
        restored = load_with_array_references(handle)
    return {
        "array_bytes": int(mapped.nbytes),
        "standard_pickle_bytes": int(standard_path.stat().st_size),
        "reference_pickle_bytes": int(reference_path.stat().st_size),
        "pickle_size_reduction_factor": float(standard_path.stat().st_size / reference_path.stat().st_size),
        "standard_write_seconds": standard_seconds,
        "reference_write_seconds": reference_seconds,
        "write_speedup": float(standard_seconds / reference_seconds),
        "restored_is_memmap": isinstance(restored["positions"], np.memmap),
        "restored_equal": bool(np.array_equal(restored["positions"], mapped)),
    }


def graph_cache_benchmark() -> dict[str, float | int | bool | str]:
    os.environ.setdefault("TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD", "1")
    try:
        import torch
        from ase import Atoms
        from e3nn import o3
        from mace import data as mace_data, modules
        from mace.calculators import MACECalculator
        from mdstats.training_data.model_features import (
            MaceCalculatorProvider,
            MaceDescriptorPolicy,
            ModelCheckpointIdentity,
            clear_mace_graph_batch_cache,
        )
    except Exception as exc:
        return {"available": False, "reason": f"{type(exc).__name__}: {exc}"}

    previous_dtype = torch.get_default_dtype()
    torch.set_default_dtype(torch.float64)
    try:
        def provider():
            model = modules.MACE(
                r_max=4.0,
                num_bessel=4,
                num_polynomial_cutoff=5,
                max_ell=1,
                interaction_cls=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
                interaction_cls_first=modules.interaction_classes["RealAgnosticResidualInteractionBlock"],
                num_interactions=2,
                num_elements=2,
                hidden_irreps=o3.Irreps("4x0e + 4x1o"),
                MLP_irreps=o3.Irreps("4x0e"),
                gate=torch.nn.functional.silu,
                atomic_energies=np.asarray([0.0, 0.0], dtype=np.float64),
                avg_num_neighbors=2.0,
                atomic_numbers=[1, 8],
                correlation=2,
                radial_type="bessel",
            )
            calc = MACECalculator(models=model, device="cpu", default_dtype="float64")
            identity = ModelCheckpointIdentity(
                model_family="MACE",
                checkpoint_locator="benchmark",
                checkpoint_sha256="0" * 64,
                calculator_class="mace.calculators.mace.MACECalculator",
                model_version="0.3.16",
                supported_atomic_numbers=(1, 8),
                device="cpu",
                default_dtype="float64",
            )
            return MaceCalculatorProvider.from_calculator(calc, checkpoint_identity=identity)

        atoms = tuple(
            Atoms(
                "H2O",
                positions=((0.0, 0.0, 0.0), (0.8 + 0.002 * index, 0.0, 0.0), (0.0, 0.8, 0.0)),
                cell=(8.0, 8.0, 8.0),
                pbc=True,
            )
            for index in range(32)
        )
        policy = MaceDescriptorPolicy()
        calls = 0
        original = mace_data.AtomicData.from_config

        def counted(*args, **kwargs):
            nonlocal calls
            calls += 1
            return original(*args, **kwargs)

        mace_data.AtomicData.from_config = counted
        try:
            clear_mace_graph_batch_cache()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                first = provider()
                second = provider()
            start = time.perf_counter()
            first.get_descriptors_batch(atoms, policy)
            first_seconds = time.perf_counter() - start
            calls_after_first = calls
            start = time.perf_counter()
            second.get_descriptors_batch(atoms, policy)
            cached_seconds = time.perf_counter() - start
            calls_after_second = calls
        finally:
            mace_data.AtomicData.from_config = original
            clear_mace_graph_batch_cache()
        return {
            "available": True,
            "structures": len(atoms),
            "first_seconds": first_seconds,
            "cached_seconds": cached_seconds,
            "speedup": float(first_seconds / cached_seconds),
            "graph_build_calls_first": calls_after_first,
            "graph_build_calls_after_cached": calls_after_second,
            "cached_rebuilt_graphs": calls_after_second != calls_after_first,
        }
    finally:
        torch.set_default_dtype(previous_dtype)


def columnar_weight_estimate(frame_count: int = 36_759) -> dict[str, float | int]:
    # Four float64 columns plus one object/reference slot per UID/reason.  The
    # numeric resident portion is exact; Python-record estimate is deliberately
    # conservative and excludes referenced string contents shared by records.
    numeric_bytes = frame_count * 4 * 8
    object_slots = frame_count * 2 * 8
    record_object_floor = frame_count * 56
    return {
        "frame_count": frame_count,
        "columnar_numeric_bytes": numeric_bytes,
        "columnar_object_slot_bytes": object_slots,
        "columnar_resident_floor_bytes": numeric_bytes + object_slots,
        "legacy_record_object_floor_bytes": record_object_floor,
        "minimum_resident_reduction_factor": float(record_object_floor / (numeric_bytes + object_slots)),
    }


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="mdstats-rev4-benchmark-") as raw:
        root = Path(raw)
        result = {
            "schema": "mdstats.mlff-runtime-optimization-rev4-benchmark.v1",
            "worker_transport": worker_transport_benchmark(root),
            "mace_graph_cache": graph_cache_benchmark(),
            "data7_columnar_weights": columnar_weight_estimate(),
        }
    output = Path("benchmarks/benchmark_mlff_runtime_optimization_rev4_results.json")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
