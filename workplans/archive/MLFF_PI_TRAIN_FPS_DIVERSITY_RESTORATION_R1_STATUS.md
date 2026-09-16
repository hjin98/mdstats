---
kind: R1-status
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: ACCEPTED_COMPLETE
accepted_current_authority_changed: true
reviewed_candidate_commit: 815823494c88969944eee8f58a6cf107d97bcc09
stakeholder_ratified_date: 2026-09-15
implementation_authorized: false
---

# R1 status — accepted D1/D2 target-order restoration

## Decision

**R1 PASS / ACCEPTED / COMPLETE.**

The independently reviewed consolidated R1 D1/D2 candidate at `815823494c88969944eee8f58a6cf107d97bcc09` was explicitly stakeholder-ratified on 2026-09-15. The accepted semantics are promoted into the current method-paper family as:

- D1: `docs/methods/mlff_target_training_order_scientific_method.md`
- D2: `docs/methods/mlff_target_training_order_numerical_algorithmic_method.md`

Those two scoped papers are the sole current D1/D2 owners for the restored `TargetTrainingOrder` / `pi_train` multi-view membership-design surface. The general MLFF D1/D2 papers remain current for unaffected method surfaces and are subordinate to the scoped papers where old target-order text conflicts.

## Review / ratification chain

1. accepted-current baseline used for reconstruction: `e72090e21cec5311ce87745b03603f8783cd15a7`;
2. coherent recovery carrier: `3937881ef00222e80845aa81f5471d89a4a7736c`;
3. initial reconstructed candidate received independent NO-PASS with bounded blockers;
4. repairs `0542b4dad005d42827292968d259300eb87f5a87` and `fcee78445f6d9ad48543fca108a5234afc32515a7` closed those blockers;
5. independent D1/D2 re-review returned PASS;
6. `815823494c88969944eee8f58a6cf107d97bcc09` consolidated the reviewed candidate without changing its proposed semantics;
7. stakeholder explicitly approved R1 on 2026-09-15;
8. this acceptance transition promotes the reviewed semantics into current scoped method authority and retires the workplan amendments as provenance rather than parallel authority.

## Accepted R1 semantics

The accepted restoration establishes:

- exact current `P_train` as the sole target-order domain;
- logical selector-input lineage plus one fitted `TargetCoverageReference` owner;
- uniform hard family threshold `0.95` with no instantiated named-family override;
- canonical automatic + explicit hard obligations defined by scientific support locus and exact incidence, with same-locus accepted minima composed by `max(k)`;
- one hard-gain vote per unsatisfied canonical locus;
- exact NEIGHBOR1/MVIDX sparse authority;
- exact binary64 MVSEL2 Phase A/B comparator and certified-lazy Phase-B equivalence to full-forward oracle;
- configured-shell REPAIR2 with exact hard deficit `sum_o max(0,k_o-q_o(S))` and recovered bounded swap policy;
- exact post-repair reconstruction/invalidation;
- independent MVQUAL and monotone configured-prefix admissibility;
- the same optimized exact selector continuing beyond the final configured shell to a complete permutation of `P_train`;
- preservation of current P1/P2/P3, `pi_eval/M1/M2/M3`, post-selection CV/replay/production, and final GPU-qualification deferral outside this scoped change.

## Superseded R1 candidate artifacts

The following remain immutable reconstruction/review provenance but are not current method authority after promotion:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_REPAIR_ADDENDUM.md`
- R1 independent-review/re-review handoff artifacts
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`

The exact reconstruction ledger remains evidence for field/source dispositions. It cannot override the accepted scoped method papers.

## Challenge state

There is no remaining Serious Challenge against the accepted reconstructed D1/D2 method.

The **current executable** `candidate_independent_priority.v1` implementation remains under the workplan's implementation-level challenge until D3/D4 replaces it and assembled qualification passes. This is no longer a D1/D2 authority ambiguity.

## Downstream gate

R1 no longer blocks downstream work. R2 dependency/provenance recovery is closed in `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R2_DEPENDENCY_PROVENANCE_MAP.md`.

A proposed R3 D3 architecture / D4 implementation contract is prepared in `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R3_D3_D4_IMPLEMENTATION_HANDOFF.md`.

D4 product-code mutation is still **not authorized by this status file**: Protocol 6.3 requires independent D3 review/acceptance first. On D3 PASS/acceptance, implementation may proceed without reopening R1 unless evidence challenges the accepted scientific/numerical method.
