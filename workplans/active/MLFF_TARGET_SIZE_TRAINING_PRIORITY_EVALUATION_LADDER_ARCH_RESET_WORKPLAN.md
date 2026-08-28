---
kind: implementation-workplan
workplan_id: CODE-MLFF-TARGET-SIZE-TRAINING-PRIORITY-EVAL-LADDER-ARCH-RESET-V1
protocol_version: 5.8.0
status: active
created_date: 2026-08-27
reviewed_head: 6f0d34366ca954eabe21740ddda96357afc12eb1
architecture_change: major
compatibility_policy: destructive-generation-reset
supersedes_conflicting_target_size_population_and_eval_design: true
---

# MLFF Target-Size Training-Priority Evaluation-Ladder Architecture Reset Workplan

## Objective and protected concerns

Rebuild the MLFF target-size population/evaluation architecture around a clean current-generation design that:

1. gives target-training data first priority over target-size evaluation data for scarce structural/condition/event coverage;
2. preserves a statistically meaningful non-gradient target-size evaluation population without allowing evaluation membership to influence training through fitted/role-local evidence;
3. removes the current full-`size_development_complement` EVAL2 population and replaces it with one deterministic nested evaluation ladder paired to the exact `n1/n2/n3` screening fidelities;
4. removes the hard-coded eight-size target universe and replaces it with a canonical configurable power-of-two ladder;
5. preserves the exact target-size continuation funnel, paired-seed comparison, REPAIR2 nesting, MVQUAL hard qualification, EVAL2 metric semantics, and OPT-EVAL4 execution machinery where they remain valid;
6. performs a destructive current-generation reset rather than accumulating compatibility aliases, migration bridges, duplicate authorities, legacy selectors, stale terminology, or fallback paths;
7. leaves the repository in a simpler single-generation state whose documentation, configuration, persisted authority, runtime behavior, tests, and current terminology agree.

The stakeholder priority order is:

```text
scientific/product correctness
    > clean single-authority architecture
    > performance/resource efficiency
    > development convenience / compatibility with obsolete campaign state
```

### Protected scientific concerns

The implementation must preserve all of the following:

- target-size rungs remain nested prefixes of one authoritative repaired training order per required training domain;
- the target-size decision remains target-only development/model-selection evidence and does not consume held-out CV, calibration, locked-test, replay-score ranking, or downstream deployment evidence;
- target-size screening remains exact continuation `0 -> n1 -> n2 -> n3`, with paired optimizer seeds and no ordinary target-success early stopping during the screen;
- production starts fresh after `N_selected` freezes and retains its independent production epoch maximum;
- evaluation data never supply gradients or fold-checkpoint-monitor evidence for the target-size protocol being selected;
- cross-role correlation leakage is prohibited at the authoritative correlation-unit boundary rather than claimed away by naive frame spacing;
- DFT labels, foundation residuals, fitted transforms, and other role-local/fitted evidence cannot influence the initial training/evaluation allocation before that role boundary freezes;
- target training has first claim on unique or scarce edge/condition/event support;
- evaluation remains sufficiently representative to measure the relative benefit of target-size candidates rather than becoming only the redundant/easy complement;
- no runtime silently shrinks/expands the configured scientific ladders to make an undersized campaign proceed;
- configuration values that change scientific population identity participate in canonical policy/state identity.

## Engineering envelope and chosen architecture

### 1. Statistical allocation model: training-priority carve-out, not a percentage split

Let `U_d` be the current-generation eligible target development universe for label domain `d` after upstream raw-event detection, DATA5 correlation-unit construction, protected outer-role assignment, and all current eligibility constraints.

The architecture does **not** introduce a percentage-based random train/evaluation split. Instead, it introduces one deterministic training-priority carve-out before role-local fitted target selection:

```text
eligible target development universe U_d
        -> TRAIN-RESERVE pre-role coverage allocation
             -> training-reserved correlation units Treserve_d
             -> residual evaluation correlation units R_d
```

The training reserve exists to protect the maximum configured target-training ladder while giving training first claim on important physical support. `R_d` is the entire residual target-size evaluation reference population for the domain.

The carve-out is a role-allocation authority, not the final target-training order. The full current rich target-training chain runs only after this boundary freezes.

### 2. Correlation-unit-safe allocation, not unsupported IID thinning

DATA5 currently models autocorrelation through complete correlation/partition units. The new design SHALL preserve that evidence instead of claiming that arbitrarily spaced retained frames are mathematically independent.

Required invariant:

```text
if any correlation unit is allocated to target training,
no frame from that unit may enter target-size evaluation;
if a unit is allocated to target-size evaluation,
no frame from that unit may enter target-size training,
CV gradient training, or target-training checkpoint-monitor roles.
```

Protected event windows and stronger declared correlation families remain indivisible where their current policy requires it.

A simple frame-count condition such as `|U_d| >= Nmax + M3` is necessary but not sufficient. Feasibility must account for whole correlation units, support obligations, and role exclusions. The implementation must not manufacture apparent independence by taking one arbitrary frame from each existing DATA5 block unless a separately justified statistical policy explicitly defines that representation.

### 3. Training-priority reserve objective and admissible evidence

The TRAIN-RESERVE allocation runs **before** role-local fitted preparation and therefore may consume only partition-/role-safe evidence available without circular dependence on future training/evaluation roles, for example:

- DATA4 raw physical/geometry summaries;
- declared thermodynamic/chemical/strain/condition identities;
- raw pair-geometry families;
- partition-independent profile/environment classifications when available upstream;
- DATA4 event identities and protected event windows;
- structural/condition/provenance/correlation identities available without training-domain fitting;
- source/replica/run/correlation-family provenance.

