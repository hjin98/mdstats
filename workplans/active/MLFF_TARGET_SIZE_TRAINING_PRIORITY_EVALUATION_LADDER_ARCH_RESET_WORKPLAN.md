---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
protocol_version: 5.8.0
status: active
created_date: 2026-08-27
reviewed_head: 6f0d34366ca954eabe21740ddda96357afc12eb1
review_revision: 1
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes_conflicting_target_size_population_and_eval_design: true
---

# MLFF Target-Size Training-Priority Evaluation-Ladder Architecture Reset Workplan

## Objective and protected concerns

Rebuild the MLFF target-size population/evaluation architecture around one clean current-generation design that:

1. gives target-training data first priority over target-size evaluation data for scarce structural/condition/event support;
2. preserves a statistically meaningful, permanently non-gradient target-size evaluation population without allowing future evaluation/model outcomes to choose training membership;
3. replaces the current full `size_development_complement` EVAL2 population with one deterministic nested evaluation ladder paired to exact `n1/n2/n3` screening fidelities;
4. replaces the hard-coded eight-size target universe and fixed 16,384 ceiling with a canonical configurable power-of-two ladder;
5. preserves exact target-size continuation, paired-seed comparison, one repaired training master order, independent MVQUAL qualification, canonical EVAL2 metric semantics, and OPT-EVAL4 execution machinery where those remain valid;
6. performs a destructive semantic-generation reset instead of adding migration bridges, compatibility aliases, duplicate authorities, legacy selectors, stale terminology, or fallback paths; and
7. leaves documentation, configuration, persistent authority, runtime behavior, tests, and current terminology describing one architecture.

The stakeholder priority is:

```text
scientific/product correctness
    > clean single-authority architecture
    > material performance/resource efficiency
    > development convenience / compatibility with obsolete derived state
```

### Protected scientific concerns

The implementation must preserve all of the following:

- target-size rungs are nested prefixes of one authoritative repaired target-training order per required training domain;
- target size remains a protocol-global cardinality while actual frame membership remains domain-local;
- the size decision consumes only authorized development/model-selection evidence, never held-out CV, calibration, locked-test, replay-score ranking, or downstream deployment evidence;
- target-size screening remains exact continuation `0 -> n1 -> n2 -> n3` with paired optimizer seeds and no ordinary target-success early stopping during screening;
- production starts fresh after `N_selected` freezes and keeps its independent production epoch maximum;
- target-size evaluation data never supply gradients and never enter fold checkpoint monitors;
- cross-role correlation leakage is prevented at the authoritative correlation/equivalence-family boundary rather than claimed away by naive frame spacing;
- allocation membership freezes before role-local fitted/model-dependent evidence and before any target-size candidate TRAIN2 trajectory can influence it;
- target training receives first claim on unique/scarce support, while evaluation retains correlation-distinct support where such support exists;
- evaluation remains representative enough to measure relative target-size benefit rather than degenerating into an easy/redundant complement;
- configuration changes that alter scientific population identity participate in canonical state identity;
- no runtime silently changes configured target/evaluation cardinalities to make an undersized campaign proceed; and
- no implementation calls correlated configuration counts “independent samples” unless a separately qualified estimator proves that interpretation.

## Final design review corrections incorporated

This revision closes material gaps found during independent review of the initial workplan:

1. **CV ordering is now frozen:** target train/evaluation allocation must occur before cross-validation plans are constructed. The current `build_cross_validation_plans()` consumes every `OuterRole.DEVELOPMENT` unit; post-hoc filtering is insufficient.
2. **Cross-domain closure is now frozen:** allocation is coherent across exact-geometry, declared structural, explicit correlation, protected-event, and other current leakage-equivalence families even when a family spans label domains.
3. **Allocation evidence is no longer ambiguous:** direct continuous target-label values and target/foundation error scores cannot rank the pre-role allocation; the allowed split-safe feature contract is explicit below.
4. **Allocation mechanics are no longer delegated wholesale:** a deterministic whole-allocation-group, cost-aware coverage order and residual-feasibility veto are required; only equivalent local realization details remain delegated.
5. **Evaluation order freezes before candidate training:** `pi_eval` cannot adapt to candidate TRAIN2 predictions, target-size outcomes, or survivor decisions.
6. **Cardinality scope is explicit:** `m1/m2/m3` are configuration counts per target label domain, not independent-unit counts and not a hidden protocol-global total.
7. **Post-selection M3 ownership is explicit:** after `N_selected` freezes, final-development production may reuse M3 as target-side checkpoint/model-selection evidence; CV continues to use fold-local checkpoint monitors; outer/calibration/locked roles remain separate.
8. **The generation boundary is explicit:** the new architecture must use a new semantic generation identity rather than silently reusing TARGET-SIZE-V5/fixed-population schemas.
9. **Documentation sequencing is safe:** Part 1 may precede Part 2 on the implementation branch, but future-state normative documentation must not be merged/released alone while executable main still implements the retired architecture.
10. **Scientific qualification cannot become a ceremonial optional pass:** missing representative decision-preservation evidence is reported as unavailable/deferred qualification, never as success.

## Engineering envelope and chosen architecture

### 1. Authoritative dependency order

For each target label domain, the current-generation control flow is:

```text
source / DATA4 partition-independent evidence / event catalog
    -> DATA5 correlation units + protected outer roles
    -> global leakage-equivalence closure
    -> training-priority target allocation
         -> target-training-authorized allocation groups
         -> residual target-size-evaluation allocation groups
    -> cross-validation plans built ONLY from target-training-authorized units
    -> role-local fitted preparation
         -> FEAS1 -> MVIDX1 -> MVSEL2 -> REPAIR2/MVSTATE2 -> MVQUAL
    -> configured target-size ladder
    -> residual evaluation reference/order -> M1/M2/M3
    -> exact paired (n1,m1) -> (n2,m2) -> (n3,m3) target-size screen
    -> selected protocol-global N
    -> fresh production/fold training
         final-development checkpoint selection may reuse M3
         CV checkpoint selection uses fold-local monitors
    -> held-out protocol validation -> calibration -> locked tests
```

No later fitted/model/evaluation result may reverse this dependency and change the frozen allocation.

### 2. Allocation unit: correlation/equivalence-safe groups, not IID thinning

DATA5 currently owns autocorrelation-aware complete-frame partition units. The new architecture preserves that evidence and adds a stricter allocation boundary.

