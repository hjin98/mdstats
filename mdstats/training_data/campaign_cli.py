"""User-facing MLFF campaign orchestration facade.

The historical implementation lives in ``_campaign_cli_core`` unchanged. The
facade installs the Protocol-5 single-owner MVSEL2 selection runtime and the
single-owner REPAIR2 orchestration seam before exposing the same module surface.
"""
from __future__ import annotations

from . import _campaign_cli_core as _core
from . import mvsel2_hardening_runtime as _hardening
from . import mvsel2_v5_runtime as _v5_runtime

# G3 leaves runtime code responsible only for REPAIR2 orchestration.  The
# scientific repair loop lives exclusively in target_multi_view_repair_v2.
_hardening.install_campaign_hardening(_core)
_v5_runtime.install_campaign_v5_selection(_core)

# Preserve the historical campaign module surface, including internal helper
# names used by focused regression tests. Function globals continue to resolve
# in _campaign_cli_core, where production overrides are installed before any
# command is executed.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def main(*args, **kwargs):
    return _core.main(*args, **kwargs)


if __name__ == "__main__":
    main()
