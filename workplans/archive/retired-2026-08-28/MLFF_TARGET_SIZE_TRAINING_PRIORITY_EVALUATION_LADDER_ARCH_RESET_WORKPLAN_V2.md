---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V2
protocol_version: 5.8.0
status: active
created_date: 2026-08-28
reviewed_head: 64f3da8a578d3749f7a2c5769b62d95c249c3e6c
review_revision: 2
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
---

# MLFF Target-Size Training-Priority Evaluation-Ladder Architecture Reset Workplan V2

## Objective

Replace the current fixed-target-size/full-complement target-size architecture with one clean current generation in which:

1. the target-size study is completed **before cross-validation is constructed**;
2. the target-size study uses one final-development target population divided into an exact maximum target-training reserve and one non-gradient target-size evaluation reserve;
3. target-training membership receives first priority for scarce/important support;
4. target-size evaluation uses one frozen nested `M1/M2/M3` ladder paired to exact `n1/n2/n3` screening boundaries;
5. target-size candidate cardinalities and evaluation cardinalities are configured canonically as powers of two;
6. the nominal target-size-stage capacity requirement is `Nmax + M3`, not a CV-multiplied or candidate-workload-derived number;
7. after `N_selected` and the selected final target dataset freeze, cross-validation partitions that already-selected dataset to validate training behavior and cannot feed back into target-size selection;
8. deprecated fixed-universe, fixed-ceiling, complement-evaluation, pre-selection-CV, compatibility/migration, duplicate selector, and stale generation semantics are removed rather than wrapped.

Priority remains:

```text
scientific/product correctness
  > clean single-authority architecture
  > material performance/resource efficiency
  > development convenience / obsolete-state compatibility
```

## Corrections from review revision 1

This V2 explicitly corrects the following review-1 design errors:

- CV is **not** an input or materializability constraint for target-size selection. CV exists to validate the already-selected training protocol and therefore begins after `select-target-size` freezes `N_selected` and the selected target dataset.
- A CV fold is not required to contain `N_selected` gradient-training configurations. Standard CV partitions the already-selected `N_selected` target dataset; fold-training subsets are smaller by construction.
- CV fold count, fold seed, monitor geometry, purge geometry, or CV feasibility may not change `N_selected` or invalidate an already-valid target-size study.
- The earlier `D * 12,288` expression is removed. It described one particular candidate/seed evaluation-work calculation, not a data-capacity requirement and not a fixed scientific constant.
- The size-study dataset-capacity contract is `Nmax + M3` configurations in the qualified target-size study population, because `M1` and `M2` are prefixes of `M3`.
- `LabelDomain` does not mean energy/force/stress or an automatic replicated target-size dataset. It is an electronic-structure label-compatibility partition. Multiple label domains do not automatically multiply the target-size cardinality requirement.

## Terminology and ownership

### Target-size study population

Let `U_size` be the final-development target population authorized for target-size study after upstream eligibility, event detection, correlation/decorrelation policy, outer protected-role exclusions, and target-size study qualification.

The target-size study owns exactly two mutually exclusive scientific roles inside `U_size`:

```text
Tmax   = maximum target-training reserve, |Tmax| = Nmax
R_eval = target-size evaluation reserve, disjoint from Tmax
```

The evaluation ladder is selected only from `R_eval`:

```text
M1 = pi_eval[:m1]
M2 = pi_eval[:m2]
M3 = pi_eval[:m3]
M1 subset M2 subset M3 subset R_eval
```

The nominal minimum target-size-stage capacity is therefore:

```text
|U_size| >= Nmax + m3
```

Default:

```text
Nmax = 2^14 = 16384
m3   = 2^10 = 1024
minimum nominal qualified target-size population = 17408 configurations
```

This is a configuration-count requirement, not a claim of 17,408 IID samples. Upstream correlation/equivalence constraints may require more raw source frames to produce that many qualified target-size configurations.

### Label domain

A `LabelDomain` groups sources whose electronic-structure labels are compatible under theory, energy-reference, derivative-convention, and configured numerical-quality/provenance rules. In normal campaigns all compatible target sources may belong to one label domain.

This architecture does **not** define a hidden multiplier `D` for target-size cardinality. One target-size study has one resolved target-size study population and one `Nmax + M3` capacity contract.