TRAIN-RESERVE SHALL NOT consume as allocation inputs:

- training-domain foundation residuals or difficulty values;
- fitted DATA6/DATA7 transforms or metrics whose fit depends on the training role;
- role-local E0 fits;
- role-local target-normalization quantities;
- held-out/CV/locked evidence;
- any quantity whose current semantic owner is downstream of the role boundary.

Raw DFT-derived physical facts already owned by partition-independent DATA4 may remain available when they are genuinely upstream physical descriptors rather than evaluation statistics, but the implementation must not create a new target-label optimization loop that reads the future evaluation pool to tune training membership.

### 4. Training-first support policy

TRAIN-RESERVE must maximize training support subject to residual evaluation feasibility. The hierarchy is asymmetric by design:

1. unique admissible support belongs to training;
2. scarce support is allocated to training first;
3. where multiple independent/correlation-distinct representatives exist, the reserve must avoid exhausting every representative of an important condition/event/support stratum when doing so would make the residual evaluation population scientifically blind;
4. evaluation residual feasibility is a guardrail, not a second hard-coverage qualification equivalent to MVQUAL.

Suggested realization: an exact deterministic coverage/provenance selector that reuses/generalizes current multi-view sparse selection primitives while operating on pre-role-safe families and whole correlation-unit allocation state. Equivalent implementations are allowed if they preserve the frozen role boundary, support priority, determinism, and scientific semantics.

The reserve need not contain exactly `Nmax` raw frames if whole correlation-unit allocation makes exact raw cardinality impossible. It must contain enough eligible frames to materialize the configured `Nmax` training prefix after downstream domain-local selection, while minimizing unnecessary reserve growth under the whole-unit constraint. This distinction must be explicit in policy/evidence rather than hidden rounding.

### 5. Rich target-training chain after role freeze

After `Treserve_d` freezes, only its frames are candidates for target-training membership in that domain. The existing rich training chain remains the scientific membership authority and should be reused/refactored rather than duplicated:

```text
training-reserved frames
    -> role-local fitted selection inputs
    -> FEAS1
    -> MVIDX1
    -> MVSEL2
    -> REPAIR2 / MVSTATE2
    -> MVQUAL
    -> qualified target-size ladder
```

Current target-label families, foundation-residual weakness families, required hard coverage, obligations, representative utility, sparse diversity, correlation/provenance balancing, REPAIR2 active-shell repair, and independent MVQUAL remain training-domain semantics unless an implementation discovery proves a specific element obsolete under this reset.

The full maximum repaired prefix of length `Nmax` belongs entirely to the training reserve by construction. Evaluation membership cannot change when rich training evidence later reorders the reserve.

### 6. Target-size evaluation reference population and nested ladder

The residual population is:

```text
R_d = U_d \ Treserve_d
```

at the correlation-unit allocation level. It is the target-size **evaluation reference population**, not a gradient domain and not the legacy `size_development_complement` of each candidate prefix.

Run one deterministic evaluation coverage/order chain over `R_d` to publish one master evaluation order `pi_eval_d`.

Evaluation prefixes are:

```text
M1_d = pi_eval_d[:m1]
M2_d = pi_eval_d[:m2]
M3_d = pi_eval_d[:m3]
```

with strict nesting:

```text
M1_d subset M2_d subset M3_d subset R_d
```

The evaluation selector should reuse the exact sparse multi-view infrastructure/scoring kernels where semantically appropriate, but it is a distinct role policy:

- it is representative/model-selection coverage, not gradient-training hard qualification;
- it does not inherit training MVQUAL's `coverage_threshold=0.95` as a pass/fail requirement merely because the same kernel is reused;
- it does not inherit REPAIR2 active-shell hard-coverage repair unless separate evidence later shows an evaluation-specific repair is necessary;
- missing/unrepresentable evaluation strata are diagnostics/qualification evidence, not permission to steal unique support back from training at runtime;
- it may use role-local target labels/foundation residuals to order `R_d` **after** allocation freezes, because those quantities can no longer change training/evaluation membership.

One master order must own all three evaluation rungs. Independent M1/M2/M3 resampling is forbidden.

The unselected residual `R_d \ M3_d` remains useful as a larger retrospective/reference population for scientific qualification of the bounded ladder and must not be reclassified as training merely because ordinary production evaluates only M1/M2/M3.

### 7. Pair evaluation fidelity and cardinality explicitly

The target-size screen owns three immutable rung pairs:

```text
(n1, m1)
(n2, m2)
(n3, m3)
```

Default:

```text
fidelity epochs:      [1, 3, 10]
evaluation sizes:     [256, 512, 1024]
```

At one screening stage, all candidate sizes and all paired optimizer seeds use the exact same authenticated evaluation prefix for that domain/stage. Metrics are compared only within the same stage/rung population. No code may compare a candidate's M1 metric directly against another stage's M2/M3 metric as though the sample were unchanged.

EVAL2 retains its existing force-metric semantics and OPT-EVAL4 staged execution/resource machinery. This work changes target-size **population authority**, not the canonical force estimator itself.

### 8. Power-of-two target-size and evaluation configuration

Remove the hard-coded scientific target-size tuple and ceiling. Canonical user configuration shall express powers of two:

```toml
[target_data.size_convergence]
target_size_power_min = 7
target_size_power_max = 14
evaluation_size_powers = [8, 9, 10]
fidelity_epochs = [1, 3, 10]
```

The resolved policy derives:

```text
candidate_target_sizes = [2^p for p in target_size_power_min..target_size_power_max]
Nmax = 2^target_size_power_max
evaluation_sizes = [2^q for q in evaluation_size_powers]
```

Default remains behaviorally equivalent to the old numerical target ladder and proposed evaluation ladder:

```text
training candidates: 128,256,512,1024,2048,4096,8192,16384
evaluation:          256,512,1024
```

Required validation:

- powers are integers;
- `target_size_power_min < target_size_power_max` unless a future accepted single-rung policy is explicitly designed;
- the derived candidate ladder contains at least the minimum number of sizes required by the target-size funnel;
- `evaluation_size_powers` contains exactly three strictly increasing integer powers;
- derived sizes are positive and fit implementation integer/resource limits;
- no hidden `<=16384` scientific guard remains;
- no runtime dynamically invents non-power-of-two rescue sizes;
- the resolved canonical configuration persists both powers and human-readable derived sizes and includes semantically relevant values in policy/state identity.

The evaluation powers need not be consecutive. `[8,10,11]` is structurally valid if explicitly configured and scientifically qualified.

### 9. Configured ceiling semantics

Replace `fixed ceiling` terminology and outcomes with configured-ceiling semantics.

Required semantic replacement:

```text
FIXED_TARGET_SIZES                 -> policy-derived power-of-two ladder
FIXED_TARGET_SIZE_CEILING          -> configured Nmax
outside the fixed universe        -> outside configured target-size ladder
nonconverged_at_fixed_ceiling      -> nonconverged_at_configured_ceiling
fixed scientific ceiling 16384    -> configured scientific ceiling 2^pmax
```

A configured ceiling remains a real scientific boundary: if the largest configured candidate is materially superior under the final comparison rule, the typed result remains non-convergence at the configured ceiling. The implementation SHALL NOT synthesize a larger rescue size.

### 10. Cross-validation and role boundary

The evaluation residual must remain non-gradient for the complete target-size protocol. A frame/correlation unit assigned to `R_d` cannot later leak into:

- final-development target gradients;
- fold target gradients;
- fold checkpoint monitors used to select checkpoints;
- target-size online training monitor if that monitor's role would make the target-size evaluation evidence non-independent under the current protocol.

The exact domain construction must be reconciled so each required final/fold training domain is derived from target-training-authorized correlation units only. Held-out CV evidence remains held out as before.

The protocol-global selected cardinality remains common while actual target membership remains domain-local.

### 11. Capacity/preflight semantics

For each required label domain, preparation must establish **before expensive rich MVIDX/MVSEL/TRAIN2 execution** that the configured architecture is feasible.

At minimum it must prove:

- enough target-training-authorized capacity exists to materialize `Nmax` in every required target training domain;
- residual evaluation capacity exists for `M3` after whole-unit training-priority allocation;
- required training-support obligations remain satisfiable;
- residual evaluation support passes its weaker feasibility guard;
- role/correlation leakage invariants hold.

The arithmetic default lower bound `16384 + 1024 = 17408` frames is only a diagnostic lower bound. Whole-unit allocation, domain overlap, required supports, purge, protected events, and CV topology may require more raw frames.

Undersized campaigns fail early with a clear resolved-policy/capacity diagnostic. They do not silently lower `pmax`, lower `m3`, reuse correlated frames across roles, or fall back to the legacy full complement.

### 12. Current-generation persistence and compatibility

This is an intentional destructive generation reset.

Existing derived campaign/prepared state is deprecated and may be discarded. The implementation SHALL NOT add migration/compatibility code to preserve:

- old `TargetDataRoleFreeze` semantics based on `size_development`;
- old full-complement or coarse-complement EVAL2 roles;
- old fixed-eight target-size policy state;
- fixed-ceiling terminal-state serialization;
- old target-size study plans/evidence bound to prior population semantics;
- old REPAIR/MVQUAL/selection identities whose candidate universe or role boundary differs;
- old DATA7/DATA8 target candidate artifacts;
- old TRAIN2/EVAL2 target-size checkpoints/evidence;
- historical fixed-fidelity/flexible-fidelity candidate-authority bridges or compatibility receipts solely needed for superseded campaign generations.

Current raw/external source data may be reused as inputs. Current-generation derived state must be rebuilt under the new policy/role identities. Old current-workspace state should fail early with an actionable `pre-training-priority/evaluation-ladder generation; start/reprepare a new campaign workspace` style error rather than being silently reinterpreted.

Historical records under `docs/history/`, release history, archived workplans, or immutable published evidence may remain historical. They must be clearly non-normative and must not create executable compatibility obligations.

## Part 1 - Documentation and specification authority reset

Part 1 MUST complete and be reviewed before Part 2 implementation begins. Its purpose is to make the accepted architecture explicit enough that implementation does not infer semantics from obsolete code.

### D1. Rewrite the architecture manuals first

Update the current MLFF training-data architecture so the authoritative dependency graph becomes conceptually:

```text
source / DATA4 raw evidence / events
    -> DATA5 correlation units + protected outer roles
    -> training-priority target role allocation
         -> target-training reserve
         -> residual target-size evaluation reference population
    -> training-domain fitted preparation
         -> FEAS1 -> MVIDX1 -> MVSEL2 -> REPAIR2/MVSTATE2 -> MVQUAL
    -> configured target-size ladder
    -> evaluation reference coverage order -> M1/M2/M3
    -> exact paired (n1,m1) -> (n2,m2) -> (n3,m3) target-size screen
    -> selected protocol-global N
    -> fresh production/CV training
    -> held-out protocol validation / calibration / locked tests
```

