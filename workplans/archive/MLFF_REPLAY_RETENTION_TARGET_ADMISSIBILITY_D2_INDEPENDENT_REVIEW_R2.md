---
kind: independent-d2-review
protocol_version: 6.4.0
status: COMPLETE
review_disposition: D2_PASS
serious_challenge: NONE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
reviewed_immutable_candidate: 4f161b1c4820de10abe638287b13152147d12fd9
reviewed_D2_blob: 3e7fb744fc733f23bbd93a8347246cfa306ebe89
ratified_parent_D1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
prior_D2_R1_candidate: e2b39917ab8c16556eb218d6a41e9682331bbca0
prior_D2_R1_review_commit: 786dd6fd40f15a048eb53dcb3c75b39087ed2ce4
review_date: 2026-09-18
stakeholder_ratification_required: true
d3_gate_state: BLOCKED_PENDING_D2_RATIFICATION
---

# Independent D2 Review R2 — replay/target numerical renewal

## 1. Disposition

**D2 PASS. No SERIOUS CHALLENGE.**

Reviewed immutable target:

`4f161b1c4820de10abe638287b13152147d12fd9`

Canonical D2 blob:

`3e7fb744fc733f23bbd93a8347246cfa306ebe89`.

Governing ratified D1 parent:

`d761171f3c86c3c79b87a90cfc02ac324c261b1a`.

The candidate is review-passed but not accepted-current until the stakeholder explicitly ratifies this exact target.

## 2. R1 repair verification

### D2-R1-F1 — replay training projection

**Closed.**

`D2.DEF.052` now projects replay authority by numerical consumption.

The training projection explicitly binds:

- replay geometry/source membership/split;
- exact training label/reference payload;
- training label provider/prediction semantics;
- label mode;
- training-consumed qualification projection `Q_r^train`;
- exact `Phi`/prediction semantics for pseudo replay;
- replay-head E0 when trainer-consumed;
- realized exposure.

Thus a TRUE_REFERENCE DFT label/provider change cannot remain assessment-only merely because geometry and the label-mode enum are unchanged. FOUNDATION_PSEUDO equivalently binds the exact foundation prediction payload/provider semantics.

The retention projection separately binds true-monitor membership/reference payload, `Q_r^ret`, foundation baseline, and measurement semantics. A coordinate may occur in both projections when consumed by both.

This is the required D2 dependency split for later D3 identity design.

### D2-R1-F2 — provider equivalence

**Closed.**

The repaired D2 no longer requires a timeless software-provider identity. Candidate and foundation replay measurements must realize the same governed observable under identical numerical semantics or an already accepted D2-equivalent realization.

Likewise, historical measurement reuse may cross realization identity only when governed numerical outputs are already established equivalent. A provider name alone neither proves nor disproves numerical equivalence.

Checkpoint/model identity and evaluation population remain exact where required.

### D2-R1-F3 — typed failure closure

**Closed.**

`D2.DEF.062` now fail-closes:

- invalid/nonfinite/nonpositive replay thresholds;
- `delta_warn >= delta_hard` after canonical conversion, including collapse;
- missing/unauthenticated/unreconstructable governed checkpoint positions or required assessments;
- unavailable recomputation after measurement equivalence cannot be proven;
- absent current-CV authorization for current final assessment/publication.

It also explicitly rejects scalar-only metric reuse, checkpoint omission and content-store winner inference as error handlers.

Recoverable missing measurement equivalence is **not** made terminal: D2.DEF.060B-060C first require recomputation from authenticated checkpoint/evaluation evidence; failure occurs only when that evidence is unavailable.

## 3. Replay arithmetic and conditioning

**PASS.**

The D1 signed replay observable is concretized as

`Delta_R = RN64(R_c - R_0)`

from finite binary64 RMSE values on the same exact true-reference monitor.

The candidate does not introduce absolute value, ratio, percentage normalization, clipping or comparison epsilon.

The arithmetic is deterministic IEEE-754 round-to-nearest, ties-to-even. The classification is intentionally defined on canonical binary64 measurements rather than on an unobservable latent real number; therefore ordinary representation rounding is part of method identity, not an uncertainty interval.

No material conditioning defect was found. Near the configured warning/hard boundaries, the subtraction result is compared directly to the canonical threshold. One-ulp perturbations can change the classification only when the canonical result crosses the exact policy boundary, which is the specified method.

## 4. Unit conversion and boundaries

**PASS.**

Public replay values in meV/angstrom convert through binary64 division by exactly representable integer 1000.

Independent binary64 checks give:

```text
50 / 1000  -> 0.05
75 / 1000  -> 0.075
100 / 1000 -> 0.1
```

with the same binary64 representations as the corresponding direct decimal values.

The candidate correctly validates the **converted** internal policy:

`0 < delta_warn < delta_hard`.

If two distinct configured values collapse to one binary64 internal value, policy resolution fails closed.

Boundary relations are coherent:

- `Delta_R == delta_warn`: no warning;
- next representable value above: warning;
- `Delta_R == delta_hard`: warning, no hard rejection;
- next representable value above: hard rejection.

Target predicates remain inclusive:

- exact `0.075` passes CV;
- next binary64 above fails;
- exact `0.050` passes production;
- next binary64 above fails.

No tolerance band is authorized.

## 5. Replay warning versus hard admissibility

**PASS.**

`W(c)` is explicitly diagnostic and excluded from `S(c)`.

Hard replay failure is only:

`Delta_R > delta_hard`

plus independent evidence-validity failures for missing/stale/incompatible/nonfinite required replay evidence.

Therefore a checkpoint in the warning region can remain hard-admissible and can win on target RMSE, exactly as required by D1.

