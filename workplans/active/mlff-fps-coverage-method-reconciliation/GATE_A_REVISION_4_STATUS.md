# Gate A Revision 4 current status

Date: 2026-09-13
Workplan: `MLFF_FPS_COVERAGE_METHOD_RECONCILIATION_AND_ORDERING_CONFORMANCE_WORKPLAN.md`
Current candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`, Revision 4
Basis review: `GATE_A_REVISION_4_REVIEW.md`
Status: **same-thread review NO PASS; repair required; separate-context independent PASS and human ratification pending; D3/D4 behavioral implementation blocked**.

## 1. Lossless workplan reconciliation

The active parent workplan is restored to its original full reviewed text from blob `9e7f4a1492d52b63a09cc836fa6b784056172608`. That restores the complete Gate A-F sequence, mandatory corrections 11.1-11.12, historical capability-transfer obligations, evidence floor, reopen triggers, and final closure criteria that were lost when an earlier status rewrite compressed the plan.

This status record is the current cycle delta. It does not replace the parent workplan. Where the parent's exploratory/menu language or historical Revision-1 assumptions conflict with the resolved Revision-4 candidate, Revision 4 is the current proposed Gate A method. All unaffected parent obligations remain binding for this cycle.

## 2. Accepted project and PEM basis

The reconciliation branch has accepted main commit `e8d04144f55c72d799ffcd3fe40c75e47078a66d` as an explicit merge parent through `9a016f6087066c036c78b13c933bf3ddf30c5cc5`. The accepted D1/D2 method-paper blobs were identical before/after that ancestry merge.

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

## 3. Revision-4 resolved method delta that survived review

The following Revision-4 repairs remain sound and should be preserved unless a directly related repair proves otherwise:

- split support is hard-feasible for every eligible neutral condition;
- condition depletion is globally minimized exactly;
- structural redundancy is recomputed against the **current retained set** after every component removal, and a candidate removal is allowed only when an exact J*-optimal completion still exists;
- target-order raw geometry excludes material-specific pair-rule coordinates;
- local structural evidence uses an element-only no-declared-group neutral view rather than the profile-sensitive default universal aggregation;
- `pi_train` remains one medoid-seeded condition-local exact-FPS order with exact proportional interleaving;
- `pi_eval` is a genuine persisted Fisher-Yates SRSWOR realization over distinct M3 occurrences;
- foundation residual/difficulty and candidate outcomes remain forbidden membership dependencies;
- score winners/ties remain governed by a canonical scalar reference rather than a generic fuzzy tie tolerance.

## 4. Review blockers

`GATE_A_REVISION_4_REVIEW.md` records the current NO-PASS findings:

1. **Missing/all-missing semantics are incomplete.** Type-7 fitting is undefined when a source coordinate has zero observed values; binary missingness treatment and the exact definition of active family dimension `d_f` are also ambiguous. Constant/all-missing coordinates can otherwise change family weight despite carrying no discriminating information.
2. **The `sqrt(u)*max_abs` scale floor is not a derived provider-error bound.** A review-side scalar counterexample shows it suppresses differences about 4.5 million ulps above binary64 resolution. It therefore needs provider/conditioning derivation or explicit scientific ratification rather than being described as finite-precision necessity.
3. **Evaluation sampling uncertainty is not reconciled with irreversible reducer decisions.** M1/M2 SRSWOR noise can cross practical-equivalence `epsilon` or reverse ranking and permanently eliminate a candidate, while the current uncertainty is diagnostic only.
4. **Exact identity/reduction semantics remain incomplete.** `source_frame_index` hash width/sign encoding, `H_mean` canonical reduction, and the immutable low-level local-structure numerical-contract binding are not fully frozen.
5. **Gate A evidence/coordination remains incomplete.** The workplan-required historical capability-transfer map is absent; real-family weighting/sensitivity and other genuine D1/D2 evidence are missing. Some persistence/restart/old-generation/prepare-consumer checks currently listed as pre-promotion evidence actually belong to downstream D3/D4 Gates B-E and must be restaged rather than creating a circular Gate A dependency.
6. D1 says “cell/strain geometry” while D2 also uses `mass_density_g_cm3`; that order-changing composition-derived coordinate needs explicit D1 authorization or removal.

## 5. Evidence state

`GATE_A_REVISION_4_BOUNDED_FALSIFICATION_RECORD.md` remains applicable only to its bounded propositions:

- retained-set rescoring closes the Revision-3 mutual-redundancy counterexample;
- hard condition-preservation behavior is coherent on bounded exhaustive cases;
- Fisher-Yates is exact under the stated independent-unbiased-bit assumption;
- the variable-atom-count fixture correctly demonstrates finite-prefix ratio-estimator bias and exact full-M3 recovery;
- static accepted-code inspection supports excluding declared/profile groups from target-order structural evidence.

The same-thread review additionally produced a direct numerical counterexample to the current `sqrt(u)` conditioning rationale. No missing required realization is counted as a pass.

## 6. Gate state

- Gate A candidate authoring: **Revision 4 reviewed; repair required**.
- Gate A same-thread D1/D2 Challenge review: **NO PASS**.
- Gate A separate-context independent PASS: **still required after repair**.
- Gate A human ratification: **pending and premature**.
- Permanent D1/D2 paper mutation: **blocked**.
- Behavior-changing D3/D4 implementation: **blocked**.
- Downstream D3/D4 evidence obligations: **retain, but restage to their owning gates rather than using them as circular Gate A prerequisites**.

The next admissible action is a narrow Revision-5 repair of the review findings. A later PASS must come from a suitably independent review context before human ratification.