At minimum reconcile:

- `docs/arch_manuals/mlff_training_data/30_statistical_design.md`;
- `docs/arch_manuals/mlff_training_data/50_target_multiview.md`;
- `docs/arch_manuals/mlff_training_data/80_ownership_and_decisions.md`;
- top-level `docs/arch_manuals/mlff_training_data_architecture.md` and its generated/include dependency surface where applicable;
- any current dependency graph/source map that presents the old role/selection/evaluation flow.

Required documentary outcomes:

- training-priority allocation and correlation-unit role exclusivity are explicit architecture;
- pre-role-safe versus role-local/fitted evidence boundary is explicit;
- training reserve versus final rich training order are distinct authorities;
- residual evaluation reference population and nested M1/M2/M3 ladder are explicit;
- target/evaluation powers and configured-ceiling semantics replace fixed-universe language;
- EVAL2 population ownership is separated from metric/execution ownership;
- CV/non-gradient implications are explicit;
- destructive generation reset/no compatibility is explicit;
- current architecture does not imply IID where only correlation-unit separation is proven.

### D2. Rewrite current normative specifications

Update/replace current normative specs whose contracts conflict, including at minimum:

- target-subset size-study specification;
- DATA5 partition/role specification if needed to expose the nested target-development allocation boundary;
- target-data role-freeze specification;
- target coverage / FEAS1 / MVIDX / MVSEL2 / REPAIR2 / MVQUAL specifications where candidate-domain ownership or fixed ladder assumptions change;
- EVAL2 target-size role specification;
- OPT-EVAL4 specification only where population identity/buffering assumptions reference full complement; preserve its execution semantics otherwise;
- campaign/configuration specification and generated example contract;
- persistence/restart/current-generation specification where old generation identities are removed.

Specifications must clearly distinguish:

```text
TRAIN-RESERVE role-allocation coverage
rich training hard coverage + MVQUAL
evaluation representative coverage
```

They are related mechanisms but not interchangeable pass/fail authorities.

### D3. Cleanse retired terminology from current documentation

Perform repository-wide inspection over **current normative/user documentation** and remove or rewrite current statements that imply any retired design, including:

- `fixed target-size universe` / `fixed nominal population` where used as current authority;
- `fixed ceiling` / `nonconverged_at_fixed_ceiling` as current terminology;
- hard-coded current scientific `16384` other than as an example/default derived from `pmax=14`;
- `size_development` where the new explicit target-training/evaluation roles supersede it;
- `size_development_complement` / `size_development_coarse` current evaluation semantics;
- candidate-prefix complement subtraction as the target-size evaluation population;
- any arbitrary train/evaluation percentage split introduced during intermediate design work;
- migration/compatibility language for campaign generations this reset intentionally discards;
- statements that every decorrelated retained point is IID/independent when the actual guarantee is correlation-unit-safe separation;
- old selector/repair generations presented as alternate current routes;
- stale current references to legacy fixed/flexible target-size authority generations.

Historical documents under `docs/history/`, archived workplans, release notes, and immutable historical evidence need not be rewritten to pretend history did not happen. They must remain clearly historical/non-current. Current architecture/spec/user docs must not point to them as executable authority.

### D4. Resolve active-workplan precedence

Update `workplans/active/README.md` and any conflicting active plan language so this workplan is the controlling authority for target-size **population, target/evaluation role allocation, evaluation ladder, configured powers, and generation reset**.

The existing exact-boundary screening workplan remains controlling for nonconflicting exact `n1/n2/n3` continuation behavior until its closure. Any sentence in it that freezes the candidate universe or old EVAL2 population is superseded by this reset and must be marked/reconciled so an implementer cannot satisfy two contradictory plans.

Unrelated active RAM/lifecycle/DATA7-8 plans remain independent unless implementation evidence shows a direct dependency.

### D5. Part 1 acceptance

Part 1 closes only when:

1. the architecture manuals tell one coherent current-generation story;
2. current normative specs agree with that architecture;
3. current user/config docs expose the new power-based configuration and evaluation ladder;
4. current terminology search finds no unexplained legacy fixed-universe/complement/current-migration language;
5. historical-only occurrences are confined to clearly historical/archive/release surfaces;
6. dependency/ownership diagrams identify the new role-allocation and evaluation-ladder owners;
7. no documentation claims unsupported statistical independence;
8. an independent design review can reconstruct Part 2 behavior from current documentation without consulting this conversation.

Part 1 is documentary/non-executable. It requires documentation build/lint/reference checks applicable to the repository but does not substitute for Part 2 executable regression.

## Part 2 - Code implementation and destructive cleanup

Part 2 implements the documented architecture. The implementer must prefer ownership correction, reuse/refactoring, and deletion over wrappers/adapters that preserve superseded semantics.

### C1. Canonical power-based target-size/evaluation policy

Replace the fixed candidate-size tuple with one canonical configuration/policy owner.

Required end state:

- canonical configured fields: `target_size_power_min`, `target_size_power_max`, `evaluation_size_powers`, `fidelity_epochs`;
- canonical derived values: candidate target sizes, `Nmax`, evaluation sizes, rung pairs;
- `TargetSizeStudyPolicy` or its clean successor owns the derived scientific ladder, screening funnel, equivalence rules, and authenticated seed set without a hard-coded 16384 guard;
- all consumers use the canonical resolved policy rather than recomputing powers independently;
- policy serialization/digest includes semantically relevant powers/derived rung mapping;
- configuration/example/status output reports both powers and resolved integer sizes;
- terminal state is `nonconverged_at_configured_ceiling`;
- remove obsolete fixed-generation candidate-authority compatibility helpers if no longer used by any current path.

