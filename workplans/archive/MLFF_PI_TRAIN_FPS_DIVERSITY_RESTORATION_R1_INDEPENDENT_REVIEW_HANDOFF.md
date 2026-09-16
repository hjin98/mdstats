---
kind: independent-D1-D2-review-handoff
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: REVIEW_REQUESTED
candidate_authority_state: PROPOSED_NOT_ACCEPTED
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
branch: design/mlff-pi-train-fps-diversity-restoration
---

# R1 independent D1/D2 review handoff

## 1. Reviewer instruction

Perform an **independent** Protocol-6.3 D1/D2 Review/Challenge. Do not inherit the reconstruction author's conclusion that the proposed method is correct merely because it matches recovered code or historical specifications.

The accepted-current authority under review remains:

- `hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:docs/methods/mlff_scientific_method.md`;
- `hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:docs/methods/mlff_numerical_algorithmic_method.md`.

Proposed candidate overlays:

- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`.

Reconstruction/evidence map:

- `workplans/active/MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`.

The candidate remains non-authoritative until this review passes and the stakeholder ratifies it.

## 2. Protected stakeholder direction

The governing stakeholder direction is to restore the **latest mature pre-P6 MVSEL2 selection path that was working**, including current-compatible optimization/parallelism later in the cycle, while dropping only historical topology/mechanisms incompatible with current machinery.

This direction does not authorize changing current P3 target-size ranking, `pi_eval/M1/M2/M3`, post-selection CV, replay or production semantics.

## 3. Historical reconstruction evidence that must be checked independently

Primary recovered implementation carrier:

`hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c`

At minimum inspect:

- `target_coverage.py`;
- `target_coverage_feasibility.py`;
- `target_coverage_exact_neighborhood.py`;
- `target_coverage_sparse_index.py`;
- `target_multi_view_selector_v2.py`;
- `target_multi_view_repair_v2.py`;
- `target_multi_view_qualification_v2.py`;
- `_target_multi_view_scoring.py`.

Historical semantic references:

- `docs/history/mlff/retired_specs/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md`;
- `docs/history/mlff/retired_specs/mlff_data7_fitted_metrics_selection_spec.md`;
- `docs/history/mlff/retired_specs/mlff_target_subset_size_study_spec.md`.

Do not assume a retired spec is correct where final executable/qualification evidence contradicts it. Conversely, do not turn an accidental implementation detail into D1/D2 authority without a semantic reason.

## 4. Required Challenge questions

### 4.1 D1 scientific adequacy

Attempt to falsify all of the following:

1. Is it scientifically legitimate for target-training membership to use `P_train` target labels, given that those labels are training-design evidence rather than held-out validation?
2. Does using correlation-unit-balanced family reference mass preserve the meaning of target size `N` as configuration count, or does the candidate accidentally redefine the estimand?
3. Are target-response families (force/energy/stress/strain/thermodynamic channels) justified scientific coverage dimensions rather than leakage from `M3` or downstream model evaluation?
4. Are foundation-residual families correctly conditional on a foundation-based target-size protocol, and does exact-`P_train` rebinding eliminate the old final-development leakage risk?
5. Does requiring every P1 correlation interval/unit to appear at least once in a configured admissible prefix remain scientifically appropriate under the current P1 protected-relation meaning?
6. Are condition, event, profile-environment, extent and explicit user obligations correctly interpreted as membership-support constraints rather than target-size ranking evidence?
7. Is hard family coverage at 0.95 plus q01/q99 extent support a defensible reconstruction of the latest mature method, or is any part merely an unaccepted historical implementation constant?
8. Is the separation between membership qualification and current P3 target-force ranking complete, so MVQUAL cannot become a second target-size reducer?
9. Does the proposed method preserve current one-`P_train` semantics without reintroducing label-domain/fold target-size authority?
10. Are all changed D1 claims necessary for restoring the stakeholder-directed method, with unaffected current P1/P3/P5 science preserved?

If any accepted-current D1 claim itself is incompatible with restoring the stakeholder-directed latest path, raise **SERIOUS CHALLENGE** rather than silently editing downstream D2.

### 4.2 D2 numerical adequacy

Attempt to falsify:

1. exact correlation-unit-balanced weight formula;
2. stable weighted-quantile convention and scale fallbacks;
3. scaled RMS-L2 family metric;
4. leave-one-out `beta=1/128` local-radius construction;
5. final `1e-12*max(1,r)` neighborhood tolerance and its consistency with direct MVQUAL;
6. exact required family catalog and applicability conditions;
7. canonical automatic + explicit hard-obligation union;
8. MVSEL2 Phase-A and Phase-B ranking order, inclusive `1e-14` contender tolerance and stable UID final tie;
9. hard gain as count of unsatisfied obligations helped, not deficit magnitude;
10. REPAIR2 removal eligibility, shortlist ordering, lexicographic objective, non-regression, limits and rank inheritance;
11. current configured ladder replacing only historical fixed-size topology while preserving method semantics;
12. full-`P_train` continuation from final repaired prefix using the same MVSEL2 method;
13. independent MVQUAL direct coverage as oracle, MVIDX secondary `5e-12` cross-check, and monotonic qualification;
14. numerical determinism under optimized/parallel execution;
15. restart reconstruction semantics after repair divergence.

### 4.3 Counterexamples that should break a weak reconstruction

A conforming review should explicitly consider or construct cases where:

- UID order clusters nearly identical structures;
- one condition contains several distinct structural regimes;
- a candidate helps many easy families but not the current bottleneck;
- a candidate closes an unsatisfied hard obligation but has worse representative gain;
- two candidates tie within `1e-14` except for correlation-unit count or UID;
- selected mass reaches 0.95 but misses a required lower or upper extent;
- a rare structural event/profile class is omitted despite high aggregate family coverage;
- a correlation unit has no selected representative;
- an `M3` label perturbation changes a selector input;
- a scratch protocol accidentally loads a foundation model;
- an accepted repair swap would invalidate a prior configured prefix;
- a post-repair continuation reuses stale pre-swap state;
- a larger nested prefix fails after a smaller prefix passed;
- suffix ranks beyond configured `N_max` fall back to UID rather than MVSEL2.

## 5. Known historical discrepancies requiring explicit reviewer disposition

The reconstruction author resolved these; reviewer must independently confirm or overturn them:

1. retired chain prose used `distance <= radius`; final NEIGHBOR1/MVIDX/direct coverage froze a `1e-12` metric boundary tolerance;
2. retired prose allowed possible named family/profile threshold overrides; final recovered `TargetCoveragePolicy` has one uniform threshold only;
3. historical target study fixed powers-of-two through 16,384; current target-size ladder is configurable and the fixed universe is old topology;
4. historical coverage/residual construction used label-domain/final-development training domains; current architecture has one exact `P_train`;
5. historical product qualification emphasized configured ranks; current `TargetTrainingOrder` requires a full permutation;
6. old direct DATA7 selector exists historically but is earlier than the later DATA7->MVIDX1->MVSEL2 chain and must not be substituted merely because its source still survives.

## 6. Scope/non-goals

Do not review D4 source restoration or performance implementation at this gate except where historical code is evidence needed to recover D1/D2 semantics.

Do not ratify the proposed method on behalf of the stakeholder. Independent review may conclude PASS/NO-PASS/Serious Challenge; human ratification remains a separate gate after any review blockers are repaired.

Do not reopen unrelated current post-selection restoration/threshold-separation science unless this candidate actually conflicts with it.

## 7. Required review output

The independent review should state, in this order:

1. any **SERIOUS CHALLENGE** to accepted or proposed D1/D2;
2. exact blocking findings by D1 or D2 owner;
3. historical evidence checked and any disputed applicability;
4. whether the reconstructed method is lossless relative to the latest mature path after justified current-architecture adaptations;
5. whether any historical mechanism was incorrectly promoted into scientific/numerical authority;
6. whether any required historical capability was accidentally dropped;
7. PASS/NO-PASS for the **proposed D1/D2 candidate**, not for implementation;
8. if PASS, an explicit statement that stakeholder ratification is still required before current-authority promotion and R2.
