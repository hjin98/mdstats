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

The current D1 paper states that candidate-independent ordering evidence *may* favor representative, difficult, diverse, or otherwise scientifically relevant frames. The current D2 paper then explicitly permits **no priority evidence**, represented by an empty vector for every frame, and defines the resulting order as condition round-robin with immutable `frame_uid` as the within-condition tie breaker. Production `prepare` currently calls `build_target_size_statistical_aggregate(...)` without either `training_priority_evidence` or `evaluation_priority_evidence`. Therefore the production `pi_train` and `pi_eval` are currently reduced, in the ordinary prepared-generation path, to condition balancing plus UID order rather than a recovered coverage/diversity method.

That is not merely a documentation omission. `T_N = pi_train[:N]` defines the experimental membership at every cardinality. If `pi_train` is scientifically arbitrary beyond condition balancing, the target-size learning curve confounds cardinality with an arbitrary ordering realization. The same problem affects the interpretation of nested `M1/M2/M3` evaluation prefixes when `pi_eval` has no actual representative-order evidence.

This workplan therefore reopens the target-order surface at the earliest affected owner, D1, then D2, and only after accepted upstream reconciliation repairs D3/D4 conformance. The plan does **not** revive the retired FEAS/MVIDX/MVSEL/REPAIR/MVQUAL public topology, label-domain fanout, pre-target cross-validation, generated rescue sizes, or per-candidate selectors.

## Background and terminology

**Farthest-point sampling (FPS)** is a deterministic maximin space-filling construction. Given feature vectors `z_i` and already selected set `S`, an FPS step chooses a remaining point maximizing distance to its nearest selected point:

```text
i* = argmax_i min_{j in S} d(z_i, z_j)
```

under the accepted fitted feature metric and deterministic tie rule.

A **covering distance** for candidate `i` under selected set `S` is

```text
d_i(S) = min_{j in S} d(z_i, z_j).
```

A **covering radius** is a population summary such as `max_i d_i(S)`; quantiles such as the 90th/95th percentile summarize how completely the selected prefix covers the authorized candidate population without claiming model accuracy.

`pi_train` is the one canonical deterministic ordering of `P_train`; every target-size candidate is the exact prefix `T_N = pi_train[:N]`. `pi_eval` is the one canonical deterministic ordering of the exact `M3` reserve; `M1/M2/M3` are exact nested prefixes of that order.

**Soft ordering evidence** influences priority/order but does not qualify or reject a candidate. **Hard-support obligations** are explicit configured prefix requirements that may qualify/reject an exact prefix. The two must remain separate.

A **coverage-progressive order** is one whose successive prefixes deliberately preserve required support and progressively improve the accepted representation/coverage objective rather than relying on an arbitrary stable identifier order.

## 1. Outcome and authority

### Protected outcome

Restore a scientifically interpretable, numerically reconstructible target-size ladder in which changing `N` means adding configurations according to one frozen candidate-independent sampling/coverage method, while preserving the accepted V7 simplification: one study, one training order, one evaluation order, exact prefixes, one prepared generation, no target-size domain fanout, and no second selector topology.

### Current normative owners

- D1: `docs/methods/mlff_scientific_method.md`
- D2: `docs/methods/mlff_numerical_algorithmic_method.md`
- D3: `docs/arch_manuals/mlff_training_data_architecture.md` and `docs/arch_manuals/mlff_training_data/{30_statistical_design,50_target_size_selection,80_ownership_and_decisions}.md`
- D4 specification: current owners indexed by `docs/specs/training_data/README.md`, especially `mlff_data_stage_plan_spec.md` and `mlff_data6_selection_descriptors_spec.md`
- D4 implementation: principally `mdstats/training_data/target_size_experiment.py`, `campaign_target_size_runtime.py`, prepared-generation persistence, neutral/DATA6 selection-evidence owners, and the mature FPS/coverage kernels currently present in `mdstats/training_data/selection.py`

### Proposed authority state

D1/D2 amendments produced by this work remain **proposed** until independent falsification and explicit human ratification. D3/D4 may be analyzed and non-semantic refactoring may be prepared, but no behavioral implementation is accepted as current merely because it anticipates the proposed upstream result.

### Explicit non-goals

This cycle does not:

- restore FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL as public or persisted current-generation authorities;
- restore label-domain target-size fanout, pre-target CV, per-seed orders, per-N repair, complement evaluation roles, or generated rescue sizes;
- make coverage/FPS scores a model-adequacy or target-size hard gate by default;
- change the paired-seed reducer, practical-equivalence rule, screen fidelity tuple, optimizer semantics, replay semantics, post-selection CV method, or final-production method unless upstream reconciliation proves one of those surfaces materially dependent;
- copy historical quota fractions or score thresholds into current authority merely because they once existed;
- perform production-scale GPU qualification. Functional/reference/resource qualification is required here; consolidated final GPU qualification remains deferred to the established final-release phase.

## 2. Historical Applicability Set and capability-transfer obligation

