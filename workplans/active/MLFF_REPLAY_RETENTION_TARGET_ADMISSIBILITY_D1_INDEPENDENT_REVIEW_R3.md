---
kind: independent-d1-review
protocol_version: 6.4.0
status: COMPLETE
review_disposition: D1_PASS
serious_challenge: NONE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
reviewed_immutable_candidate: d761171f3c86c3c79b87a90cfc02ac324c261b1a
reviewed_d1_blob: 612294ec4680db01a18085e13fbfe5dcfa9fb7ed
dependency_trace_blob: d41a9fa452f9afb3bb2c67a485a04a2c68426289
review_date: 2026-09-18
highest_open_owner: D1
stakeholder_ratification_required: true
d2_gate_state: BLOCKED_PENDING_D1_RATIFICATION
---

# Independent D1 Review R3 — 75/75 CV policy reconciliation

## 1. Disposition

**D1 PASS. No SERIOUS CHALLENGE.**

Reviewed immutable target:

`d761171f3c86c3c79b87a90cfc02ac324c261b1a`

against accepted Protocol-6.4 D1 baseline:

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.

Canonical reviewed D1 blob:

`612294ec4680db01a18085e13fbfe5dcfa9fb7ed`.

This review does not self-ratify the candidate. Accepted-current D1 remains the main baseline until the stakeholder explicitly ratifies this exact target.

## 2. Independence and scope

The review reconstructed the accepted role-threshold semantics from the accepted D1 kernel and exact imported P5 source, including the historical threshold-separation authority. Prior R2 PASS, the active workplan, R3 dependency trace, current implementation, historical closeout records and stakeholder discussion were treated as evidence/challenge material, not as authority to assume the R3 amendment is correct.

The material R3 delta is:

- foundation CV common-monitor checkpoint default `tau_CV: 45 -> 75 meV/angstrom`;
- foundation CV held-out default-force threshold `theta_CV: 45 -> 75 meV/angstrom`;
- foundation production checkpoint default remains `tau_prod = 50 meV/angstrom`;
- clarification of the already-accepted global E:F:S property-loss coefficient tuple `1:10:1` without changing that objective.

The previously reviewed replay `50/100`, governed checkpoint universe, target-only representative ordering, publication ordering and assessment/training separation were rechecked for regression but are not materially redefined by R3.

## 3. Historical calibration challenge

No evidence was found that the accepted `45 meV/angstrom` CV values were a proved physical boundary, externally validated universal competence threshold, or mathematical consequence of the method.

The accepted source explicitly described `45/45` as stakeholder-authorized calibration based on recalled learning-curve behavior, with no stated confidence interval, and explicitly made all three role thresholds configurable policy parameters. The scientific invariant was role separation, evidence population, all-required-position conjunction, fixed-budget training and selective currentness—not immutability of `45`.

Therefore replacing the generated CV calibration by `75/75` does not contradict an established theorem or external constraint. It deliberately reduces CV conservatism and must carry the corresponding false-authorization risk, which the R3 candidate now states explicitly.

## 4. Threshold-role challenge

### 4.1 `tau_CV = 75`

PASS.

`tau_CV` and `tau_prod` measure the same target force-component RMSE on the same exact campaign-common `M_mon`. The candidate correctly states the direct ordering:

```text
75 meV/angstrom CV checkpoint ceiling
> 50 meV/angstrom production checkpoint ceiling
```

because lower RMSE is better. Thus the default CV checkpoint gate is intentionally more permissive.

The candidate does not claim that a CV checkpoint satisfying 75 is production quality. CV remains a method-authorization screen over every required fold/seed, while fresh production must independently satisfy the tighter 50-meV checkpoint gate.

No contradiction arises if a method passes CV and a fresh production trajectory later has no admissible representative. That outcome is now explicitly represented rather than hidden.

### 4.2 `theta_CV = 75`

PASS.

For the default target-force outer metric, the held-out representative must satisfy `theta_CV = 75 meV/angstrom` on `O_i`. This is distinct evidence from `tau_CV`: same physical observable family/units under the default metric, different population and role.

The candidate does not equate held-out `O_i` with `M_mon`, does not allow held-out labels to control checkpoint selection, and retains all-required fold/seed conjunction. Therefore the looser numeric threshold does not collapse checkpoint control and held-out generalization into one evidence source.

For an explicitly different outer metric, the 75-meV force default does not apply. The reconciled workplan correctly preserves the alternative metric's accepted units/default resolution and forbids force-unit migration.

### 4.3 Does 75/75 make CV vacuous?

No current evidence proves that it does.

The review cannot establish from repository evidence that `75/75` is an empirically optimal threshold, and the candidate does not make that claim. The threshold is a stakeholder-selected current policy calibration. CV still requires:

- every required fold/seed to complete its fixed budget;
- an admissible checkpoint satisfying all other hard requirements;
- the common-monitor checkpoint predicate;
- the held-out predicate;
- mandatory replay/integrity evidence where applicable;
- no mean/majority/best-seed rescue.

Accordingly, `75/75` remains a nontrivial authorization predicate in the formal method. The material uncertainty is calibration adequacy, not internal incoherence. R3 correctly makes evidence that `75/75` admits materially incompetent methods an explicit D1 reopen condition.

## 5. CV authorization versus production success

PASS.

This distinction was under-specified before the final reconciliation and is now explicit:

- current CV acceptance authorizes a **fresh production attempt** under the frozen method/design;
- it does not guarantee that the fresh production trajectory will contain a checkpoint satisfying `tau_prod=50`;
- CV authorization does not waive, substitute for or imply the production checkpoint gate;
- production with no hard-admissible checkpoint remains a legitimate no-representative outcome.

