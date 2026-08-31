"""User-facing MLFF campaign orchestration facade.

The implementation lives in :mod:`_campaign_cli_core`.  The facade re-exports
that module surface so ``mdstats.training_data.campaign_cli`` remains the stable
public entry point for the campaign commands.

The retired MVSEL2/REPAIR2/MVQUAL2/MVIDX1 selection runtimes that this facade
used to install into the core module were removed with the destructive
target-size generation cutover: the current runtime has exactly one target-size
architecture and no installable alternative selection engine.
"""
from __future__ import annotations

from . import _campaign_cli_core as _core

# Preserve the campaign module surface, including internal helper names used by
# focused regression tests.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def main(*args, **kwargs):
    return _core.main(*args, **kwargs)


if __name__ == "__main__":
    main()