```yaml
pem_basis:
  accepted_project_state: 4eabe2ae9783c7ff92f3a1093c37502a01380812
  accepted_pem: hjin98/mdstats@4eabe2ae9783c7ff92f3a1093c37502a01380812:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
has:
  - id: SP-001
    disposition: APPLICABLE
    reason: The repair must return selection/coverage responsibility to one real owner and reuse/consolidate mature kernels rather than add a new wrapper or parallel selector.
  - id: FF-005
    disposition: APPLICABLE
    reason: Pre-order evidence is preparation-owned scientific state; downstream select/status/execution must consume the immutable prepared generation rather than reconstruct FPS/coverage from live inputs.
  - id: SP-002
    disposition: APPLICABLE
    reason: Ordering evidence, metric/policy identity, and derived orders must fail closed on stale or mismatched prepared-generation ancestry.
  - id: SP-003
    disposition: APPLICABLE
    reason: Expensive descriptor/coverage products should be published once at the prepared-generation boundary and reused by downstream consumers.
  - id: SP-004
    disposition: APPLICABLE
    reason: Final acceptance must execute the real prepare -> P2 order -> prepared-generation consumer chain rather than proving behavior only through helper fixtures.
  - id: FF-001
    disposition: NOT_APPLICABLE
    reason: This cycle does not change TRAIN2/EVAL2 model-construction authority.
  - id: FF-002
    disposition: NOT_APPLICABLE
    reason: TRAIN2 checkpoint continuation is outside the affected ordering surface; ordinary prepared-generation restart/currentness remains covered by SP-002/SP-003.
  - id: FF-003
    disposition: NOT_APPLICABLE
    reason: Destructive storage routing is not modified.
  - id: FF-004
    disposition: NOT_APPLICABLE
    reason: GPU admission/process lifetime is not modified and GPU qualification stays deferred.
```

### Required capability-transfer map

Before D1/D2 acceptance, reconstruct the historical selection capabilities and classify each as `current authority`, `proposed for promotion`, `diagnostic/evidence only`, or `retired mechanism`. At minimum cover:

| Historical capability | Required disposition question |
| --- | --- |
| one deterministic master order with exact nested prefixes | preserve; already current D1/D2 |
| mandatory condition/support anchors | preserve only through current explicit hard-support semantics or an accepted D1/D2 strengthening |
| representative-density/centroid support | determine exact current D1/D2 role |
| configuration-level exact FPS/maximin diversity | determine exact current D2 role and metric domain |
| species/environment/profile-group coverage | preserve material-neutral capability if accepted; do not hard-code historical LTA species |
| protected/rare-event prioritization | determine soft ordering role versus explicit hard obligation |
| foundation residual/difficulty enrichment | determine allowed fit/label domain and controlled role |
| candidate-to-selected nearest-distance quantiles and maximum covering radius | restore as method/diagnostic evidence where accepted |
| selected-to-selected nearest-neighbor diagnostics | restore where accepted |
| condition/environment/event coverage counts | restore where accepted |
| historical `D_max`, `D_sum`, `N95`, uncovered mass and independent rescoring | determine whether any remain current numerical diagnostics/oracles versus retired multi-view specifics |
| reference-equivalent bounded FPS/sparse/lazy kernels | reuse/consolidate when semantically applicable |
| independent coverage rescoring rather than trusting selector-internal flags | preserve as a verification pattern when an optimized selector has nontrivial internal scoring |
| public FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology | retire; capability may survive without mechanism |
| historical fixed quota fractions and thresholds | evidence only until D2 explicitly justifies and human owner accepts current values |

Historical evidence to inspect includes, at minimum:

- `docs/history/mlff/manual_snapshots/mlff_training_data_architecture_pre_doc_gov1.md`;
- `docs/history/mlff/architecture_revisions/ARCHITECTURE_NOTES_MLFF_REV72.md`;
- retired TARGET-DATA2B/TARGET-DATA2C/MVSEL/MVQUAL specifications and their bounded qualification evidence;
- `workplans/archive/MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md`;
- `workplans/archive/mlff-target-size-v7-packages/P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md`;
- current `mdstats/training_data/selection.py` exact FPS and coverage-report kernels;
- current D1/D2/D3/D4 sources at basis commit `1093a8bdf3c291b20623f8f2daee8b794d80ebb4`.

Do not choose between conflicting historical quota/score variants by recency alone. Reconstruct the intended capability and current scientific question first, then define the minimum current method.

## 3. D1 reconciliation: scientific meaning of the ladders

D1 review must answer and, after human ratification, state unambiguously:

1. **Why the training order exists.** `pi_train` is not merely any deterministic permutation. It exists to produce nested candidate populations whose increasing cardinality is scientifically interpretable as progressively broader/better-supported coverage under one frozen candidate-independent data-selection policy.
2. **What must be represented.** Determine the minimum accepted balance among ordinary representative support, condition/composition/regime support, structurally/environmentally distinct support, rare/protected events, and difficult-but-valid configurations. Distinguish universal requirements from profile-provided evidence.
3. **Why pure FPS is insufficient.** Space filling alone can overemphasize feature-space boundaries and underrepresent dense production mass; representative support and declared scientific strata/events must remain visible.
4. **Why coverage is not adequacy.** Coverage metrics characterize sampling support. They do not prove force-field accuracy, long-horizon stability, or deployment adequacy. EVAL2 learning behavior and downstream validation remain separate evidence.
5. **Soft versus hard evidence.** Rich coverage/diversity/difficulty signals may order frames without becoming candidate-qualification gates. Only explicit accepted hard-support obligations gate an exact prefix.
6. **Evaluation-ladder meaning.** Define what `pi_eval` must achieve over exact `M3`: nested prefixes must be useful and representative target-size model-selection populations, frozen before candidate outcomes. Decide explicitly whether difficulty/tail enrichment is appropriate for evaluation or whether evaluation uses only geometry/condition/representativeness evidence.
7. **Split meaning.** Reconcile the accepted statement that training support has priority while `M3` should preferentially consume redundant residual support and preserve useful representative coverage. Decide whether feature-space coverage participates in `P_train/M3` choice among otherwise feasible protected-relation allocations.
8. **Leakage boundaries.** Define which geometry-only, condition/event, foundation-prediction, and label-derived difficulty evidence may be fitted/used for: `U_size -> P_train/M3`, `pi_train`, and `pi_eval`. Do not let a convenient implementation decide these domains implicitly.

