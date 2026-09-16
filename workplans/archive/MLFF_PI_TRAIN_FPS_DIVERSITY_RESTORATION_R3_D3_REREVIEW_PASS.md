---
kind: independent-D3-rereview
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R3
protocol_version: 6.3.0
reviewed_repaired_candidate_commit: c7db32b4c9f2487450ae18d8d9dd5b948905a9ed
reviewed_candidate_path: workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF_REPAIRED.md
review_basis_head: 1a178e0b846cb68bcaca91446a43d0d9cf79602b
prior_no_pass_review: e129776186b986a7e26383806a9cf34bfef8996e
verdict: PASS
serious_challenge: false
r1_authority_reopened: false
r2_reopened: false
canonical_d3_promoted: false
d4_authorized: false
---

# Independent Protocol-6.3 D3 re-review — repaired R3 PASS

## 1. Verdict

**PASS.** A fresh independent review of the repaired R3 candidate found no remaining genuine D3 blocker and no Serious Challenge to accepted R1 D1/D2 authority.

The repaired architecture is sufficiently explicit that a conforming D4 cannot legally duplicate the normal-path neighborhood construction, duplicate canonical obligation meaning, consume unauthenticated pre-adoption selector state, or begin product implementation while canonical current D3 still contradicts the accepted design.

This PASS accepts the repaired R3 architecture candidate for promotion. It does **not** itself authorize D4. The exact accepted architecture must next be reconciled into the canonical D3 Architecture Manual and that promoted D3 checked for internal consistency before product-code mutation begins.

R1 remains **PASS / ACCEPTED / COMPLETE**. R2 remains **PASS / CLOSED**.

## 2. Independent review basis

Reviewed against:

- accepted D1 `docs/methods/mlff_target_training_order_scientific_method.md`;
- accepted D2 `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`;
- composed workplan Revisions 5, 6, 7 and 8;
- closed R2 dependency/provenance map;
- current pre-promotion D3 Architecture Manual;
- current prepare/P2/prepared-generation ownership at accepted basis `e72090e21cec5311ce87745b03603f8783cd15a7`;
- coherent historical recovery carrier `3937881ef00222e80845aa81f5471d89a4a7736c`;
- prior R3 NO-PASS counterexamples, used only as falsification targets rather than inherited conclusions;
- Revision-8 PEM/HAS basis recorded in the repaired candidate.

The branch head was verified unchanged at `1a178e0b846cb68bcaca91446a43d0d9cf79602b` before recording this review.

## 3. Prior blocker closure

### R3-B1 — shared FEAS1 / NEIGHBOR1 / MVIDX topology: CLOSED

The repaired candidate now owns one exact NEIGHBOR1 construction on the normal prepared path. FEAS1 reductions may execute while that relation streams, and the authenticated NEIGHBOR1 store is then adopted/inverted by MVIDX rather than queried again.

This matches the mature recovered capability in `target_coverage_feasibility.py@3937881...`, where `build_target_coverage_feasibility_artifacts(...)` returns both `TargetCoverageFeasibilityReport` and `TargetCoverageExactNeighborhoodStore` from one exact pass.

The repair does not make obligation semantics part of the NEIGHBOR scientific relation: canonical obligations are a parent of FEAS capacity analysis and MVIDX obligation incidence, while exact candidate-witness geometry remains owned by TargetCoverageReference/NEIGHBOR semantics. D4 may therefore reuse an authenticated NEIGHBOR artifact across obligation-only changes when its own scientific parents still match; the architecture does not require needless geometry recomputation.

### R3-B2 — one canonical membership-obligation authority: CLOSED

The repaired candidate explicitly constructs one canonical obligation authority after exact `P_train` and TargetCoverageReference are known and before FEAS/MVIDX/selector execution.

It binds canonical locus `L(o)`, exact incidence `A(o)`, effective minimum `k(o)`, applicability/provider identity, source provenance and governing P2 policy identity. The same semantic authority is an explicit parent of FEAS1, MVIDX representation, MVSEL2, REPAIR2, independent MVQUAL semantics and current P2 qualification projection.

MVIDX is explicitly an exact sparse representation of that authority rather than its definition. Incidence equality alone cannot create semantic aliases. Same-locus minima compose by `max`, and distinct loci remain distinct.

### R3-B3 — pre-adoption restart/currentness ownership: CLOSED

The repaired candidate cleanly distinguishes:

```text
pre-adoption prepare build state
  = reconstructible, attempt/build-owned, never downstream-current

completed prepared generation
  = immutable prepared products + manifest
  -> CampaignStore CAS adoption establishes currentness
```

