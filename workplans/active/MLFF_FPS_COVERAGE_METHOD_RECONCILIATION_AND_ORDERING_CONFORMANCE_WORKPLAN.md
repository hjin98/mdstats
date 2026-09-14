---
kind: abstraction-concretization-change-plan
workplan_id: MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1
protocol_version: 6.3.0
status: active
created_date: 2026-09-13
branch: design/mlff-fps-coverage-method-reconciliation
basis_commit: 1093a8bdf3c291b20623f8f2daee8b794d80ebb4
highest_affected_domain: D1
challenge_state: SERIOUS_CHALLENGE
human_ratification: required-before-d1-d2-acceptance
---

# MLFF FPS/coverage methodology reconciliation and ordering-conformance workplan

## 0. Disposition: SERIOUS CHALLENGE to the promoted target-order methodology

The accepted 2026-09-13 D1/D2 reconstruction is not yet adequate around construction of the target-size training and evaluation orders.

The current D1 paper permits candidate-independent priority evidence but the current D2 paper also permits empty priority vectors. Production `prepare` calls `build_target_size_statistical_aggregate(...)` without training/evaluation priority evidence, so ordinary `pi_train` and `pi_eval` reduce to condition balancing plus UID order. Because `T_N = pi_train[:N]`, that makes the target-size learning curve depend on an arbitrary ordering realization rather than a recovered coverage method.

This workplan reopens the earliest affected owner, D1, then D2, and only after accepted upstream reconciliation repairs D3/D4 conformance. It does **not** revive retired FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology, label-domain fanout, pre-target CV, generated rescue sizes, or per-candidate selectors.

## 1. Protected outcome and non-goals

Restore a scientifically interpretable target-size ladder in which changing `N` adds configurations according to one frozen candidate-independent sampling/coverage method, while preserving V7's one-study/one-order/exact-prefix simplification.

Current normative owners remain:

- D1: `docs/methods/mlff_scientific_method.md`
- D2: `docs/methods/mlff_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data_architecture.md` and subordinate architecture chapters
- D4: current training-data specifications and `mdstats/training_data/*`

D1/D2 amendments remain **proposed** until independent falsification and explicit human ratification. No behavior-changing D3/D4 implementation is accepted before Gate A closes.

This cycle does not change the paired-seed reducer, screen fidelity tuple, optimizer/replay/post-selection CV/final-production methods, restore historical quota constants, or require production-scale GPU qualification.

## 2. Gate A authority package — completed authoring, pending independent review and human ratification

The implementation request of 2026-09-13 directed the cycle to fix D1/D2 authority before D3/D4. Gate A authoring has therefore been completed as a **resolved candidate**, without prematurely modifying permanent authority or downstream behavior.

Authoritative candidate artifacts on this branch:

- `workplans/active/mlff-fps-coverage-method-reconciliation/GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`
- `workplans/active/mlff-fps-coverage-method-reconciliation/GATE_A_BOUNDED_FALSIFICATION_RECORD.md`

The candidate resolves every workplan decision row rather than leaving a menu for implementation. Its proposed method is:

```text
mu_train
  = equal mass per P_train frame
  + one representative medoid anchor per nonempty neutral condition

split
  = preserve current exact protected-relation P_train/M3 allocation
  + replace arbitrary UID tie steering with scientific occurrence/component keys

training evidence
  = geometry-only current neutral raw features
  + current-generation rebound universal structural frame descriptors
  - target labels, foundation residuals, difficulty, candidate outcomes

metric
  = two equal blocks
  = median/IQR robust scaling with explicit missing/fallback semantics
  = block dimension normalization
  = FP64 Euclidean, no PCA/whitening/random projection

pi_train
  = condition medoid anchors
  -> exact within-condition FPS
  -> empirical-condition proportional global interleaving through max configured N
  -> deterministic nonexperimental completion tail

mu_eval
  = exact M3 empirical force-component EVAL2 estimand

pi_eval
  = deterministic scientific-key hash within neutral condition
  + empirical-condition proportional interleaving
  - FPS, difficulty, target labels, candidate outcomes

qualification
  = only explicit hard-support obligations gate
  = coverage/event/environment metrics remain soft diagnostics
```

The candidate also contains the required stage-by-evidence authorization matrix, capability-transfer map, exact tie/tolerance rule, UID-independent scientific key, resource envelope, currentness identity inputs, old-generation fail-closed rule, and explicit retired mechanisms/constants.

