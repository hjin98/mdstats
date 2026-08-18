from pathlib import Path

import mdstats

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specs" / "training_data" / "mlff_lightweight_ranking_spec.md"
MANUAL = ROOT / "docs" / "arch_manuals" / "mlff_training_data_architecture.md"
GUIDE = ROOT / "docs" / "guides" / "mlff_campaign_cli_user_guide.md"


def test_adapt_rank1_release_and_spec_contract() -> None:
    assert mdstats.__version__ == "0.20.140a0"
    text = SPEC.read_text(encoding="utf-8")
    assert "Status: implemented in mdstats 0.20.125a0" in text
    assert "zero" in text.lower() and "inference" in text.lower()
    assert "lightweight_run_champion.json" in text
    assert "weighted score" in text.lower()
    assert "lower target force RMSE" in text
    assert "earlier epoch" in text
    assert "no_lightweight_admissible_checkpoint" in text


def test_adapt_rank1_manual_closed_and_eval_now_implemented() -> None:
    text = MANUAL.read_text(encoding="utf-8")
    rank = text.split("## ADAPT-RANK1", 1)[1].split("## ADAPT-EVAL1", 1)[0]
    evaluation = text.split("## ADAPT-EVAL1", 1)[1].split("## ADAPT-VERIFY1", 1)[0]
    assert "**Status:** implemented in `mdstats 0.20.125a0`." in rank
    assert "lightweight_run_champion.json" in rank
    assert "performs no inference" in rank
    assert "**Status:** implemented in `mdstats 0.20.126a0`." in evaluation


def test_user_guide_states_current_rank1_boundary() -> None:
    text = GUIDE.read_text(encoding="utf-8")
    assert "MLCV-RANK1 is implemented in 0.20.134a0" in text
    assert "retains at most five candidates independently" in text
    assert "complete finite lightweight target/replay RMSE is rankable" in text
    assert "Ranking launches no new inference" in text
    assert "MLCV-SELECT1" in text
    assert "adaptive_topk" in text
