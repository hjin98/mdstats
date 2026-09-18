---
kind: independent-d2-review
protocol_version: 6.4.0
status: COMPLETE
review_disposition: D2_NO_PASS
serious_challenge: NONE
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
reviewed_immutable_candidate: e2b39917ab8c16556eb218d6a41e9682331bbca0
reviewed_D2_blob: 9e12728432d20bc7d16b9c5654bf7833cdee8df9
ratified_parent_D1_target: d761171f3c86c3c79b87a90cfc02ac324c261b1a
review_date: 2026-09-18
highest_open_owner: D2
---

# Independent D2 Review R1 — replay/target numerical renewal

## 1. Disposition

**D2 NO-PASS. No SERIOUS CHALLENGE to ratified D1.**

The numerical direction is coherent, but the exact candidate has blocking D2 dependency/equivalence defects that could authorize stale training evidence.

## 2. Blocking finding D2-R1-F1 — replay training projection omits training-label identity

`D2.DEF.052` separates D1 replay lineage into training and retention-measurement projections. That split is necessary, but the training projection currently binds geometry/source membership/split, label **mode**, foundation/prediction policy where pseudo, E0 and exposure without explicitly binding the exact replay training label payload/provider identity.

Counterexample:

1. retain identical replay geometry membership and `TRUE_REFERENCE` label mode;
2. change the DFT/reference label payload or numerically material training-label provider semantics;
3. keep all currently enumerated training-projection coordinates unchanged;
4. the actual gradients change, but the candidate's stated projection permits classifying the change as outside TRAIN2.

That violates D1 assessment-policy noninterference in the opposite direction: D1 permits reuse only when **training-bearing semantics are unchanged**.

Required repair:

- training projection must bind exact training label payload/reference identity and numerically material provider/prediction semantics for TRUE_REFERENCE;
- for FOUNDATION_PSEUDO it must bind exact pseudo prediction payload/provider semantics and frozen `Phi`;
- project `Q_r` by consumption: training-applicable qualification belongs to the training projection, retention-only qualification belongs to the measurement projection;
- a change that can alter training labels/gradients must stale TRAIN2.

## 3. Blocking finding D2-R1-F2 — provider identity is over-strengthened where numerical equivalence is sufficient

`D2.DEF.057` requires candidate/foundation replay RMSE to use the same evaluator/provider, and `D2.DEF.060B` similarly lists provider/prediction realization as exact measurement-equivalence inputs.

D1 requires the same replay observable and valid numerical comparability, not timeless equality of a software provider identity. Accepted D2 already permits replaceable execution dependencies when their governed numerical outputs satisfy the accepted equivalence relation.

Requiring literal provider identity would unnecessarily make a qualified numerically equivalent evaluator non-admissible and turn a D3/D4 realization identity into D2 meaning.

Required repair:

- require the same metric/reference/reduction/precision **semantics** and either the same provider realization or a provider realization proven equivalent under the accepted numerical-equivalence relation;
- preserve exact checkpoint/model identity and exact evaluation population;
- scalar equality alone remains insufficient.

## 4. Blocking finding D2-R1-F3 — new fail-closed states are missing from D2.DEF.062

The candidate adds new invalid states but the canonical typed failure set does not name them.

At minimum it must cover:

- invalid/nonfinite/nonpositive replay decision thresholds;
- warning/hard ordering failure, including binary64 conversion collapse;
- missing/unreconstructable required governed checkpoint position or required assessment;
- inability to prove measurement equivalence when recomputation evidence is unavailable;
- absent current-CV authorization for current final assessment/publication.

Without this closure, descendants could invent inconsistent fallback behavior despite the local definitions saying the policy is invalid.

## 5. Nonblocking challenge results

The following reviewed semantics are otherwise coherent:

- `RN64(R_c-R_0)` is a valid deterministic binary64 concretization of the D1 signed degradation observable; no epsilon is introduced.
- `v_meV/1000` uses exactly representable denominator 1000 and generated 50/100 values resolve to the same binary64 values as 0.05/0.1.
- strict `>` warning/hard relations correctly make threshold equality non-triggering.
- `75/75/50` direct inclusive target predicates faithfully concretize ratified D1.
- complete-checkpoint ordering by target RMSE with exact non-quality tie keys is deterministic and leaves P3 practical-equivalence ranking untouched.
- `theta_CV` outer-verdict-only currentness is correctly distinct from `tau_CV` representative currentness.
- alternative outer metrics are not assigned the force-RMSE 0.075 default.
- historical verdicts are not monotonically relabeled current.

## 6. Repair/re-review requirement

Repair F1-F3 without altering the ratified D1 semantics or broadening the reopened D2 surface. Freeze a new immutable candidate and perform fresh independent D2 re-review.

D3 remains blocked.