### 2.1 Author-side falsification result

A bounded clustered/common + rare-support fixture compared UID order, pure FPS, representative-only, difficulty-only, and the combined candidate. The combined method preserved empirical condition proportions while removing representative-only coverage holes and avoiding difficulty-only/pathological UID behavior. At prefix 32, for example:

```text
method               mean-distance  q95     R_max   condition-L1
UID                   3.037          5.101   5.107   1.300
pure FPS              0.104          0.206   0.224   0.300
representative only   0.399          0.789   4.704   0.037
difficulty only       2.657          4.773   4.956   0.988
combined candidate    0.100          0.224   0.283   0.037
```

The same fixture passed one-to-one UID-renaming invariance because UID spelling is not read by the proposed governing scores. This is author-side evidence only; it does not satisfy the independent Gate A review requirement.

## 3. Historical capability transfer — resolved in the candidate

The candidate distinguishes the two historical lineages rather than reviving either topology:

- early DATA7: representative anchors, condition support, exact FPS, environment/event/difficulty queues, coverage reporting;
- later MVSEL/MVQUAL: multi-view progressive coverage, independent rescoring, `D_max`/`D_sum`/`N95`/uncovered-mass families and bounded optimized kernels.

Disposition summary:

- preserve one deterministic order/exact prefixes;
- promote representative condition medoid + exact FPS capability;
- promote current material-neutral structural frame descriptors, rebound to current ancestry;
- map historical `D_max` to current `R_max`;
- replace unnormalized historical `D_sum` with `D_mean` under explicit `mu_train`;
- retain independent rescoring as a verification pattern;
- keep profile/environment evidence diagnostic-only in the baseline;
- retire foundation residual/difficulty from baseline membership ordering;
- retire `N95`/uncovered mass until a current radius threshold is scientifically accepted;
- retire historical quotas/fractions/thresholds and FEAS/MVIDX/MVSEL/REPAIR/MVQUAL public topology.

The refreshed Historical Applicability Set in the candidate uses accepted project state `e8d04144...` and the accepted PEM at `4eabe2ae...`.

## 4. Producer-lineage decision

Current `FittedFeatureMetric`/DATA7 role authority is **not** reusable as the target-order owner because its fit-domain identity remains tied to retired label-domain/fold-local DATA7 semantics. Likewise, a current `Data6FeatureBundle` cannot be imported wholesale merely to obtain descriptors.

The candidate instead authorizes the smallest current inputs:

- `NeutralFeatureEvidence.raw_features` for current neutral raw geometry;
- the material-neutral `mdstats.analysis.local_structure` / `UniversalStructuralFeatureCatalog` low-level provider for frame structural descriptors, rebound by D3/D4 to current P1/P2 ancestry;
- mature pure FPS/coverage numerical kernels from `selection.py`, consolidated behind a neutral numerical implementation boundary rather than through `TrainingSelectionPlan`.

This keeps `prepare` CPU-capable and avoids a new foundation-model/GPU dependency.

## 5. D3/D4 target after Gate A closes

Once the candidate is independently reviewed and human-ratified, downstream implementation must realize:

```text
canonical/neutral P1 evidence
  -> one preparation-owned target-order evidence/metric owner
  -> one P2 split/order owner
       -> exact split
       -> fitted P_train metric
       -> pi_train + pi_eval + diagnostics
  -> common target-size preparation
  -> immutable prepared generation
  -> downstream screen/manual/CV/production consumers
```

Required consequences:

1. production order policy is explicit and non-optional;
2. missing current pre-order evidence is a typed preparation failure, never empty-vector/UID fallback;
3. current order/evidence/metric/method identities participate in generation currentness;
4. old empty-evidence generations and dependent target-order evidence remain historical and require fresh `prepare`;
5. downstream consumers perform zero source rereads, DATA6/DATA7 rebuilds, metric fits, or FPS reconstruction;
6. no per-N/per-seed/per-fold/per-label-domain master-order fanout appears;
7. soft coverage diagnostics cannot become hidden qualification/reducer gates;
8. `pi_eval` remains candidate-outcome independent and preserves the ordinary M3 EVAL2 estimand;
9. pure numerical FPS/coverage kernels are centralized/reused rather than copied or wrapped through retired product topology.

## 6. Required Gate A independent review

