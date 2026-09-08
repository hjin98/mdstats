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


_INIT_MODEL_FAMILIES = {
    "mh-1": "mace_mh_1",
    "mpa-0": "mace_mpa_0",
}


def _normalize_init_model_argv(argv: Sequence[str] | None) -> list[str]:
    """Translate ``init [model]`` into the existing foundation-family authority.

    The positional spelling is convenience only.  The core parser, generated
    TOML, foundation inspection, and all downstream scientific identity continue
    to use the existing canonical ``mace_mh_1`` / ``mace_mpa_0`` family values.
    """

    values = list(sys.argv[1:] if argv is None else argv)
    try:
        init_index = values.index("init")
    except ValueError:
        return values
    model_index = init_index + 1
    if model_index >= len(values):
        return values
    model = str(values[model_index]).strip().lower()
    family = _INIT_MODEL_FAMILIES.get(model)
    if family is None:
        return values

    configured_family: str | None = None
    for index in range(model_index + 1, len(values)):
        token = values[index]
        if token == "--foundation-family":
            if index + 1 < len(values):
                configured_family = str(values[index + 1]).strip()
            break
        if token.startswith("--foundation-family="):
            configured_family = token.split("=", 1)[1].strip()
            break
    if configured_family is not None:
        if configured_family != family:
            raise _core.CampaignCliError(
                f"`init {model}` selects foundation family {family!r}, which "
                f"conflicts with --foundation-family {configured_family!r}. "
                "Choose one model family."
            )
        # Same semantic choice was supplied twice.  Keep the canonical flag and
        # remove only the convenience spelling so the core sees one authority.
        del values[model_index]
        return values

    values[model_index : model_index + 1] = ["--foundation-family", family]
    return values


def main(argv: Sequence[str] | None = None) -> int:
    try:
        normalized = _normalize_init_model_argv(argv)
    except _core.CampaignCliError as exc:
        print(f"mdstats-mlff-campaign: {exc}", file=sys.stderr)
        return 2
    return _core.main(normalized)


if __name__ == "__main__":
    main()
