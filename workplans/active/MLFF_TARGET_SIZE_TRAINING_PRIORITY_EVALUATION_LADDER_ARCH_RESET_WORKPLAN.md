---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V6
protocol_version: 5.8.0
status: active
created_date: 2026-08-28
reviewed_source_head: 6f0d34366ca954eabe21740ddda96357afc12eb1
review_revision: 6
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes:
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V3
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V4
  - CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V5
---

# MLFF target-size scientific simplification — V6

## 0. Purpose

Rebuild target-size selection around the actual scientific question and delete historical machinery that obscures it.

The question is one-dimensional:

> For one fixed MLFF training protocol and one fixed target dataset construction policy, what is the smallest target-training size `N` beyond which increasing `N` no longer gives a practically meaningful accuracy improvement?

Target-size selection is therefore a **data-size convergence experiment**. Cross-validation is a separate **methodological validation experiment** performed only after the target size and exact selected dataset are frozen.

The implementation must prefer the minimum scientific state necessary to answer those two separate questions.

## 1. Corrections relative to V5

V5 overinterpreted several generic pipeline dependencies as scientific authorities. V6 freezes the following corrections.

1. **Electronic-structure provenance is descriptive, not a compatibility gate.** DFT, DFT+U, hybrid, smearing, PAW/pseudopotential, spin, numerical settings, software provenance and energy-reference details remain recorded precisely and systematically. They do not automatically split target training or block mixing.
2. **No target-size LabelDomain fan-out.** Provenance groups may be reported, counted and diagnosed, but target-size owns one study over the user-authorized target data.
3. **CV has no target-size role.** Do not use CV folds, CV evaluation, CV training-domain materializability, CV seeds or CV digests to qualify, rank or select target size.
4. **CV is built after `T_selected`.** Its purpose is to test robustness/generalization of the selected dataset/training method, not to help choose `N`.
5. **Hold preprocessing fixed across candidate sizes.** Size `N` must be the material experimental variable. Candidate-specific refits of E0, normalization, objective scaling or equivalent fitted training transforms are not introduced by this redesign. A common preprocessing/training-protocol identity is frozen across the entire size ladder, excluding target-size evaluation/held-out evidence.
6. **Collapse target-training ordering machinery.** FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL may contribute optimized internal algorithms, but they no longer form a chain of independent public scientific authorities for target-size selection. The current generation owns one training-order object with diagnostics and one simple prefix-qualification contract.
7. **Do not redesign DATA5/DATA6/DATA7 merely because they currently exist upstream.** Change them only where necessary to remove a real target-size/CV/provenance coupling or to expose the clean inputs required below.

## 2. Scientific invariants

### 2.1 Independent variable

The material variable tested by the target-size experiment is:

```text
N = number of target configurations used for gradient training
```

Across target-size candidates hold fixed, as applicable:

- foundation/model initialization;
- model architecture/head policy;
- replay source and replay exposure semantics;
- target/replay loss definitions and property weights;
- preprocessing/reference-energy/normalization policy;
- optimizer and learning-rate schedule;
- precision/backend;
- batch/exposure semantics;
- ordered optimizer seed set;
- exact fidelity boundaries `(n1,n2,n3)`;
- target-size evaluation population and metric policy.

If an implementation discovers a quantity that necessarily changes with `N`, it must be identified explicitly as part of the experiment rather than hidden inside generic preparation.

### 2.2 Evaluation independence

No frame used for target-size evaluation may enter any target-size candidate's gradient-training data.

Use existing duplicate/correlation/decorrelation identities only to prevent obvious train/evaluation leakage. Do not create additional scientific incompatibility classes merely from different electronic-structure settings.

### 2.3 Provenance observability, not enforcement

Preserve the existing decomposed electronic-structure metadata where useful:

- XC/theory family;
- DFT+U settings;
- hybrid/dispersion settings;
- PAW/pseudopotential identities;
- spin settings;
- energy-reference and smearing conventions;
- force/stress convention and units;
- numerical-quality settings/k-points/SCF information;
- source program/version/parser provenance.

The current `ElectronicStructureFingerprint` is a useful basis for this record. The compatibility decision/domain machinery is not training eligibility authority in the new target-size generation.

Different fingerprints are allowed to coexist. Heterogeneity is reported as diagnostics such as counts by provenance fingerprint/group, unresolved fields and differing metadata dimensions. Warnings are advisory by default.

Hard rejection is limited to data that are mechanically/scientifically unusable for the configured training operation, for example:

- missing required labels;
- non-finite/corrupt labels or geometry;
- conventions/units that cannot be converted into the canonical training representation;
- an explicit user exclusion/filter.

Methodological differences such as DFT versus DFT+U versus hybrid are not automatic blockers.

## 3. Minimal target-size data model

Let `U_size` be all user-authorized, usable target-development configurations after outer protected roles are excluded.

Canonical configuration:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

Resolve once:

```text
candidate_sizes = [2^p for pmin..pmax]
Nmax = max(candidate_sizes)
(m1,m2,m3) = [2^q for q in evaluation_size_powers]
(n1,n2,n3) = fidelity_epochs
```

Nominal capacity requirement:

```text
|U_size| >= Nmax + m3
```

This count is not multiplied by label domains, CV folds, seeds or cumulative inference work. Real source-data requirements may be larger when duplicate/correlation exclusions reduce independent train/evaluation availability.

## 4. One simple train/evaluation split

Before candidate training, one deterministic owner constructs:

```text
P_train  = target-size training-authorized configurations
M3       = exact target-size evaluation reserve, |M3| = m3
```

with:

```text
P_train intersect M3 = empty
|P_train| >= Nmax
```

Training has priority. The splitter should preserve rare/important structural, condition, event and composition support for `P_train` and draw `M3` preferentially from redundant residual data while respecting existing duplicate/correlation exclusion rules.

Do not build a large separate evaluation hierarchy or several allocation authorities. Persist the split, its deterministic policy identity, and concise support/correlation diagnostics.

Order the exact evaluation reserve once:

```text
pi_eval = deterministic order over M3
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
```

`M1 subset M2 subset M3`. The order freezes before the first candidate TRAIN2 trajectory and cannot depend on candidate predictions or survivor outcomes.

## 5. One target-training order

The new generation exposes one scientific training-order authority:

```text
build_target_training_order(P_train, frozen_features, policy) -> pi_train + diagnostics
```

Its job is simply to produce a deterministic rich ordering of training configurations. It may reuse existing vectorized/indexed machinery for:

- structural/environmental diversity;
- composition/condition/event coverage;
- frozen foundation-model difficulty/residual information;
- target-label tails or other explicitly accepted training-selection signals;
- deterministic repair of obvious coverage holes.

But the current public/persisted scientific topology is one order, not a FEAS -> MVIDX -> MVSEL -> REPAIR -> MVQUAL authority chain.

Each candidate is exactly:

```text
T_N = pi_train[:N]
```

Candidate qualification is intentionally simple:

- the prefix exists at exact size `N`;
- all required labels are usable;
- any explicitly configured hard support requirement is satisfied.

Diagnostic diversity/coverage metrics may be rich without becoming multiple independent gate systems.

Internal optimized kernels/classes from the old machinery may survive if they reduce implementation risk or preserve performance, provided they are implementation details behind the single current authority.

## 6. Common training preparation across N

Target-size convergence should compare data size, not a moving preprocessing target.

Freeze one common target-size training-protocol/preparation identity before the candidate ladder runs. It may be derived from `P_train` or from the configured foundation/training protocol, but it must not consume `M1/M2/M3`, CV validation data, outer held-out data, calibration data or locked tests.

The same identity is used for every candidate size unless the external training engine mathematically requires a size-dependent quantity. In that exceptional case the dependency must be explicit, deterministic and tested as part of target-size semantics.

Do **not** introduce candidate-specific DATA7 E0/normalization/objective refits merely because a generic API can do so. Holding those choices fixed is the default scientific design.

Candidate-specific state should primarily be:

- exact `T_N` membership;
- optimizer seed;
- continuation/checkpoint state for the active fidelity boundary.

## 7. Exact target-size screen

Preserve the useful existing funnel:

```text
qualified q sizes
 -> n1 on M1: q -> min(q,4)
 -> n2 on M2: <=4 -> 2
 -> n3 on M3: 2 -> 1
```

Requirements:

- ordered paired optimizer seeds are identical across sizes;
- survivor trajectories continue exactly from `n1` to `n2` to `n3`;
- ordinary target-success early stop does not truncate the screening boundary;
- target-side screening metric and practical-equivalence widths are fixed policy;
- smaller `N` wins inside practical equivalence;
- replay/physical/deployment/CV evidence does not rank target sizes;
- no eliminated candidate receives later ordinary screen work;
- no complement evaluation fallback;
- configured largest size is the ceiling; material superiority at the ceiling yields typed non-convergence rather than a rescue size.

