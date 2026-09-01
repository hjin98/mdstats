"""Compatibility name for the authenticated P6 qualification driver.

The old builder accepted an arbitrary destination and imported whichever
checkout happened to contain the script.  P6 qualification now requires the
safe, authenticated two-worktree workflow in ``qualify_p5a6_to_p6.py``.
"""

from __future__ import annotations

from pathlib import Path
import runpy


_DRIVER = Path(__file__).with_name("qualify_p5a6_to_p6.py")


if __name__ == "__main__":
    runpy.run_path(str(_DRIVER), run_name="__main__")