An **allocation group** is the smallest deterministic connected component that must share one target-training-versus-target-size-evaluation role. At minimum closure must include every relation currently treated as incompatible-role leakage by DATA5/TARGET-DATA role policies, including as applicable:

- one DATA5 correlation/partition unit;
- exact-geometry identity families;
- declared structural/near-duplicate families;
- explicit correlation/active-learning correlation families;
- protected event-window linkage;
- source lineage relations whose current policy forbids independent-role splitting.

If such a relation crosses label domains, the allocation group crosses those domains for role consistency. A structure/correlation family cannot be target training in one label domain and target-size evaluation in another when current leakage policy treats those observations as correlated equivalents.

Required invariant:

```text
allocation_group_role in {target_training, target_size_evaluation}

all member units/frames share that role
no group is split across roles
```

This is a cross-role independence safeguard. It does **not** assert that frames within one training or evaluation group are IID.

`N` and `m_i` count configurations. They do not count independent correlation units. Evaluation evidence must report correlation-unit/effective-sample diagnostics so 1,024 configurations are never presented as 1,024 independent observations merely by cardinality.

### 3. Pre-role allocation feature contract

The training-priority allocation runs before role-local fitted preparation. Its inputs are therefore limited to a versioned **split-safe feature contract** whose values are computed independently of the eventual train/evaluation role and of target-size candidate models.

Allowed classes are:

- immutable source/replica/run/provenance/correlation identities;
- composition, cell, geometry, pair-distance/coordination and other partition-independent structural descriptors;
- declared thermodynamic/chemical/strain/regime/condition identities;
- partition-independent profile/environment classifications whose provider does not fit on the eventual target-training role;
- predeclared DATA4 event identities/protected windows computed before role assignment;
- other explicitly documented DATA4/DATA5 categorical or structural evidence proven role-independent.

Prohibited pre-role ranking inputs are:

- continuous target energy/force/stress values or quantiles used as optimization scores merely because they are stored in DATA4;
- target-model error, target-size candidate prediction/error, or later EVAL2 result;
- foundation residual/difficulty values when their current semantic owner is a fitted/final-development domain;
- DATA6/DATA7 fitted transforms/metrics;
- role-local E0 fits or normalizations;
- held-out CV, calibration, outer-validation, or locked evidence;
- any feature whose production meaning depends on the allocation being chosen.

A predeclared event class may be used categorically even if its upstream event detector consumes physical labels, provided the event detector is partition-independent, specified before the allocation, and is not tuned from target-size evaluation outcomes. Direct label magnitudes remain forbidden as allocation ranking scores unless Software Design explicitly reopens this contract.

Part 1 specifications must enumerate the exact current allowlisted feature families. Part 2 must authenticate that feature-contract identity in allocation state.

### 4. Training-priority allocation policy

The allocation is asymmetric: training has first claim, but it cannot blindly exhaust every correlation-distinct representative of all important residual strata when alternatives exist.

The authoritative process is:

#### 4.1 Build one deterministic allocation-group order

Use the split-safe feature contract and whole allocation groups. Shared exact sparse neighborhood/coverage primitives may be reused, but allocation scoring is **unit/group cost-aware** and must not pretend a variable-size allocation group is the same scientific object as one frame in MVSEL2.

Required lexicographic priorities are:

1. satisfy mandatory/unique training-support obligations;
2. improve the current worst split-safe training coverage family;
3. improve total split-safe training coverage;
4. prefer underrepresented condition/provenance/correlation groups;
5. improve representative structural utility/diversity;
6. for otherwise equivalent gain, prefer lower incremental reserved-frame cost;
7. stable allocation-group identity is the final tie-break.

Coverage-gain comparison for variable-size groups must account for incremental usable-frame cost so large temporal blocks are not preferred merely because they contain more redundant frames. Mandatory rare support may override cost.

The exact normalization/tolerance implementation may be delegated only if it preserves this ordering and is independently deterministic/reference-tested.

#### 4.2 Residual evaluation feasibility is an admissibility constraint

Before accepting a group into target training, the allocator evaluates residual consequences for configured `M3` and declared split-safe evaluation strata.

- If a required/important stratum has only one admissible allocation group, training gets it and the evaluation deficiency is recorded explicitly.
- If two or more correlation-distinct groups exist, the allocator must preserve at least one residual representative where doing so is compatible with training capacity/mandatory support.
- It is forbidden to steal a uniquely required training group merely to make evaluation look complete.
- It is also forbidden to exhaust all residual representatives of a multiply-supported important stratum merely because training coverage gain is marginally higher, unless no feasible allocation satisfying training/CV capacity exists.

This residual guard is weaker than MVQUAL and is not a hidden second training qualification threshold.

#### 4.3 Reserve length is the shortest feasible prefix, not necessarily Nmax raw frames

Because groups are indivisible and CV later removes fold evaluation/monitor/purge units, the target-training reserve generally requires more than `Nmax` raw frames.

The allocator freezes the **shortest admissible prefix** of its deterministic group order for which all of the following are simultaneously true:

- residual target-size-evaluation capacity is at least configured `M3` per target label domain;
- deterministic CV construction using only training-authorized units succeeds at the configured fold topology;
- every resulting required fold training domain and final-development domain has at least `Nmax` eligible target-training configurations after its monitor/evaluation/purge exclusions;
- mandatory split-safe training support remains represented;
- residual feasibility guard remains satisfied as far as the data permit.

The CV plan may be recomputed while searching this prefix because no allocation has frozen yet. Once the shortest feasible prefix and resulting CV plans freeze, no later FEAS1/MVQUAL/TRAIN2/EVAL2 result may enlarge the reserve by stealing groups from evaluation. If rich training later proves infeasible, fail closed or reopen the affected design; do not adapt membership post hoc.

### 5. Cross-validation construction order is mandatory

Current code builds CV from every DATA5 `OuterRole.DEVELOPMENT` unit. The new generation must change that ownership/order.

Required current flow:

```text
outer DATA5 roles
 -> target allocation
 -> target-training-authorized development units
 -> CV evaluation/monitor/training/purge assignment
```

The `CrossValidationPlan` or successor must bind the allocation authority/digest. Evaluation-residual groups must be absent before `_assign_evaluation_folds`, checkpoint-monitor selection, purge calculation, and fold-training construction execute.

Post-hoc filtering of already-built CV plans is forbidden because it can change fold balance, monitor support, purge topology, and training capacity.

Held-out CV folds are still protocol-validation evidence and are distinct from the target-size evaluation ladder.