The target-size result freezes:

```text
N_selected
T_selected = pi_train[:N_selected]
```

## 8. CV is a separate post-selection experiment

Only after `N_selected/T_selected` freeze:

```text
T_selected -> CV folds -> methodological validation
```

CV owns its own fold count, partition seed, fold monitoring/evaluation policy and any fold-local preprocessing required by the CV methodology.

CV rules:

- folds are constructed from `T_selected`, not from the whole pre-selection development pool;
- existing duplicate/correlation groups should not be split across incompatible CV roles when avoidable/required by the accepted leakage policy;
- CV never changes `N_selected`;
- CV failure is reported as a methodological-validation failure, not converted into a different target size;
- a material change to the training method/protocol after CV failure requires a new target-size experiment because the method being converged has changed.

The current source already states that held-out CV evaluation cannot control target-size selection and that CV evaluates the already-frozen protocol. Remove the remaining historical coupling where CV **gradient-training domain identities** restrict target-size materializability/qualification.

Do not create target-size invalidation machinery around CV settings. Target-size simply does not depend on them.

## 9. Final production

After CV accepts the selected method/protocol:

- start a fresh final training run on full `T_selected`;
- use the accepted common training protocol;
- production epoch horizon remains independent of `n3`;
- frozen `M3` may remain development/model-selection evidence for final target-side checkpoint selection if required by the accepted training protocol;
- outer held-out/calibration/locked evidence remains downstream and is not retroactively called independent if it influenced model selection.

## 10. Ownership simplification

The target-size subsystem should own only:

1. power/fidelity/evaluation-size configuration resolution;
2. one target-size train/evaluation split;
3. one target-training order `pi_train`;
4. one frozen evaluation order/ladders `M1/M2/M3`;
5. successive-fidelity candidate evidence/reduction;
6. frozen `N_selected/T_selected`.

It should **not** own or depend on:

- label compatibility domains as training partitions;
- CV folds or CV validation state;
- per-domain candidate-prefix maps;
- multiple public selection/repair/qualification authorities;
- complement evaluation populations;
- production qualification or deployment evidence;
- candidate-specific preprocessing refits added solely by this redesign.

Generic DATA5/DATA6/DATA7/DATA8 utilities may continue to exist where useful, but they are support code. They do not define target-size scientific semantics merely because target-size calls them.

## 11. Destructive cleanup

Remove from the reachable current target-size path:

- `LabelDomain` multiplicity as target-size study/cardinality authority;
- target-size candidates with `domain_prefix_digests` or equivalent per-domain maps;
- target-size materializability/qualification across CV training domains;
- fixed-eight/fixed-ceiling constants as scientific authority; replace with configured powers/ceiling;
- complement/coarse evaluation roles and fallback subtraction logic;
- public/persisted FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL chain where its sole purpose is target-size ordering;
- old candidate-authority/migration/receipt layers used only to preserve retired generations;
- dead compatibility aliases and duplicate target-size reducers.

Where an old optimized numerical kernel is still useful, keep/refactor it behind the new single owner instead of deleting performance for cosmetic reasons.

## 12. Implementation gates

### Gate A — documentation and source map

Rewrite the target-size/CV/provenance architecture docs first on the implementation branch. Clearly state:

```text
provenance report
 -> target-size data split
 -> one training order + one M ladder
 -> data-size convergence screen
 -> freeze selected data
 -> post-selection CV
 -> final production
```

Document that provenance differences are advisory and CV is scientifically separate from target-size selection.

### Gate B — provenance and configuration simplification

- preserve systematic electronic-structure metadata;
- demote compatibility/domain outcomes from target-training eligibility authority;
- implement power-based target/evaluation configuration and configured ceiling;
- regression-test mixed DFT/DFT+U/hybrid provenance without automatic target-size blocking.

### Gate C — single split and training-order authority

- implement one deterministic train/M3 split;
- implement one current `pi_train` authority, reusing old optimized internals where justified;
- persist concise diagnostics rather than a chain of scientific gate records;
- test exact cardinality, disjointness, deterministic restart and support preservation.

### Gate D — target-size screen

Integrate real owners:

```text
config -> U_size -> train/M split -> pi_train/pi_eval
 -> T_N -> TRAIN2 n1/M1 -> reduce
 -> continue n2/M2 -> reduce
 -> continue n3/M3 -> selected/configured-ceiling
 -> freeze T_selected
```

