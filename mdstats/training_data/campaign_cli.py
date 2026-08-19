"""User-facing MLFF campaign orchestration facade.

The historical implementation lives in ``_campaign_cli_core`` unchanged.  The
facade installs narrow MVSEL2 hardening overrides before exposing the same
module surface.  REV8 routes both checkpoint-started REPAIR2 and Phase-B resume
rebase through shared resource-bounded exact helpers used by qualification.
"""
from __future__ import annotations

from . import _campaign_cli_core as _core
from . import mvsel2_hardening_runtime as _hardening
from . import target_multi_view_selector_v2 as _selector_v2
from . import target_multi_view_selector_v2_resume as _resume_v2
from .mvsel2_repair_checkpoint_runtime import build_repair_from_checkpoints
from .mvsel2_streaming_frontier import (
    build_target_multi_view_lazy_frontier_v2_streaming,
)

# Keep one exact checkpoint-started repair implementation at the production
# orchestration seam.  Production and REV8 qualification both call it.
_hardening._build_repair_from_checkpoints = build_repair_from_checkpoints

# The streaming frontier preserves canonical FP64 accumulation while releasing
# one family's mmap pages at a time.  Patch both the selector module global and
# the resume module's imported alias before installing the campaign overrides.
_selector_v2.build_target_multi_view_lazy_frontier_v2 = (
    build_target_multi_view_lazy_frontier_v2_streaming
)
_resume_v2.build_target_multi_view_lazy_frontier_v2 = (
    build_target_multi_view_lazy_frontier_v2_streaming
)

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