### 6. Rich target-training chain after allocation freeze

Only target-training-authorized frames may enter fitted target preparation. Preserve/reuse the current rich chain:

```text
training-authorized domain
 -> role-local fitted selection inputs
 -> FEAS1
 -> MVIDX1
 -> MVSEL2
 -> REPAIR2 / MVSTATE2
 -> MVQUAL
 -> configured qualified target-size prefixes
```

Current target-label families, foundation-residual weakness families, required hard coverage/obligations, representative utility, sparse diversity, correlation/provenance balancing, REPAIR2 repair, and independent MVQUAL remain training-domain semantics unless evidence requires a bounded redesign.

One repaired master order per required training domain remains authoritative. Every configured target-size rung is a prefix. Independent per-rung re-selection/repair is forbidden.

If the full configured `Nmax` cannot materialize or rich hard qualification cannot be satisfied inside the frozen reserve, the campaign fails closed. It does not move evaluation groups into training after seeing role-local evidence.

### 7. Residual target-size evaluation reference and ladder

For domain `d`, let `R_d` contain frames belonging to target-size-evaluation allocation groups after role allocation freezes.

Build one deterministic evaluation master order `pi_eval_d` over `R_d`. The order must freeze **before the first target-size TRAIN2 candidate trajectory/checkpoint is executed**.

The evaluation order may use, after allocation freezes:

- role-local target-label distributions;
- a frozen external/foundation model's residuals if that model identity is independent of the target-size candidate trajectories;
- the same structural/condition/event/provenance evidence used by the generalized exact coverage machinery.

It may not use:

- predictions/errors from any target-size candidate model;
- survivor outcomes or selected-size decisions;
- production-model predictions produced after size selection;
- held-out CV/calibration/locked evidence.

Thus evaluation selection can be rich but cannot become adaptive hard-example mining against the candidates it later ranks.

Evaluation prefixes are exact nested views:

```text
M1_d = pi_eval_d[:m1]
M2_d = pi_eval_d[:m2]
M3_d = pi_eval_d[:m3]
M1_d subset M2_d subset M3_d subset R_d
```

Evaluation selection is representative/model-selection coverage, not MVQUAL hard qualification. It does not inherit the training 0.95 threshold or REPAIR2 by default. Deficits and unrepresentable strata are diagnostics/qualification evidence.

Correlation/provenance balance must be explicit in evaluation ordering so frames do not concentrate in one residual correlation group when alternatives exist. Multiple frames from one evaluation allocation group are permitted when required for cardinality, but selected correlation-unit counts/effective-sample diagnostics must be persisted.

`R_d \ M3_d` stays non-gradient and serves only as larger residual/reference evidence for qualification or other explicitly authorized development diagnostics. It is not an automatic fallback evaluation set in production.

### 8. Cardinality scope and multi-domain aggregation

Configured evaluation sizes are **per target label domain**:

```text
m1 = 2^q1 configurations per target label domain
m2 = 2^q2 configurations per target label domain
m3 = 2^q3 configurations per target label domain
```

Each target label domain has its own authenticated nested evaluation order/prefixes. The canonical EVAL2 target-metric aggregation/weighting across label domains remains unchanged by this work and remains the sole metric owner; this work must not silently introduce equal-domain averaging, domain reweighting, or a new score merely because cardinalities changed.

If `D` target label domains participate and all eight default candidate sizes are initially qualified with two seeds, the default ordinary configuration-evaluation upper bound is:

```text
D * (8*2*256 + 4*2*512 + 2*2*1024)
= D * 12,288 configurations
```

before batching/cache reuse. Documentation/performance claims must not quote 12,288 as a protocol-global bound without the domain factor.

### 9. Pair evaluation fidelity and cardinality explicitly

The target-size screen owns exactly three immutable stage pairs:

```text
(n1,m1)
(n2,m2)
(n3,m3)
```

Default:

```text
fidelity_epochs       = [1, 3, 10]
evaluation_size_powers = [8, 9, 10]
evaluation_sizes      = [256, 512, 1024]
```

At one stage, every candidate size and paired optimizer seed uses the exact same authenticated evaluation-rung identity per target label domain. Metrics are compared only within that stage population. Cross-rung metric values are not directly compared as though the sample were unchanged.

EVAL2 retains the canonical target-force estimator and OPT-EVAL4 retains execution/resource ownership. Population authority changes; metric definition does not.

### 10. M3 lifecycle after target-size selection

M3 is development/model-selection evidence, not held-out validation.

After `N_selected` freezes:

- final-development production may reuse the frozen M3 target population for target-side checkpoint/model selection, replacing the retired development-complement role;
- M3 remains non-gradient;
- final-development checkpoint selection may not mutate M3 membership/order;
- cross-validation models continue to use their fold-local checkpoint monitors, not M3;
- held-out CV, outer validation, uncertainty calibration, and locked tests remain separate and cannot be collapsed into M3;
- using M3 for final-development checkpoint selection means M3 cannot later be advertised as independent protocol validation evidence.

If an existing separate common target-online monitor has no remaining independent responsibility after this consolidation, Part 2 must remove/merge it rather than preserve duplicate model-selection authorities. If it still owns a distinct required training-time diagnostic that does not control target-size evaluation or final checkpoint choice, document that narrower role explicitly.

### 11. Power-of-two target-size/evaluation configuration

Canonical user configuration is exponent-based:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

Resolved policy derives:

```text
candidate_target_sizes = [2^p for p in pmin..pmax]
Nmax = 2^pmax
evaluation_sizes = [2^q for q in evaluation_size_powers]
rungs = [(n1,m1),(n2,m2),(n3,m3)]
```

Defaults therefore remain numerically:

```text
target sizes: 128,256,512,1024,2048,4096,8192,16384
evaluation sizes per target label domain: 256,512,1024
```

Required validation:

- all powers are integers and nonnegative;
- `pmin < pmax` for the current three-or-more-rung funnel;
- the derived target ladder contains at least the policy's minimum qualified-size count;
- evaluation powers contain exactly three strictly increasing values;
- every derived cardinality is an exact positive integer representable by all owning serialized/index/count types;
- there is no scientific `<=16384` guard; implementation/resource representation limits are explicit technical limits, not hidden scientific ceilings;
- no non-power-of-two rescue size is generated;
- resolved configuration persists both canonical powers and human-readable derived sizes;
- powers, rung mapping, and other scientific population fields participate in semantic policy/state identity.

