---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1-GATE-A-R5-IMPLEMENTATION-REPAIR
protocol_version: 6.3.0
status: active
parent_workplan: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
branch: design/mlff-fps-coverage-method-reconciliation
reviewed_candidate: 029653d8f6a7001c766368bef1de6efdf2933aa8
prior_reviewed_candidate: 7ae141f3c60bf2819a9da2aa7af975109ded110a
accepted_d1_d2_baseline: e8d04144f55c72d799ffcd3fe40c75e47078a66d
highest_affected_domain: D1
current_repair_highest_affected_domain: D2
challenge_state: no-serious-challenge-revision-5-core
human_ratification: required-before-d1-d2-acceptance
---

# Gate A Revision 5 implementation-repair workplan

## 0. Disposition

The original assembled D1/D2 materialization at `7ae141f3c60bf2819a9da2aa7af975109ded110a` was **NO PASS** because materialization rewrote unaffected accepted authority. Candidate `029653d8f6a7001c766368bef1de6efdf2933aa8` repaired that losslessness problem and restored the accepted non-target-order method surface, but a second author-side review found four remaining D2 reconstructibility/identity blockers.

The Revision-5 target-order scientific method itself is still not reopened: no Serious Challenge remains against its central scientific design. This repair does not create Revision 6. It preserves the settled Revision-5 scientific/numerical construction and closes only the newly identified D2 identity, numerical-authority, and ordering gaps while leaving still-unrealized Gate-A evidence open.

## 1. Governing repair invariants

1. **Lossless baseline preservation.** Canonical D1/D2 remain based on `hjin98/mdstats@e8d04144f55c72d799ffcd3fe40c75e47078a66d`. Outside explicitly affected Gate-A paragraphs/sections and necessary lifecycle/provenance metadata, accepted text remains preserved.
2. **No conceptual redesign.** Preserve the Revision-5 target-order core: exact protected `U_size -> P_train + M3`; at least one retained training frame per eligible neutral condition; exact rational globally minimum condition depletion `J*`; completion admissibility; retained-set redundancy rescoring; material-neutral cell/strain/local-structure metric; separate `d_U`/`d_P`; one representative anchor per condition; condition-local exact farthest-point sampling (FPS); exact proportional condition scheduling; one immutable `pi_train`; exact `T_N` prefixes; exact full `M3` automatic EVAL2 at every fidelity boundary; diagnostic-only `pi_eval/M1/M2`.
3. **No collateral method mutation.** Preserve accepted practical-equivalence, optimizer, replay, post-selection cross-validation (CV), checkpoint, final-production, source-convention, strain/stress, and numerical-equivalence semantics unless Revision 5 explicitly changes them.
4. **Real-owner numerical authority.** Numerical equations owned by `mdstats.analysis.local_structure` must be made reconstructible at that analysis owner. The MLFF D2 paper binds the exact owner/specification identity and does not duplicate/redefine the local kernel.
5. **Identity separation.** Scientific occurrence/tie identity must distinguish declared occurrences; numerical component tie ordering must not depend on non-semantic `frame_uid` or serialized P1 relation spelling; P1 ancestry/currentness remains separately bound and fail-closed.
6. **Lifecycle honesty.** Canonical branch files are proposed candidates only. The accepted baseline remains current until separate-context independent review passes and the human owner ratifies the exact candidate.
7. **Evidence cannot be manufactured.** Repairing documents does not close pending real-feature sensitivity, precision, resource-feasibility, metamorphic, provider-lineage, capability-transfer, or independent-review obligations.

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
    reason: Repair the real D1/D2 and analysis numerical owners rather than adding another selector, wrapper, or shadow specification.
  - id: FF-005
    disposition: APPLICABLE
    reason: Preparation-owned target-order scientific state remains immutable and downstream-consumed rather than reconstructed.
  - id: SP-002
    disposition: APPLICABLE
    reason: Exact occurrence, component, metric, order, and currentness identities are fail-closed obligations; the copied-occurrence collision is therefore blocking.
  - id: SP-003
    disposition: APPLICABLE
    reason: Prepared target-order state remains publication-owned and reusable without reconstructing accepted scientific state.
  - id: SP-004
    disposition: APPLICABLE
    reason: Later D3/D4 acceptance still requires real-owner integration evidence rather than proxy-only proof.
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

No new PEM family is admitted by this repair. The newly found defects are current D2 specification defects inside the already governed Gate-A cycle, not evidence of a new generalized recurring project family.

## 3. Required D1 repair

The lossless D1 materialization remains valid. Make only the terminology clarification discovered by the second review:

- Section 5.1 must say that the candidate-independent evidence defines one target-order **metric policy/schema** and one order owner, while D2 realizes that policy as separately fitted `d_U` and `d_P` instances on their authorized fit domains.

This is a layer-boundary clarification, not a scientific-method change. All other D1 wording from candidate `029653d8...` remains unchanged.

## 4. Required D2 repair

The lossless D2 materialization remains the base. Preserve the existing Revision-5 exact split/order/full-`M3` method and close the following blockers.

### 4.1 Scientific occurrence identity

The target-order occurrence key must use the accepted `source_occurrence_signature`, not only `source_identity_signature`. The key must distinguish two declared source occurrences that intentionally share identical source content, frame index, condition, and geometry.

Define an exact new occurrence-key schema/encoding and require `kappa` uniqueness over exact `U_size`. A duplicate `kappa` is fail-closed identity failure; it must not be resolved by traversal order or lexical `frame_uid` spelling.

Add an oracle with two copied/distinct declared occurrences sharing source-content identity and geometry but differing in source-occurrence identity.

### 4.2 Component numerical tie identity versus P1 ancestry

