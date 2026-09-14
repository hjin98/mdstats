---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1-GATE-A-R5-IMPLEMENTATION-REPAIR
protocol_version: 6.3.0
status: active
parent_workplan: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
branch: design/mlff-fps-coverage-method-reconciliation
reviewed_candidate: 7ae141f3c60bf2819a9da2aa7af975109ded110a
accepted_d1_d2_baseline: e8d04144f55c72d799ffcd3fe40c75e47078a66d
highest_affected_domain: D1
challenge_state: no-serious-challenge-revision-5-core
human_ratification: required-before-d1-d2-acceptance
---

# Gate A Revision 5 implementation-repair workplan

## 0. Disposition

The assembled D1/D2 materialization at `7ae141f3c60bf2819a9da2aa7af975109ded110a` is **NO PASS**. The Revision-5 target-order method itself is not reopened: no Serious Challenge remains against its central scientific/numerical design. The blocking defects are implementation/materialization drift and still-unrealized Gate-A evidence.

This repair therefore does not create Revision 6. It restores the accepted 2026-09-13 D1/D2 text outside the exact Gate-A amendment surface and applies the already-settled Revision-5 semantics only where required.

## 1. Governing repair invariants

1. **Lossless baseline preservation.** Start canonical D1/D2 from `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d`. Outside explicitly affected Gate-A paragraphs/sections and necessary lifecycle/provenance metadata, preserve accepted text verbatim.
2. **No conceptual redesign.** Preserve the Revision-5 target-order core: exact protected `U_size -> P_train + M3`; at least one retained training frame per eligible neutral condition; exact rational globally minimum condition depletion `J*`; completion admissibility; retained-set redundancy rescoring; material-neutral cell/strain/local-structure metric; separate `d_U`/`d_P`; condition medoids; condition-local exact farthest-point sampling (FPS); exact proportional condition scheduling; one immutable `pi_train`; exact `T_N` prefixes; exact full `M3` automatic EVAL2 at every fidelity boundary; diagnostic-only `pi_eval/M1/M2`.
3. **No collateral method mutation.** Restore accepted practical-equivalence, optimizer, replay, post-selection cross-validation (CV), checkpoint, final-production, source-convention, strain/stress, and numerical-equivalence semantics unless Revision 5 explicitly changes them.
4. **Lifecycle honesty.** Canonical branch files are proposed candidates only. The accepted baseline remains current until separate-context independent review passes and the human owner ratifies the exact candidate.
5. **Evidence cannot be manufactured.** Repairing documents does not close pending real-feature sensitivity, precision, resource-feasibility, metamorphic, provider-lineage, capability-transfer, or independent-review obligations.

## 2. Historical Applicability Set

The parent workplan Historical Applicability Set (HAS) remains current for this repair and uses:

```yaml
pem_basis:
  accepted_project_state: 4eabe2ae9783c7ff92f3a1093c37502a01380812
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: Repair by restoring the real D1/D2 owners rather than adding another semantic wrapper.
  - id: FF-005
    disposition: APPLICABLE
    reason: Preparation-owned target-order scientific state remains immutable and downstream-consumed rather than reconstructed.
  - id: SP-002
    disposition: APPLICABLE
    reason: Exact metric/order/currentness identities remain fail-closed obligations.
  - id: SP-003
    disposition: APPLICABLE
    reason: Prepared target-order state remains publication-owned and reusable.
  - id: SP-004
    disposition: APPLICABLE
    reason: Later D3/D4 acceptance still requires real-owner integration evidence.
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: TRAIN2/EVAL2 model-construction authority is unchanged.
  - id: FF-002
    disposition: NOT_APPLICABLE
    reason: TRAIN2 checkpoint continuation is unchanged.
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: Destructive storage routing is unchanged.
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: GPU admission/process lifetime is unchanged; consolidated GPU qualification remains deferred.
```

## 3. Required D1 repair

Rebuild `docs/methods/mlff_scientific_method.md` from the accepted baseline, applying only:

- lifecycle metadata/authority paragraph identifying the file as the proposed Gate-A candidate while preserving 2026-09-13 reconstruction provenance;
- Section 2.3 target-size paragraph: one fixed exact `M3` decision population; `M1/M2` diagnostic only;
- Section 4.4 evidence-role statement;
- Section 5.1 pre-order target-order evidence and leakage scope;
- Section 6 in full for `mu_sel`, `mu_loss`, `mu_eval`, exact protected split, training-support priority, structural-support scope, one coverage-progressive `pi_train`, exact full-`M3` decisions, diagnostic `M1/M2`, EVAL2 estimand, paired seeds/successive fidelity, practical equivalence/operator decision, and leakage limits;
- Section 13.1 validity statement and Section 13.4 evaluation-sampling clarification;
- Section 14 target-order falsification additions;
- Section 15 target-order reproducibility/provenance update;
- D1 -> D2 handoff.