Evaluation powers need not be consecutive. A configuration such as `[8,10,11]` is structurally legal but is scientifically unqualified until representative qualification supports it.

### 12. Configured-ceiling semantics

Replace current fixed-ceiling semantics everywhere in current authority:

```text
FIXED_TARGET_SIZES                 -> policy-derived target ladder
FIXED_TARGET_SIZE_CEILING          -> configured Nmax
outside the fixed universe        -> outside configured target-size ladder
nonconverged_at_fixed_ceiling      -> nonconverged_at_configured_ceiling
fixed scientific ceiling 16384    -> configured scientific ceiling 2^pmax
```

If the largest configured candidate remains materially superior under the final practical-equivalence rule, return typed non-convergence at the configured ceiling. Do not synthesize a larger/intermediate rescue size.

### 13. Capacity and early feasibility

Preparation must establish before expensive rich MVIDX/MVSEL/TRAIN2 work that the configured architecture is feasible.

Per target label domain it must prove, using the frozen allocation/CV topology:

- every required final/fold training domain can materialize `Nmax` target configurations;
- residual evaluation contains at least `M3` target configurations;
- mandatory split-safe training support is available;
- residual support guard is accounted for, including explicit unrepresentable strata;
- global/cross-domain leakage-equivalence groups are role-consistent;
- CV monitor/evaluation/purge construction succeeds without consuming residual target-size-evaluation groups.

`16384 + 1024 = 17408` is only a single-domain raw arithmetic lower bound under defaults. It is neither an independence guarantee nor a sufficient capacity criterion. Whole allocation groups, CV fold/monitor/purge requirements, multiple target domains, outer roles, and support obligations may require materially more source frames.

An undersized campaign fails early with resolved-policy/capacity diagnostics. It never silently lowers `pmax`, lowers `m3`, reuses a correlation group across roles, or falls back to the old complement evaluator.

### 14. Semantic-generation reset and compatibility

This architecture is a new semantic generation. It must not silently reuse TARGET-SIZE-V5/fixed-universe/complement schemas or authority-version strings in a way that lets old state deserialize as current.

The exact public generation name/version is delegated, but the implementation must make old/new identity distinguishable at the earliest persisted owner. Current documentation/code should not continue to call the new current architecture `TARGET-SIZE-V5` where that name denotes retired fixed-population/complement semantics.

Existing derived campaign/prepared state is intentionally unsupported. Do not add migration/compatibility paths for:

- old `size_development` role-freeze semantics;
- old full/coarse complement target-size EVAL2 roles;
- fixed-eight/fixed-ceiling target-size policy state;
- old target-size study/evidence population identities;
- old REPAIR/MVQUAL candidate universes;
- old DATA7/DATA8 candidate artifacts;
- old target-size TRAIN2/EVAL2 checkpoints/evidence;
- fixed/flexible candidate-authority bridges or compatibility receipts retained only for superseded generations.

Raw/external source data remain valid inputs. A current run must rebuild derived state under the new generation. A pre-reset workspace fails early with a clear “unsupported pre-training-priority/evaluation-ladder generation; create/reprepare a new campaign workspace” class of error.

Historical docs/release evidence may remain historical. Executable historical readers may remain only when an independently required product capability consumes them; otherwise remove them from the current training package rather than retaining dead compatibility code.

## Part 1 - Documentation and specification authority reset

Part 1 executes before Part 2 on the implementation branch. It defines the target architecture precisely enough that implementation need not infer intent from obsolete code.

**Publication constraint:** Part 1 future-state normative documentation must not be merged/released by itself to a branch that still ships the retired executable architecture. Part 1 closes as an implementation-branch design gate; public/main documentation and executable code become authoritative together when Part 2 is accepted.

### D1. Rewrite architecture manuals

At minimum reconcile:

- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- `docs/arch_manuals/mlff_training_data_architecture.md`;
- current dependency graph/source maps and generated architecture inputs.

Required documentary outcomes:

- target allocation precedes CV construction and fitted preparation;
- allocation/equivalence-group closure across label domains is explicit;
- split-safe allocation evidence versus role-local rich evidence is explicit;
- allocation group/configuration counts/effective independence are not conflated;
- training reserve versus final rich training order are distinct authorities;
- residual evaluation order freezes before candidate TRAIN2;
- M1/M2/M3 are per-domain nested populations;
- M3 post-selection checkpoint role is explicit;
- configured powers/configured-ceiling semantics replace fixed-universe language;
- destructive new-generation/no-migration semantics are explicit;
- EVAL2 population ownership is distinct from metric/execution ownership.

### D2. Rewrite current normative specifications

Update/replace every current spec affected by role/population ownership, including at minimum:

- target-subset size-study policy;
- DATA5 partition/CV role policy;
- TARGET-DATA role-freeze/allocation policy;
- leakage/equivalence-family policy;
- target coverage / FEAS1 / MVIDX / MVSEL2 / REPAIR2 / MVQUAL where domain/ladder ownership changes;
- EVAL2 target-role/population policy;
- OPT-EVAL4 only where population identity/buffer assumptions reference full complement;
- final-development checkpoint-selection/monitor policy;
- campaign/configuration/default-generation policy;
- persistence/restart/current-generation policy.

Specifications must distinguish three related but non-interchangeable mechanisms:

```text
TRAIN-RESERVE split-safe allocation coverage
rich target-training hard coverage + MVQUAL
residual target-size-evaluation representative coverage
```

The allocation spec must enumerate split-safe feature families and the group-level deterministic objective/admissibility semantics from this workplan.

### D3. Cleanse retired terminology from current documentation

Perform repository-wide inspection over current normative/user documentation and rewrite/remove current statements that imply retired behavior, including:

- fixed target-size universe/fixed nominal population;
- fixed ceiling / `nonconverged_at_fixed_ceiling`;
- scientific 16,384 except as the default `2^14` example;
- current `size_development` where explicit target-training/evaluation roles supersede it;
- `size_development_complement` / `size_development_coarse` target-size evaluation semantics;
- candidate-prefix complement subtraction as current evaluation population;
- arbitrary train/evaluation percentages;
- current migration/compatibility promises intentionally removed by this reset;
- unsupported claims that retained frames are IID after decorrelation;
- old selector/repair generations presented as alternate current paths;
- current uses of TARGET-SIZE-V5/fixed/flexible generation terminology that would misidentify the new semantic generation.

Historical/archive/release documents need not be rewritten to erase history, but they must remain clearly non-current and must not be referenced as executable authority.

