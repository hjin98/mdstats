"""Single canonical owner for target-size execution-root layout and locators.

Both the runtime and the retention fence (and any downstream tooling or P5 consumers)
derive the target-size execution root from this leaf module, guaranteeing that the
execution root and its deletion-protection fence never diverge.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

TARGET_SIZE_EXECUTION_ROOT_NAME: str = "target-size"


def _extract_workspace(workspace_or_paths: str | os.PathLike[str] | Any) -> Path:
    if hasattr(workspace_or_paths, "workspace"):
        return Path(workspace_or_paths.workspace).resolve()
    return Path(workspace_or_paths).resolve()


def _extract_internal(workspace_or_paths: str | os.PathLike[str] | Any) -> Path:
    if hasattr(workspace_or_paths, "internal"):
        return Path(workspace_or_paths.internal).resolve()
    workspace = _extract_workspace(workspace_or_paths)
    return workspace / ".mdstats"


def target_size_execution_root(
    workspace_or_paths: str | os.PathLike[str] | Any,
    generation: int | str,
) -> Path:
    """Absolute Path to the campaign-owned target-size execution root for one generation."""

    internal = _extract_internal(workspace_or_paths)
    return internal / TARGET_SIZE_EXECUTION_ROOT_NAME / f"g{int(generation)}"


def target_size_execution_root_locator(
    workspace_or_paths: str | os.PathLike[str] | Any,
    generation: int | str,
) -> str:
    """Campaign-relative POSIX locator for one target-size generation root."""

    workspace = _extract_workspace(workspace_or_paths)
    root = target_size_execution_root(workspace_or_paths, generation)
    return root.relative_to(workspace).as_posix()


__all__ = [
    "TARGET_SIZE_EXECUTION_ROOT_NAME",
    "target_size_execution_root",
    "target_size_execution_root_locator",
]
