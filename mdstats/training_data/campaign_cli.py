"""User-facing MLFF campaign orchestration facade.

The implementation lives in :mod:`_campaign_cli_core`.  The facade re-exports
that module surface so ``mdstats.training_data.campaign_cli`` remains the stable
public entry point for the campaign commands.

Historical pre-cutover selector runtimes are not installed through this facade.
The current runtime has exactly one target-size architecture: `prepare` owns the
restored `P_train -> TargetCoverageReference -> FEAS1/NEIGHBOR1 -> MVIDX ->
MVSEL2/REPAIR2 -> pi_train -> MVQUAL` chain, and downstream commands consume its
authenticated compact projection.
"""
from __future__ import annotations

import sys
from typing import Sequence

from . import _campaign_cli_core as _core

# Preserve the campaign module surface, including internal helper names used by
# focused regression tests.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

# Star imports expose only the intentionally small current command surface.
# Focused owner tests may still access private helpers directly, but historical
# compatibility names are never promoted through the facade's public API.
__all__ = list(_core.__all__)

def main(argv: Sequence[str] | None = None) -> int:
    return _core.main(argv)


if __name__ == "__main__":
    main()