### D1 falsification questions

Attempt at least these counterexamples before acceptance:

- a deterministic UID/condition order that satisfies all current hard obligations but places nearly duplicate configurations in early prefixes while distant valid regimes appear only late;
- pure FPS that covers extremes but badly distorts dense production/condition mass;
- a difficulty-only order dominated by foundation-model outliers;
- an evaluation ladder enriched by target labels in a way that makes successive screen metrics a changing challenge distribution rather than a stable model-selection population;
- a coverage diagnostic that appears favorable while important declared event/condition support is absent.

D1 acceptance requires an explicit human decision on the scientific role of coverage/diversity/representativeness and on any unresolved historical conflict. Until then the current D1 target-order wording remains challenged.

## 4. D2 reconciliation: exact numerical construction

After D1 meaning is settled, D2 must define enough method that a competent reader can reconstruct `pi_train` and `pi_eval` without reverse-engineering code.

### 4.1 Pre-order evidence and metric

Define the exact authorized evidence classes and fit domains used by each order. Where a fitted heterogeneous feature metric is current, specify:

- input feature blocks and canonical feature-name/order rules;
- missing-value treatment;
- robust scaling/normalization and any PCA/whitening/projection semantics;
- fixed numerical seeds where decomposition is randomized;
- metric distance and precision;
- profile/group contributions and whether they enter one concatenated metric, separate views, or a declared interleaving policy;
- foundation residual/difficulty coordinates and their fit/label-access restrictions;
- immutable evidence/metric identity required for restart and prepared-generation currentness.

Do not preserve a historical fitted metric merely because the kernel expects one. The metric is part of the numerical method if it changes order/membership.

### 4.2 Training-order algorithm

Specify one canonical deterministic construction satisfying D1. The design may reuse the mature mechanisms—representative anchors, exact FPS, environment/group queues, rare-event queues, difficulty enrichment, correlation balancing, deterministic support-hole repair—but they must be composed into **one** order owner.

The accepted D2 method must state:

- mandatory seed/anchor semantics;
- how representative support is scored;
- the FPS/maximin rule and initial seed rule;
- how multiple evidence classes/views compete or interleave;
- any quota/fraction/weight schedule and its justification, if retained;
- deterministic deficit/tie resolution;
- what happens when one evidence class is exhausted;
- whether and how protected correlation relations affect order after the `P_train/M3` split;
- exact output/permutation invariants;
- which diagnostics are emitted but cannot mutate qualification.

`T_N` remains exactly `pi_train[:N]`; there is no per-N rerun, repair, swap, or selector.

### 4.3 Evaluation-order algorithm

Define `pi_eval` independently of candidate outcomes. It may share numerical kernels with `pi_train` only where its D1 role justifies that sharing. D2 must explicitly specify any distinct representative/coverage objective so the implementation cannot silently reuse the training-priority order when that would bias evaluation.

### 4.4 Coverage diagnostics and oracles

At minimum evaluate whether current D2 should restore the following formally defined diagnostics for each relevant prefix `S_N`:

```text
candidate nearest distance: d_i(S_N) = min_{j in S_N} d(z_i, z_j)
maximum covering radius:    R_max(N) = max_i d_i(S_N)
covering quantiles:         Q50/Q90/Q95 of {d_i(S_N)}
selected NN distances:      min_{j in S_N, j != i} d(z_i, z_j)
represented condition/environment/event support
```

If historical multi-view `D_max`, `D_sum`, `N95`, uncovered-mass, or related metrics remain scientifically useful, map them explicitly onto the accepted current representation; otherwise classify them historical rather than leaving ambiguous half-owners.

Required invariants/oracles include:

- prefix cardinality and permutation exactness;
- deterministic tie behavior;
- nonincreasing candidate covering radius for nested prefixes;
- nondecreasing represented-support counts where the support definition is monotone;
- bounded exact FPS reference equivalence;
- optimized-kernel equivalence against an independently simple implementation on bounded fixtures;
- no selector-internal coverage flag accepted as independent qualification evidence when an independent scorer is materially needed.

### 4.5 Resource/scaling semantics

Retain the V7 requirement that target-scale selection remain resource-feasible. Do not restore dense persistent `O(N^2)` pairwise state or millions-of-atomic-environment full FPS ordering when frame-level/bounded exact constructions satisfy the accepted method.