An independent D1/D2 reviewer must review the assembled candidate rather than inheriting this authoring context. At minimum falsify:

- UID/condition-only, pure-FPS, representative-only, and difficulty-only counterexamples;
- whether one mandatory medoid per training neutral condition plus empirical proportional interleaving is scientifically coherent;
- whether excluding foundation/difficulty from baseline ordering is an unacceptable loss of scientifically required support;
- whether the raw + universal structural metric is sufficient and free of target-label leakage;
- the exact median/IQR/missing/fallback/block-normalization metric;
- the `1e-12 * max(1, |score|)` FP64 tie policy;
- the bounded-FPS-through-max-N completion-tail semantics;
- the proportional deterministic-hash evaluation order and preservation of the M3 EVAL2 estimand;
- the decision not to make the split coverage-aware in this repair;
- the UID-independent scientific occurrence/component key;
- capability-transfer and producer-lineage classifications;
- CPU/resource feasibility.

The independent reviewer must reproduce or replace the author-side evidence and cover input-enumeration invariance, metric-coordinate identity, direct simple-reference FPS equivalence, evaluation-estimand reference checks, and old-generation rejection at the appropriate level.

## 7. Human ratification gate

Explicit human adjudication remains mandatory for the resolved bundle. Gate A is not closed by this implementation pass itself.

The human decision is specifically whether to accept the candidate's:

- empirical-frame `mu_train` plus one training medoid anchor per neutral condition;
- geometry-only raw + universal structural metric and exclusion of foundation/difficulty ordering;
- robust two-block FP64 metric and tolerance;
- condition-local medoid-seeded FPS with proportional global interleaving;
- proportional deterministic-hash `pi_eval` preserving the ordinary M3 EVAL2 estimand;
- unchanged split objective apart from UID-independent tie repair;
- absence of historical quota/radius-threshold machinery;
- CPU-capable bounded-FPS preparation.

**Blocker:** permanent D1/D2 edits and behavior-changing D3/D4 implementation remain prohibited until independent review passes and this human ratification is explicit.

## 8. Gates B–F after ratification

### Gate B — D3/D4 contract reconciliation

Update D3 ownership/data flow/currentness/invalidation and current D4 specs. Do not duplicate D1/D2 mathematics in D3.

### Gate C — numerical kernel consolidation

Extract/reuse the pure exact FPS and coverage-distance kernels under one current numerical owner, retain a simple bounded oracle, prove exact equivalence/ties, and remove/narrow duplicate obsolete paths.

### Gate D — prepare/persistence wiring

Construct current pre-order evidence during `prepare`, pass it to P2, persist all material identities, preserve zero-rebuild downstream consumption, and add stale-generation negatives.

### Gate E — assembled qualification

Run focused reference/metamorphic tests, affected regression, real `prepare -> order -> publish -> consume`, RAM/scaling checks, static/package/import checks, and independent D1–D4 conformance review. Full production GPU qualification remains deferred.

### Gate F — history/closeout

After accepted implementation, update permanent D1/D2/D3/D4 owners, add descendant semantic-history reconciliation, record stale descendant impact, perform PEM closeout assessment, and archive this workplan only when no current authority remains in the workplan.

## 9. Acceptance oracles after ratification

The implementation evidence floor remains:

- exact FPS simple-reference equivalence and stable ties;
- UID-renaming, input-enumeration, and feature-coordinate invariance;
- monotone training `R_max` and monotone support counts where definitions are monotone;
- exact prefix/permutation invariants;
- evaluation-prefix proportionality/direct M3-estimand check;
- changed method/evidence/metric identity invalidates stale descendants;
- old empty-evidence generation fails current admission;
- no dense persistent O(N^2) pairwise state;
- real prepare path follows the accepted method when it conflicts with UID order;
- manual selection after prepare performs zero metric/FPS/source reconstruction;
- repository search proves no current FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology has reappeared.

## 10. Current disposition

**Gate A authoring: COMPLETE.**

**Gate A independent D1/D2 review: PENDING.**

**Gate A human ratification: PENDING.**

**D3/D4 behavioral implementation: BLOCKED BY GATE A.**

This is the correct Protocol 6.3 stopping point for the requested authority-first implementation: the missing D1/D2 choices are now explicit, falsifiable, and implementation-complete as a proposal, while the repository has not been made internally contradictory by silently implementing an unratified scientific/numerical method.