Test paired seeds, practical equivalence, continuation, restart, eliminated-candidate no-work, non-default powers/rungs and no CV dependency.

### Gate E — post-selection CV and production

- build CV only from frozen `T_selected`;
- verify CV settings/results cannot change target-size state;
- fresh final production only after CV acceptance;
- preserve downstream held-out/calibration/locked separation.

### Gate F — structural cleanup and final regression

- delete retired target-size authorities/aliases/reachable dead paths;
- run affected regression after each material stage;
- run final affected regression/integration through the real CLI/config/state/persistence owners;
- broaden to the full suite where affected surface cannot be bounded;
- preserve performance/resource machinery and run bounded performance/reference checks;
- run documentation/PDF checks required by the repository.

Full long GPU/production qualification remains deferred to the established final release phase.

## 13. Mandatory acceptance cases

At minimum prove:

- DFT, DFT+U, hybrid/smearing/provenance differences are recorded but do not automatically split or block target training;
- unresolved/heterogeneous provenance is reported clearly;
- mechanically unusable labels still fail cleanly;
- exactly one target-size study exists regardless of provenance-group count;
- target-size runs correctly with CV disabled/not yet constructed;
- changing CV fold count/seed cannot alter target-size identity/result;
- no CV training-domain materializability requirement remains;
- default and non-default power configuration resolve correctly;
- nominal capacity is `Nmax + m3`, with no domain/fold/seed multiplier;
- one current training order exists and every `T_N` is its exact prefix;
- old multi-authority selection intermediates are absent from the current target-size public/persisted topology;
- common training preparation/protocol identity is the same across candidate sizes unless an explicitly justified size-dependent quantity exists;
- `M1 subset M2 subset M3`, all disjoint from every `T_N`;
- evaluation order freezes before candidate results;
- exact `n1 -> n2 -> n3` continuation and paired-seed ranking work;
- selected size is frozen before CV;
- CV folds contain only frames from `T_selected`;
- CV failure cannot select a different N;
- final production is fresh and uses full `T_selected`;
- no fixed/complement/domain/CV fallback authority remains reachable;
- no material performance/resource regression from replacing optimized internals with slower scalar code.

## 14. Scientific qualification

Functional regression proves software correctness, not that default `M=[256,512,1024]` is statistically sufficient.

Retrospective/reference qualification should separately test whether the default M ladder preserves coarse survivors, finalists and the final selected N relative to a larger reference evaluation population. If representative evidence is unavailable, record `deferred/unavailable`; do not invent a pass.

Provenance heterogeneity is similarly reported, not converted into an automatic pass/fail compatibility judgement.

## 15. Frozen / delegated / reopen

### Frozen

- provenance is precise and advisory by default;
- one target-size study across user-authorized usable target data;
- CV is completely outside target-size selection and occurs after selected-data freeze;
- target-size variable is N; non-N training choices are held fixed as far as scientifically possible;
- one training order, one M ladder, one reducer;
- configured power ladders and configured ceiling;
- nominal target-size capacity `Nmax + m3`;
- exact continuation, paired seeds and practical-equivalence/smaller-size preference;
- destructive cleanup of retired target-size complexity;
- full GPU qualification deferred.

### Delegated

- exact class/module/schema names;
- internal vectorized/sparse/index structures;
- deterministic training/evaluation ordering algorithms;
- which old optimized kernels are reused behind the new owners;
- exact provenance-report presentation;
- CV-local fitting details, provided CV remains post-selection and cannot feed back into N.

### Reopen only on evidence

1. the training engine cannot consume mixed provenance even after canonical unit/convention conversion;
2. a specific provenance difference is demonstrated to make labels mathematically unusable together rather than merely scientifically heterogeneous/noisy;
3. one deterministic training order cannot preserve required target-data coverage without a materially different algorithm;
4. the default M ladder fails decision-preservation qualification;
5. a training transform is proven to require N-dependent fitting for correct target-size comparison;
6. a real product requirement appears for genuinely separate target models/heads/studies rather than one mixed training corpus;
7. a real implementation/performance limit invalidates the configured ladder design.

## 16. Freeze verdict

V6 intentionally removes speculative authority layers instead of explaining them more carefully. The implementation target is now the smallest architecture that directly represents the scientific workflow: record provenance, choose disjoint training/evaluation data, order training data once, run a controlled convergence experiment in N, freeze the selected dataset, then run CV as a separate validation experiment.
