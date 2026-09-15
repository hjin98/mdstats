# Active workplans

Active workplans are temporary engineering coordination contracts. They do not define current mdstats product behavior by repository presence alone; current behavior remains owned by accepted D1-D4 authority and conforming implementation.

## Active workplans status

There are currently **no active workplans**.

The MLFF CV competence threshold separation and parameterization cycle on branch `fix/mlff-cv-competence-threshold-separation` has completed:
- All three foundation post-selection thresholds are configurable policy parameters by design, with generated/current defaults `45 / 45 / 30 meV/angstrom`.
- D1/D2 independent re-review recorded PASS (`workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_D1_D2_REREVIEW.md`).
- D3 architectural ownership (`docs/arch_manuals/mlff_training_data/85_post_selection_threshold_policy_ownership.md`) and D4 specifications (`docs/specs/training_data/mlff_post_selection_threshold_policy_spec.md`, `docs/specs/training_data/mlff_post_selection_p5_spec.md`, `docs/specs/training_data/mlff_data9b3_campaign_cli_spec.md`) are accepted.
- D4 implementation (`mdstats/training_data/post_selection_identity.py`, `mdstats/training_data/_campaign_cli_core.py`, `campaign.toml.example`) is conforming.
- Full executable test suite and affected regressions passed (96 passed tests).
- Broad canonical documentation and tracked PDFs were consolidated and rebuilt.
- The parent workplan (`workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_WORKPLAN.md`), parameterization alignment handoff (`workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_PARAMETERIZATION_ALIGNMENT.md`), and supporting review/reopen records were closed and archived beside the closeout record:
  `workplans/archive/MLFF_CV_COMPETENCE_THRESHOLD_SEPARATION_AND_PARAMETERIZATION_CLOSEOUT_2026-09-15.md`.

Completed/superseded workplans belong under `workplans/archive/`.