If a campaign contains multiple incompatible label domains, that fact is a label/protocol-topology issue. The implementation must not silently replicate the target-size ladder across every domain. It must either:

- resolve one explicit target-size-study domain/head owned by the campaign protocol; or
- treat genuinely separate target-training domains as separately configured studies under an explicit higher-level design.

Automatic `D * (...)` target-size population or workload semantics are forbidden.

## Frozen architecture

### 1. Authoritative lifecycle

The target-data lifecycle becomes:

```text
source / DATA4 raw evidence / events
 -> DATA5 outer roles + correlation/decorrelation authority
 -> target-size-study qualified final-development population U_size
 -> training-priority Tmax allocation
 -> residual evaluation reserve R_eval
 -> rich target-training ordering/qualification inside Tmax
 -> frozen residual evaluation order pi_eval -> M1/M2/M3
 -> select-target-size exact n1/n2/n3 funnel
 -> freeze N_selected and selected target dataset T_selected
 -> materialize final production dataset
 -> construct CV partitions from T_selected
 -> CV training/validation of frozen protocol
 -> final/held-out validation, calibration, locked tests
```

CV is downstream of target-size selection and cannot influence any target-size membership, qualification, ranking, or terminal result.

### 2. Training-priority allocation

The training/evaluation role boundary must freeze before role-local target-size candidate training or evaluation can feed back into membership.

`Tmax` contains exactly `Nmax` target-size-study configurations. Training receives first claim on unique/scarce structural, condition, event, provenance, and other split-safe support.

Allocation may consume only evidence whose meaning is independent of the eventual target-training/evaluation role. Allowed inputs include partition-independent structural/geometry descriptors, condition identity, composition, regime, event classes, source/run/provenance/correlation identity, and other explicitly documented split-safe upstream features.

The allocation must not rank membership using:

- target-size candidate predictions or errors;
- target-size EVAL2 outcomes;
- role-local fitted DATA6/DATA7 transforms;
- candidate-dependent foundation residuals/difficulty;
- held-out CV, calibration, or locked-test evidence;
- any downstream product whose meaning depends on the split being chosen.

If correlation/equivalence policy declares observations inseparable across train/evaluation roles, the allocator must keep them on one side or exclude surplus correlated observations from the target-size study population. It must not violate role separation merely to hit cardinality.

### 3. Rich training chain owns ordering inside Tmax

After `Tmax` freezes, current rich target-training semantics run only inside `Tmax`:

```text
Tmax
 -> role-local fitted preparation
 -> FEAS1
 -> MVIDX1
 -> MVSEL2
 -> REPAIR2 / MVSTATE2
 -> MVQUAL
 -> one repaired master order pi_train
```

Configured target-size candidates are prefixes:

```text
T_N = pi_train[:N]
```

for configured `N` values.

Because `|Tmax| = Nmax`, the maximum target-training candidate remains the entire training reserve even if rich selection reorders it.

No CV fold is part of MVQUAL or target-size materializability in this generation. MVQUAL qualification is owned by the target-size final-development training authority only.

### 4. Residual evaluation ladder

After the train/eval allocation freezes, build one deterministic evaluation master order `pi_eval` over `R_eval` and freeze it before the first target-size candidate TRAIN2 trajectory begins.

The evaluation selector may use richer target-side evidence after role freeze, including target-label distributions and a frozen external/foundation-model residual signal, provided that evidence cannot alter `Tmax` membership and is independent of candidate TRAIN2 trajectories.

It may not use candidate predictions, survivor decisions, selected-size outcomes, final-production predictions, held-out CV, calibration, or locked-test evidence.

Evaluation ordering is representative/model-selection coverage, not training MVQUAL. It must not automatically inherit the training hard threshold or REPAIR2.

### 5. Exact target-size screening

Canonical stage pairs are:

```text
(n1, M1)
(n2, M2)
(n3, M3)
```

At each stage all candidate sizes and paired seeds use exactly the same frozen evaluation population.

Preserve:

```text
0 -> n1 -> n2 -> n3
q -> min(q,4) -> 2 -> 1
paired-seed aggregation
practical-equivalence/smaller-size preference
exact boundary checkpoints
no ordinary target-success early stopping during screening
fresh production after selected size freezes
```

