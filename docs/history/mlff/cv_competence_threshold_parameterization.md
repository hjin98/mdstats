# Foundation CV / production threshold parameterization

This file is non-normative semantic history. Current authority is owned by the broad canonical owners: D1 `docs/methods/mlff_scientific_method.md` §10.3/§11, D2 `docs/methods/mlff_numerical_algorithmic_method.md` §17.1/§23.7, D3 `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`, and D4 `docs/specs/training_data/mlff_post_selection_p5_spec.md` §12.1. Threshold-specific delta authority files used during the cycle were incorporated into those owners and removed so that no parallel current authority remains (recoverable from Git history).

The first threshold-separation candidate correctly split foundation CV competence from fresh-production checkpoint quality, but represented the generated/default values too rigidly: CV checkpoint competence was fixed at `45 meV/angstrom` and D1/D2 described production `30 meV/angstrom` as an unconditional constant even though production already had an explicit policy input.

Independent D1/D2 review identified that mismatch. On 2026-09-15 the stakeholder clarified the intended design: **all three foundation post-selection thresholds are configurable policy parameters**, with generated/current defaults:

```text
CV checkpoint competence    45 meV/angstrom
CV held-out acceptance      45 meV/angstrom under the default force-RMSE metric
production checkpoint       30 meV/angstrom
```

The resulting authority keeps threshold ownership role-local. It does not move any threshold into shared `PostSelectionMethodIdentity`, and it does not add a second checkpoint-policy engine. The existing CV policy owns CV checkpoint and held-out thresholds; the existing production policy owns production checkpoint quality.

The only missing public configuration surface in the prior D4 realization was the CV checkpoint threshold. The accepted design exposes that value through the existing CV policy configuration surface while retaining the existing CV outer threshold and production `[acceptance]` threshold source. Explicit default and omission are semantically equivalent after resolution; non-default values move the appropriate role-policy identity and materially dependent evidence.

Scratch, shared replay/integrity constraints, fixed-budget training, common-monitor membership, held-out leakage prohibitions, P1/P2/P3 target selection, and downstream release qualification remain unchanged.
