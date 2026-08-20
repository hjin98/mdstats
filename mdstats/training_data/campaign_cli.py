"""User-facing MLFF campaign orchestration facade.

The historical implementation lives in ``_campaign_cli_core`` unchanged. The
facade installs the narrow MVSEL2 production overrides before exposing the same
module surface.
"""
from __future__ import annotations

from . import _campaign_cli_core as _core
from . import mvsel2_hardening_runtime as _hardening
from . import target_multi_view_selector_v2 as _selector_v2
from . import target_multi_view_selector_v2_resume as _resume_v2
from .mvsel2_phase_a_kernel import (
    choose_target_multi_view_phase_a_candidate_v2_kernel,
)
from .mvsel2_repair_checkpoint_runtime import build_repair_from_checkpoints
from .mvsel2_streaming_frontier import (
    build_target_multi_view_lazy_frontier_v2_streaming,
)

# Protocol-5 G1 production scoring authority. PAR1 threading is retired; the
# compatibility ``workers`` argument is accepted by the kernel but does not
# create Python worker threads. Patch both module globals because the resumable
# selector imported the chooser by name before this facade is initialized.
_selector_v2.choose_target_multi_view_phase_a_candidate_v2 = (
    choose_target_multi_view_phase_a_candidate_v2_kernel
)
_resume_v2.choose_target_multi_view_phase_a_candidate_v2 = (
    choose_target_multi_view_phase_a_candidate_v2_kernel
)

# Keep one exact checkpoint-started repair implementation at the production
# orchestration seam while the Protocol-5 ownership consolidation proceeds.
_hardening._build_repair_from_checkpoints = build_repair_from_checkpoints

# The family-streaming frontier preserves canonical FP64 accumulation while
# releasing one family's mmap pages at a time. It remains the production Phase-B
# implementation until the selector owner is consolidated directly.
_selector_v2.build_target_multi_view_lazy_frontier_v2 = (
    build_target_multi_view_lazy_frontier_v2_streaming
)
_resume_v2.build_target_multi_view_lazy_frontier_v2 = (
    build_target_multi_view_lazy_frontier_v2_streaming
)

_hardening.install_campaign_hardening(_core)

# Preserve the pre-hardening campaign module surface, including internal helper
# names used by focused regression tests. Function globals continue to resolve
# in _campaign_cli_core, where the two v2 orchestration functions were patched
# before any command is executed.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)


def main(*args, **kwargs):
    return _core.main(*args, **kwargs)


if __name__ == "__main__":
    main()