No cross-rung metric comparison may pretend M1, M2, and M3 are the same sample.

### 6. Freeze selected target dataset before CV

When `select-target-size` returns `selected(N)`:

```text
N_selected = N
T_selected = pi_train[:N]
```

Both become immutable target-size outputs.

CV is then constructed from `T_selected`, not from the full pre-selection development population and not from `R_eval`.

CV purpose is training validation of the already-selected dataset/protocol. Standard CV therefore creates fold-local subsets of `T_selected`:

```text
T_selected
 -> fold held-out subset
 -> optional fold checkpoint-monitor subset
 -> purge as required
 -> fold gradient-training subset
```

Fold training cardinality is expected to be smaller than `N_selected`. It is **not** required to rematerialize `N_selected` configurations in every fold.

CV may diagnose that the selected dataset cannot support the requested fold/monitor/purge topology. Such a result is a CV feasibility/validation result. It does not reopen target-size selection, steal M3 frames, alter `N_selected`, or search a smaller target size.

If existing CV policy allows fold-count reduction as a declared validation fallback, that fallback may operate after size freeze without changing target-size authority.

### 7. M3 after size selection

M3 remains non-gradient development/model-selection evidence.

After `N_selected` freezes, final-development production may reuse frozen M3 for target-side checkpoint/model selection. CV uses fold-local validation/checkpoint-monitor roles derived from `T_selected`, not M3.

M3 must never be presented later as independent held-out protocol-validation evidence after it has participated in target-size or checkpoint selection.

Outer validation, calibration, and locked tests remain separate.

### 8. Power-of-two configuration

Canonical configuration:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

Resolved values:

```text
target_sizes = [2^p for p in pmin..pmax]
Nmax = 2^pmax
evaluation_sizes = [2^q1, 2^q2, 2^q3]
M1/M2/M3 cardinalities = evaluation_sizes
```

Rules:

- powers are integers and derived cardinalities are positive/representable;
- target ladder contains enough candidates for the current funnel;
- evaluation powers contain exactly three strictly increasing values;
- evaluation powers need not be consecutive;
- all target/evaluation scientific cardinalities come from this one resolver;
- no scientific `<=16384` guard remains;
- no runtime rescue size is invented;
- policy identity binds powers and resolved rung mapping.

### 9. Configured ceiling

Replace retired terminology:

```text
FIXED_TARGET_SIZES            -> resolved configured target ladder
FIXED_TARGET_SIZE_CEILING     -> configured Nmax
outside fixed universe        -> outside configured target-size ladder
nonconverged_at_fixed_ceiling -> nonconverged_at_configured_ceiling
```

If the configured largest candidate remains materially superior at the final screen, return configured-ceiling non-convergence. Do not synthesize a larger candidate.

### 10. Capacity and feasibility

Target-size-stage capacity preflight depends only on target-size-study roles and policy:

```text
qualified target-size configurations >= Nmax + M3
Tmax can materialize exactly Nmax
R_eval can materialize at least M3
training split-safe support is feasible
evaluation support diagnostics are acceptable/explicit
```

It does **not** require:

- CV fold construction;
- each CV fold to hold Nmax or N_selected;
- a `D` multiplier across label domains;
- any candidate/seed cumulative evaluation-work count.

CV feasibility is evaluated later against `T_selected` after size freeze.

### 11. No compatibility migration

This is a new semantic generation. Old fixed-universe/complement/pre-selection-CV target-size derived state is unsupported.

Do not migrate or alias:

- old `size_development` target-size role semantics;
- `size_development_complement` / coarse complement evaluation roles;
- fixed-eight/fixed-ceiling study state;
- previous candidate-authority bridges/receipts;
- old target-size TRAIN2/EVAL2 evidence bound to prior populations;
- old CV-before-size-selection target-size qualification topology.

Raw/external source data remain reusable. Derived current campaign state must be rebuilt.

## Part 1 - Documentation/specification authority reset

Part 1 completes before executable implementation on the implementation branch. Future-state docs must not be released alone while main still executes retired behavior.

### D1. Rewrite statistical architecture and lifecycle

Update at minimum:

- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/40_training_evaluation.md`;
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- `docs/arch_manuals/mlff_training_data_architecture.md`;
- current dependency graphs/source maps.

Required current story:

```text
outer roles
 -> target-size train/eval allocation
 -> rich training/eval ladders
 -> select target size
 -> freeze selected dataset
 -> CV partition/validation
 -> later held-out/calibration/test evidence
