#!/usr/bin/env python3
"""Run the mdstats MLFF campaign CLI from a source checkout.

The campaign launcher exits with :func:`os._exit` after flushing Python and
logging streams.  Real MACE/PyTorch subprocesses can otherwise leave runtime
threads registered during interpreter teardown after all campaign artifacts
have already been written.  The campaign core persists every durable state
change atomically before returning, so a hard final process exit is safe and
keeps UNIX exit status deterministic.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from mdstats.training_data.campaign_cli import main


def _flush_and_exit(code: int) -> "NoReturn":
    """Flush user-visible output and terminate without runtime shutdown hangs."""

    try:
        logging.shutdown()
    finally:
        for stream in (sys.stdout, sys.stderr):
            try:
                stream.flush()
            except Exception:
                pass
    os._exit(int(code))


if __name__ == "__main__":
    _flush_and_exit(main())