Define one explicit numerical `component_key` from the canonical sorted member scientific occurrence keys, including singleton components. Do not use an ambiguous “P1 protected-relation identity” or the existing UID-derived P1 component digest as the numerical tie key.

Keep the accepted P1 split-exclusion authority identity, projected component membership, and currentness/ancestry evidence separately bound to split identity. A P1 authority change may stale the split even when a component's semantic member set and numerical tie key happen to remain unchanged.

### 4.3 Analysis-owned local-structure numerical contract

Reconcile `docs/specs/analysis/local_structure_features_spec.md` at its real analysis owner so a competent reader can reconstruct the already implemented feature values without reverse-engineering `local_structure.py`. Preserve current behavior and make explicit at minimum:

- covalent-radius fallback and smooth cosine-switch equation;
- weighted distance mean/std, smooth coordination, hard-neighbor count, weighted-degree norm, and species entropy;
- radial Gaussian and local-density Gaussian kernels;
- weighted Legendre angular moments;
- weighted Steinhardt/bond-orientational `q_l` normalization;
- coincident-neighbor handling;
- exact missing-mask/zero-fill semantics;
- stable feature order and current default policy values; and
- binary64/backend-equivalence boundary.

This is documentation/numerical-authority completion of existing semantics, not permission to change feature values. The MLFF D2 paper must bind the exact reconciled specification blob and remain downstream of that owner.

### 4.4 Canonical target-order coordinate order

Because target-order squared distances use left-to-right binary64 accumulation and exact score ties, define the canonical semantic coordinate order completely rather than delegating it to provider serialization or mapping iteration.

The D2 paper must explicitly define:

- family order;
- global versus element scope;
- atomic-number order;
- feature order inside every family;
- aggregation-statistic order; and
- numerical-coordinate versus missing-indicator order.

Feature-column permutation after semantic naming must leave the canonical accumulation order and downstream discrete decisions unchanged.

### 4.5 Representative terminology

The condition anchor is the observed frame nearest the coordinate-wise median vector; it is not the conventional minimum-total-distance medoid. Rename it **median-nearest representative** in current D2 prose, retaining the earlier “medoid” name only as provenance where useful.

### 4.6 Preserve previously repaired structural policy

Retain:

- at least three strictly increasing positive power-of-two candidate sizes;
- configured `0 < m1 < m2 < m3`, all positive powers of two, with `m1/m2` diagnostic-only and `m3=|M3|` the exact decision population;
- exactly three strictly increasing positive fidelity epochs;
- one ordered unique nonnegative optimizer-seed population;
- at least three qualified candidates before automatic screening; and
- the accepted tiny fixed floating-point comparison guard beyond scientific `epsilon`.

### 4.7 Preserve unaffected post-selection/final-production method

Keep accepted D2 Sections 14-19 unchanged except mechanically necessary cross-reference wording. In particular retain missing-fold/failed-seed/no-admissible-checkpoint handling, replay-label semantics, no hidden target duplication, both accepted final-publication modes, current MACE realization boundary, and numerical-failure/precision semantics.

## 5. Review/lifecycle repair

After the repaired semantic commit exists:

1. update the independent-review handoff to name that exact commit as the assembled review subject;
2. make the copied-occurrence, component-key separation, reconciled local-kernel specification, canonical coordinate order, and median-nearest representative explicit review checks;
3. state that amendment overlays/candidate summaries remain provenance/cross-check aids, not the primary reconstruction burden;
4. update repair status so canonical branch paths remain explicit **proposed candidate owners**, while accepted authority remains immutable `e8d04144...` until acceptance; and
5. retain pending Gate-A evidence as blockers and do not close Gate A.

## 6. Evidence status

The prior author-side exact-solver falsification found no defect in the documented `J*`/completion recurrence: randomized bounded exhaustive comparisons and multistep completion-admissibility checks matched the proposed exact semantics. The second author-side review also found no Serious Challenge to the Revision-5 D1 scientific design. These observations narrow repair scope but are not a separate-context Gate-A PASS.

Still required before PASS FOR HUMAN RATIFICATION:

- representative real-feature equal-family ablation/reweight sensitivity;
- provider/aggregation precision sensitivity;
- independent copied-occurrence/component-key/coordinate-order metamorphics and reference checks;
- independent exact-solver/reference evidence as required by the handoff;
- representative exact-method CPU/RAM feasibility;
- independent capability-transfer/provider-lineage audit;
- separate-context independent assembled D1/D2 review; and
- explicit human ratification after review PASS.

## 7. Acceptance for this implementation-repair stage

This repair stage is complete when:

1. unaffected accepted D1/D2 sections remain preserved rather than editorially rewritten;
2. no accepted strain/source/training/CV/replay/final-production numerical semantics are lost;
3. the candidate retains the complete Revision-5 target-order method and explicit `M3` limitation;
4. occurrence identity uses `source_occurrence_signature`, exact `U_size` `kappa` values are required unique, and the copied-occurrence collision is eliminated;
5. numerical `component_key` is defined independently from P1 serialization while P1 ancestry/currentness remains separately bound;
6. the analysis-owned local-structure specification contains reconstructible numerical equations matching the existing implemented feature contract, and MLFF D2 binds its exact blob;
7. canonical target-order coordinate accumulation order is fully defined at D2;
8. the condition anchor is unambiguously defined as the median-nearest representative;
9. structural candidate/evaluation/fidelity/seed constraints remain explicit;
10. practical-equivalence floating guard semantics match the accepted baseline;
11. the review handoff identifies the exact assembled candidate commit and contains the new falsification obligations;
12. Gate A remains open for the still-required evidence/review/human gate; and
13. no GPU qualification prerequisite is introduced.

Failure of any item reopens this implementation-repair child plan. It does not by itself reopen the settled Revision-5 scientific design.