```

Remove the current architectural claim that CV training domains participate in target-size materializability/MVQUAL.

### D2. Rewrite target-size and CV specifications

Update current specs so they state:

- target size is selected entirely before CV construction;
- one target-size study population owns `Nmax + M3` capacity;
- M1/M2/M3 are one nested ladder, not full complements;
- `T_selected` is frozen before CV;
- CV partitions `T_selected` and fold training sets are smaller subsets;
- CV outcomes cannot choose or change target size;
- CV settings are not target-size policy identity;
- M3 may serve final-development checkpoint selection but not held-out validation.

### D3. Clarify label-domain terminology

Current documentation must explain that `LabelDomain` is an electronic-structure compatibility partition, not a target property axis and not an automatic target-size cardinality multiplier.

Remove any workplan/spec language that introduces `D * M` or `D * workload` as a mandatory target-size capacity requirement.

If the product supports more than one incompatible target label domain in one campaign, document the explicit campaign-level authority deciding which target-size study applies; do not infer replication from the number of domains.

### D4. Clean retired terminology and topology

Clean current normative/user docs of:

- fixed target-size universe/fixed ceiling;
- hard-coded scientific 16384 except default `2^14` example;
- complement/coarse-complement target-size evaluation;
- CV-before-size-selection or CV-as-size-qualification language;
- requirement for every CV fold to materialize selected/full target cardinality;
- `D * 12,288` or other fixed candidate-workload language presented as data capacity;
- legacy migration/current-generation aliases intentionally retired;
- unsupported IID claims.

Historical/archive/release documents may preserve history but remain non-current.

### D5. Documentation acceptance

Part 1 closes when:

1. target-size selection clearly precedes CV everywhere current;
2. capacity is documented as `Nmax + M3` for one resolved target-size study population;
3. LabelDomain meaning is clear and no automatic D multiplier remains;
4. CV partitions the selected dataset and cannot feed back;
5. fixed/complement/legacy terminology is absent from current authority;
6. generated docs/PDFs/reference checks pass;
7. an implementer can reconstruct Part 2 without consulting this conversation.

## Part 2 - Code implementation

### C1. Canonical power resolver and semantic generation

Implement one resolver for target/evaluation powers, resolved cardinalities, configured ceiling, fidelity/rung mapping, serialization/digests, and current generation identity.

Remove current fixed constants/guards and old-generation aliases that could deserialize retired state as current.

### C2. Build target-size-study qualified population and exact Tmax/R_eval roles

Create/replace the target-size role owner so it publishes:

- target-size study population identity `U_size`;
- exact `Tmax` membership of `Nmax` configurations;
- residual evaluation membership `R_eval`;
- split-safe allocation feature/policy identity;
- disjointness/correlation-equivalence audit;
- capacity/support diagnostics.

Preflight must fail before expensive selection/training if `Nmax + M3` cannot be supported.

No CV plan or CV policy is needed to build this authority.

### C3. Reconcile rich training chain inside Tmax

Route DATA6/DATA7/FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL target-size preparation through `Tmax` only.

Required behavior:

- one repaired order;
- configured candidate prefixes;
- MVQUAL on target-size final-development prefixes only;
- no CV domain enters candidate qualification;
- no residual evaluation frame enters training-fitted inputs;
- rich failure cannot mutate the train/eval role split.

### C4. Build and freeze residual M1/M2/M3

Create one deterministic `pi_eval` over `R_eval` before candidate TRAIN2 starts.

Persist exact nested M memberships, feature/foundation/policy identities, correlation/effective-sample diagnostics, and support deficits.

No candidate-model outcome may alter this order.

### C5. Rebind EVAL2 and select-target-size

Replace complement evaluation with direct M-stage resolution:

```text
coarse -> M1
short -> M2
final_screen -> M3
```

Preserve canonical EVAL2 metric and OPT-EVAL4 execution/resource behavior.

Target-size study evidence binds exact M rung identity and exact n boundary.

### C6. Freeze T_selected and construct CV afterward

After selected outcome:

```text
T_selected = pi_train[:N_selected]
```

Persist this selected dataset authority.

Then construct CV from `T_selected`.

Required CV behavior:

- fold evaluation/monitor/purge/training partitions are subsets/roles derived from `T_selected`;
- fold training sets are not required to have `N_selected` configurations;
- `R_eval`/M1/M2/M3 never enter CV gradients;
- CV fold count/seed/monitor/purge policy changes invalidate CV descendants only;
- CV settings do not invalidate target-size study state;
- CV infeasibility cannot revise `N_selected`;
- held-out CV remains validation evidence, not target-size evidence.

### C7. Final-development checkpoint selection

Final production starts fresh from `T_selected` and may use frozen M3 for target-side checkpoint/model selection.

CV models use fold-local monitor/evaluation roles. Outer/calibration/locked evidence remains separate.

### C8. Persistence/restart

Identity/invalidation must prove:

- changing target/evaluation powers or allocation/evaluation-selection policy invalidates target-size descendants;
- changing CV fold count/seed/monitor/purge settings after target-size freeze does **not** invalidate `Tmax`, `M1/M2/M3`, target-size evidence, `N_selected`, or `T_selected`;
- it invalidates only CV/materialization/validation descendants as applicable;
- restarting target-size stages reuses identical frozen train/eval memberships;
- old derived state fails as unsupported rather than migrating.

### C9. Destructive cleanup

Delete/retire current code/tests/exports whose only purpose is:

- fixed target-size tuple/ceiling;
- complement/coarse-complement EVAL2 target-size roles;
- target-size materializability across CV domains;
- per-CV-domain REPAIR2/MVQUAL target-size qualification;
- CV-before-size-selection lifecycle;
- old candidate-authority migration bridges/receipts;
- dead legacy selectors/wrappers;
- current-generation aliases for retired TARGET-SIZE-V5 population semantics.

Do not keep fallbacks.

### C10. Performance/resource preservation

Reuse existing exact sparse selection/index machinery, memory mapping/out-of-core paths, optimized selector kernels, bounded EVAL2 preparation/finalization, inference admission, batching and cache reuse where semantics remain valid.

Performance reporting may derive actual target-size evaluation work dynamically from the number of qualified candidates, seeds, and configured M sizes. That execution-work calculation must never be stored or documented as a fixed dataset-capacity requirement.

## Implementation authority

### Frozen

- target-size selection completes before CV construction;
- target-size selection owns one resolved target-size study population;
- exact maximum training reserve size is Nmax;
- target-size evaluation reserve is disjoint and supplies one frozen nested M ladder;
- nominal target-size capacity is Nmax + M3;
- no automatic LabelDomain/D multiplier;
- rich training selection/qualification occurs only inside Tmax;
- exact n1/n2/n3 continuation and paired-seed funnel remain unchanged;
- selected dataset T_selected freezes with N_selected;
- CV partitions T_selected afterward and cannot feed back;
- CV fold training subsets need not and generally will not equal N_selected;
- M3 may control final-development checkpoint selection after size freeze;
- power-based configuration/configured ceiling;
- destructive no-migration generation reset;
- canonical EVAL2 metric/OPT-EVAL4 execution preserved.

### Delegated

- concrete current generation identifier;
- exact class/schema names;
- exact deterministic split-safe allocation scoring realization consistent with training priority;
- internal sparse/index structures;
- CV implementation details consistent with partitioning T_selected;
- artifact materialization form for nested M sets;
- bounded test fixture sizes.

### Reopen only on evidence

Reopen only if evidence shows:

1. exact Nmax training reserve plus M3 residual cannot be made correlation-safe at target scale;
2. split-safe allocation features fail to protect important training support;
3. `[256,512,1024]` fails target-size decision preservation;
4. M3 reuse for final checkpoint selection conflicts with another independently required model-selection authority;
5. selected-dataset CV semantics fail to provide the intended training-validation evidence;
6. multiple incompatible target label domains require an explicit multi-study architecture not currently defined.

## Gate sequence and acceptance

### Gate A - Documentation/spec reset

Complete Part 1 and documentation checks before executable behavior work.

### Gate B - Generation/power/target-size role authority

Tests must cover:

- default and nondefault powers;
- `Nmax + M3` capacity;
- exact Tmax cardinality;
- disjoint residual role;
- no CV dependency in target-size role creation;
- no fixed 16384 guard;
- old workspace rejection.

Stage-local regression: config, role freeze, leakage, serialization.

### Gate C - Rich training + evaluation ladders

Tests must cover:

- one pi_train and nested configured prefixes;
- MVQUAL without CV domains;
- frozen nested M1/M2/M3;
- candidate outcomes cannot change M order;
- no training/eval leakage;
- nondefault target/eval ladders.

Stage-local regression: DATA6/7/8, coverage/index/select/repair/qualification, EVAL2 population preparation.

### Gate D - Real select-target-size integration

Exercise:

```text
resolved config
 -> target-size role authority
 -> Tmax rich training preparation
 -> frozen M ladder
 -> TRAIN2 n1/M1
 -> reduce
 -> TRAIN2 n2/M2
 -> reduce
 -> TRAIN2 n3/M3
 -> selected/configured-ceiling outcome
 -> freeze T_selected
