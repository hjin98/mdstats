from __future__ import annotations

from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs/specs/training_data/mlff_mvidx_queue_backpressure_spec.md"
MANUAL = ROOT / "docs/arch_manuals/mlff_training_data_architecture.md"


def test_mvidx_backpressure_release_metadata() -> None:
    assert mdstats.__version__ == "0.20.240a0"
    manual = MANUAL.read_text(encoding="utf-8")
    assert 'release: "mdstats 0.20.240a0"' in manual
    assert "architecture_revision: 103" in manual
    assert "165-family / 56-ready-slot" in manual
    assert "FINAL-GPU1" in manual


def test_mvidx_backpressure_spec_preserves_bounded_queue_contract() -> None:
    text = SPEC.read_text(encoding="utf-8")
    for token in (
        "165 required",
        "56 tasks",
        "queue.can_submit()",
        "drains canonical completions",
        "RAM admission remains fail-closed",
        "Out-of-core MVIDX",
    ):
        assert token in text


def test_mvidx_runtime_uses_submit_drain_refill_loop() -> None:
    source = (ROOT / "mdstats/training_data/target_coverage_sparse_index.py").read_text(
        encoding="utf-8"
    )
    assert "while next_submit < len(required) and queue.can_submit():" in source
    assert "obligation_submitted" in source
    assert "bounded producer/consumer queue did not drain exactly" in source