### D4. Resolve active-workplan precedence

Reconcile `workplans/active/README.md` and conflicting active-plan text.

This workplan controls target-size population, allocation, evaluation-ladder, power/configured-ceiling, new-generation and compatibility semantics.

The exact-boundary screening workplan remains controlling only for nonconflicting `n1 -> n2 -> n3` continuation/fresh-production behavior. Its fixed-candidate/population/EVAL2 assumptions must be explicitly marked superseded so an implementer cannot satisfy contradictory contracts.

Unrelated RAM/lifecycle/DATA7-8 workplans remain independent unless implementation evidence shows a direct dependency.

### D5. Document multi-domain and post-selection metric semantics

Current docs/specs must state:

- `m_i` cardinality is per target label domain;
- existing EVAL2 domain aggregation/weighting remains unchanged;
- final-development M3 may control checkpoint/model selection only after target size is frozen;
- CV fold monitors remain separate;
- M3 is not held-out validation after it has controlled target-size/final checkpoint decisions;
- outer validation/calibration/locked roles remain independent.

### D6. Part 1 acceptance

Part 1 closes only when:

1. architecture manuals tell one coherent future current-generation story;
2. current normative specs agree with the architecture and this reviewed contract;
3. user/config docs expose power-based configuration and per-domain M1/M2/M3;
4. current terminology search has no unexplained retired fixed/complement/migration/TARGET-SIZE-V5 current authority;
5. dependency diagrams place target allocation before CV/fitted preparation;
6. ownership diagrams identify one allocation owner and one evaluation-ladder owner;
7. docs do not claim unsupported IID semantics;
8. post-selection M3/checkpoint/CV roles are unambiguous;
9. active workplan precedence is noncontradictory; and
10. documentation build/lint/reference/PDF checks required by the repository pass on the branch.

An independent implementer should be able to reconstruct Part 2 behavior from current branch documentation without this conversation.

## Part 2 - Code implementation and destructive cleanup

Part 2 implements the documented architecture. Prefer ownership correction, semantic reuse/refactoring, and deletion over adapters that preserve superseded designs.

### C1. Canonical power policy and new generation identity

Required end state:

- canonical config fields `target_size_power_min`, `target_size_power_max`, `evaluation_size_powers`, `fidelity_epochs`;
- one canonical resolver derives target sizes, `Nmax`, per-domain evaluation sizes, and stage pairs;
- `TargetSizeStudyPolicy` or clean successor owns the derived ladder/funnel/equivalence/seed semantics;
- all consumers use resolved policy instead of recomputing powers;
- current schemas/authority versions distinguish the new generation from TARGET-SIZE-V5/fixed/complement state;
- terminal non-convergence is `nonconverged_at_configured_ceiling`;
- default and nondefault configs print/persist powers plus derived sizes;
- semantically relevant fields participate in identity.

Structural acceptance proves current production code has no scientific `FIXED_TARGET_SIZES`, `FIXED_TARGET_SIZE_CEILING`, `<=16384` guard, fixed-universe error, or old-generation alias capable of deserializing retired state as current.

### C2. Build global allocation-equivalence groups

Create/reuse one owner that closes DATA5 units under all incompatible-role leakage/equivalence relations, including cross-label-domain relations.

Required tests:

- exact geometry family spanning domains cannot split roles;
- declared structural/correlation/active-learning family cannot split roles;
- protected event linkage cannot split roles when policy declares it indivisible;
- unrelated groups remain independently allocatable;
- group identity is deterministic and digest-bound.

Do not create a second leakage-family definition inconsistent with existing DATA5/TARGET-DATA policy; consolidate the current relations into one allocation input authority.

### C3. Implement deterministic training-priority allocation + shortest feasible reserve

Create one authoritative allocation record/policy that publishes:

- source/equivalence-group identity;
- split-safe feature-contract identity;
- deterministic ordered allocation groups and selected training prefix;
- training-authorized units/frames by label domain;
- residual evaluation units/frames by label domain;
- training split-safe coverage/support diagnostics;
- residual support/deficiency diagnostics;
- CV-feasibility/capacity result;
- exact config/policy digest;
- proofs of disjointness/equivalence-group role consistency.

Implement the lexicographic/cost-aware selection and residual admissibility rules frozen above. Role assignment freezes only after the shortest prefix satisfying residual M3 capacity and deterministic CV/Nmax feasibility is found.

No percentage/random split authority is introduced.

### C4. Rebuild CV plans from training-authorized units only

`build_cross_validation_plans()` or its current successor must consume target-training-authorized units, not all outer development units.

Required behavior:

- evaluation residual absent before fold assignment begins;
- fold evaluation/monitor/purge/training roles are recomputed from training-authorized units;
- CV plan identity binds allocation identity;
- each fold training domain has Nmax capacity;
- held-out CV remains distinct from target-size evaluation;
- changing allocation invalidates CV/fitted descendants.

A test that constructs old CV and merely filters residual UIDs afterward is specifically insufficient.

### C5. Route fitted/rich training chain through training-authorized domains

Update DATA6/DATA7/FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL ownership so:

- no residual evaluation UID enters fitted target-training inputs;
- configured target sizes, not a static eight-rung tuple, drive materializable prefixes;
- one repaired master order remains authoritative;
- MVQUAL monotonicity and hard predicates remain exact;
- candidate materialization identities bind allocation/CV/current-generation authority;
- nondefault smaller/larger ladders work subject to actual capacity/resource limits.

If rich training fails inside the frozen reserve, do not adapt the role split from role-local evidence.

### C6. Generalize shared exact coverage/index primitives without conflating policies

Reuse shared mathematical primitives for allocation, rich training, and evaluation where the relation is genuinely the same; do not copy the implementation three times.

However, keep policy layers distinct:

- allocation uses whole groups, split-safe features, variable cost and residual veto;
- rich training uses frame-level hard coverage/obligations, REPAIR2 and MVQUAL;
- evaluation uses representative coverage without training hard pass/fail.

Do not force these materially different policies through one generic score abstraction if doing so obscures semantics. Reuse adjacency/index/vector kernels and shared state primitives; retain role-specific policy owners.

Preserve exact/reference oracles for optimized selection/index paths where materially useful.

### C7. Build frozen residual evaluation order and M1/M2/M3

Required end state per target label domain:

- one `pi_eval_d` freezes before any candidate TRAIN2 execution;
- M1/M2/M3 are exact configured prefixes;
- all selected frames belong to residual allocation groups;
- no target-training frame/group appears;
- evaluation feature/reference/policy/foundation identities are digest-bound;
- target labels/frozen-foundation residuals may influence ordering only after allocation freeze and before candidate TRAIN2;
- candidate-model predictions/outcomes cannot influence ordering;
- correlation-unit/effective-sample diagnostics are recorded;
- unrepresentable strata remain diagnostics, not runtime reallocation triggers;
- no fallback to full complement or arbitrary temporal sampling exists.

Suggested materialization remains three authenticated bounded ExtXYZ/monitor artifacts unless one indexed artifact proves equally clear/restart-safe and materially simpler.

### C8. Rebind EVAL2 and final-development checkpoint selection

Delete current target-size/full-development semantics based on:

- `build_eval2_size_study_target_role()` complement subtraction;
- `size_development_complement`;
- `size_development_coarse`;
- maximum-training-prefix subtraction;
- legacy block sampling used only for retired generations.

Resolve target-size stages directly:

```text
coarse -> M1
short -> M2
final_screen -> M3
```

After target size freezes, final-development checkpoint/model selection may reuse M3. CV continues to use fold checkpoint monitors.

Preserve canonical EVAL2 target-force metric/domain aggregation, checkpoint/foundation identity checks, and OPT-EVAL4 CPU-prepare -> accelerator-inference -> CPU-finalize -> parent-commit execution/resource machinery.

Evaluation evidence binds exact evaluation-ladder/rung identity, not a generic role name.

### C9. Reconcile target-size evidence/orchestration

Update study/evidence schemas so every stage authenticates:

- exact stage and boundary `n_i`;
- exact per-domain evaluation rung `m_i`/rung digests;
- complete ordered paired-seed population;
- candidate data/current-generation identity;
- shared metric/domain-aggregation policy;
- exact continuation ancestry.

Preserve `q -> min(q,4) -> 2 -> 1`, practical-equivalence/smaller-size rules, and exact boundary continuation.

Cross-rung population mixing fails closed. Selected N is a configured target-size rung. Configured-ceiling nonconvergence is typed/authenticated. Status/reporting prints active boundary and per-domain evaluation cardinality.

### C10. Persistence/restart/invalidation

Identity must invalidate unsafe reuse when changing at least:

- target min/max powers;
- evaluation powers;
- fidelity epochs;
- allocation group/equivalence policy;
- split-safe feature contract;
- allocation scoring/residual-feasibility policy;
- evaluation order feature/policy/foundation identity;
- correlation-unit source identity;
- relevant rich target coverage policy.

Required restart behavior:

- identical scientific config/inputs -> deterministic same allocation/CV/orders/digests;
- execution-only worker/chunk/cache changes -> scientific identities stable when mathematically unchanged;
- changed scientific policy -> affected descendants invalidate;
- pre-reset workspace -> clear unsupported-generation failure;
- restart at each target-size boundary uses the same frozen M_i identities;
- no restart path recomputes evaluation order from candidate predictions.

### C11. Destructive cleanup

After the new path passes, remove superseded current code/tests/exports rather than retaining parallel implementations.

Delete/retire as applicable:

- fixed target-size constants/guards;
- fixed/flexible candidate-authority migration/bridge/receipt code no longer serving an independent historical-reader product;
- full/coarse complement EVAL2 helpers/role kinds;
- deprecated `size_development` current role fields;
- stale serializers/current-generation aliases;
- current TARGET-SIZE-V5 strings that identify the retired semantic generation;
- dead selector/repair/migration wrappers;
- tests that exist only to preserve retired behavior.

Structural acceptance requires repository-wide import/reference/search evidence that no removed authority has a reachable current production consumer.

### C12. Performance/resource preservation

Preserve/reuse where semantically compatible:

- exact sparse forward MVIDX representation;
- mmap/out-of-core execution;
- optimized MVSEL2 forward/lazy kernels;
- bounded evaluation prepare/finalize buffers;
- current inference admission/concurrency;
- graph/context reuse enabled by nested M1/M2/M3.

Default ordinary target-size evaluation cost is bounded per target label domain by 12,288 configuration evaluations when all eight candidates are initially qualified and two seeds are used. Total cost scales by the number of target label domains.

Do not trade exactness, role separation, or configured cardinality for performance.

## Implementation authority

### Frozen

The implementer MUST preserve:

- target allocation before CV construction and fitted preparation;
- allocation-group closure across all current incompatible-role leakage/equivalence relations, including cross-domain relations;
- split-safe feature contract and prohibition on direct target-label/error ranking before allocation freeze;
- deterministic cost-aware training-priority group order, residual feasibility veto, and shortest feasible reserve prefix;
- no post-freeze stealing between target training and target-size evaluation;
- rich training chain inside training-authorized domains;
- one frozen evaluation master order per target label domain before candidate TRAIN2;
- exactly three per-domain evaluation rungs paired with n1/n2/n3;
- M3 reuse for final-development checkpoint selection after N freezes, with CV monitors remaining fold-local;
- exponent-based target/evaluation configuration and configured-ceiling semantics;
- new semantic generation identity and destructive no-migration policy for derived state;
- canonical EVAL2 metric/domain aggregation and OPT-EVAL4 execution semantics;
- exact screening continuation and fresh production;
- full long target-machine/GPU qualification remains separate from routine functional acceptance.

### Delegated

Implementation may choose, without changing frozen semantics:

- exact class/module/schema names for allocation/evaluation authorities;
- whether allocation lives in DATA5 or an immediate TARGET-DATA consumer, provided there is one owner and CV consumes it before fold construction;
- internal sparse/group data structures;
- mathematically equivalent floating tolerance/normalization realization for the frozen group-level objective;
- three artifacts versus one indexed M-ladder artifact;
- concrete new semantic-generation identifier/version string;
- local schema/error-code names;
- bounded test fixture sizes and numerical fakes below accepted owner boundaries.

### Reopen only on evidence

Reopen only the affected surface if representative evidence proves:

1. whole allocation-group closure causes pathological reserve inflation or makes the default architecture infeasible;
2. split-safe features cannot protect training edge support adequately;
3. residual evaluation is systematically biased enough to change target-size decisions at practical M sizes;
4. current multi-view primitives cannot be reused without materially worse complexity/semantics;
5. configured sizes above 16,384 encounter a genuine representation/algorithm bound requiring an explicit technical limit;
6. multi-domain equivalence closure or CV topology requires a different statistically valid allocation formulation;
7. default `[256,512,1024]` fails survivor/winner preservation;
8. M3 reuse for final checkpoint selection conflicts with an independently required distinct development/model-selection authority.