```

Required cases:

- default and nondefault powers/fidelities;
- insufficient Nmax+M3 capacity;
- configured-ceiling nonconvergence;
- restart at every boundary;
- no eliminated candidate receives later work;
- no complement fallback;
- no CV object is required to select target size.

### Gate E - Post-selection CV lifecycle

Exercise real CV owner after `T_selected` exists.

Required cases:

- CV cannot be constructed before selected dataset freeze in the new public lifecycle;
- every CV role is derived from T_selected;
- fold training subsets are smaller than/equal to T_selected as expected;
- M sets never enter CV gradients;
- CV configuration change preserves target-size digests/results;
- CV failure does not change N_selected;
- final production still uses full T_selected.

### Gate F - Final checkpoint + destructive cleanup

Verify M3 final-development checkpoint role, fold-local CV monitor role, and remove all retired fixed/complement/CV-size-qualification/current-generation compatibility paths.

### Gate G - Final assembled regression/integration

Run complete affected regression, broader repository checks as required, docs/PDF rebuild, structural legacy-absence inspection, restart/invalidation tests, and bounded performance/reference checks.

## Scientific qualification

The nested M ladder is a sampling approximation and requires decision-preservation qualification distinct from functional tests.

Qualification should compare M1/M2/M3 against the larger authenticated residual evaluation reference where representative evidence is available and assess:

- coarse survivor recall;
- short finalist preservation;
- final selected-size agreement under practical-equivalence rules;
- representative condition/event/feature coverage;
- leakage/correlation diagnostics;
- deterministic restart/result identity;
- material evaluation-cost reduction.

If representative evidence is unavailable during implementation, sampling-policy qualification is **deferred/unavailable**, not passed. Full long target-machine/GPU qualification remains separately deferred.

## Anti-shortcut constraints

Forbidden:

- building CV before target-size selection and making its domains part of size qualification;
- requiring every CV fold to materialize N_selected;
- using CV outcomes to change N_selected;
- using R_eval/M sets in CV gradients;
- multiplying target-size capacity by LabelDomain count automatically;
- presenting candidate/seed cumulative evaluation work as dataset capacity;
- adapting train/eval membership after candidate results;
- candidate-adaptive M selection;
- retaining complement evaluator fallback;
- supporting fixed tuple and power resolver as equal current authorities;
- silently migrating old derived campaign state;
- weakening MVQUAL/exact boundaries/practical-equivalence/disjointness to pass tests;
- independent resampling of M1/M2/M3;
- preserving dead compatibility/selector code because archived tests reference it;
- claiming configuration counts are IID sample counts.

## Handoff closure

```text
size-study data:
  U_size -> exact Tmax(Nmax) + residual R_eval
                    -> pi_train prefixes
  R_eval -> pi_eval -> M1 subset M2 subset M3

size decision:
  (n1,M1) -> (n2,M2) -> (n3,M3) -> N_selected

selected dataset:
  T_selected = pi_train[:N_selected]

only then:
  T_selected -> CV folds -> training validation
  T_selected -> fresh final production
  M3         -> final-development checkpoint/model selection

nominal target-size-stage capacity:
  Nmax + M3
```

This V2 is controlling over V1/review-1 statements that placed CV before target-size selection, required target-size materializability across CV fold-training domains, introduced per-domain M multiplication, or quoted a fixed 12,288 evaluation-work count as if it were a dataset requirement.