D2 must distinguish numerical identity from execution optimization. An incremental nearest-distance FPS state that exactly reproduces the accepted maximin/tie rule is an admissible realization; changing the metric, seed, tie rule, or evidence composition is not a performance-only change.

## 5. D3 architecture reconciliation

After D1/D2 acceptance, update D3 so the accepted pre-order method has one explicit software owner and one direct dependency flow.

Required architecture:

```text
canonical/neutral evidence owners
  -> one preparation-owned pre-order selection-evidence/metric owner
  -> one P2 split/order owner
       -> P_train/M3
       -> pi_train + pi_eval + diagnostics
  -> one common target-size training preparation
  -> immutable prepared target-size generation
  -> downstream screen/manual selection/CV/production consumers
```

### Frozen D3 decisions for this cycle

1. **Prepare owns construction.** Descriptor/metric/FPS/coverage inputs needed to define the current target-size generation are built or authenticated during `prepare`, then published in the immutable prepared generation. `select-target-size`, status, CV, and production do not rebuild them from live source data.
2. **One order owner.** `target_size_experiment` or its accepted replacement owns construction of `pi_train/pi_eval`; no DATA7 selector, MVSEL object, CLI helper, or runtime scheduler becomes a competing membership owner.
3. **Reuse kernels, not topology.** Mature pure FPS/coverage kernels may be extracted/moved/consolidated behind a neutral numerical-kernel boundary if current layering makes direct reuse inappropriate. Do not import the retired DATA7/MVSEL product model merely to reach those functions, and do not copy the kernels into a second implementation.
4. **Prepared identity binds the method.** Feature/metric/order-policy identities and the resulting pre-order evidence/order identities participate in target-size generation currentness. A material ordering-method change creates a new generation and invalidates dependent screen/provisional/frozen descendants according to the existing dependency model.
5. **No D1/D2 duplication in D3.** D3 documents producer/consumer ownership, persistence, currentness, and invalidation, not the mathematical FPS/coverage algorithm.
6. **No downstream reconstruction regression.** The repair must preserve the prepared-generation efficiency property captured by FF-005/SP-003.

### Simplification target

Prefer relocating/reusing the existing exact FPS and coverage-distance kernels from `selection.py` under the actual current numerical owner and deleting/narrowing obsolete duplicate call paths. A new wrapper that simply translates current target-size objects into the old `TrainingSelectionPlan`/legacy public selector topology is not an acceptable architecture.

## 6. D4 implementation-conformance obligations

The exact patch remains delegated to implementation after upstream acceptance, but the following behavioral end state is mandatory.

### 6.1 Production prepare must not silently choose empty evidence

The ordinary current `build_prepared_target_size_substrate(...)` path must construct/authenticate the accepted pre-order evidence and pass it to the target-order owner. If the accepted D2 policy requires a real metric/coverage method, the production API must not silently fall back to empty vectors and UID ordering when that evidence is missing.

Any intentionally supported minimal/no-feature regime must be explicit in D2/D4 policy and visibly identified; it cannot remain an accidental consequence of omitted optional arguments.

### 6.2 Bind/persist current pre-order evidence

Where a new or revised record is required, it must bind:

- exact authorized frame population/domain;
- source/feature provider identities;
- fitted metric/policy identity;
- exact per-frame evidence or reconstructible authenticated sidecars;
- deterministic numerical seed/tie policy where applicable;
- content digest and parent ancestry.

Use existing prepared-generation publication/currentness machinery. Do not introduce a second mutable target-size state store.

### 6.3 Consolidate the FPS/coverage kernel

Reuse/refactor the mature exact FPS state and incremental coverage-distance logic already qualified in the repository. Preserve a simple bounded oracle implementation for semantic comparison. Remove or narrow duplicated versions where safe.

If `selection.py` still has unrelated current DATA7 consumers, preserve those consumers while centralizing only the pure kernel. If it no longer has a legitimate current product owner, route its surviving capabilities to current owners and retire obsolete selection-plan machinery rather than keeping dead authority-shaped code for convenience.

### 6.4 Maintain hard/soft separation

Candidate qualification remains derived from exact prefix existence, usable labels, and explicit hard-support obligations. Soft FPS/coverage/representativeness/difficulty scores must not become hidden qualification gates, reducer tie-breakers, or target-size recommendations outside the accepted D2 policy.

### 6.5 Evaluation remains candidate-independent

No candidate predictions, optimizer outcomes, reducer survivor state, selected `N`, post-selection CV evidence, replay scores, or downstream physical evidence may enter `pi_eval` construction.

### 6.6 Specification reconciliation

Update existing D4 specification owners rather than adding another permanent spec by default. At minimum reconcile:

- `docs/specs/training_data/README.md`;
- `mlff_data_stage_plan_spec.md`;
- `mlff_data6_selection_descriptors_spec.md`;
- any exact current record/schema owner changed by implementation.

Create a narrowly scoped new target-order specification only if the existing current owners cannot represent the exact D4 contract without duplicating or mixing authority.

The specification index must also be corrected where it still describes the accepted D1/D2 reconstruction as merely proposed.

## 7. Required acceptance evidence

### 7.1 D1/D2 method evidence

Before authority acceptance, produce bounded fixtures/counterexamples demonstrating the behavior of the proposed method against at least:

1. UID/condition-only ordering;
2. pure FPS;
3. representative-only ordering;
4. difficulty-only ordering; and
5. the proposed combined method.

Use interpretable synthetic/real-small fixtures with clustered common support plus distant/rare/difficult support so tradeoffs are visible. The goal is not to optimize a benchmark score; it is to falsify the proposed claim that the combined order gives the intended nested scientific coverage without obvious pathological bias.

Historical quota variants are comparison candidates, not privileged answers.

### 7.2 Numerical/kernel evidence

- exact FPS bounded reference equivalence;
- stable tie tests;
- coverage-distance/quantile oracle tests;
- incremental versus direct recomputation equivalence;
- no missing/duplicate/foreign order members;
- exact prefix/nesting tests for all configured N and M rungs;
- changed metric/policy/evidence identity invalidates stale aggregate/order descendants;
- representative scaling and peak-memory tests showing no unjustified dense quadratic state;
- independent rescoring when required to avoid a self-confirming selector/scorer oracle.

### 7.3 D3/D4 real-owner integration

Run the real preparation/persistence path and prove:

```text
prepare
 -> accepted pre-order evidence
 -> P2 split/orders
 -> immutable prepared generation
 -> downstream manual/automatic target-size consumers
```

with these counterfactuals:

- a crafted feature-space fixture whose FPS/coverage order conflicts with lexical UID order; production `pi_train` must follow the accepted method, not UID;
- changing only the accepted feature/metric/order policy produces a new prepared-generation identity and rejects stale descendants;
- changing only a soft diagnostic threshold cannot toggle prefix qualification unless it is explicitly promoted to a hard obligation;
- candidate outcome/evaluation evidence cannot influence `pi_eval`;
- manual `select-target-size <N>` after prepare performs zero source rereads, zero DATA4/DATA6 rebuilds, and zero FPS/metric reconstruction;
- no per-N, per-seed, per-CV-fold, per-provenance, or per-label-domain master-order fanout exists;
- no current public/persisted FEAS/MVIDX/MVSEL/REPAIR/MVQUAL topology reappears.

### 7.4 Regression surface

At minimum re-run all materially affected current suites, including the owners represented by:

- `tests/test_mlff_target_size_statistical_authorities.py`;
- `tests/test_mlff_neutral_scientific_substrate.py`;
- DATA7/FPS selection-scaling/reference tests that exercise the reused kernel;
- `tests/test_mlff_campaign_prepared_generation_efficiency.py`;
- `tests/test_mlff_target_size_p4_authority_reconstruction_io.py`;
- `tests/test_mlff_target_size_p4d_runtime_cutover.py`;
- target-size prepared-generation/currentness/storage-composition tests implicated by changed component identity;
- D1/D2/D3/D4 documentation/specification structure tests.

Re-derive the final affected surface from the assembled candidate; this list is a floor, not a ceiling.

## 8. Concretization sequence and gates

### Gate A — reconstruct and propose D1/D2

1. Build the capability-transfer map across generic DATA7 FPS/coverage, later multi-view coverage/qualification, V7 simplification, and current code.
2. Resolve contradictions: historical quota values, coverage score families, hard-vs-soft roles, fit domains, and training-vs-evaluation ordering goals.
3. Draft D1 scientific-method amendments and D2 exact numerical-method amendments.
4. Execute independent D1/D2 falsification/review.
5. Obtain explicit human ratification.

**Blocker:** no behavior-changing D4 implementation is accepted before this gate closes.

### Gate B — reconcile D3/D4 contracts

1. Update D3 ownership/data flow/currentness/invalidation to realize accepted D1/D2.
2. Reconcile current D4 specification owners.
3. Independently review abstraction adequacy: D3/D4 must not permit silent empty-evidence UID ordering when accepted D2 requires the recovered method.

### Gate C — consolidate/reuse numerical kernels

1. Extract/move/reuse pure exact FPS and coverage-distance kernels under one current numerical implementation owner.
2. Keep a bounded simple oracle.
3. Prove exact equivalence for the retained kernel semantics and resource bounds.
4. Remove/narrow duplicate or obsolete selection-kernel copies rather than wrapping them.

### Gate D — wire preparation and persistence

1. Construct/authenticate accepted pre-order evidence at `prepare`.
2. Pass exact evidence to the single P2 order owner.
3. Publish every material identity in the prepared generation.
4. Preserve zero-rebuild downstream consumption.
5. Add restart/currentness negatives for changed evidence/policy/metric identities.

### Gate E — assembled qualification

1. Run focused numerical/reference tests.
2. Run stage-local affected regression.
3. Run real-owner prepare -> order -> publish -> consume integration.
4. Run scaling/RAM checks sufficient to detect an accidental dense-quadratic regression.
5. Run repository-required static/package/import checks.
6. Perform independent D1-D4 conformance review and Challenge pass.

Long GPU/full-production qualification remains deferred; no missing GPU run blocks this CPU/statistical ordering repair unless the implementation unexpectedly introduces GPU-dependent numerical semantics, in which case reopen the relevant owner.

### Gate F — documentation/history/closeout

After accepted implementation:

