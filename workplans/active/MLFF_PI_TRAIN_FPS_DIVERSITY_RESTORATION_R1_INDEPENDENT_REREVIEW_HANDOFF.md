---
kind: independent-D1-D2-rereview-handoff
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: REREVIEW_REQUESTED
candidate_authority_state: PROPOSED_NOT_ACCEPTED
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_snapshot: 3937881ef00222e80845aa81f5471d89a4a7736c
branch: design/mlff-pi-train-fps-diversity-restoration
---

# R1 independent D1/D2 re-review handoff — repaired candidate

## 1. Reviewer instruction

Perform a fresh independent Protocol-6.3 D1/D2 Review/Challenge of the **repaired** R1 candidate. Do not inherit either the reconstruction author's repair conclusion or the first review's NO-PASS conclusion. Verify that the specific blockers are actually closed and re-run the broader falsification needed to ensure the repair did not introduce drift.

Accepted-current authority remains:

- `hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:docs/methods/mlff_scientific_method.md`;
- `hjin98/mdstats@e72090e21cec5311ce87745b03603f8783cd15a7:docs/methods/mlff_numerical_algorithmic_method.md`.

The candidate is still proposed and requires stakeholder ratification after a PASS.

## 2. Candidate evidence set

Review together:

1. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
2. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`;
3. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_RECONSTRUCTION_EVIDENCE.md`;
4. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_D2_REPAIR_ADDENDUM.md`;
5. `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`.

The repair addendum controls wherever earlier proposed R1 text conflicts with it. The exact reconstruction ledger is the required lossless field/input disposition map.

The earlier `R1_INDEPENDENT_REVIEW_HANDOFF.md` is evidence of the first review scope only and is superseded as the active handoff by this document.

## 3. Immutable historical evidence basis

Primary recovery carrier:

`hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c`

At minimum independently inspect the exact recovery-snapshot versions of:

- `mdstats/training_data/target_coverage.py`;
- `mdstats/training_data/target_coverage_feasibility.py`;
- `mdstats/training_data/target_coverage_exact_neighborhood.py`;
- `mdstats/training_data/target_coverage_sparse_index.py`;
- `mdstats/training_data/target_multi_view_selector_v2.py`;
- `mdstats/training_data/target_multi_view_repair_v2.py`;
- `mdstats/training_data/target_multi_view_qualification_v2.py`;
- `mdstats/training_data/_target_multi_view_scoring.py` where qualification behavior requires it;
- `docs/specs/training_data/mlff_data7_fitted_metrics_selection_spec.md`;
- `docs/specs/training_data/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md`;
- relevant target-size study specification/evidence.

Do not substitute relocated history copies for exact recovery identities when deciding what the mature chain actually owned.

## 4. First-review blockers that must be re-falsified

### 4.1 Canonical hard-obligation semantic deduplication

Attempt to break the repaired rule that automatic restored obligations plus current explicit hard-support obligations are normalized and semantically deduplicated before canonical IDs and hard-gain scoring.

Verify:

- source-local ID/name does not define semantic identity;
- exact aliases collapse to one obligation;
- same supplied source ID with different semantics fails closed;
- same semantic locus with conflicting minimum/incidence/applicability fails closed rather than becoming two votes;
- retired label-domain/fold target-size topology does not survive via obligation projection;
- `H(c)` counts only unsatisfied canonical obligations.

Construct the metamorphic counterexample: duplicate one obligation under a different source ID/name. The canonical set, selected UID history, REPAIR2 outcome and MVQUAL result must be unchanged.

### 4.2 Lossless field/input reconstruction ledger

Check that the exact ledger is genuinely complete rather than representative. In particular verify dispositions for:

- every `TargetCoveragePolicy` scientific field;
- FEAS1 `support_degree_bins`, `exclude_own_correlation_unit`, `fragile_zero_mass_tolerance`, historical capacity ceiling;
- NEIGHBOR1/MVIDX1 exact boundary/tolerance and obligation/correlation incidence;
- MVSEL2 comparator/tolerances/lazy certification;
- all REPAIR2 policy fields including `clustering_score_authority`;
- MVQUAL threshold/universe/monotonicity/independence;
- DATA6/DATA7 selector inputs and non-selector DATA7 fields.

Any selector-relevant field lacking one current owner and explicit `RESTORE/REBIND/DROP` disposition is a blocker.

### 4.3 DATA7 versus TargetCoverageReference ownership

Challenge the repair conclusion that `TargetCoverageReference` should be the sole fitted selector numeric owner while DATA7 retains only logical lineage/input semantics for this subchain.

Determine whether this is the only reconstruction consistent with the mature executable without losing an instantiated scientific capability. Specifically test whether any fitted DATA7 metric/PCA/scaler/atomic-reference/objective/checkpoint quantity was actually consumed by mature TargetCoverage/FEAS1/MVIDX1/MVSEL2 membership behavior. If yes, identify the exact missing dependency. If no, reject any attempt to restore a duplicate fitted owner merely because the integrated prose named a DATA7 bundle.

### 4.4 Certified-lazy MVSEL2 contract

Independently derive whether the repaired D2 lazy invariant is sufficient for exact rank equivalence:

1. exact all-available-candidate Phase-B rebase;
2. outward conservative upper bounds (`nextafter` or proven stronger equivalent);
3. stale score is only a bound, never current exact authority;
4. refresh whenever its bound can reach the incumbent contender interval;
5. certification only once `B_max < R_best - 1e-14`;
6. all candidates in `R >= R_best - 1e-14` have exact current scores before downstream correlation/diversity/UID tie-breaks;
7. full-forward exact scorer remains per-rank oracle/fallback;
8. accepted REPAIR2 swaps invalidate every pre-swap frontier/cache/history dependency and force exact state reconstruction before continuation.

Test epsilon ties, stale-bound refresh, full rebuild, restart, fallback and post-repair continuation.

### 4.5 Named-family threshold override

Attempt to falsify the repaired threshold census. Search the coherent recovery snapshot and associated accepted qualification evidence for any **instantiated** material/profile policy that changes a named selector-family hard-coverage threshold away from 0.95.

If one exists, the uniform mapping is a blocker and the exact owner/threshold must be restored. If none exists, confirm that classifying the historical override sentence as a dormant/uninstantiated extension point preserves evidence without granting D4 permission to invent overrides.

## 5. Broader D1 falsification still required

The repair does not waive the original D1 review. Re-evaluate:

1. use of exact `P_train` labels as training-design evidence rather than held-out evidence;
2. separation of configuration count `N` from correlation-balanced reference mass;
3. target-response families as scientific membership coverage, not model-accuracy ranking;
4. foundation residuals only for an authenticated foundation-based protocol and exact `P_train`;
5. mandatory support for every represented current P1 correlation unit;
6. condition/event/profile/extent/explicit obligations as membership constraints, not P3 ranking;
7. 0.95 mass coverage plus q01/q99 extent support;
8. complete separation of MVQUAL membership admissibility from P3 target-force ranking;
9. one current `P_train`, no historical label-domain/fold selector authority;
10. no unnecessary change to accepted P1/P3/P5 science.

Raise **SERIOUS CHALLENGE** if accepted/proposed D1 itself is scientifically incompatible with the stakeholder-directed restoration rather than hiding the disagreement in D2.

## 6. Broader D2 falsification still required

Re-evaluate:

1. correlation-unit-balanced family weight formula;
2. stable weighted quantiles and scale fallbacks;
3. scaled RMS-L2 family metric;
4. leave-one-out `beta=1/128` local radius;
5. exact `1e-12*max(1,r)` neighborhood boundary;
6. required family catalog/applicability;
7. exact two-phase comparator and inclusive `1e-14` tie semantics;
8. hard gain as canonical-obligation count;
9. REPAIR2 eligibility, shortlist, objective, non-regression, limits and rank inheritance;
10. current ladder replacing only obsolete fixed topology;
11. full-`P_train` continuation with the same MVSEL2 method rather than UID suffix;
12. independent direct MVQUAL oracle and MVIDX secondary check;
13. deterministic equivalence under qualified optimized/parallel execution;
14. restart reconstruction after any authoritative repair divergence.

## 7. Counterexamples

At minimum test or reason through:

- exact obligation alias under a new ID;
- conflicting minimum counts for the same semantic obligation locus;
- UID-clustered structures;
- one condition containing multiple structural regimes;
- candidate helps easy families but not bottleneck;
- hard-closing candidate with worse representative gain;
- contenders tied within `1e-14` except correlation count/UID;
- mass coverage passes but lower/upper extent fails;
- rare event/profile class omitted;
- represented correlation unit omitted;
- `M3` perturbation changing selector inputs;
- scratch protocol loading a foundation provider;
- accepted repair changing a protected lower prefix;
- pre-repair lazy state reused after a swap;
- stale bound hides a true `1e-14` contender;
- larger nested prefix fails after smaller pass;
- suffix after configured `N_max` becomes UID order;
- hypothetical profile threshold override is invented without an accepted policy identity.

## 8. Required output

Report, in order:

1. any **SERIOUS CHALLENGE**;
2. exact blocking findings by D1/D2 owner;
3. disposition of each of the five first-review blockers;
4. historical evidence checked and any applicability dispute;
5. whether the field/input reconstruction is lossless after justified current-architecture adaptations;
6. whether any historical mechanism was incorrectly promoted to authority;
7. whether any instantiated mature capability was dropped;
8. PASS/NO-PASS for the **repaired proposed D1/D2 candidate**;
9. if PASS, state explicitly that stakeholder ratification and accepted-paper promotion are still required before R2/D3/D4 implementation.

Do not implement source code as part of this re-review.