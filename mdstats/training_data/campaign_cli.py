"""User-facing MLFF campaign orchestration facade.

The historical implementation lives in ``_campaign_cli_core`` unchanged.  The
facade installs narrow MVSEL2 hardening overrides before exposing the same
module surface.  REV8 additionally routes the production checkpoint-started
REPAIR2 builder through the shared helper used by bounded qualification.
"""
from __future__ import annotations

from . import _campaign_cli_core as _core
from . import mvsel2_hardening_runtime as _hardening
from .mvsel2_repair_checkpoint_runtime import build_repair_from_checkpoints

# Keep one exact checkpoint-started repair implementation at the production
# orchestration seam.  The original hardening module remains readable history,
# but production and REV8 qualification both call the shared implementation.
_hardening._build_repair_from_checkpoints = build_repair_from_checkpoints
_hardening.install_campaign_hardening(_core)

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