- update D1/D2 current method papers;
- update D3 architecture/dependency views;
- update affected D4 specs/indexes;
- record a new semantic-history reconciliation explaining the discovered loss and repair; do not rewrite archived snapshots to make the gap disappear;
- reconcile the 2026-09-13 promotion preservation record by a new descendant correction/evidence record rather than pretending the original review found this issue;
- perform PEM closeout assessment for recurrence/new preservation capability, but do not self-promote a new family without admissible evidence;
- archive this workplan only after current owners contain all accepted semantics and independent review passes.

## 9. Reopen and Challenge triggers

### D1 reopen

Reopen D1 if evidence shows that a coverage-progressive ladder is not actually required for the intended target-size scientific claim, if training/evaluation representation goals conflict materially, or if a proposed use of label-derived difficulty would bias the scientific interpretation of `M3/pi_eval`.

### D2 reopen

Reopen D2 if the accepted D1 goal cannot be expressed by one deterministic nested order without material loss; if the intended metric/coverage objective is ill-conditioned or unstable; if historical mechanisms encode materially incompatible objectives; or if no resource-feasible algorithm can preserve the accepted semantics at expected scale.

### D3 reopen

Reopen D3 if one preparation-owned pre-order evidence owner cannot be integrated without a cyclic dependency, duplicate scientific authority, or downstream reconstruction path; do not patch around the cycle with adapters or synchronized shadow state.

### D4-local blockers

Implementation bugs, serialization gaps, missing currentness bindings, incorrect tie/order behavior, duplicate kernel copies, or failure to pass evidence from prepare are D4 blockers under coherent accepted D1-D3 and do not justify weakening the method.

### Human decision triggers

Explicit human adjudication is required for:

- final D1 statement of the scientific purpose of training/evaluation coverage;
- final D2 composition of representative/FPS/environment/event/difficulty evidence when historical sources conflict;
- any retained current quota/fraction/score threshold not already independently accepted;
- any proposal to promote a historical diagnostic into a hard candidate gate.

## 10. Final acceptance condition

This work closes only when a fresh competent reader can recover from current D1/D2 **why** the target-size ladders are constructed, **how** `pi_train` and `pi_eval` are numerically constructed, what coverage diagnostics mean and do not mean, and what exact evidence is allowed at each boundary; and when the production D3/D4 path demonstrably realizes that method through one preparation-owned evidence flow and one order owner.

A green target-size screen is insufficient. Closure requires proof that production no longer obtains its ordinary ladder from omitted priority evidence and lexical UID fallback, while the accepted V7 simplification, exact nested prefixes, hard/soft separation, leakage boundaries, prepared-generation reuse, and bounded execution all remain intact.

## 11. Mandatory review corrections — remaining closure gaps

The first workplan draft is directionally correct but was not yet snapshot-complete for implementation. This section is normative for the current workplan and refines Sections 2–10 where they were underspecified. If an earlier sentence can be read more weakly than the requirements below, the requirements below control this cycle.

### 11.1 Define the represented measure before choosing a coverage method

“Representative” and “coverage” are incomplete scientific terms unless the reference measure is explicit. D1 must define, separately where necessary, the measure that the training ladder and evaluation ladder are intended to represent. At minimum adjudicate among or explicitly compose:

- equal mass per eligible frame;
- equal or configured mass per scientific condition/stratum;
- empirical trajectory/production-frequency mass;
- correlation-adjusted or unique-reference mass;
- profile-declared scientific importance weights; and
- any deliberate challenge/tail mass that is not intended to approximate the ordinary population frequency.

Call the accepted measures `mu_train` and `mu_eval` conceptually; exact symbol/name is delegated. They may differ only with an explicit D1 rationale. Historical “covered mass”, `N95`, centroid representation, condition balancing, and ordinary frame-count coverage must be mapped to the accepted measure rather than mixed implicitly.

D2 must then define every weighted/unweighted coverage statistic against the accepted measure. A quantile, `D_sum`, uncovered fraction/mass, or representative-centroid objective is not reproducible until its weighting measure and normalization are specified. Equal-condition round-robin, equal-frame FPS, and weighted-reference coverage are materially different numerical methods.

### 11.2 Preserve the EVAL2 estimand across the nested evaluation ladder

The current EVAL2 force RMSE is evaluated directly on `M_i`. Therefore a diversity-biased `pi_eval` can change the effective evaluation distribution between `M1`, `M2`, and `M3` even when every candidate at one rung sees the same frames.

D1 must explicitly decide whether each `M_i` is intended to:

1. approximate the same `mu_eval`/M3 model-selection estimand at increasing resolution; or
2. act as a deliberately different nested challenge distribution.

If option 1 is accepted, D2 must make the nested construction and any required evaluation weights preserve that estimand to the accepted approximation/error semantics. If option 2 is accepted, D1 must state what scientific conclusion early-rung comparisons support and why survivor decisions remain valid despite the changing challenge distribution. The implementation may not silently use pure FPS for `pi_eval` while interpreting unweighted RMSE as ordinary representative error.

Any evaluation weights introduced by this reconciliation are numerical-method identity, common to all candidates at the same rung, and must not depend on candidate predictions/outcomes. If no weights are accepted, D2 must justify the unweighted direct-population estimator under the accepted `pi_eval` construction.

### 11.3 Close the `U_size -> P_train + M3` algorithm, not only its D1 intent