Replay margin and warning state have no target ranking or tie-break authority.

## 6. Role thresholds and outer metric

**PASS.**

Foundation generated/default predicates are correctly concretized as:

```text
tau_CV   = 0.075 eV/angstrom
theta_CV = 0.075 eV/angstrom  only for default target-force outer metric
tau_prod = 0.050 eV/angstrom
```

`tau_CV` and `tau_prod` apply to the same common-monitor target RMSE and therefore have a directly meaningful strictness ordering.

`theta_CV` applies to held-out `O_i` and remains a distinct estimator/population.

Alternative outer metrics retain their own units, estimator and accepted threshold resolution. The candidate does not numerically donate force-unit `0.075` to another metric.

The required 0.060 eV/angstrom counterexample is sound: it can satisfy default CV checkpoint competence and must fail default production checkpoint quality.

## 7. Complete-checkpoint representative selection

**PASS.**

`D2.DEF.059A` uses the complete D1-governed checkpoint universe. Quality-dependent shortlist/rescue thinning is explicitly non-equivalent.

After hard admissibility, the total key is:

`(target RMSE, epoch, checkpoint SHA-256)`.

All target RMSE values entering the key are finite canonical binary64 values. Epoch is exact integer and SHA is canonical digest. Therefore the key is deterministic.

A strictly larger target RMSE cannot be promoted by:

- replay margin or warning status;
- secondary target/energy/stress diagnostics;
- maturity/refinement;
- practical-equivalence;
- bootstrap uncertainty;
- historical score weights;
- shortlist status.

Exact target ties alone reach the non-quality epoch/SHA tie coordinates.

This does not alter P3 practical-equivalence ranking, which remains separately imported.

## 8. Final seed ordering

**PASS.**

Each production seed first freezes its own representative.

`all_qualified_final_seeds` performs no cross-seed ranking.

`single_best_final_seed` orders already-frozen representatives by:

`(target RMSE, optimizer seed, checkpoint SHA-256)`.

There is no second evaluation and no replay/secondary/bootstrap/maturity tie authority.

## 9. Currentness and fixed-budget noninterference

**PASS.**

The numerical dependency effects are correctly separated:

- `delta_warn`: warning/report only;
- `delta_hard`: hard assessment/representative/verdict descendants;
- `tau_CV`: CV hard assessment/reselection and dependent outer verdict/production authorization;
- `theta_CV`: outer verdict/production authorization only;
- `tau_prod`: production assessment/reselection/publication;
- strict-order identity: representative/publication descendants.

None is a TRAIN2 input under fixed-budget authority.

The distinction between a decision object becoming stale and the selected checkpoint actually changing is handled by reassessment: old verdicts are not declared current by monotonic implication, while equivalent numeric measurements may be reused.

## 10. Training-semantic equivalence and continuation

**PASS.**

`D2.DEF.060` keeps restart authentication strict for interrupted trajectories: exact predecessor state, optimizer/EMA/RNG lineage and every trajectory-generating numerical coordinate remain required.

For completed historical TRAIN2, assessment-only thresholds/order are excluded from training-semantic equivalence because they are not consumed by training.

The repaired D2.DEF.052 ensures this exclusion cannot accidentally hide a replay label/provider change that would alter gradients.

No historical checkpoint, runtime summary, optimizer state or hash is rewritten during policy migration.

## 11. Measurement equivalence and reassessment

**PASS.**

`D2.DEF.060B` requires provenance-level equivalence:

- exact checkpoint/model state;
- exact evaluation population/reference values;
- metric/unit/reduction semantics;
- correct model/head prediction semantics;
- provider/precision semantics or established numerical equivalence.

Scalar equality alone is explicitly insufficient.

If equivalence is unprovable but authenticated checkpoint/evaluation evidence remains available, the method recomputes the metric rather than failing or copying the scalar.

`D2.DEF.060C` then creates new current assessment decisions without mutating historical verdicts.

For CV, a changed representative purchases the required held-out evaluation; an unchanged representative may reuse an equivalent outer measurement.

For final production, current strict selection is reconstructed from the complete governed checkpoint universe. A historical shortlist or content-store scan cannot stand in for that universe.

## 12. Current-CV reauthorization

**PASS.**

A genuinely fresh historical final-production trajectory can be reassessed without retraining only when:

1. current CV is reclosed and accepted; and
2. production training-semantic equivalence is proven.

Current CV rejection blocks current publication even if historical final checkpoints remain numerically good.

This preserves D1's authorization dependency without pretending that later assessment policy changed already-realized training bytes.

## 13. Source closure and unaffected semantics

**PASS.**

The candidate explicitly supersedes only the reopened imported clauses:

- one hard replay budget;
- old foundation role defaults;
- foundation-P5 uncertainty/secondary/maturity ordering;
- assessment-only policy in training continuation/currentness.

P3 practical-equivalence, target-size selection, MVSEL2/REPAIR2/MVQUAL, E0, objective, exposure, monitor/fold construction and all other accepted D2 semantics remain imported unchanged.

The representation sweep is clean: no duplicate D2 IDs, no malformed display delimiters, and one Section 15 heading.

## 14. Final disposition

**D2 PASS. No SERIOUS CHALLENGE.**

No blocking numerical-method, precision, stochastic, ordering, equivalence, currentness, dependency or failure-semantics defect remains in exact candidate:

`4f161b1c4820de10abe638287b13152147d12fd9`.

The candidate is review-passed but not accepted-current.

Next required action is stakeholder ratification of exact target `4f161b1c4820de10abe638287b13152147d12fd9`. D3 remains blocked until that ratification.
