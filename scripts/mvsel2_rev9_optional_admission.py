"""Fail-closed REV9 optional-rung admission correction.

The REV9 no-artifact worker originally included a hard-coded 1.0 s/rank floor
when deciding whether the optional 512/1024 REPAIR2 calibration rungs could be
reached.  At 1024 that floor alone charges at least 768 s for 512 remaining
ranks and therefore makes the frozen 585 s operating window impossible to
satisfy regardless of measured current Phase-B performance.

This qualification-only shim replaces exactly that one admission expression
with a conservative measured bound:

    2 * max(observed current Phase-B rank seconds) * remaining + 45 s reserve

The external 900 s hard wall, RSS/scratch limits, selector/repair science, and
10x acceptance floor are unchanged.  The patch is deliberately fail-closed:
if the expected source block is absent or duplicated, qualification aborts
rather than applying an ambiguous transformation.
"""
from __future__ import annotations

import inspect
from typing import Any

import mvsel2_bounded_qualification_noartifacts as base

_OLD = '''                    sampled_max = max(\n                        [float(row["seconds"]) for row in phase_b_rows]\n                        + [float(row["seconds"]) for row in optional_phase_b_rows]\n                        + [1.0]\n                    )\n                    remaining = optional_size - int(state.selected_count)\n                    if elapsed() + 1.5 * remaining * sampled_max > operating_seconds:\n                        break\n'''

_NEW = '''                    observed_rank_seconds = (\n                        [float(row["seconds"]) for row in phase_b_rows]\n                        + [float(row["seconds"]) for row in optional_phase_b_rows]\n                    )\n                    if not observed_rank_seconds:\n                        break\n                    sampled_max = max(observed_rank_seconds)\n                    remaining = optional_size - int(state.selected_count)\n                    projected_optional_seconds = (\n                        2.0 * remaining * sampled_max + 45.0\n                    )\n                    admission_ok = (\n                        elapsed() + projected_optional_seconds <= operating_seconds\n                    )\n                    print(\n                        "[REV9 LQ3 admission] "\n                        f"target={optional_size}; remaining={remaining}; "\n                        f"observed-max-rank={sampled_max:.6f}s; "\n                        f"projected-optional={projected_optional_seconds:.1f}s; "\n                        f"elapsed={elapsed():.1f}s; operating={operating_seconds:.1f}s; "\n                        f"admit={'yes' if admission_ok else 'no'}",\n                        flush=True,\n                    )\n                    if not admission_ok:\n                        break\n'''


def _patched_worker() -> Any:
    source = inspect.getsource(base._worker)
    count = source.count(_OLD)
    if count != 1:
        raise RuntimeError(
            "REV9 optional-admission shim source mismatch: "
            f"expected exactly one frozen admission block, found {count}"
        )
    patched = source.replace(_OLD, _NEW, 1)
    namespace = dict(base.__dict__)
    exec(compile(patched, str(base.__file__), "exec"), namespace, namespace)
    worker = namespace.get("_worker")
    if not callable(worker):
        raise RuntimeError("REV9 optional-admission shim failed to construct worker")
    return worker


_PATCHED_WORKER = _patched_worker()


def install(engine: Any) -> None:
    """Install the corrected REV9 worker into the frozen supervisor."""
    engine._worker = lambda args: _PATCHED_WORKER(engine, args)
