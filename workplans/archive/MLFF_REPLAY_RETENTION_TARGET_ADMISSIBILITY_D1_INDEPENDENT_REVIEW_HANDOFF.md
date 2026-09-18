---
kind: independent-review-handoff
protocol_version: 6.4.0
status: AWAITING_FRESH_INDEPENDENT_D1_REVIEW
workplan_id: MLFF-REPLAY-RETENTION-TARGET-ADMISSIBILITY-REWORK-1
accepted_baseline_commit: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
immutable_d1_candidate_target: 06f1255ed39f41d178daf73985829a2190a2bee8
d1_candidate_blob: 65713ab4e8caa848e21d27a75e594664528ee6eb
branch: design/mlff-replay-retention-target-admissibility-rework
highest_review_owner: D1
d2_gate_state: BLOCKED_PENDING_D1_ACCEPTANCE
---

# Independent D1 Review handoff — MLFF replay retention and target admissibility renewal

## 1. Binding and independence

Perform a fresh Protocol-6.4 D1 Review of immutable target

`06f1255ed39f41d178daf73985829a2190a2bee8`

against accepted current baseline

`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2`.

The semantic D1 candidate blob is

`65713ab4e8caa848e21d27a75e594664528ee6eb`

at `docs/methods/mlff_scientific_method.md`.

Treat the active workplan, author Challenge notes, motivating production trajectory, prior D1/D2 history, and this handoff strictly as evidence/challenge material. Do not inherit the author conclusion that the amendment is coherent. Reconstruct the accepted D1 and the exact imported source authority independently.

This handoff descendant is not part of the semantic candidate. Review the immutable target above.

## 2. Accepted authority to reconstruct

The accepted baseline is the Protocol-6.4 D1 kernel on `main@a759e81...`, including its exact imports:

- `D1.SRC.GENERAL = a4824d28775164aa942fd29fa97ee0957eb87e6f:docs/methods/mlff_scientific_method.md`;
- `D1.SRC.ORDER = a4824d28775164aa942fd29fa97ee0957eb87e6f:docs/methods/mlff_target_training_order_scientific_method.md`.

The candidate intentionally changes only the replay-retention / foundation-P5 checkpoint admissibility and ranking / foundation-production target default / final single-best ordering / dependent currentness surface. P1-P4, target-order membership, P3 target-size semantics, foundation objective/E0/exposure, monitor/fold construction, scratch semantics, and downstream qualification are intended to remain unchanged.

## 3. Proposed D1 delta to challenge

The candidate proposes:

1. TRUE_DFT replay remains mandatory independent retention evidence for foundation adaptation.
2. Signed replay degradation is candidate replay force RMSE minus exact foundation replay force RMSE on the same authenticated TRUE_DFT monitor.
3. Replay warning and catastrophic hard limits are independent configurable policy coordinates with current defaults `50` and `100 meV/angstrom`.
4. Warning-only degradation does not veto a checkpoint; degradation beyond the catastrophic hard limit does.
5. Missing/stale/incompatible/non-finite required replay evidence remains hard-invalid.
6. Replay is auxiliary inherited-capability evidence, not target quality or release adequacy, and receives no positive ranking/tie credit.
7. Foundation-P5 representative choice is strict minimum authoritative target force-component RMSE on the common target monitor among all hard-admissible checkpoints.
8. Practical-equivalence/bootstrap/secondary target metrics/maturity/refinement and historical target/replay score weights cannot promote a strictly worse target RMSE.
9. Exact target-RMSE ties remain a D2 deterministic non-quality question; replay or another quality metric cannot break them.
10. Foundation-CV defaults stay `tau_CV = theta_CV = 45 meV/angstrom`; foundation-production target default becomes `tau_prod = 50 meV/angstrom`.
11. No scientific ordering relation is required between CV and production target ceilings; the prior “production is deliberately stricter” rationale is superseded.
12. `single_best_final_seed` applies the same strict target ordering to already-frozen admissible production-seed representatives; `all_qualified_final_seeds` remains unranked.
13. Threshold/selection-policy crossing never changes fixed-budget training.
14. Assessment-policy-only changes do not scientifically redefine an otherwise identical realized training trajectory; old verdicts nevertheless require current reassessment.
15. Current accepted CV remains a prerequisite for current final-production assessment/publication. A historical fresh final trajectory may be reused only after current CV reclosure accepts and exact training-semantic equivalence is established.

## 4. Mandatory Challenge Pass

Review must independently attempt to falsify at least the following.

