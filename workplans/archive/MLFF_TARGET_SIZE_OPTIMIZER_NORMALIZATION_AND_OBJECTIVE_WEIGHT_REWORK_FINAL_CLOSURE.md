---
kind: implementation-workplan-closure
workplan_id: MLFF-TARGET-SIZE-OPTIMIZER-NORMALIZATION-AND-OBJECTIVE-WEIGHT-REWORK
protocol_version: 5.15.0
status: closed
review_revision: 7
reviewed_source_branch: rework/mlff-target-size-normalization-practical-ceiling
reviewed_rework_base_commit: 573ba3005edc40810cbbe009de8de18915ca5728
reviewed_implementation_commit: 2f1da001234f72e04282214660c88ef5ee4db8f3
design_handoff_verdict: pass
implementation_review_verdict: pass
closure_verdict: pass
architecture_change: none
closed_date: 2026-09-06
---

# Final independent Software Design closure

## Verdict

**PASS / CLOSED.**

Software Design independently re-reviewed commit
`2f1da001234f72e04282214660c88ef5ee4db8f3` against Revision 7 of
`MLFF_TARGET_SIZE_OPTIMIZER_NORMALIZATION_AND_OBJECTIVE_WEIGHT_REWORK_WORKPLAN.md`,
its retained P3 restart/partial-boundary/acceleration-replay relatives, P4
currentness/adoption authority, P5 CV/final-production authority, and Protocol
5.15.0.

No genuine blocking implementation, scientific, persistence/restart,
configuration-identity, loss-realization, or acceptance gap remains. No Frozen
scientific or high-level architectural decision requires reopening.

This closure supersedes only the archived workplan's pre-review status/verdict
metadata. The archived Revision 7 workplan remains the complete historical
problem/design/repair contract.

## Closure findings

### R7-1 — canonical optimizer real-value identity: closed

`MaceOptimizerPolicy.__post_init__()` now routes `learning_rate`, `ema_decay`,
`weight_decay`, and `clip_grad` through the existing `strict_finite_real` owner
and assigns the returned canonical float before serialization/digesting.
Integer-valued and float-valued spellings therefore converge to one current
method identity without weakening bool/string/non-finite rejection or the
field-specific ranges.

The focused policy-domain regression includes direct integer-vs-float payload
and digest equivalence plus serialize/deserialize stability.

### R7-2 — proxy-proof pinned-MACE weighted-loss semantics: closed

The semantic acceptance no longer fabricates the training-weight metadata below
the owner under acceptance. It constructs a bounded mixed-label/mixed-stratum
candidate through the real mdstats P1-P3 preparation/materialization/export
path, reads the actual exported ExtXYZ frames, and passes those frames unchanged
through MACE's `config_from_atoms` / `AtomicData` path.

The test discriminates all required ownership layers:

- non-default global E/F/S coefficients remain in the generated MACE config;
- exported configuration weights include values distinct from `1.0` and match
  mdstats' realized weight authority;
- local property weights remain `1`/`0` availability/modifier masks rather than
  copies of the global objective ratio;
- missing stress arrives with a zero local mask and contributes zero even under
  a deliberately perturbed prediction;
- the dependency resolves `WeightedEnergyForcesStressLoss`, not `UniversalLoss`;
- the dependency-computed loss agrees with an independently derived weighted
  reduction;
- the acceptance environment positively asserts `mace-torch==0.3.16`.

This is now proxy-proof for the actual mdstats-export -> MACE-loss claim.

### R7-3 — final assembled functional closure: closed

The committed implementation evidence records the exact commands and candidate
surface used for final acceptance. The executable source/test delta from the
prior review consists only of:

- `mdstats/training_data/protocol.py`;
- `tests/test_mlff_target_size_policy_domain_rework.py`;
- `tests/test_mlff_target_size_mace_objective_realization.py`.

The final commit adds only the workplan evidence record beyond that tested
executable candidate, so no post-test executable edit invalidates the recorded
results.

Recorded focused acceptance:

```text
compileall: PASS
focused policy-domain + pinned-MACE semantic suite:
47 passed, 20 warnings
```

Recorded final affected-surface regression:

```text
945 passed, 2 skipped, 1819 warnings
```

The two skips are not closure blockers for this workplan:

1. the slow real-MPA-0 / external-VASP critical-precision qualification requires
   external reference assets and exercises unchanged pre-existing precision
   realization rather than the R7 repair; production/external-reference
   qualification remains outside this closure;
2. the preserved P5A6 real-workspace compatibility test requires an external
   generated workspace; affected current/legacy policy serialization and
   target-size/P5 ownership paths were exercised by the bounded regression, and
   this repair introduced no migration or historical reinterpretation layer.

Neither skipped test is counted as passing evidence for an R7 claim. The
required MACE 0.3.16 semantic acceptance executed and passed.

The recorded affected regression also retained first-rung live-writer/retry,
partial-boundary/restart, acceleration replay, practical-ceiling -> P4 terminal
adoption -> P5 cross-validation handoff, historical-method rejection, campaign
currentness, TRAIN2 continuation, executable config, objective/export, and
policy-domain coverage. Non-PDF `git diff --check` passed.

## Global invariant and architecture assessment

The implementation preserves the Tier-1/Frozen contract:

- exact nested `T_N = pi_train[:N]` target membership;
- paired-seed target-force-RMSE screening and practical-equivalence semantics;
- practical-ceiling selection with non-convergence warning rather than invented
  rescue size;
- one continuous `(N, seed)` trajectory through exact authenticated fidelity
  boundaries;
- inverse-update target-size LR/EMA normalization with general LR/EMA-decay kept
  out of target-size authority;
- P3 immutable accepted execution/restart authority and execution-only stale
  first-rung scratch;
- process liveness excluded from scientific identity;
- historical acceleration realization preserved for accepted replay while
  current realization governs new work;
- global objective coefficients, configuration weights, and local property masks
  remain distinct semantic layers;
- dependency-native MACE weighted energy/force/stress loss remains the executable
  loss architecture;
- P4 owns terminal/currentness/adoption;
- P5 requires exact corrected-method CV authorization and fresh final production;
- historical evidence is never silently reinterpreted under corrected semantics.

The repair strategy is also consistent with the Protocol 5 simplicity rule. It
consolidates canonical validation through the existing helper, reuses the
existing export and dependency owners for acceptance, and preserves the existing
execution-local artifact lock. It does not add a validator hierarchy, lease
state machine, scientific attempt identity, compatibility registry, restart
authority, loss adapter, or terminal lifecycle.

## Final disposition

Revision 7 is complete. No further implementation gate or design amendment is
required for this workplan.

Production-scale GPU qualification remains deferred to the final release under
the existing MLFF project policy and is not part of this closure.