This is consistent with the accepted historical D1 statement that fold models need not reach production checkpoint quality.

## 6. Currentness and reassessment challenge

PASS.

The repaired `D1.AX.010A` now distinguishes the three threshold roles correctly:

- `tau_CV` can change CV checkpoint hard admissibility, representative identity, dependent outer evaluation/verdict and production authorization;
- `theta_CV` can change only the CV outer pass/fail verdict and dependent production authorization; it cannot change `C_rho`, `H_rho`, the frozen checkpoint representative, or TRAIN2;
- `tau_prod` can change production hard assessment/representative/publication descendants;
- none changes an already-realized TRAIN2 trajectory when training-bearing semantics are unchanged.

Historical classifications are not silently re-thresholded into current evidence. A new current assessment is required, with numerical measurement reuse allowed only through downstream exact-equivalence rules.

This is sufficient D1 meaning for the D2/D3 currentness concretization.

## 7. UniversalLoss / 1:10:1 clarification

PASS.

Accepted D1 already owns the foundation-P5 robust energy/force/stress objective with global coefficients `1:10:1`, binary property masks, no nontrivial configuration-weight layer and no target/replay training-head scalar.

Accepted D2 concretizes that scientific objective as:

`L_P5 = L_E + 10 L_F + L_S`.

R3 correctly clarifies that the tuple is:

- global E/F/S property-loss coefficients on separately reduced property losses;
- not target/replay balancing;
- not replay/target sampling balance;
- not per-configuration weighting;
- not per-frame property-availability masks.

The final reconciliation also correctly keeps the native MACE `UniversalLoss` class out of the D1 coordinate itself: it is a qualified D2/D3/D4 realization of the D1 objective, not the scientific invariant by dependency class name.

No loss coefficient or objective meaning changed in R3.

## 8. Regression of prior R2 semantics

No blocker was found in the unchanged R2 surfaces.

The candidate still preserves:

- exact foundation identity as a replay-retention parent;
- signed same-monitor foundation-relative replay degradation;
- `50/100 meV/angstrom` warning/catastrophic defaults;
- strict exceedance semantics;
- warning-only non-veto/non-ranking behavior;
- governed complete checkpoint universe with no quality-dependent thinning;
- strict target-RMSE representative ordering after hard gates;
- non-quality exact tie delegation to D2;
- target-only `single_best_final_seed` ordering;
- fixed-budget training;
- current-CV authorization before current final assessment/publication;
- historical fresh-final reassessment only after current CV reclosure and exact training equivalence;
- downstream qualification as a separate no-feedback layer.

Scratch, P1-P4, P3 target-size/order, E0/exposure, monitor/fold construction and downstream qualification are not redefined by the R3 threshold change.

## 9. Source/dependency closure

The R3 dependency trace is adequate.

The material new dependency consequences are correctly represented:

- `D1.DEF.025` owns `75/75/50`;
- `D1.DEF.026` consumes `tau_CV`/role target ceiling in the hard-admissible set;
- `D1.AX.009` consumes both CV checkpoint and held-out thresholds;
- `D1.AX.010` preserves independent production `50`;
- `D1.AX.010A` differentiates `tau_CV` versus `theta_CV` currentness.

The implementation-specific UniversalLoss class does not become a direct D1 prerequisite.

## 10. Workplan/downstream-authority reconciliation

The active workplan is consistent with the reviewed D1 amendment and no longer carries the old production-only assumption.

It now requires, after D1 ratification:

- D2 defaults `75/75/50` with exact inclusive boundary semantics;
- separate D2 currentness for `tau_CV`, `theta_CV` and `tau_prod`;
- D3 assessment/training identity separation preserving `theta_CV` as outer-verdict-only;
- D4 default/config/spec migration to `75/75/50` for the default force outer metric;
- no `0.075` migration for alternative outer metrics;
- migration of historical generated `0.045/0.045` without rewriting explicit new-generation `0.045/0.045` overrides;
- current reassessment rather than monotonic relabeling of historical CV verdicts;
- a corrected discriminating example such as `60 meV/angstrom`, which may pass default CV 75 but must fail default production 50; the old 42-meV production-failure example is no longer valid;
- unchanged UniversalLoss numerical objective and coefficients.

The accepted-current D2/D3/D4 authority files intentionally remain unchanged until D1 is ratified. This is correct lifecycle behavior, not an authority gap.

## 11. Limitations and reopen conditions

PASS does **not** establish that `75 meV/angstrom` is empirically optimal or universally adequate.

The candidate must be reopened if applicable evidence shows, for example:

- healthy but materially inadequate foundation methods routinely pass `75/75`;
- the CV policy ceases to discriminate methods relevant to the claimed target use;
- the looser CV authorization causes unacceptable false authorization not caught by the intended production/downstream layers;
- the production `50` default conflicts with downstream adequacy;
- the replay `100` hard limit is inadequate;
- any other scientific estimand/evidence-role assumption becomes false.

These are calibration/adequacy reopen conditions, not present internal contradictions.

## 12. Final lifecycle disposition

**D1 PASS. No SERIOUS CHALLENGE.**

No blocking scientific, formal-definition, evidence-role, dependency, currentness or representation defect remains in exact candidate:

`d761171f3c86c3c79b87a90cfc02ac324c261b1a`.

The candidate is review-passed but **not accepted-current**.

Next required action is explicit stakeholder ratification of exact target `d761171f3c86c3c79b87a90cfc02ac324c261b1a`. Only after that ratification may Gate B close and Gate C begin the D2 numerical-authority renewal.