### 4.1 Replay scientific role

- Does the proposed signed degradation compare scientifically commensurate observables on exactly the same replay estimand?
- Is TRUE_DFT replay still sufficiently protected as mandatory evidence after moderate degradation becomes warning-only?
- Does classifying replay as auxiliary retention evidence contradict any claimed target/deployment domain or imported P5 validity statement?
- Could the wording accidentally permit pseudo replay to substitute for mandatory TRUE_DFT retention evidence?

### 4.2 Warning versus catastrophic hard protection

- Is the warning/hard separation coherent without turning a diagnostic threshold into a hidden admissibility parent?
- Does equality/boundary meaning remain properly delegated to D2 rather than silently fixed at D1?
- Are `50/100 meV/angstrom` correctly described as configurable current defaults, not universal constants?
- Does any accepted physical/integrity or replay-qualification premise implicitly require the historical `30 meV/angstrom` hard budget?

### 4.3 Target-only representative ordering

- Does minimum authoritative common-monitor target force RMSE answer the intended checkpoint-quality question after all hard gates are satisfied?
- Does removing replay/secondary/maturity/bootstrap ranking credit create a scientific contradiction with the common-monitor or CV estimand?
- Are exact ties correctly left to deterministic non-quality D2 resolution rather than smuggling another scientific quality criterion back in?
- Does the candidate eliminate every imported P5 route by which a strictly worse target RMSE could still win?

### 4.4 CV versus production thresholds

- Is `tau_CV=45`, `tau_prod=50 meV/angstrom` scientifically coherent when both use the same target monitor but answer different role questions?
- Does the candidate correctly remove the old monotone “production stricter” rationale rather than merely contradicting it?
- Could a looser production checkpoint ceiling invalidate the meaning of earlier CV acceptance, or is external adequacy correctly left to downstream qualification?
- Is scratch isolated from this foundation-only default change?

### 4.5 Final publication semantics

- Does strict target-only `single_best_final_seed` materially narrow publication meaning in a scientifically acceptable way?
- Is `all_qualified_final_seeds` genuinely unchanged?
- Can downstream qualification still reject a frozen publication without feeding back into member selection?

### 4.6 Training/assessment currentness

- Is it scientifically valid to say that warning/hard/target/selection policy changes do not alter already-realized training when objective, memberships, exposure, optimizer, horizon, foundation and other training-bearing semantics are unchanged?
- Does requiring a new current assessment avoid relabeling historical verdicts?
- Does reuse of a genuinely fresh historical final trajectory after current CV reacceptance preserve the “fresh production” axiom, or does it accidentally promote CV-trained state?

### 4.7 Authority boundaries and collateral drift

- Has the candidate kept exact numerical boundaries, tie keys, floating arithmetic and durable identity mechanics out of D1 for D2/D3 ownership?
- Are P1-P4, target-order, P3, E0/objective/exposure, monitor/fold construction and downstream qualification unchanged?
- Is the bounded import-supersession statement complete enough that old imported replay/ranking/default prose cannot regain authority transitively?

Raise **SERIOUS CHALLENGE** before ordinary findings if any scientific estimand, evidence role, validity regime, or claimed use becomes incoherent.

## 5. Evidence and uncertainty

The observed production trajectory and historical replay-forgetting recurrence are motivation, not proof of the new numeric defaults. The candidate explicitly treats `50/100 meV/angstrom` replay and `50 meV/angstrom` production target values as stakeholder-selected current policy calibrations without universal confidence claim.

Independent review should challenge whether any existing downstream adequacy evidence contradicts those defaults. Absence of such evidence is not proof that the defaults are universally adequate.

No D4 test, current implementation behavior, workplan statement, or prior review may be used as authority to silently rewrite D1.

## 6. Review output and lifecycle

Return **D1 PASS** only if the candidate is:

- scientifically coherent and source/import closed;
- explicit about replay versus target versus downstream evidence roles;
- explicit about the warning/hard distinction and target-only quality ordering;
- non-contradictory with fixed-budget/fresh-production/current-CV semantics;
- bounded so unaffected accepted D1 remains unchanged;
- sufficiently precise for D2 concretization without D1 absorbing D2 numerical choices.

If any material blocker remains, return **D1 NO-PASS** with exact repair instructions against the canonical owner.

PASS does not self-promote. Stakeholder ratification of exact reviewed target `06f1255e...` remains required. Gate C D2 renewal may start only after D1 PASS plus that exact-target ratification.
