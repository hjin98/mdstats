# Gate A Revision 4 current status

Date: 2026-09-13
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Current candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 4
Basis review: `GATE_A_REVISION_3_INDEPENDENT_REVIEW.md`
Status: **proposal repaired; fresh independent review pending; human ratification pending; D3/D4 behavioral implementation blocked**.

## 1. Lossless workplan reconciliation

The active parent workplan is restored to its original full reviewed text from blob `9e7f4a1492d52b63a09cc836fa6b784056172608`. That restores the complete Gate A-F sequence, mandatory corrections 11.1-11.12, historical capability-transfer obligations, evidence floor, reopen triggers, and final closure criteria that were lost when an earlier status rewrite compressed the plan.

This status record is the current cycle delta. It does not replace the parent workplan. Where the parent's exploratory/menu language or historical Revision-1 assumptions conflict with the resolved Revision-4 candidate, Revision 4 is the current proposed Gate A method and this status record identifies the supersession. All unaffected parent obligations remain binding for this cycle.

## 2. Accepted project and PEM basis

The reconciliation branch now has accepted main commit `e8d04144f55c72d799ffcd3fe40c75e47078a66d` as an explicit merge parent through `9a016f6087066c036c78b13c933bf3ddf30c5cc5`. The accepted D1/D2 method-paper blobs were identical before/after that ancestry merge.

Session-local Historical Applicability Set remains:

```yaml
pem_basis:
  accepted_project_state: e8d04144f55c72d799ffcd3fe40c75e47078a66d
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: one order/evidence owner; no revived selector topology or wrapper duplication
  - id: FF-005
    disposition: APPLICABLE
    reason: preparation-owned metric/order evidence must be persisted and reused downstream
  - id: SP-002
    disposition: APPLICABLE
    reason: changed metric/split/randomization identity must fail closed on stale generations
  - id: SP-003
    disposition: APPLICABLE
    reason: expensive neutral descriptors and fitted metrics should publish once at prepare
  - id: SP-004
    disposition: APPLICABLE
    reason: final conformance must exercise the real prepare/order/persistence/consumer path
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: TRAIN2/EVAL2 model construction is unchanged by this Gate A method
  - id: FF-002
    disposition: NOT_APPLICABLE
    reason: TRAIN2 checkpoint continuation is outside this target-order repair
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: destructive-storage authority is unchanged
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: GPU scheduling/lifetime is unchanged; consolidated GPU qualification remains deferred
```

## 3. Revision-4 resolved method delta

The proposed method now resolves the Revision-3 review findings as follows:

- split support is hard-feasible for every eligible neutral condition;
- condition depletion is globally minimized exactly;
- structural redundancy is recomputed against the **current retained set** after every component removal, and a candidate removal is allowed only when an exact J*-optimal completion still exists;
- target-order raw geometry excludes material-specific pair-rule coordinates;
- local structural evidence uses a frozen material-neutral low-level policy with element-only aggregation, no declared/profile groups, no profile phase plan, and no atom-count/fraction membership coordinates;
- robust scaling uses a unit-rescaling-invariant `sqrt(u)*max_abs` conditioning floor plus max-deviation fallback, while score winners/ties remain exact canonical binary64 decisions;
- `pi_train` remains one medoid-seeded condition-local exact-FPS order with exact proportional interleaving;
- `pi_eval` remains one persisted exact Fisher-Yates SRSWOR permutation over distinct M3 occurrences;
- foundation residual/difficulty and candidate outcomes remain forbidden membership dependencies.

## 4. Evidence state

`GATE_A_REVISION_4_BOUNDED_FALSIFICATION_RECORD.md` contains new author-side mathematical/static evidence for:

- the mutual-redundancy counterexample that defeated Revision 3;
- hard condition-preservation infeasibility/reference enumeration;
- near-degenerate scale suppression and rare-outlier fallback;
- small-n Fisher-Yates exact-uniform construction;
- variable-atom-count EVAL2 ratio behavior; and
- accepted-code audit showing why the target-order structural view must disable declared/profile groups.

This evidence is deliberately bounded. Real current-provider construction, complete coordinate mapping on representative data, family-weight sensitivity, optimized/reference equivalence, solver/resource qualification, restart/persistence, stale-generation rejection, and prepare->consume integration remain unavailable until the accepted method is ready for D3/D4 concretization or an independent reviewer can realize equivalent pre-implementation evidence.

## 5. Gate state

- Gate A candidate authoring: **Revision 4 complete**.
- Gate A bounded author-side falsification: **complete for the stated mathematical/static fixtures; partial overall**.
- Gate A fresh independent D1/D2 review: **pending**.
- Gate A human ratification: **pending**.
- Permanent D1/D2 paper mutation: **blocked**.
- D3/D4 behavioral implementation: **blocked**.

The next admissible action is a fresh independent review of Revision 4 and its evidence. Human ratification applies only to the Revision-4 bundle after that review passes.