Structural acceptance must prove `FIXED_TARGET_SIZES`, `FIXED_TARGET_SIZE_CEILING`, executable `<=16384` scientific guards, and current fixed-universe error text are absent from the current code path.

### C2. Introduce correlation-unit-safe target role allocation before fitted selection

Create one current authoritative target-development allocation record/policy (names may differ if a cleaner existing owner is extended) that publishes per label domain:

- source eligible/correlation-unit identity;
- target-training-reserved units/frames;
- target-size-evaluation residual units/frames;
- support/coverage diagnostics;
- residual evaluation feasibility diagnostics;
- exact policy/config identity;
- proof of disjointness and correlation-unit exclusivity.

Required behavior:

- allocation runs before role-local fitted target preparation;
- allocation inputs are limited to approved pre-role-safe evidence;
- training has first claim on unique/scarce support;
- residual evaluation receives correlation-distinct remaining support where possible;
- enough training capacity for `Nmax` is guaranteed before proceeding;
- enough residual capacity for `M3` is guaranteed before proceeding;
- role assignment is deterministic/restartable;
- changing allocation/power policy invalidates dependent derived state;
- no percentage/random split authority is introduced.

If current DATA5 ownership is the cleanest place for the nested allocation, extend it there; if a dedicated TARGET-DATA authority is cleaner, keep DATA5 outer-role ownership and make the new authority consume DATA5. Do not create two synchronized owners.

### C3. Reconcile CV and fitted-domain construction to the new roles

Modify final-development/CV domain construction so target-training fitted products and target gradients can consume only target-training-authorized correlation units.

Required negative invariants:

- evaluation residual units never enter final target gradients;
- evaluation residual units never enter fold target gradients;
- evaluation residual units never enter a checkpoint-monitor role that would invalidate target-size evaluation independence;
- held-out CV folds remain held out and are not repurposed as the new evaluation ladder;
- calibration/locked-test roles remain unchanged and cannot become target-size evaluation data.

Extend leakage audit to fail closed on any prohibited crossing.

### C4. Make coverage/MVIDX machinery role-generic where reuse is justified

Refactor current target coverage/reference/index primitives enough to support:

1. TRAIN-RESERVE pre-role-safe allocation coverage;
2. rich training-domain FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL;
3. residual evaluation representative coverage/order.

Do not copy the current coverage implementation three times. Shared exact geometric/sparse primitives should have one semantic implementation where the mathematical relation is the same, with explicit role policies controlling which feature families, hard predicates, obligations, and scoring phases apply.

Preserve a bounded independent/reference oracle for optimized selector kernels where one already exists or is materially useful.

Anti-shortcut: do not route the new evaluation path through legacy `TrainingSelectionPlan` quota/FPS selection merely because it already accepts arbitrary cardinalities. Current architecture has one multi-view family; semantic reuse must be through that current mechanism or a justified generalized successor.

### C5. Preserve rich training chain inside the reserve

Update FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL candidate/reference ownership to the target-training reserve and configured target-size ladder.

Required behavior:

- one master repaired order per required training domain;
- configured target-size rungs are prefix views;
- hard-coverage monotonicity remains enforced;
- MVQUAL evaluates all configured materializable prefixes needed by the policy;
- no hidden eight-rung loops/arrays/tests remain;
- configured ladders smaller/larger than the default work subject to actual feasibility/resource limits;
- candidate data identities bind the new training-role/allocation authority.

Preserve current exact scientific selector/repair semantics unless the new role boundary makes a specific predicate invalid; such a discovery is a bounded design-reopen trigger, not permission to silently weaken qualification.

### C6. Implement the residual evaluation master order and M1/M2/M3 artifacts

Create the current evaluation-ladder authority over `R_d`.

Required end state:

- one deterministic `pi_eval_d` per required evaluation domain;
- `M1/M2/M3` are exact prefixes at configured evaluation sizes;
- all ladder frames belong to the residual evaluation role and no training frame appears;
- nested UID identity is explicitly validated;
- evaluation-order policy/feature/reference identities are persisted and digest-bound;
- rich evaluation-local target labels/foundation residuals may influence ordering only after the role allocation is frozen;
- evaluation hard-coverage deficits/support holes are recorded diagnostically;
- no automatic fallback to full complement or arbitrary temporal sampling.

Suggested materialization: three authenticated bounded ExtXYZ/monitor artifacts for M1/M2/M3, even if M1/M2 bytes duplicate prefixes of M3. Simplicity of restart/parsing/identity is preferred unless measurement shows material I/O/storage harm. Membership identity, not duplicated bytes, proves nesting.

### C7. Rebind EVAL2 to stage-specific evaluation rungs

Delete current target-size semantics based on:

- `build_eval2_size_study_target_role()` full complement subtraction;
- `size_development_complement`;
- `size_development_coarse` legacy helper behavior;
- maximum-training-prefix subtraction as evaluation role definition;
- legacy deterministic block-sampler compatibility used only for old target-size generations.

The target-size owner shall resolve:

```text
coarse       -> M1
short        -> M2
final_screen -> M3
```

for every candidate and paired seed.

Preserve:

- canonical EVAL2 target-force metric definition;
- exact candidate/checkpoint/foundation identity checks;
- OPT-EVAL4 CPU-prepare -> accelerator-inference -> CPU-finalize -> parent-commit pipeline;
- resource admission/RAM/VRAM/parallelism machinery unless a direct incompatibility is found;
- same-rung paired-candidate comparison semantics.