Section 3 intentionally reopens whether representative/coverage evidence participates in choosing `M3` among exact feasible protected-relation allocations. Gate A must close that question completely:

- If coverage does **not** participate, D2 must explicitly preserve or replace the current deterministic exact-subset allocation rule and explain how the resulting split satisfies the accepted D1 meaning.
- If coverage **does** participate, D2 must define the constrained split objective, weighting measure, deterministic tie rule, precision, approximation/exactness semantics, and failure behavior while preserving exact `|M3| = m3`, `|P_train| >= Nmax`, and complete protected-relation components.
- A heuristic traversal may not claim scientific infeasibility merely because it missed a feasible exact allocation. Keep an exact/reference feasibility oracle on bounded cases and specify the admissible production approximation, if any.
- Split-scoring evidence must obey the stage authorization matrix in 11.4; post-split fitted or M3-label-derived evidence cannot flow backward into split selection.

This is a D2 obligation, not an implementation detail left to P2 code.

### 11.4 Produce an explicit stage-by-evidence authorization matrix and eliminate circular fitting

Before D1/D2 acceptance, publish one compact matrix covering every candidate evidence class and every target-order stage. At minimum include:

```text
rows:
  canonical condition/provenance facts
  geometry-only/raw structural features
  profile/environment features
  fitted geometry metric / scaler / PCA / whitening
  frozen foundation descriptors/predictions
  target-label-derived foundation residual/difficulty
  protected-event evidence
  correlation/duplicate/protected-relation evidence

columns:
  U_size eligibility
  P_train/M3 split scoring
  pi_train construction
  pi_eval construction
  soft coverage diagnostics
  hard prefix qualification
```

For every allowed cell record the owning source, fit domain, label access, and identity dependency; forbidden cells are explicit.

The matrix must prevent circularity. In particular:

- evidence used to choose `P_train/M3` cannot be fitted only on `P_train` after that split exists;
- P_train-only label-derived difficulty may be admissible for `pi_train` after the split if D1 accepts it, but cannot thereby influence the earlier split;
- M3 target labels may not be used to fit a training-order metric or difficulty signal merely because M3 is development/model-selection evidence;
- a geometry-only transform fitted over `U_size` may use M3 geometry only if D1/D2 explicitly accept that non-label information boundary;
- `pi_eval` may not consume candidate outcomes and may consume label-derived difficulty only if D1 explicitly accepts the resulting evaluation estimand;
- hard qualification consumes only the exact accepted hard-obligation evidence, never soft scores by implication.

No implementation work may resolve an empty/ambiguous cell by convenience.

### 11.5 Audit current producer lineage before reusing DATA6 or other historical products

The plan must not assume that an existing `Data6FeatureBundle`, DATA7 record, retired target-coverage artifact, or MACE model-sweep product is automatically a valid current-generation pre-order evidence owner. Before D3/D4 design freeze:

1. inventory the current code paths that can produce each accepted D2 input;
2. verify their fit/role/label-domain ancestry against the 11.4 authorization matrix;
3. distinguish reusable low-level descriptor/prediction sidecars from obsolete role/membership authority;
4. reject any producer whose identity still depends on retired pre-target CV, `label_domain_id` target-size fanout, fold-local DATA7 selection, or another incompatible lineage;
5. choose the smallest current owner/API that can publish the accepted evidence without recreating the retired product topology.

If foundation-model descriptors, predictions, or residuals are part of the accepted method, their checkpoint/head, calculator/adapter, dependency/runtime version where numerically material, dtype/precision, and fit-domain identities must be bound. Reusing bytes from an old cache is allowed only after the new owner authenticates that those bytes are semantically valid for the current evidence contract.

### 11.6 Make the order method explicit and non-optional at the production boundary

D4 must expose one resolved target-order policy/identity (exact class/name delegated) whose method kind and required evidence are explicit. Production semantics must not be represented by `None`, omitted optional arguments, or “empty vector means default” when the accepted method requires coverage evidence.

Required consequences:

- missing mandatory pre-order evidence is a typed preparation failure, not UID fallback;
- an intentionally supported no-feature/minimal policy has an explicit distinct policy identity and is admissible only if D1/D2 accept that scientific method;
- changing method kind, represented measure, feature/metric recipe, evidence composition, tie rule, or another order-changing parameter changes target-size generation identity;
- exact parser/default/configuration behavior is reconciled in the current D4 specification instead of being inferred from call-site omissions.

### 11.7 Old empty-evidence generations and their descendants are not silently upgraded

Once the revised D1/D2 method is accepted, target-size generations created under the challenged empty-evidence/UID-order method become evidence for the old method, not current evidence for the new method.

D3/D4 must provide a fail-closed generation boundary strong enough that an old prepared aggregate cannot deserialize/re-hash itself into the new order policy by supplying newly defaulted fields. Use a schema/version/method-identity transition sufficient to guarantee:

- old `pi_train/pi_eval` and prefix identities cannot remain current under the new method;
- old screen/reducer/provisional/frozen/CV/production descendants are invalidated for the new protocol according to actual dependency;
- historical artifacts remain recoverable as historical evidence where useful;
- current operation requires re-`prepare` rather than semantic migration/reinterpretation;
- no current frozen campaign is relabeled as having used FPS/coverage when it actually used UID fallback.