Add one explicit limitation: `M3` is a deliberately constructed finite development/model-selection reserve chosen while training support has priority. Exact-`M3` RMSE is the screen's finite-population estimand; it is **not claimed to be an unbiased estimator of a broader physical or deployment population**.

All other accepted D1 wording remains unchanged.

## 4. Required D2 repair

Rebuild `docs/methods/mlff_numerical_algorithmic_method.md` from the accepted baseline, applying only the established Revision-5 numerical amendments:

- candidate lifecycle metadata and target-order core-invariant bullets;
- Section 4.1 fixed material-neutral pre-order evidence with separate `d_U`/`d_P`; preserve accepted Section 4.2 verbatim;
- replace Sections 5-7 with the reconstructible feature/transform/split/order method;
- Section 12 exact full-`M3` EVAL2;
- Section 13.4 full-`M3` funnel interpretation while preserving Sections 13.1-13.3 and 13.5 except exact membership identity wording where necessary;
- revised Section 20 scaling/resource semantics;
- target-order verification/reproducibility additions;
- D2 -> D3 handoff and later reconciliation provenance.

### 4.1 Restore unaffected structural policy

Preserve the accepted structural-policy constraints that Gate A did not authorize changing:

- at least three strictly increasing positive power-of-two candidate sizes;
- exactly three strictly increasing positive fidelity epochs;
- one ordered unique nonnegative optimizer-seed population;
- at least three qualified candidates before automatic screening.

Reconcile the former evaluation-size rule without restoring decision authority: retain configured `0 < m1 < m2 < m3`, with the three values positive powers of two under the current structural policy. `m3 = |M3|` is the exact automatic decision population; `m1` and `m2` are only diagnostic prefix cardinalities of `pi_eval` and are not attached to funnel decisions.

### 4.2 Restore practical-equivalence numerical guard

Preserve the accepted D2 statement that only the existing **tiny fixed floating-point comparison guard** beyond scientific `epsilon` is permitted by the current method and that machine epsilon itself is not the scientific practical-equivalence policy. Do not delegate an unbounded decision-affecting tolerance to D4 as generic implementation detail.

### 4.3 Restore unaffected post-selection/final-production method

Preserve accepted D2 Sections 14-19 verbatim except mechanically necessary cross-reference wording. In particular retain:

- missing fold, failed required seed, no-admissible-checkpoint, or method-identity mismatch cannot be ignored for a favorable CV result;
- no inadmissible checkpoint fallback;
- true-reference/DFT versus pseudo-label replay semantics;
- no hidden target duplication;
- both accepted final-publication modes and the prohibition on downstream qualification selecting publication members;
- current MACE dependency realization boundary and numerical-failure/precision semantics.

## 5. Review/lifecycle repair

After the D1/D2 repair commit exists:

1. update the independent-review handoff to name the exact D1/D2 implementation commit as the assembled review subject;
2. state that amendment overlays/candidate summaries are provenance and cross-check aids, not the primary reconstruction burden;
3. update repair status so canonical branch paths are explicitly **proposed candidate owners**, while accepted authority remains the immutable `e8d04144...` baseline until acceptance;
4. retain pending Gate-A evidence as blockers and do not close Gate A.

## 6. Evidence status

The prior review's bounded author-side exact-solver falsification found no defect in the documented `J*`/completion recurrence: randomized bounded exhaustive comparisons and multistep completion-admissibility checks matched the proposed exact semantics. This narrows repair scope but is not a separate-context Gate-A PASS and does not waive the independent evidence required by the review handoff.

Still required before PASS FOR HUMAN RATIFICATION:

- representative real-feature equal-family ablation/reweight sensitivity;
- provider/aggregation precision sensitivity;
- representative exact-method CPU/RAM feasibility;
- independent target-order metamorphics/reference checks;
- independent capability-transfer/provider-lineage audit;
- separate-context independent assembled D1/D2 review;
- explicit human ratification after review PASS.

## 7. Acceptance for this implementation-repair stage

This repair stage is complete when:

1. comparison against `e8d04144...` shows unaffected D1/D2 sections preserved rather than editorially rewritten;
2. no accepted strain/source/training/CV/replay/final-production numerical semantics are lost;
3. the candidate contains the complete Revision-5 target-order method and the explicit `M3` limitation;
4. structural candidate/fidelity/seed constraints and diagnostic `m1/m2/m3` cardinality semantics are explicit;
5. practical-equivalence floating guard semantics match the accepted baseline;
6. the review handoff identifies the exact assembled candidate commit;
7. Gate A remains open for the still-required evidence/review/human gate;
8. no GPU qualification prerequisite is introduced.

A failure of any item reopens this implementation-repair child plan; it does not by itself reopen the settled Revision-5 scientific design.