Evaluation evidence must bind the evaluation-ladder authority/rung digest, not merely a generic role name.

### C8. Reconcile target-size study evidence and orchestration

Update target-size study/evidence schemas so each stage authenticates its exact `(n_i,m_i)` rung and evaluation population.

Required behavior:

- exact `n1/n2/n3` continuation remains unchanged;
- `q -> min(q,4) -> 2 -> 1` remains unchanged unless the configured ladder has fewer than required qualified sizes, which remains a typed insufficiency;
- paired seeds remain complete and ordered;
- successful candidates within one stage share one evaluation-rung identity;
- cross-rung metric mixing fails closed;
- selected `N` is always one configured target-size power-of-two rung;
- configured-ceiling nonconvergence is typed and authenticated;
- status/reporting prints active training boundary and active evaluation cardinality clearly.

### C9. Current-generation invalidation and legacy deletion

Perform a deliberate cleanup sweep after the new path works.

Delete or retire from current execution any code whose sole purpose is a superseded design, including as applicable:

- fixed target-size constants/guards;
- old candidate-authority migration/bridge/receipt code;
- old fixed/flexible target-size generation aliases no longer needed for current state;
- full-complement/coarse-complement EVAL2 helpers;
- deprecated `size_development` current role fields if the new explicit roles supersede them;
- stale serializer branches for unsupported current campaign generations;
- tests that only prove deprecated behavior;
- duplicate selectors/wrappers introduced by earlier revisions and no longer referenced by current code.

Do not retain dead compatibility code merely because deletion is inconvenient. Historical evidence readers may remain only where independently required to inspect durable historical records and must be isolated from current execution.

Structural acceptance requires repository-wide import/reference/search evidence that removed current authorities have no reachable production consumer.

### C10. Configuration, state identity, persistence, and restart

All scientific policy fields introduced by this reset must participate in canonical resolved configuration and state identity where they affect membership/evaluation meaning.

At minimum identity must prevent unsafe reuse when changing:

- target-size min/max powers;
- evaluation size powers;
- fidelity epochs;
- TRAIN-RESERVE allocation policy/feature contract;
- evaluation selection policy/feature contract;
- correlation-unit source identity;
- relevant target coverage policies.

Restart tests must cover:

- same config -> deterministic same allocation/orders/digests;
- changed powers/allocation/evaluation policy -> affected state invalidates;
- irrelevant execution-only worker/chunk/cache changes -> scientific identities remain stable where mathematically unchanged;
- pre-reset campaign state -> clear unsupported-generation failure rather than migration.

### C11. Performance/resource preservation

Reuse current performance architecture:

- exact sparse forward MVIDX representation;
- memory mapping/out-of-core support;
- current optimized MVSEL2 forward/lazy scoring;
- bounded evaluation preparation/finalization buffers;
- current inference admission/concurrency machinery;
- graph/context reuse where the new nested evaluation population permits it.

The new evaluation ladder should materially reduce inference compared with full-complement EVAL2. For the default eight qualified sizes and two seeds, the ordinary upper funnel workload is bounded by:

```text
8*2*256 + 4*2*512 + 2*2*1024 = 12,288 evaluated configurations
```

before accounting for batching/cache reuse. This is a design-scale diagnostic, not a substitute for measured qualification.

Do not weaken selector exactness, coverage semantics, or role separation to optimize performance.

## Implementation authority

### Frozen

The implementer MUST preserve:

- training-priority role allocation before fitted target selection;
- correlation-unit-safe train/evaluation separation;
- no percentage/random split as current scientific authority;
- pre-role-safe evidence only for allocation;
- rich training selection inside the training reserve;
- residual evaluation reference population and one nested evaluation master order;
- exactly three configured evaluation rungs paired one-to-one with `n1/n2/n3`;
- power-of-two configured target ladder using min/max exponents;
- default powers `7..14` and evaluation powers `[8,9,10]` unless current config-generation ownership requires an equivalent canonical spelling;
- configured-ceiling nonconvergence semantics;
- no dynamic rescue sizes;
- destructive generation reset/no compatibility migration for old derived campaign state;
- reuse of EVAL2 metric and OPT-EVAL4 execution semantics;
- preservation of exact screening continuation and fresh post-selection production;
- target/evaluation role exclusion from gradients and prohibited CV monitor use;
- stage-local and final regression/integration requirements;
- full long real-data/GPU production qualification remains separate and deferred to the established final qualification phase unless specifically requested later.

### Delegated

Implementation may choose, while preserving the frozen contract:

- exact class/module/schema names for TRAIN-RESERVE and evaluation-ladder authority;
- whether nested target allocation is physically owned inside DATA5 or by a dedicated immediate consumer, provided there is one authority and DATA5 outer roles remain coherent;
- internal sparse data structures and generalized selector interfaces;
- exact pre-role-safe coverage weighting/tie implementation consistent with the documented deterministic training-priority objective;
- whether M1/M2/M3 are materialized as three artifacts or one indexed artifact if restart clarity and bounded I/O remain equivalent;
- local schema version numbers and error-code names;
- test fixture sizes and faked expensive numerical layers below the semantic owners.

### Reopen only on evidence

Reopen the affected design surface only if implementation/representative evidence proves one of these assumptions false:

