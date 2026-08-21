"""Deprecated compatibility import for pre-G3 REPAIR2 runtime callers.

REPAIR2 scientific execution is owned exclusively by
:mod:`target_multi_view_repair_v2`.  The former checkpoint runtime contained a
second per-rung repair algorithm and is intentionally retired.  The remaining
name delegates to the orchestration-only compatibility facade so older focused
callers fail neither import nor lineage checks while no duplicate science
remains here.
"""
from __future__ import annotations

from .mvsel2_hardening_runtime import (
    _build_repair_from_checkpoints as build_repair_from_checkpoints,
)

__all__ = ["build_repair_from_checkpoints"]
