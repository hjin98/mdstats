from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"


def test_target_data2c_architecture_is_recorded_as_implemented() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    required = (
        "TARGET-DATA2C in `mdstats 0.20.166a0`",
        "Implementation status (`0.20.166a0`): complete for deterministic ladder construction and rung evidence.",
        "quota first, diversity second",
        "correlation-aware development interval",
        "mandatory-obligation pass/fail record",
        "hierarchically normalized fused feature space",
        "exact deterministic maximin FPS",
        "TargetDataLadderPlan",
        "minimum_materializable_rungs = 3",
        "reserve_correlation_intervals = true",
    )
    for phrase in required:
        assert phrase in text