1. whole correlation-unit allocation cannot preserve enough training capacity without pathological reserve inflation;
2. the documented pre-role-safe feature set is insufficient to protect training edge support, requiring a different leakage-safe upstream descriptor authority;
3. residual evaluation support is systematically too biased after training priority to preserve target-size decisions at practical `m1/m2/m3`;
4. exact reuse/generalization of current multi-view kernels would materially increase complexity or change semantics compared with a cleaner mathematically equivalent component;
5. a configured target-size ladder beyond the old 16384 exposes an unanticipated algorithm/resource bound that cannot be addressed cleanly;
6. current CV topology makes one global residual role impossible without a better per-domain correlation-safe formulation;
7. retrospective scientific qualification shows `[256,512,1024]` fails required survivor/winner preservation.

Do not reopen unrelated exact-boundary, production-freshness, or held-out evidence doctrine when only one of these local assumptions fails.

## Initially expected affected surface

The implementer must re-derive this list from the assembled candidate; initially expected surfaces include:

### Core code

- `mdstats/training_data/partition.py` and/or immediate target-role allocation owner;
- `mdstats/training_data/target_data_roles.py`;
- `mdstats/training_data/leakage.py`;
- target coverage/reference/feasibility/index modules;
- `target_multi_view_selector_v2.py`, current selection engine/state, REPAIR2, MVQUAL2 where policy/domain inputs change;
- `target_size_study.py`;
- `eval2.py`;
- `_campaign_cli_core.py` target-size orchestration/config/state/reporting;
- DATA7/DATA8 materialization/planning owners;
- CV/final-domain assembly and checkpoint-monitor role ownership;
- configuration parsing/resolution and generated examples;
- serializers/current-state reconciliation and package exports.

### Tests

At minimum inspect/reconcile:

- DATA5 partition/leakage tests;
- target role-freeze tests;
- coverage/FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL tests;
- target-size study/flexible-fidelity/topology tests;
- EVAL2 tests;
- OPT-EVAL4 staged-evaluation tests;
- campaign CLI/state/restart/preflight tests;
- CV lifecycle/materialization tests;
- configuration/default/digest tests;
- performance/reference-equivalence tests where generalized kernels are changed.

### Documentation

Part 1 surfaces plus campaign examples, README/user guides, dependency graphs, current release/current architecture references, generated PDF/documentation inputs as required by repository policy.

## Part 2 stage sequence and required acceptance

### Gate C-A - Power policy + role-allocation primitives

Implement canonical power configuration, configured-ceiling semantics, target role allocation record/policy, whole-correlation-unit disjointness, and early feasibility.

Focused tests:

- default/nondefault power resolution;
- exact derived ladders;
- invalid power combinations;
- no hidden 16384 ceiling;
- deterministic allocation;
- unique/scarce training priority;
- residual support guard;
- whole-unit train/eval disjointness;
- insufficient-capacity fail-closed behavior.

Stage-local affected regression: configuration, partition/role, current state identity, target-data role freeze/leakage.

### Gate C-B - Training-chain domain reconciliation

Route fitted preparation/FEAS1/MVIDX/MVSEL2/REPAIR2/MVQUAL through target-training-authorized domains and configured ladders.

Focused tests:

- default ladder exact equivalence where semantics intentionally match old default training order on a fully training-authorized fixture;
- nondefault smaller/larger power ladders;
- one master order/nested prefixes;
- MVQUAL monotonicity and configured-prefix population;
- no residual evaluation UID in training inputs;
- CV/final training domain role exclusion.

Stage-local regression: all affected DATA6/7, coverage, selector, repair, MVQUAL, DATA7/8, CV domain tests.

### Gate C-C - Evaluation master order and nested ladder

Implement role-local residual evaluation coverage/order and M1/M2/M3 publication.

Focused tests:

- deterministic master order;
- strict M1 subset M2 subset M3;
- exact configured cardinalities;
- all UIDs belong to residual role;
- training unique support remains excluded;
- diagnostic behavior when an evaluation stratum is unrepresentable;
- evaluation-local rich features cannot mutate role allocation.

Stage-local regression: generalized coverage/index/selector primitives and evaluation role/materialization tests.

### Gate C-D - EVAL2 and target-size rung integration

Rebind real `select-target-size` orchestration to `(n1,M1)`, `(n2,M2)`, `(n3,M3)`.

Acceptance boundary must exercise the real owner path:

```text
resolved TOML/config
 -> current campaign state/reconciliation
 -> target role-allocation authority
 -> target-training study authority
 -> evaluation-ladder authority
 -> select-target-size stage resolver
 -> TRAIN2 boundary continuation
 -> EVAL2 role resolution
 -> OPT-EVAL4 execution owner
 -> target-size reducer
 -> next-stage survivor authorization
 -> selected-size/configured-ceiling terminal state
```

Allowed doubles are below the owner boundary: expensive MACE numerical stepping/GPU inference may be bounded/faked after real runtime/evaluation role assembly. Do not patch/reimplement the stage resolver, role authority, reducer, or selected-size transition in tests intended to prove orchestration.

Required integration cases:

1. default `[1,3,10]` + powers `7..14` + eval `[8,9,10]`;
2. nondefault fidelity and nondefault evaluation powers;
3. changed target `pmax`/`pmin`;
4. configured-ceiling nonconvergence;
5. insufficient residual M3 capacity;
6. pre-reset workspace rejection;
7. restart at each screen boundary preserves exact rung identity;
8. no eliminated candidate receives later training/evaluation;
9. no full-complement EVAL2 fallback executes.

Stage-local regression: target-size study, campaign CLI, scheduler, persistence/restart, EVAL2, OPT-EVAL4, DATA7/8 consumers.

### Gate C-E - Destructive legacy cleanup

After new assembled path passes, remove superseded code/tests/current terminology rather than keeping parallel implementations.

Required structural checks:

- no reachable current `FIXED_TARGET_SIZES`/fixed-ceiling authority;
- no current `size_development_complement`/coarse-complement runtime role;
- no obsolete target-size migration bridge/receipt reachable from current state loading;
- no second target membership selector on the production path;
- no stale eight-rung-only loop or static current tuple hidden outside the canonical resolver;
- no deprecated compatibility alias in current config that would silently reinterpret old scientific semantics;
- no current doc/spec claims the retired architecture.

Run focused deletion/import/package tests plus stage-local affected regression after cleanup because deletion can expose hidden dependencies.

### Gate C-F - Final assembled acceptance

After all executable changes:

1. reconcile every frozen obligation against source/current documentation;
2. re-derive the complete affected surface from the final diff and dependency/ownership graph;
3. run the complete affected regression suite;
4. run assembled integration through real target-size CLI/state owners with bounded numerical fakes only below accepted owner boundaries;
5. run repository-required broader/full tests when impact cannot be confidently bounded;
6. rebuild/check affected documentation/PDF outputs per repository policy;
7. perform structural legacy-absence/authority-uniqueness inspection;
8. run bounded deterministic performance/reference-equivalence checks for generalized selection/index paths;
9. run retrospective scientific qualification described below on available representative historical/bounded evidence when feasible without a full target-machine production campaign.

Newly introduced or plausibly affected failures block closure. Pre-existing unrelated failures may be documented only after proving they are unrelated.

## Scientific qualification obligations

Because this work changes evaluation sampling/population semantics, ordinary unit/regression tests are necessary but not sufficient to establish the scientific approximation.

Use completed/bounded checkpoint evidence where available to compare the nested evaluation ladder against a larger residual reference/oracle population.

Qualification must assess the **target-size decision**, not demand that a 256-point metric numerically equal a full-residual metric.

Required claims:

1. M1 coarse screen does not falsely eliminate an eventual competitive/finalist size on qualification cases;
2. M2 preserves the reference finalist population;
3. M3 selects the same target size as the larger residual reference under the configured practical-equivalence/smaller-size rule;
4. same-size nested coverage/support diagnostics improve monotonically where the metric mathematically implies monotonicity;
5. M1/M2/M3 representative coverage is materially better than naive temporal/uniform same-cardinality baselines on declared important strata;
6. training reserve retains/qualifies required rich training coverage after evaluation is carved out;
7. correlation-unit leakage audit remains clean;
8. deterministic rerun/restart/worker-count/cache realization preserves scientific identities/results;
9. the assembled real target-size path consumes exact M_i at exact n_i;
10. bounded timing/inference-count evidence confirms the expected reduction versus full-complement evaluation.

If `[256,512,1024]` fails decision preservation, revise the affected evaluation powers/cardinalities explicitly and requalify. Do not silently expand evaluation at runtime.

Full long real-data GPU/resource production qualification remains separate and deferred to the established final GPU/release qualification process. CPU/bounded functional tests cannot claim GPU qualification.

## Anti-shortcut and cleanup constraints

The following are explicitly forbidden:

- retaining the old complement evaluator behind a fallback flag;
- accepting both fixed-size tuples and power-based policy as equal current authorities;
- silently mapping legacy config keys to materially new semantics in this destructive generation;
- creating a compatibility migration solely so old campaign state continues;
- running the full rich training selector over the future evaluation role before allocation freezes;
- using held-out CV to choose the target size;
- treating one arbitrary frame per DATA5 block as proven IID without a defined/statistically justified policy;
- satisfying tests by weakening MVQUAL, evaluation-ladder disjointness, configured cardinalities, or practical-equivalence rules;
- implementing evaluation M1/M2/M3 as independently sampled datasets;
- copying current multi-view code into parallel train/eval implementations when one generalized mathematical kernel suffices;
- preserving dead selector/repair/migration code because archived tests reference it; update/delete obsolete tests instead;
- adding a new target role while leaving `size_development` as an equally authoritative current role;
- letting execution worker counts, batch sizes, cache state, RAM/VRAM admission, or parallel scheduling alter scientific membership/order.

## Handoff closure

This plan intentionally changes current architecture documented at reviewed head `6f0d34366ca954eabe21740ddda96357afc12eb1`, where the target-size population is fixed at eight powers through 16384 and EVAL2 still exposes `size_development_complement` behavior.

The handoff is closed as follows:

```text
stakeholder requirement:
  training coverage priority + bounded nested evaluation + configurable base-2 ladders

protected concerns:
  scientific role separation, correlation leakage, exact screening,
  rich training coverage, representative evaluation, clean single generation

accepted architecture:
  pre-role training-priority correlation-unit carve-out
  -> rich training order inside reserve
  -> residual evaluation reference/order
  -> nested M1/M2/M3 paired with n1/n2/n3
  -> configured power-of-two target ladder

known cross-module consequences:
  DATA5/role freeze/CV -> coverage/MVIDX/select/repair/MVQUAL
  -> target-size policy/state -> EVAL2/OPT-EVAL4 -> CLI/restart/config/docs/tests

implementation obligations:
  Parts 1 and 2 / Gates D1-D5 + C-A-C-F

acceptance:
  documentation authority reset + structural legacy deletion
  + stage-local affected regression
  + final affected regression/integration
  + bounded scientific decision-preservation qualification
```

No material discussed design decision is intentionally delegated back to implementation discovery. Implementation may refine local mechanics, but any material change to the frozen training-priority role boundary, evaluation-ladder semantics, power-based target universe, or destructive compatibility policy requires a bounded Software Design reopen.