Do not reopen exact-boundary/fresh-production/held-out doctrine merely because one local assumption fails.

## Initially expected affected surface

Implementation must re-derive the final affected surface. Initially inspect at least:

### Core code

- `partition.py` outer/CV planning;
- `target_data_roles.py` or replacement allocation owner;
- `leakage.py` and correlation/equivalence-family ownership;
- target coverage/reference/feasibility/sparse-index modules;
- MVSEL2 engine/state, REPAIR2, MVQUAL2;
- `target_size_study.py`;
- `eval2.py`;
- final-development checkpoint/monitor owner;
- `_campaign_cli_core.py` orchestration/config/state/reporting;
- DATA6/7/8 planning/materialization owners;
- CV/final-domain assembly;
- configuration resolution/default generation;
- serializers/current-state reconciliation/package exports.

### Tests

At minimum reconcile:

- DATA5 partition/CV/leakage;
- target allocation/role freeze;
- cross-domain leakage families;
- coverage/FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL;
- target-size study/flexible-fidelity/topology;
- EVAL2/OPT-EVAL4;
- production checkpoint selection;
- campaign CLI/state/restart/preflight;
- CV lifecycle/materialization;
- configuration/default/digest;
- reference/performance tests for changed generalized kernels.

### Documentation

Part 1 surfaces plus README/user guides, campaign examples, dependency graphs, current architecture/release references, and generated PDFs required by repository policy.

## Part 2 gate sequence and required acceptance

Each executable material gate closes semantic/conformance plus focused tests and stage-local affected regression before dependent work proceeds.

### Gate C-A - Generation/power policy + allocation-equivalence primitives

Implement new semantic generation, canonical power resolver, configured ceiling, global allocation-equivalence groups, split-safe feature contract and identity.

Focused acceptance:

- default/nondefault power resolution;
- nonnegative/representable power validation;
- exact derived ladders/rung pairs;
- no hidden 16,384 scientific ceiling;
- cross-domain geometry/correlation family closure;
- split-safe feature allow/prohibit enforcement;
- deterministic identities.

Stage-local regression: config, partition/role/leakage/current-state identity.

### Gate C-B - Training-priority allocation + CV reconstruction

Implement cost-aware deterministic group order, residual guard, shortest feasible reserve and CV-from-training-only construction.

Focused acceptance:

- unique/scarce support goes to training;
- multiply-supported strata retain residual support when feasible;
- variable-size group cost prevents redundant large-block preference under equal coverage;
- whole-group disjointness;
- shortest prefix satisfies M3 + every fold/final Nmax capacity;
- evaluation residual absent before CV assignment;
- insufficient capacity fails closed;
- no post-hoc CV filtering path.

Stage-local regression: DATA5/target roles/CV/leakage/preflight/state identity.

### Gate C-C - Rich training chain reconciliation

Route DATA6/7/FEAS/MVIDX/MVSEL2/REPAIR2/MVQUAL through training-authorized domains/configured ladders.

Focused acceptance:

- no residual UID/group in fitted target inputs;
- one repaired order/nested prefixes;
- default configured ladder matches intentionally preserved scientific selector behavior on bounded fixtures;
- nondefault ladders work;
- MVQUAL monotonicity and configured-prefix population;
- final/fold Nmax capacity;
- rich failure cannot mutate role allocation.

Stage-local regression: affected DATA6/7/8, coverage, selector, repair, qualification, CV/final domain consumers.

### Gate C-D - Frozen evaluation order + nested ladder

Build one evaluation order per target label domain before candidate TRAIN2.

Focused acceptance:

- deterministic order/digest;
- strict M1 subset M2 subset M3 and exact per-domain cardinalities;
- all frames from residual role;
- candidate-model prediction unavailable/forbidden as order input;
- frozen foundation/label ordering cannot mutate allocation;
- correlation/effective-sample diagnostics;
- unrepresentable-stratum diagnostics;
- no full-complement/temporal fallback.

Stage-local regression: generalized coverage/index/evaluation role/materialization.

### Gate C-E - EVAL2, M3 checkpoint role and target-size orchestration

Exercise the real owner path:

```text
resolved config/current generation
 -> outer roles
 -> allocation-equivalence + training-priority allocation
 -> CV-from-training-only plans
 -> rich target-training study
 -> frozen evaluation ladder
 -> select-target-size stage resolver
 -> TRAIN2 exact boundary continuation
 -> EVAL2 stage-specific M role
 -> OPT-EVAL4
 -> reducer/survivor authorization
 -> selected/configured-ceiling state
 -> fresh final-development training
 -> M3 final checkpoint selection
```

Allowed doubles are below these owners: expensive MACE stepping/GPU inference may be bounded/faked after real runtime/evaluation assembly. Tests intended to prove orchestration must not patch/reimplement allocation, CV construction, rung resolution, reducer, or selected-size/checkpoint transitions.

Required integration cases:

1. default `[1,3,10]`, target powers `7..14`, eval powers `[8,9,10]`;
2. nondefault fidelity/evaluation powers;
3. changed pmin/pmax;
4. multiple target label domains verifying per-domain cardinality and unchanged metric aggregation;
5. configured-ceiling nonconvergence;
6. insufficient residual M3 capacity;
7. insufficient fold Nmax capacity despite raw `Nmax+M3` frames;
8. pre-reset workspace rejection;
9. restart at every screen boundary preserves allocation/CV/M identities;
10. eliminated candidate receives no later work;
11. no full-complement fallback;
12. M3 final checkpoint selection after N freeze;
13. CV checkpoint monitors remain fold-local.

Stage-local regression: target-size study, CLI, scheduler, persistence/restart, EVAL2/OPT-EVAL4, checkpoint selection, DATA7/8 consumers.

### Gate C-F - Destructive cleanup

Remove superseded code/tests/current terminology after new assembled path passes.

Structural checks:

- no reachable fixed-size/fixed-ceiling authority;
- no complement/coarse-complement target-size role;
- no obsolete migration bridge/receipt reachable from current loading;
- no TARGET-SIZE-V5 current semantic alias for the new generation;
- no second current target-membership selector;
- no stale eight-rung-only loop/static tuple outside canonical default derivation/examples;
- no old config alias that silently changes scientific meaning;
- no current doc/spec claims retired behavior.

