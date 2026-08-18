from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_adaptive_revision_gate_order_and_defaults():
    version_text = (ROOT / "mdstats" / "_version.py").read_text(encoding="utf-8")
    assert '__version__ = "0.20.140a0"' in version_text
    text = MANUAL.read_text(encoding="utf-8")
    headings = [
        "## ADAPT-PREC1",
        "## ADAPT-MON1",
        "## ADAPT-STOP1",
        "## ADAPT-RANK1",
        "## ADAPT-EVAL1",
        "## ADAPT-VERIFY1",
        "## ADAPT-MIGRATE1",
    ]
    positions = [text.index(h) for h in headings]
    assert positions == sorted(positions)
    assert "256 configurations" in text
    assert "512 configurations" in text
    assert "T_{\\max}=30\\ \\mathrm{meV/\\AA}" in text
    assert "f_T=0.80" in text
    assert "f_R=1.20" in text
    assert "finalist_count = 5" in text
    assert "finalist_rescue_batch_size = 5" in text


def test_adaptive_revision_precision_and_evaluation_invariants():
    text = MANUAL.read_text(encoding="utf-8")
    assert "single  -> FP32 learned model" in text
    assert "double  -> FP64 learned model" in text
    assert "The words `refine` and `mixed` cease to denote supported production model-precision" in text
    assert "Hard FP64 scientific-arithmetic invariant" in text
    assert "performs no new model inference" in text
    assert "retirement of EVAL-MF screening" in text
    assert "full **true-label** replay" in text
    assert "Historical EVAL-MF/PREC records remain valid evidence" in " ".join(text.split())
    assert "seven-gate adaptive revision is complete" in text
    migrate = text[text.index("## ADAPT-MIGRATE1") : text.index("## Completion rule for the adaptive-training revision")]
    assert "**Status:** implemented in `mdstats 0.20.128a0`." in migrate
    assert "ProtocolFreezeAuthorityRecord" in migrate
    assert "AdaptiveMigrationRecord" in migrate
