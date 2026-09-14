## Gate A Revision 2 repair state — 2026-09-13

The first resolved Gate A candidate (`cc55be388fa8ab6dd0641eeefc3b914bfcaefe0f`) received an independent **NO PASS** recorded in `workplans/active/mlff-fps-coverage-method-reconciliation/GATE_A_INDEPENDENT_D1_D2_REVIEW.md`. Do not ratify or implement that revision.

The candidate has now been repaired as **Revision 2** in `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`. Material changes are:

- evaluation prefixes now have a finite-population SRSWOR interpretation targeting the actual component-weighted EVAL2 ratio-of-totals estimand, with explicit finite-prefix sampling uncertainty rather than frame-count condition quotas;
- `P_train/M3` now has an explicit training-priority, exact-feasible neutral-condition depletion objective over protected components instead of arbitrary deterministic subset choice;
- selection/support mass, training-loss influence, and evaluation estimand are explicitly distinct;
- D1 coverage is narrowed to frame-level raw/material-neutral structural support rather than implying exhaustive atomic-environment coverage;
- metric weighting is by named semantic feature family with equal prior family mass, subject to mandatory sensitivity/ablation falsification;
- D2 freezes type-7 quantiles, coordinate traversal, median-medoid semantics, exact integer proportional deficits, exact hash byte encoding, and finite-precision equivalence envelopes;
- correlation/effective-sample limitations, source-repackaging scope, and stale-descendant impact are explicit.

`GATE_A_REVISION_2_AUTHOR_REPAIR_CHECK.md` maps every prior blocker/gap to the repair and records remaining self-challenge points.

**Current gate state:** Revision 2 is ready for a **fresh independent D1/D2 review**. It is not current authority. Human ratification and D3/D4 behavioral implementation remain blocked until that fresh review passes.