Run focused import/package/deletion checks and affected regression after deletion.

### Gate C-G - Final assembled functional acceptance

After all executable edits:

1. reconcile every frozen obligation against source/current docs;
2. re-derive the complete affected surface from final diff/dependency graph;
3. run the complete affected regression suite;
4. run assembled integration through real semantic owners with bounded expensive numerical doubles only below those owners;
5. run repository-required broader/full tests if impact cannot be confidently bounded;
6. rebuild/check affected documentation/PDF outputs;
7. perform structural legacy-absence/authority-uniqueness inspection;
8. run bounded deterministic reference/performance checks for changed allocation/coverage/index/selector paths;
9. package/execute scientific qualification below or explicitly record unavailable external evidence as deferred—not passed.

New or plausibly affected failures block functional closure. Proven pre-existing unrelated failures may be attributed.

## Scientific qualification obligations

This architecture changes the sampling estimator/population used for target-size decisions. Functional tests cannot by themselves establish that `[256,512,1024]` preserves the intended decision.

### Required qualification harness and claims

Provide a reproducible retrospective/oracle path that can use completed candidate checkpoints/predictions or a bounded representative run to compare M1/M2/M3 with the complete residual reference population `R` (or the largest practical authenticated reference when complete R is infeasible).

Qualification assesses decisions, not pointwise equality:

1. M1 does not falsely eliminate an eventual competitive/reference-finalist size on qualified cases;
2. M2 preserves the reference finalist population;
3. M3 selects the same target size under the configured practical-equivalence/smaller-size rule;
4. evaluation coverage/support improves monotonically where the metric mathematically implies monotonicity;
5. M ladders cover declared conditions/events/features better than naive temporal/uniform same-cardinality baselines;
6. training reserve still supports rich training/MVQUAL after carve-out;
7. allocation/evaluation/CV leakage audit is clean;
8. rerun/restart/worker/cache realization preserves scientific identities/results;
9. real assembled target-size path consumes exact M_i at exact n_i;
10. timing/inference evidence confirms material reduction versus full-complement evaluation.

Policy tuning/qualification must not use held-out CV/locked evidence. If M powers are changed based on qualification, that creates a new policy identity and invalidates target-size evidence produced under the old M ladder.

### Qualification closure semantics

- Representative decision-preservation evidence is required before declaring the new default M ladder scientifically qualified for production use.
- If the development environment lacks the historical checkpoints/data/hardware needed for representative qualification, implementation may be functionally complete but the qualification is **deferred/unavailable**, not passed.
- The final report must distinguish functional acceptance, scientific sampling-policy qualification, and target-machine/GPU performance qualification.
- Full long real-data GPU/resource qualification remains deferred to the established final GPU/release phase; CPU/bounded functional tests cannot claim it.
- If default `[256,512,1024]` fails decision preservation, explicitly revise the affected powers and requalify. Never silently expand M at runtime.

## Anti-shortcut and cleanup constraints

Explicitly forbidden:

- build CV from the whole outer development pool and filter residual evaluation units afterward;
- split one leakage-equivalence/allocation group across train/evaluation, including across label domains;
- use direct continuous target-label values, candidate errors, or role-fitted residuals to rank pre-role allocation contrary to the split-safe contract;
- adapt allocation after FEAS1/MVQUAL/TRAIN2/EVAL2 reveals a difficult case;
- choose/reorder M1/M2/M3 using candidate-model predictions or survivor outcomes;
- retain old complement evaluator behind fallback/config flag;
- accept fixed-size tuples and exponent policy as equal current authorities;
- silently map legacy config keys to materially new semantics;
- migrate old derived campaign state solely for compatibility;
- use held-out CV to choose target size or final checkpoint;
- claim configuration count equals independent-sample count;
- weaken MVQUAL, disjointness, configured cardinalities, practical-equivalence, or exact boundary rules to satisfy tests;
- independently resample M1/M2/M3;
- copy full multi-view implementations into parallel train/eval/allocation code when mathematical primitives can be shared;
- preserve dead selector/repair/migration code because archived tests reference it;
- leave `size_development` or TARGET-SIZE-V5 as an equally authoritative current semantic path;
- let worker/batch/cache/RAM/VRAM/scheduling choices alter scientific membership/order;
- merge/release Part 1 future-state docs alone while main executable behavior still implements the retired architecture;
- report unavailable scientific qualification as a pass.

## Handoff closure

Reviewed-head current behavior includes a fixed eight-size ladder through 16,384, CV plans built from all outer development units, and target-size/final-development EVAL2 complement roles. This plan intentionally replaces those population/role semantics while preserving nonconflicting exact-boundary continuation and fresh production doctrine.

```text
stakeholder requirements:
  training coverage priority
  + bounded nested evaluation
  + configurable base-2 target/evaluation ladders
  + documentation first
  + destructive cleanup/no compatibility accretion

protected concerns:
  statistical role separation
  correlation/equivalence leakage
  exact screening continuation
  rich target-training coverage
  representative nonadaptive evaluation
  clean one-generation ownership

accepted architecture:
  outer roles
  -> global allocation-equivalence closure
  -> split-safe cost-aware training-priority allocation
  -> shortest reserve satisfying residual M3 + CV/final Nmax capacity
  -> CV built from training-authorized units only
  -> rich training order/qualification inside reserve
  -> frozen residual per-domain evaluation order before candidate TRAIN2
  -> nested M1/M2/M3 paired with n1/n2/n3
  -> configured exponent target ladder
  -> selected N
  -> fresh production with M3 final-development checkpoint selection

known cross-module consequences:
  DATA4/DATA5/leakage/role allocation/CV
  -> DATA6/7 coverage/MVIDX/MVSEL2/REPAIR2/MVQUAL
  -> target-size policy/state/EVAL2/OPT-EVAL4/checkpoint selection
  -> CLI/restart/config/docs/tests/cleanup

acceptance:
  Part 1 coherent future docs on branch
  + Part 2 stage-local semantic/functional closure
  + final affected regression/integration
  + structural legacy absence/authority uniqueness
  + explicit scientific sampling qualification status
```

No material reviewed design decision is intentionally delegated back to implementation discovery. A material change to allocation-before-CV ordering, cross-domain equivalence closure, split-safe feature policy, target/evaluation role boundary, nonadaptive M ladder, per-domain cardinality, M3 lifecycle, power-based target universe, or destructive compatibility policy requires a bounded Software Design reopen.