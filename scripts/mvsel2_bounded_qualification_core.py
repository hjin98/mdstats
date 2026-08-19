#!/usr/bin/env python3
"""Authority-cache wrapper for the REV8 qualification compatibility launcher.

This wrapper prevents the missing-plan recovery shim from opening a second copy
of the production TARGET-DATA2B reference and native-forward MVIDX authority.
The first read performed by the frozen worker is cached per process and reused
by the recovery launcher.  Scientific content, read-only semantics, and the
REV8 hard resource ceilings are unchanged.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from mdstats.training_data import target_coverage_store as _reference_store
from mdstats.training_data import target_coverage_sparse_index_store as _forward_store

_ORIGINAL_READ_REFERENCE = _reference_store.read_target_coverage_native_record
_ORIGINAL_READ_FORWARD = _forward_store.read_target_coverage_sparse_index_forward_view_native_record
_REFERENCE_CACHE: dict[tuple[str, str], Any] = {}
_FORWARD_CACHE: dict[tuple[str, str], Any] = {}


def _cache_key(pointer: Mapping[str, Any], root: str | Path) -> tuple[str, str]:
    identity = str(
        pointer.get("content_digest")
        or pointer.get("pointer_digest")
        or pointer.get("sha256")
        or repr(sorted(pointer.items()))
    )
    return str(Path(root).resolve()), identity


def _cached_read_reference(pointer: Mapping[str, Any], root: str | Path) -> Any:
    key = _cache_key(pointer, root)
    cached = _REFERENCE_CACHE.get(key)
    if cached is not None:
        return cached
    value = _ORIGINAL_READ_REFERENCE(pointer, root)
    _REFERENCE_CACHE[key] = value
    return value


def _cached_read_forward(pointer: Mapping[str, Any], root: str | Path) -> Any:
    key = _cache_key(pointer, root)
    cached = _FORWARD_CACHE.get(key)
    if cached is not None:
        return cached
    value = _ORIGINAL_READ_FORWARD(pointer, root)
    _FORWARD_CACHE[key] = value
    return value


_reference_store.read_target_coverage_native_record = _cached_read_reference
_forward_store.read_target_coverage_sparse_index_forward_view_native_record = _cached_read_forward

import mvsel2_bounded_qualification_recovery as recovery

# The frozen engine constructs its worker subprocess from engine.__file__.  Keep
# every worker launch routed through this cache wrapper so the same no-duplicate
# authority rule applies in supervisor and worker mode.
recovery.engine.__file__ = __file__


if __name__ == "__main__":
    raise SystemExit(recovery.engine.main())