Reusable MVSTATE/history/checkpoint state requires deterministic prospective build identity, schema/content integrity, prefix/repair ancestry validation, attempt isolation and crash-safe publication. Mutable scratch cannot be cross-adopted. Stale/corrupt/incompatible state is discarded or reconstructed from primitive authority. Downstream commands cannot discover pre-adoption continuation state.

The resulting design preserves CampaignStore as the sole completed-generation currentness owner and does not introduce selector-specific currentness, GC or migration machinery.

### R3-B4 — canonical D3 authority promotion before D4: CLOSED

The repaired R3 makes promotion a mandatory post-review D3 gate:

```text
repaired proposed R3
 -> independent PASS
 -> direct canonical Architecture Manual reconciliation
 -> internal-consistency / stale-owner check
 -> D4 authorization
```

The candidate names the minimum affected canonical D3 owners and also requires removal/reconciliation of any additional stale competing target-order topology. Thus D4 cannot legally implement against a workplan overlay while contradictory current D3 remains active.

## 4. Additional falsification results

### P2 dependency direction is acyclic

The repaired graph requires resolved target-size policy and `U_size -> P_train + M3` before selector construction, but only the final P2 experiment-definition/qualification projection after the order exists. This is compatible with the current P2 decomposition: split/policy and order are separable inputs, and `build_target_size_experiment_definition(...)` consumes an already-constructed split plus training/evaluation orders. No circular P2 owner is required.

### TargetCoverageReference remains the sole selector-specific fitted owner

Historical DATA7 fitted numeric ownership remains retired. Provider-dependent families are admitted only through an already-authorized current target-size provider; current target-size execution does not activate a foundation/replay provider. No second fitted selector reference is introduced.

### MVQUAL independence is preserved

MVQUAL receives immutable TargetCoverageReference, canonical obligation definitions and configured prefixes and independently recomputes accepted predicates. MVIDX may be used only as an exact secondary cross-check; selector/repair counters are not an oracle.

### Performance/resource capability transfer is preserved

The repaired contract retains the accepted mature capability envelope: shared FEAS/NEIGHBOR computation, file-backed/OOC sparse construction, bounded anonymous scratch, O(1)-in-family-count mapped descriptors, certified-lazy/full-forward equivalence, qualified native row scoring where retained, post-repair cache/history invalidation, optimized complete-order suffix, bounded restart, clean installed-package/native qualification and representative current-scale prepare performance evidence.

### No new wrapper/parallel-owner architecture

The repaired design uses the current prepare, P2, prepared-storage/CampaignStore and resource owners. It permits local D4 merging/renaming of recovered modules where semantics remain exact, and explicitly forbids compatibility routers, duplicate selector stores/currentness, alternate suffix selectors and selector-specific GC.

## 5. HAS disposition

The repaired candidate's Revision-8 HAS is coherent for this current selector path:

- SP-001, SP-002, SP-003, SP-004, FF-002 and FF-005 remain APPLICABLE;
- FF-001 and FF-004 are NOT_APPLICABLE to the current target-size selector path because the current target-size protocol authenticates foundation/replay mode `none`; they must be refreshed if a future accepted target-size method activates such a provider;
- FF-003 remains NOT_APPLICABLE because no destructive selector cleanup owner is introduced.

No new PEM family/occurrence is warranted by this review.

## 6. Nonblocking implementation/promotion clarifications

These are not D3 blockers:

1. the canonical D3 promotion should keep NEIGHBOR scientific identity tied to its true geometry/reference parents rather than broadening it merely because FEAS reductions share the construction pass;
2. the D4 cutover skeleton may be implemented early internally, but the new policy identity must not become current until the restored path is complete enough to satisfy the accepted currentness/publication contract;
3. exact class names, checkpoint file layouts, policy-token strings and helper/module boundaries remain delegated D4 choices provided the accepted ownership and identity relations are preserved.

## 7. Gate disposition

**R3 independent D3 re-review: PASS.**

Next mandatory action is canonical D3 promotion. At minimum reconcile:

- `docs/arch_manuals/mlff_training_data_architecture.md`;
- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/50_target_size_selection.md`;
- `docs/arch_manuals/mlff_training_data/60_execution_performance.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- any additional current D3 passage found to encode the superseded target-order topology.

After promotion, verify one internally consistent current D3 authority with no stale competing target-order owner. Only then set `d4_authorized: true` and begin product implementation.
