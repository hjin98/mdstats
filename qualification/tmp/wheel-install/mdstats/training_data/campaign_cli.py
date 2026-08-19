"""User-facing MLFF campaign orchestration facade.

The historical implementation lives in ``_campaign_cli_core`` unchanged.  The
facade installs narrow MVSEL2 hardening overrides before exposing the same
module surface.  This keeps the broad campaign implementation byte-identical
while making the v2 runtime switch reviewable and removable as one local seam.
"""
from __future__ import annotations

from . import _campaign_cli_core as _core
from .mvsel2_hardening_runtime import install_campaign_hardening

install_campaign_hardening(_core)

# Preserve the pre-hardening campaign module surface, including internal helper
# names used by focused regression tests.  Function globals continue to resolve
# in _campaign_cli_core, where the two v2 orchestration functions were patched
# before any command is executed.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def main(*args, **kwargs):
    return _core.main(*args, **kwargs)


if __name__ == "__main__":
    main()