The final impact record must identify which prior evidence remains valid for unrelated claims and which target-order-dependent evidence is stale/review-required.

### 11.8 Strengthen numerical falsification with metamorphic identity tests

Add the following discriminating oracles to Section 7:

1. **UID-renaming invariance:** replace every frame UID with a one-to-one different lexical naming while preserving all scientific/numerical evidence. `pi_train/pi_eval` mapped back to original frames must remain unchanged except where the accepted method declares a genuine numerical tie whose final tie-break is UID.
2. **Input-enumeration invariance:** reorder source/catalog/serialization traversal without changing canonical evidence; the resulting orders and coverage diagnostics must be identical.
3. **Tie-locality:** changing UID spelling may affect only frames inside an accepted exact/tolerance tie set, never frames with distinct governing scores/distances.
4. **Metric-coordinate identity:** when feature names define canonical coordinate identity, permuting serialized feature-column order while preserving names/values must not change the fitted metric/order after canonicalization.
5. **Old-generation negative:** a real pre-repair/constructed empty-evidence generation must fail current-generation admission rather than deserialize with new defaults.
6. **Independent evaluation-estimand check:** for bounded fixtures with known `mu_eval`, verify the accepted nested `M_i` construction/weights against a direct reference estimator, not the production selector itself.
7. **Split counterexample:** when coverage-aware split selection is accepted, include a fixture where two exact feasible M3 component subsets exist but have materially different accepted coverage score; verify deterministic choice of the better subset and exact-feasibility preservation.

These tests target the actual failure mode more strongly than checking that one crafted fixture differs from lexical UID order.

### 11.9 Complete the capability-transfer map as a transfer map, not only a disposition checklist

Before Gate A closes, expand the Section 2 table so every materially relevant capability records:

```text
historical capability
 -> immutable evidence/source identity
 -> current authority binding or PROPOSED_FOR_PROMOTION / EVIDENCE_ONLY / retired
 -> accepted replacement/current mechanism
 -> acceptance/oracle route
 -> omission rationale when not preserved
```

This must cover both the early quota/FPS DATA7 lineage and the later target-coverage/MVSEL/MVQUAL lineage. The review must not collapse those two histories into one mechanism: they expressed overlapping but not identical objectives. Historical qualification success may justify a capability hypothesis; it cannot by itself choose the current D1/D2 objective or numerical constants.

Refresh the PEM basis/HAS before Gate A acceptance and again before final closeout if the accepted project state/PEM advances materially. A stale HAS cannot close the work merely because this branch began from `1093a8b...`.

### 11.10 Bound new dependency/resource consequences of descriptor or difficulty evidence

If accepted `pi_train`/`pi_eval` requires foundation-model inference, high-dimensional descriptors, or another expensive provider, Gate A/B must state whether that dependency is mandatory or optional and what environment is required to construct a prepared generation.

- Do not accidentally turn `prepare` into an undocumented GPU-only scientific prerequisite.
- Full production GPU qualification remains deferred as already required by this project, but every mandatory preparation dependency must have bounded functional evidence on an available supported backend or remain an explicit blocker.
- Provider construction, batching, cache layout, worker count, and device scheduling remain D3/D4 unless they change the accepted metric/order; their resource behavior must remain bounded.
- If a simpler geometry-only evidence set satisfies D1/D2, do not retain foundation inference solely because historical machinery once used it.

### 11.11 Gate A must emit one resolved method contract, not a menu of undecided mechanisms

Before human ratification, Gate A must produce a compact decision table that resolves, for the proposed current method:

- `mu_train` and `mu_eval`;
- `P_train/M3` allocation objective and exactness/tie semantics;
- every allowed pre-order evidence class and its fit domain;
- the fitted metric and numerical precision/tolerance identity;
- exact `pi_train` construction and composition/interleaving policy;
- exact `pi_eval` construction and EVAL2 estimator/weighting semantics;
- hard-support versus soft-diagnostic boundary;
- required coverage diagnostics and their weighting measure;
- resource/scaling envelope;
- restart/currentness identity inputs; and
- explicit retired historical mechanisms/constants.

An implementation agent must not need to infer any of those choices from old specifications, source code, or this workplan's list of alternatives. If one of these rows is still unresolved, Gate A is not accepted and D3/D4 behavioral implementation remains blocked.

### 11.12 Revised closure condition

Section 10 remains necessary but is not sufficient. Final closure additionally requires:

- the represented training/evaluation measures and EVAL2 estimand are explicit and internally consistent;
- the exact P_train/M3 split algorithm is reconciled if its objective changed;
- the stage-by-evidence authorization matrix has no circular or unauthorized label dependencies;
- current pre-order evidence is produced by authenticated current-generation owners rather than inherited authority-shaped legacy products;
- the production order method is explicit/non-optional and old empty-evidence generations fail closed;
- UID renaming/input ordering cannot materially steer membership outside genuine accepted tie sets;
- any new model/provider dependency has bounded functional/resource evidence without violating the deferred final-GPU policy; and
- capability transfer, evidence applicability, semantic history, and stale descendant impact are closed explicitly.

**Workplan review disposition after these corrections:** PASS for the reconciliation cycle. The underlying D1/D2 method remains under the declared SERIOUS CHALLENGE until Gate A independent falsification and human ratification complete.
