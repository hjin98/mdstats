---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 3
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
entry_p5_workplan_revision: 11
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
reconciliation_reason: Revision 3 closes the remaining Design-review gaps in revision 2 without reopening P1-P5 or the frozen parent. It forbids semantic compatibility reading/migration of retired V5/V6 target-size derived state except for minimal reject-only generation detection; preserves validation-only reference oracles and benchmarks when they independently validate retained current implementations; restores the frozen parent's explicit restart/invalidation matrix; makes real production CLI parsing/dispatch mandatory in assembled acceptance; preserves accepted scheduling/cache/checkpoint/accelerator/resource owners; narrows design-reopen conditions so ordinary incomplete cutover remains implementation reconciliation; and restores explicit documentation/PDF and three-way final qualification reporting requirements.
---

# P6 revision 3 — destructive cleanup and assembled final closure

## 0. Authority, accepted baseline, scope, and precedence

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict for the target-size reset. P6 translates the parent's final destructive-cleanup and closure obligations onto the accepted P1-P5 implementation. It does not supersede or reinterpret the parent.

P6 is bound to **Protocol 5.8.0**. Do not silently reinterpret this package under a later protocol version.

The exact accepted implementation baseline for P6 is:

```text
1670275487d29bbcde4c59efafdef9d1f8b0ced7  P5A6
```

with tree:

```text
17e2c5609974712bda1efd3375f09f42da830f68
```

P6 is a **destructive cleanup plus final assembled-closure package**. It is not permission to redesign accepted P1-P5 science, alter selected-set semantics, weaken persistence/currentness/restart checks, revive compatibility-domain target-size topology, add migration fallbacks for retired derived state, or replace real semantic owners with proxies merely to make cleanup easier.

If branch HEAD changes before P6 implementation begins, implementation must reconcile the intervening diff against this package before destructive edits. A local change that still satisfies the frozen architecture is implementation reconciliation. Reopen Design only under Section 11.

Full production-scale/long target-machine GPU qualification remains deferred to the established final-release phase. P6 closure requires bounded CPU-safe functional, regression, integration, determinism, reference-equivalence, persistence/restart, and resource-lifecycle evidence. It must not counterfeit production-scale GPU qualification from bounded tests.

---

## 1. Frozen assembled product state P6 must preserve

### 1.1 Parent scientific lifecycle

The current assembled lifecycle remains:

```text
precise provenance / canonical numerical-label identity
 -> neutral current statistical/correlation substrate
 -> one P_train / M3 target-size development split
 -> one canonical pi_train
 -> one canonical pi_eval / M1 subset M2 subset M3 ladder
 -> paired optimizer-seed target-size screen
 -> one current P4 reducer
 -> N_selected
 -> T_selected = pi_train[:N_selected]
 -> post-selection CV on exact T_selected
 -> fresh final production on exact full T_selected
 -> current publication/restart-authenticated downstream state
```

Preserve all of the following:

- electronic-structure provenance is precise descriptive/advisory evidence and does not recreate compatibility-domain numerical branching;
- canonical numerical label identity is separate from provenance grouping;
- the neutral pre-target substrate has no compatibility-domain partition axis and no pre-target-size CV authority;
- one deterministic common target-size preparation is shared across candidate sizes and optimizer seeds;
- only the ordered optimizer-seed set is the target-size stochastic replicate dimension;
- current default/current-policy screen uses the same ordered two seeds `[1, 2]` for every `N` unless a future accepted policy changes it;
- exact `n1 -> n2 -> n3` continuation/restart and exact `M_i` evaluation semantics remain intact;
- target-side metric/practical-equivalence policy alone owns target-size ranking, with smaller `N` preferred inside practical equivalence;
- replay/CV/physical/deployment evidence cannot rank or tie-break target size;
- configured-ceiling nonconvergence remains typed rather than inventing a rescue size;
- post-selection CV cannot feed back into target-size selection;
- final production is fresh, uses full exact `T_selected`, fresh optimizer/RNG/run state, and `[training].max_num_epochs` as its independent production horizon authority.

### 1.2 Destructive current-generation rule

P6 completes the destructive current-generation cutover.

- Valid current P1-P5 state created by the accepted V7 generation must remain reloadable and restart-authenticatable.
- Retired V5/V6 **derived target-size** state is not migrated, semantically read forward, reconstructed, or rebound into V7.
- Obsolete target-size state may be recognized only enough to reject it with actionable reset/reprepare guidance before any candidate/checkpoint/derived target-size reuse.
- Raw scientific inputs and independently valid low-level content/recipe caches may still be reused when their recipes are genuinely independent of retired target-size/domain semantics.
- Historical documentation/evidence may remain clearly historical, but it must not appear in current package exports, current source maps, current configuration examples, or current architecture documentation as supported authority.

### 1.3 No mixed current architecture

After P6, the current runtime must not expose a hidden dual architecture:

```text
V7 current owner -> direct current implementation
```

Forbidden:

- V7-or-V5 runtime feature flags;
- try-V7/fallback-V5;
- V7 objects rebuilt from retired per-domain target-size maps;
- writing both old and new target-size authoritative records;
- compatibility aliases that reinterpret V5/V6 target-size schemas as V7;
- keeping obsolete CV/domain requirements solely to preserve old tests;
- wrapping `TargetDataRoleFreeze`, FEAS/MVIDX/MVSEL/REPAIR/MVQUAL, old complement EVAL2 roles, or old per-domain materialization and presenting them as the V7 scientific owner.

---

## 2. P6-A — mandatory P5A6 census and disposition before destructive deletion

### 2.1 Census surface

Before destructive executable edits, inspect the exact P5A6 tree and enumerate every material legacy-looking or current-mixed surface across:

1. Python modules/classes/functions/constants/enums/schema/version identifiers;
2. `mdstats.training_data`, top-level package imports, and automatically generated `__all__` surfaces;
3. CLI commands/options, configuration keys/defaults, parser branches, help text and examples;
4. CampaignStore/SQLite fields, serializers/deserializers, payload schemas, receipt/manifest keys, current pointers, restart/reopen and reconstruction paths;
5. filesystem path/layout helpers, cleanup/retention owners, caches/checkpoints and promotion/publication helpers;
6. P1-P5 production call edges and dependency imports;
7. tests, fixtures, golden payloads, benchmarks, reference implementations and helper factories;
8. current architecture/specification/source-map/user documentation and generated-documentation inputs.

At minimum search for materially equivalent instances of:

```text
TargetDataRoleFreeze / TargetDataDomainRoleFreeze
FEAS1
MVIDX1
MVSEL2
REPAIR2
MVSTATE2
MVQUAL / MVQUAL2
FIXED_TARGET_SIZES / fixed target-size ceiling authority
domain_prefix_digests
per-domain target-size candidate/materializability/qualification maps
size_development_complement / size_development_coarse
prescribed_final_development_prefixes
prescribed_training_domain_prefixes
prescribed_target_size_evaluation_frames
preselection cross_validation_plans used by target size
old DATA5/MLCV target-size coupling
V5/V6 target-size prepare contract / receipt / migration aliases
legacy target-size reconstruction helpers
compatibility-domain training eligibility/fanout used as current authority
label_domain_id participating in current numerical-label/partition/target-size identity
```

This is a minimum search set, not a ceiling. Add discovered aliases and equivalent schemas to the census.

### 2.2 Required disposition classes

Every material legacy-looking surface receives exactly one disposition before refactor/deletion:

| Class | Meaning | Required action |
|---|---|---|
| R1 | retired current scientific/authorization/runtime authority | remove current call edge/implementation as applicable and unexport |
| R2 | current V7/shared neutral implementation | retain under canonical current owner |
| R3 | mixed legacy + current/shared implementation | cut current/shared responsibility to canonical owner first, prove it, then remove retired authority |
| R4 | advisory/diagnostic compatibility/provenance helper | retain only if observational and unable to authorize selection/training/CV/final/current publication |
| R5 | current-generation or independently supported **non-target-size** compatibility reader | retain read-only/non-authoritative under explicit supported contract; no promotion/reconstruction into current authority |
| R6 | independently supported product feature outside target-size V7 | preserve its independent product contract |
| R7 | historical-only source/evidence/docs | retain only in clearly historical/archive context, never current runtime/API/docs |
| R8 | validation-only reference/oracle/benchmark for a retained current implementation | retain outside production authority when it provides material independent equivalence/performance evidence |

For every retained R2-R6/R8 item, implementation evidence must record the concrete current/independent purpose. “An old test imports it” is not a supported purpose.

### 2.3 Hard R5 exclusion for retired target-size state

R5 **must not** be used to preserve semantic readers/migrators for retired V5/V6 target-size derived state.

The following are R1/R7, not R5, unless the frozen parent is explicitly reopened:

- V5/V6 target-size candidate/state/qualification plans;
- old target-size prepare contracts/receipts;
- FEAS/MVIDX/MVSEL/REPAIR/MVSTATE/MVQUAL persisted semantic readers;
- per-domain target-size derived maps/prefix/evaluation records;
- migration adapters that turn retired target-size state into current V7 objects;
- reconstruction helpers that infer current V7 target-size authority from old payload shape.

A **minimal reject-only generation detector** may remain if needed to identify an obsolete workspace and emit actionable reset/reprepare guidance. Such a detector may inspect only enough metadata/header/version information to determine that the workspace is obsolete. It must reject **before** semantic deserialization, candidate/checkpoint reuse, or descendant reconstruction.

Acceptance must prove both:

1. an old target-size workspace is rejected before any target-size candidate/checkpoint/derived-state reuse; and
2. no retired target-size migration/receipt/current semantic reader remains publicly exposed as supported current API.

### 2.4 R8 validation-only retention rule

A current optimized implementation may legitimately retain a simple/reference/oracle path or benchmark even when no production runtime caller invokes that validation artifact.

R8 is valid only when:

- the implementation under test is R2/R3/R6 and remains current/supported;
- the oracle/reference is independent enough to detect implementation drift rather than reproducing the same algorithmic defect;
- the benchmark/equivalence harness exercises the **current** implementation and current scientific semantics;
- it does not itself become current scientific authority or runtime state;
- its maintenance cost is justified by material correctness/performance assurance.

A benchmark whose central contract is to reopen persisted V5/V6 target-size authorities and execute fixed old topology is **not** R8. For example, an MVQUAL/M5 benchmark that explicitly reopens V5 state and exercises fixed-eight MVQUAL2 is obsolete and must be deleted, archived as history, or rewritten to benchmark a retained current V7 kernel through a current/reference boundary.

### 2.5 Cutover-before-delete rule

For any R3 surface:

1. identify the legitimate current/shared responsibility;
2. move it to or route it through the canonical current/neutral owner without changing accepted science;
3. update all current callers;
4. run focused semantic tests through the new owner;
5. run stage-local affected regression for the cutover;
6. only then remove the retired legacy authority/module/export.

Do not delete shared machinery because its filename is old. Do not preserve a dead wrapper solely to keep old tests green.

### 2.6 P6-A closure

P6-A closes when the census/disposition is complete enough that every destructive edit has an explicit semantic reason and every retention has an explicit current/independent purpose.

P6-A is reconciliation unless it changes executable code. Any executable R3 cutover performed during the census must close with focused checks plus stage-local affected regression before dependent deletion continues.

---

## 3. Protected P1-P5 owners and implementation machinery

These task-local preservation requirements are normative in P6. Implementation must not need historical chat/review context to recover them.

### 3.1 P1/P2 substrate and protected relations

Preserve:

- canonical current frame/source/numerical-label/provenance identities;
- precise provenance separated from canonical numerical label identity;
- duplicate/correlation/protected-relation evidence used by the accepted neutral substrate;
- canonical P1 split-exclusion/protected-relation authority consumed by later CV;
- absence of compatibility-domain partitioning from current target-size science;
- mechanically unusable labels still failing cleanly while heterogeneous but canonicalizable provenance remains usable.

Generic partition/identity machinery with an independent current purpose is not deletable merely because old target-size topology once used it.

### 3.2 P3 target-size science and execution

Preserve:

- one current `P_train/M3` target-size split;
- one canonical `pi_train` and exact prefixes `T_N = pi_train[:N]`;
- one canonical `pi_eval` with exact nested `M1 subset M2 subset M3`;
- one target-size scheduler/execution authority;
- same ordered optimizer seeds at every `N`;
- one common deterministic preparation identity across `N` and optimizer seed;
- exact continuation of model/optimizer/RNG state across fidelity boundaries;
- no ordinary early stop truncating required screen boundaries;
- exact direct M-rung EVAL2 populations, not complements;
- configured-ceiling typed nonconvergence;
- public ordinary `train`/`evaluate` cannot become a second screen owner.

### 3.3 P4 CampaignStore/STOR/currentness/selected authority

P4 `CampaignStore` remains the sole current terminal selected-set authority:

```text
N_selected
T_selected = pi_train[:N_selected]
```

Preserve:

- current-generation/current-terminal ownership;
- canonical execution-root ownership through the production STOR ownership/retention-fence path;
- destructive cleanup through established ownership rather than ad hoc file deletion of current evidence;
- terminal currentness established from the current CampaignStore revision, not caller-supplied stale snapshots;
- exposure-time currentness for public/current terminal views and downstream consumers;
- stale generation/current-pointer evidence failing closed;
- current P1-P5 evidence surviving P6 cleanup;
- current state reopen/restart authenticity after cleanup.

If P6 touches serializers, schemas, store fields/readers, cleanup helpers, pointers, type names imported by persisted state, or storage layout, stage-local persistence/restart/currentness regression is mandatory.

### 3.4 P5 CV/final/replay/foundation/TRAIN2/EVAL2 authority

Preserve all accepted P5 semantics:

- P4 current selected binding is the only selected-data input authority;
- CV starts only after current terminal selection, consumes exact selected-only coverage, uses configured `K >= 2`, preserves full P1 split exclusion, and requires every required fold/seed/variant;
- no mean/majority/best-seed/partial/K0/K1 authorization;
- fold-local preparation/training/checkpoint/replay admissibility cannot see that fold's held-out outer target set;
- representative freezes before held-out outer evaluation;
- replay training exposure and TRUE_DFT replay admissibility monitor remain distinct;
- TRUE_DFT replay gives zero target-size ranking/tie/fold/seed credit;
- candidate and foundation baseline use the same authenticated TRUE_DFT monitor;
- supported training modes remain exactly `scratch`, `naive_fine_tuning`, `multihead_replay`, with no replay-monitor-only fourth mode;
- canonical post-selection heads remain `target_head` / `pt_head`;
- foundation checkpoint head remains a separate foundation-owned concept;
- foundation/replay/method/content identity is fail closed;
- M3 remains development/model-selection evidence only;
- final production starts fresh on full exact `T_selected`;
- final authorization/publication remains currentness-fenced and restart-authenticatable.

Real semantic owners that must remain in the assembled path include:

- `MacePostSelectionTrainer` for TRAIN2 request/config/environment/prelaunch authentication;
- real candidate provider authentication;
- `build_post_selection_foundation_baseline_provider()`;
- `MaceCalculatorProvider.from_model_path()`;
- real EVAL2 reduction/admissibility/target-only representative selection;
- real CampaignStore/currentness/final publication/restart owners.

### 3.5 P5 provider lifetime/non-overlap

Preserve the accepted provider lifecycle:

```text
candidate provider acquire
 -> target EVAL2
 -> candidate TRUE_DFT replay EVAL2 when applicable
 -> candidate close in exception-safe finally
 -> candidate no longer owned
 -> only then foundation provider construction
 -> foundation TRUE_DFT replay EVAL2
 -> foundation close in exception-safe finally

outer representative provider acquire
 -> held-out outer EVAL2
 -> outer close in exception-safe finally
```

Do not replace this with GC timing, a new P6 VRAM manager, a live provider cache, or direct P6 CUDA cleanup that duplicates provider lifecycle ownership.

### 3.6 Shared DATA8/TRAIN2/performance/resource owners

P6 cleanup must preserve semantically valid execution/performance machinery from the frozen parent, including where used by current P3-P5 paths:

- fixed-file/content-valid caches and atomic promotion/publication;
- replay staging;
- foundation checkpoint/head staging;
- MACE config generation;
- accelerator backend selection and precision behavior;
- shared TRAIN2 lifecycle/resource ownership;
- checkpoint publication and exact continuation;
- existing parallel scheduling/concurrent-job control;
- structured progress/telemetry;
- CPU/RAM/VRAM/disk/I/O resource budgets and admission behavior;
- bounded worker/thread policy and nested-parallelism protections;
- failure propagation and cleanup of owned child/process/temp resources.

P6 may simplify/remove machinery only when the census proves it is retired topology rather than current execution infrastructure. If imports or owners above are moved/refactored, run focused scheduling/resource/restart regression in addition to scientific regression.

---

## 4. P6-B — destructive cleanup after safe cutover

### 4.1 Delete/unexport retired current surfaces

After P6-A classification and required R3 cutover, remove as applicable:

- compatibility-domain training eligibility/fanout paths with no supported advisory purpose;
- old DATA3 compatibility-domain numerical-label identity schemas used only by retired topology;
- old label-domain partition condition/unit schemas used only as retired target-size authority;
- `TargetDataRoleFreeze` and equivalent per-domain target-size role authorities;
- public/persisted FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL target-size plan/state authorities;
- fixed target-size/fixed-ceiling scientific authorities;
- `domain_prefix_digests` and retired per-domain target-size candidate maps;
- complement/coarse target-size EVAL2 population authorities;
- old per-domain target-size prefix/evaluation/materialization fields;
- old preselection DATA5/MLCV target-size/CV coupling;
- V5/V6 target-size prepare-contract/receipt/migration semantic readers and reconstruction helpers;
- package imports/exports advertising retired plans as current;
- CLI/config/help surfaces advertising retired current behavior;
- current docs/source-map entries naming retired authority as current;
- tests/fixtures/benchmarks whose only contract is retired topology.

The package currently builds broad public exports from imported globals. Removing an implementation while leaving a package import is not sufficient: package exports must be reconciled so retired target-size authority is not publicly advertised.

### 4.2 Preserve legitimate shared/validation functionality

- R2/R3 current kernels survive under legitimate current owners.
- R6 independent product features survive under their independent contracts.
- R8 oracles/reference implementations/benchmarks survive only when they validate current implementation semantics.
- Retained validation artifacts remain outside current runtime authority and must not create duplicate product state.

### 4.3 MLCV rule

Remove preselection target-size/MLCV coupling and any MLCV path able to authorize/influence target-size selection.

Independently supported MLCV functionality may remain when:

- it has a real product purpose outside retired target-size coupling;
- it descends from current selected-data identity when used in the current post-selection lifecycle;
- it cannot recreate pre-target-size CV authority via alias/helper/compatibility path.

### 4.4 Persistence/deserialization rule

When deleting schemas/types:

- valid current-generation P5A6 evidence required by the accepted current product remains reopenable;
- obsolete target-size V5/V6 derived state fails closed;
- no old target-size payload-shape inference may synthesize missing V7 identity;
- no generic “ignore unknown fields” behavior may silently turn retired target-size state into current state;
- reject-only legacy generation detection must occur before semantic target-size deserialization/reuse;
- retained non-target-size compatibility readers are read-only/non-authoritative and cannot mutate current selection/CV/final publication state.

### 4.5 Test disposition

```text
obsolete-authority-only test
    -> delete

old test containing still-valid neutral/current behavior
    -> rewrite/move against canonical owner

current-generation compatibility/restart test
    -> retain

retired target-size migration-reader test
    -> replace with reject-before-reuse test

R8 reference/oracle/equivalence test
    -> retain when it validates current implementation

historical-only artifact/test
    -> retain only when clearly historical and excluded from current acceptance
```

Do not weaken production validation to keep an obsolete test shape green.

### 4.6 P6-B stage-local closure

After each material executable cutover/cleanup stage and before dependent implementation proceeds, complete both semantic and functional closure.

At minimum run:

1. package import/public-export checks;
2. structural absence/current-call-edge checks for the retired surface changed in that stage;
3. focused tests through each canonical owner affected by R3 cutover;
4. current-caller tests for retained shared kernels;
5. affected persistence/restart/currentness tests when persistence/imported persisted types changed;
6. affected CLI/config tests when parser/help/config changed;
7. affected scheduling/resource/checkpoint/cache tests when shared execution machinery changed;
8. stage-local affected regression over every materially/transitively affected executable surface.

A green import/grep check is not functional closure. Record exact commands, executed counts, failures/skips and dispositions.

---

## 5. P6-C — current tests/specifications/docs/public surface

### 5.1 Replace obsolete topology assertions

Delete/rewrite assertions whose only contract is:

- fixed target-size universe/ceiling;
- mandatory MVSEL2 -> REPAIR2 -> MVQUAL2 target-size route;
- old prepare receipt keys;
- label-domain namespace resolution for target size;
- per-final/CV-domain target-size materialization;
- complement/coarse target evaluation;
- preselection CV/MLCV ownership of target-size choice;
- semantic migration of retired target-size state.

Preserve or strengthen behavioral coverage for:

- one public target-size scheduler;
- paired optimizer seeds and separate seed namespaces;
- exact continuation/restart;
- exact selected-data freeze before CV;
- final-production horizon independence;
- real DATA8/TRAIN2/EVAL2 semantic owners;
- P4 currentness/destructive ownership/stale-generation rejection;
- P5 replay/foundation/mode/head/lineage identity;
- P5 provider construction and explicit provider retirement/non-overlap;
- numerical failure semantics;
- current optimized-kernel reference equivalence and bounded performance where applicable;
- reject-before-reuse handling for obsolete target-size workspaces.

### 5.2 Documentation/source maps

Reconcile current architecture manuals, specifications, source maps, CLI help, config examples and generated-documentation inputs.

Requirements:

- no current document presents retired target-size topology as current authority;
- current source maps point to actual P1-P5 owners after cleanup;
- current examples expose only supported current configuration;
- historical snapshots remain clearly historical;
- generated documentation remains reproducible;
- useful historical rationale need not be erased merely to remove a retired search term.

Run applicable documentation link/reference/lint/build checks **including required PDF generation/build checks present in the repository/project documentation workflow**. If a required PDF build cannot execute because a documented external dependency is unavailable, report it as unavailable/blocking or explicitly project-deferred according to repository policy; do not count it as passed.

### 5.3 P6-C stage closure

If P6-C is documentation-only, executable regression need not be invented. Any code/config/test-helper/public API change made here is executable and requires focused checks plus the corresponding stage-local affected regression.

---

## 6. P6-D — final semantic/source conformance before final test pass

Before broad final tests, inspect the complete assembled P6 candidate against the frozen parent and this P6 snapshot.

Verify from production source/call edges, not test names alone:

1. provenance remains advisory and separate from numerical-label identity;
2. neutral substrate has no compatibility-domain target-size partition axis or pre-target CV authority;
3. exactly one current `P_train/M3`, one `pi_train`, one `pi_eval/M` ladder and one P4 reducer exist;
4. common preparation remains shared across `N`/seed;
5. only optimizer seeds are screen replicates;
6. exact continuation and exact direct `M_i` evaluation remain intact;
7. current persistence/runtime authority is current-generation only;
8. CampaignStore selected binding/currentness remains authoritative;
9. stale validated snapshots cannot be exposed as current after CampaignStore advances;
10. CV consumes exact current `T_selected`, preserves protected-relation exclusions, and cannot feed back into selection;
11. final production is fresh on full exact `T_selected` with independent production horizon;
12. replay/foundation/mode/head/lineage semantics remain fail closed;
13. real TRAIN2/provider/EVAL2 owners remain in the assembled path;
14. provider close/non-overlap remains intact;
15. fixed-file/cache/atomic-promotion/checkpoint/scheduler/resource/accelerator/precision machinery used by current execution remains intact or legitimately reconciled;
16. retired target-size authorities are absent from current runtime/API rather than hidden behind wrappers;
17. retired target-size semantic migration/read-forward paths are absent; only reject-only obsolete-generation detection may remain;
18. every retained legacy-looking surface has an R2-R6/R8 justification;
19. every retained R8 oracle/benchmark validates current semantics rather than retired topology.

A material omission is repaired before final functional closure. Green tests do not substitute for this conformance pass.

---

## 7. P6-E — fresh final affected-surface regression

### 7.1 Re-derive from final candidate

Derive the final affected regression surface from the **assembled final P6 diff**, including deleted modules and transitive import/caller effects. Do not rely only on the original deletion list or stage-local test set.

At minimum consider:

- DATA2/DATA3 provenance/numerical identity;
- duplicate/protected-relation/neutral statistical base;
- P3 target-size preparation/screen/restart;
- P4 CampaignStore/state/currentness/retention/destructive ownership/terminal selection;
- DATA7/DATA8;
- TRAIN2 wrapper/prelaunch/config/checkpoint/resource/scheduling paths;
- EVAL2/provider authentication/reduction/provider lifetime;
- accelerator/precision/config realization if touched;
- CLI/config/public imports;
- persistence/restart/reopen/obsolete-workspace rejection;
- post-selection CV and independently supported MLCV touched by cleanup;
- fresh final production/publication/reopen;
- current docs/source maps/generated docs.

### 7.2 Required final regression

Run on the same final candidate:

1. all focused tests material to affected retained P1-P5 behavior;
2. complete affected-surface regression derived above;
3. broader/full repository CPU-safe suite because P6 crosses package exports, foundational identity, persistence and orchestration boundaries unless implementation can independently prove a smaller complete bound;
4. repository/project-required static/type/lint/build checks for changed files;
5. applicable documentation link/reference/lint/build/PDF checks.

A required check that does not execute is not a pass. Only demonstrably pre-existing unrelated failures may be attributed rather than repaired.

Long production-scale GPU/real-data qualification remains outside this functional gate.

---

## 8. P6-F — mandatory restart/invalidation matrix

The frozen parent requires not only deterministic restart but correct **scope of invalidation**. P6 final acceptance must execute a bounded matrix proving both what becomes stale and what remains reusable/current when one policy/input dimension changes.

Use current production identities/state transitions and real CampaignStore/restart owners. Do not emulate invalidation logic in the harness.

### 8.1 Target-size-scientific changes — invalidate target-size descendants

For each materially supported dimension below, modify only that dimension and prove target-size evidence/descendants are invalidated/rebuilt as required while unrelated upstream raw/current inputs remain reusable where their recipe is unchanged:

- actual source/frame membership;
- canonical numerical label values;
- canonical numerical label interpretation/conversion policy;
- target-size candidate powers / configured ceiling;
- evaluation-size powers / M-ladder membership policy;
- fidelity epochs/boundaries;
- ordered optimizer seed set;
- training-order policy/features affecting `pi_train`;
- `P_train/M3` split or `pi_eval` ordering policy;
- common preparation/training scientific policy;
- target-size metric/practical-equivalence policy;
- foundation/replay scientific identity when part of the target-size experiment.

Acceptance: old target-size candidate/terminal/current selected evidence cannot remain current under the modified scientific identity, and downstream CV/final evidence that depends on that selected authority cannot remain current.

### 8.2 Advisory provenance-only change — must not invalidate training math

Change only advisory provenance grouping/report presentation while canonical source membership, canonical numerical labels/interpretation and current training policy remain unchanged.

Acceptance:

- frame UID and canonical numerical label identity remain unchanged where the parent requires;
- neutral partition/training membership remains unchanged;
- target-size scientific identity/result remains reusable/current;
- only advisory provenance/report evidence that actually depends on the changed presentation is invalidated/rebuilt.

### 8.3 CV-only changes — invalidate CV descendants only

Change CV-only settings such as fold count and/or CV partition seed while target-size scientific inputs/policy remain unchanged.

Acceptance:

- P4 `N_selected/T_selected` remains current and unchanged;
- target-size candidates/terminal evidence are not rebuilt or rebound;
- affected CV plans/evidence become stale/rebuilt;
- final evidence depending on CV acceptance is invalidated as required.

### 8.4 Final-production-only changes — invalidate production descendants only

Change a production-only budget/adaptive/runtime policy that is explicitly outside target-size and CV scientific identity.

Acceptance:

- target-size selected authority remains current;
- accepted CV evidence remains current when scientifically unaffected;
- only final-production descendants whose identity includes the changed production policy become stale/rebuilt.

### 8.5 Obsolete generation rejection

Present representative retired V5/V6 target-size derived workspace metadata/state.

Acceptance:

- current runtime detects obsolete generation through the real load/preflight path;
- rejection occurs before semantic old target-size state is deserialized into current authority, before candidate/checkpoint reuse, and before descendant publication;
- message/action is an explicit destructive reset/reprepare requirement;
- no migration adapter silently reconstructs V7 authority.

### 8.6 Corruption/currentness counterfactuals

Include representative negative cases for:

- missing/corrupt current persisted identity required for restart;
- stale current pointer/generation after CampaignStore advancement;
- stale terminal object exposure after store revision changes;
- final publication identity mismatch on reopen.

These may be focused owner tests rather than one giant matrix test, but collectively must exercise the real current owners.

---

## 9. P6-G — mandatory assembled real-owner integration through real CLI and completed final publication

### 9.1 Required entry boundary: real production CLI parsing/dispatch

At least one bounded assembled lifecycle must enter through the **actual production CLI parser and command-dispatch owner** for the current workflow. Internal helper-only invocation is insufficient for this claim.

The integration must exercise the real current command path for the relevant sequence, including the actual production equivalents of:

```text
prepare
 -> select-target-size
 -> current selected-data freeze/publication
 -> post-selection cross-validation command/path
 -> final-production command/path
```

Use the repository's actual current command names/dispatch functions. Invoking the real CLI `main()`/argument parser directly in-process is acceptable when it executes the same parser/dispatch semantics as the user-facing command. A shell subprocess is not required solely for ceremony. What is forbidden is bypassing CLI parsing/dispatch and manually seeding post-CLI state while claiming CLI integration.

### 9.2 Required assembled lifecycle

On the same final P6 candidate, execute a bounded semantic path:

```text
real CLI/config/source ingestion
 -> current neutral substrate
 -> current preparation authorities
 -> bounded real P3 paired target-size screen
 -> real P4 reducer
 -> real CampaignStore current terminal selection
 -> persist exact N_selected / T_selected
 -> close and reopen store/process context
 -> reauthenticate current terminal selected authority
 -> real CLI/current post-selection CV creation/execution
 -> all-required bounded CV acceptance
 -> reauthenticate method/foundation/replay/current selected binding
 -> real CLI/current fresh full-T_selected final-production orchestration
 -> final run completes through real final semantic owner
 -> final evidence/current publication completes
 -> close providers/store/process context
 -> reopen CampaignStore/current context
 -> reauthenticate selected binding + CV + final publication
```

Do not stop at final-production entry.

### 9.3 Semantic owners that must remain real

The assembled acceptance must traverse, as applicable to the current supported mode:

- production CLI parser and command dispatch;
- production config resolution;
- real CampaignStore/SQLite and P4 state/currentness transitions;
- current P3 screen owners and P4 reducer/terminal projection;
- selected binding from CampaignStore;
- P5 method/foundation/replay identity resolution;
- CV/final currentness and authorization;
- DATA7/DATA8 materialization ownership;
- `Train2RuntimePlan` construction;
- `MacePostSelectionTrainer` request/prelaunch authentication/config/environment/cwd ownership;
- canonical TRAIN2 summary/checkpoint authentication;
- candidate provider authentication;
- `build_post_selection_foundation_baseline_provider()`;
- `MaceCalculatorProvider.from_model_path()`;
- EVAL2 reduction/admissibility/target-only checkpoint/representative selection;
- provider acquisition/retirement scopes;
- final evidence/current publication;
- restart/currentness reauthentication after reopen.

### 9.4 Allowed bounded fakes

Expensive scientific numerical work may be substituted **below** the semantic owners above:

- external MACE numerical training may use the already accepted bounded fake/wrapper seam below `MacePostSelectionTrainer`;
- low-level MACE model-load/forward numerical dependency may be bounded/faked only at seams already accepted by P5 while retaining the real mdstats provider owner;
- tiny synthetic scientific datasets/checkpoints may be used when they exercise real identity/state owners.

Forbidden:

- injected/precomputed selected authority;
- injected/precomputed replay lineage;
- seeded CV/final authorization;
- replacing `MacePostSelectionTrainer`;
- replacing the foundation baseline provider builder;
- replacing `MaceCalculatorProvider.from_model_path()`;
- bypassing CampaignStore/currentness/restart;
- fabricated post-decision EVAL2 metrics;
- bypassing provider close scopes;
- bypassing CLI parser/dispatch while claiming CLI integration;
- a proxy harness that could remain green while a required owner above is materially broken.

### 9.5 Representative counterfactuals

Focused and/or assembled tests must collectively demonstrate failure for representative broken-owner conditions affected by cleanup, including:

- stale CampaignStore generation/current terminal exposure;
- obsolete target-size state attempting semantic read-forward;
- broken TRAIN2 authentication/summary;
- provider construction/authentication failure;
- provider evaluation exception still causing explicit close;
- final publication/currentness mismatch on reopen.

---

## 10. P6-H — deterministic/reference/resource closure

### 10.1 Determinism

Verify deterministic reproduction of current split/orders/target-size evidence for fixed bounded inputs/seeds and exact restart behavior at affected P3/P4/P5 boundaries.

### 10.2 Reference/oracle equivalence

For each retained optimized current kernel for which an R8 oracle/reference exists or is materially justified, run applicable equivalence checks using exact equality for discrete identities/orderings and scientifically justified tolerances for floating observables.

Do not retain a dead old kernel merely to keep a reference test. Do not delete a useful independent oracle merely because production code does not call it.

### 10.3 Scheduling/resource/performance regression

When P6 touches shared execution imports or machinery, run bounded checks sufficient to detect accidental regression in:

- repeated per-domain/redundant work;
- CPU worker/process/thread oversubscription;
- RAM/VRAM admission and provider overlap;
- disk/I/O/cache behavior;
- checkpoint/atomic promotion/restart;
- scheduler failure propagation/cleanup;
- accelerator/precision realization where affected.

Always rerun affected P5 provider-lifecycle guards if provider execution/imports are touched.

### 10.4 M-ladder scientific qualification

Functional tests do not prove the default M ladder preserves the same size decision as a larger reference population.

If representative qualification evidence exists, evaluate the frozen parent requirements for M1 competitive retention, M2 finalist retention, M3 selected-N agreement, support/correlation representativeness, and sensible same-cardinality ordering comparison.

If representative evidence is unavailable, report **`deferred/unavailable`**, not passed. Do not tune M using post-selection CV/calibration/locked evidence and do not manufacture decision-preservation from synthetic timing.

Long target-machine GPU/real-data qualification remains deferred.

---

## 11. Reconciliation versus Design reopen

### 11.1 Implementation reconciliation — do not reopen Design

The following remain implementation work when frozen parent semantics can be preserved:

- discovering an old module that still has a legitimate current/shared kernel that can be cut over under R3;
- discovering a supposedly retired current call edge that is simply an incomplete old->V7 cutover and can be redirected to an already accepted P1-P5 owner;
- moving neutral/shared code to a canonical module;
- deleting unexpected aliases/imports/docs/tests/benchmarks that are clearly retired;
- adding newly discovered affected regression coverage;
- replacing a retired target-size semantic reader with reject-only obsolete-generation detection;
- preserving an independent non-target-size product feature through bounded neutral-owner refactor.

Do not reopen merely because repository reality contains more cleanup than the initial search list.

### 11.2 Reopen Design only on evidence

Stop the affected destructive work and amend Design only if evidence shows one of:

1. a material current scientific/authorization responsibility genuinely requires a retired architecture concept and cannot be represented by the frozen V7 owners without changing accepted semantics;
2. cleanup requires changing frozen target-size/CV/final scientific decisions rather than removing/reconciling retired topology;
3. valid current P5A6 persisted state cannot be reopened without a material current-generation schema migration not already authorized by P1-P5/P6;
4. an independently supported non-target-size product responsibility cannot survive without a material architecture/product-contract change;
5. the implementation baseline materially changed in a way that invalidates protected P1-P5 ownership assumptions;
6. a new product-level compatibility policy is required rather than destructive current-generation cutover;
7. a frozen parent scientific reopen condition fires, including demonstrated mixed-provenance incompatibility, one-order scientific infeasibility, M-ladder decision-preservation failure, proven N-dependent training transform requirement, inadequate two-seed decision reliability, need for separate target heads/studies, material performance infeasibility, or inability of shared TRAIN2/MACE to provide the accepted non-controlling screen validation semantics.

Do not solve a reopen trigger by adding broad compatibility fallbacks, reconstructing old plans from partial evidence, or weakening current validation.

### 11.3 Delegated implementation choices

Implementation may choose:

- exact neutral module placement for R3 cutovers;
- exact grouping of coherent deletions into material stages;
- exact test-file organization;
- exact bounded synthetic fixtures and allowed low-level fakes;
- exact current documentation files derived from source-map impact;
- exact R8 benchmark/oracle file location/name.

These choices are delegated only when all frozen owners and acceptance obligations remain intact.

---

## 12. Implementation evidence and final reporting

P6 implementation evidence must record at minimum:

1. exact starting commit/tree;
2. P6-A disposition ledger, including R2-R6/R8 retention justification;
3. deleted modules/symbols/schemas/public exports and retirement reason;
4. R3 old/new owner mappings;
5. legacy target-size reader/migration removals and reject-only detector behavior;
6. stage-local test commands/results for every material executable stage;
7. final affected-surface derivation;
8. final focused/affected/broader regression commands/results;
9. restart/invalidation matrix commands/results;
10. real-CLI assembled integration command/result and allowed fake seams used;
11. deterministic/reference/resource checks;
12. documentation link/lint/build/PDF checks;
13. unresolved failures, if any, classified as implementation issue, pre-existing unrelated issue, or Design reopen trigger.

Do not report a check as passed when it did not execute. Absence of CI status is neither success nor failure; report actual executed commands/results.

### 12.1 Mandatory three-way final status

Report separately:

1. **Functional V7/P6 acceptance** — conformance + regression + restart/invalidation + real-owner/real-CLI assembled integration.
2. **M-ladder scientific decision-preservation qualification** — `passed`, `failed`, or `deferred/unavailable` based on representative evidence.
3. **Long target-machine GPU/real-production qualification** — remains explicitly `deferred` until the final release qualification phase unless the user separately requests/runs it.

A pass in one category does not imply a pass in the others.

---

## 13. Final P6 exit gate

P6 and the complete V7 implementation are accepted only when all of the following are true on one final candidate:

- implementation started from or explicitly reconciled against the exact P5A6 baseline;
- P6-A census/disposition is complete for material retired/current-mixed/validation surfaces;
- every R3 current/shared cutover was proven before destructive deletion;
- retired target-size scientific authorities, aliases, semantic readers/migrators/reconstruction helpers and unsupported public exports are structurally absent rather than hidden behind wrappers;
- any remaining obsolete-generation reader is reject-only and cannot semantically deserialize/reuse retired target-size state;
- old target-size workspaces are rejected before candidate/checkpoint/derived-state reuse;
- independently supported/shared current functionality remains under legitimate owners;
- useful R8 reference/oracle/benchmarks validate current semantics only;
- P1-P5 frozen scientific semantics remain unchanged;
- P4 CampaignStore/STOR/currentness/restart/selected-set ownership remains intact;
- P5 replay/foundation/CV/final/TRAIN2/provider/EVAL2/provider-lifecycle ownership remains intact;
- accepted fixed-file/cache/atomic-promotion/checkpoint/scheduler/telemetry/resource/accelerator/precision machinery remains intact where current paths use it;
- valid current-generation state reopens/authenticates correctly;
- the mandatory invalidation matrix proves correct target-size vs advisory-provenance vs CV-only vs final-only invalidation scope;
- obsolete derived target-size state cannot be promoted into current V7 authority;
- stage-local affected regression passed after every material executable cleanup/cutover stage;
- final affected-surface regression and required broader CPU-safe checks passed;
- applicable documentation link/lint/build/PDF checks passed or are truthfully classified under repository policy;
- at least one assembled lifecycle entered through the real production CLI parser/dispatch and completed config/source -> prepare -> target-size selection -> selected freeze -> reopen -> CV -> fresh full-`T_selected` final -> publication -> second reopen/currentness reauthentication;
- assembled acceptance kept all protected semantic owners real and used fakes only below allowed boundaries;
- retained optimized current kernels passed applicable reference/oracle equivalence checks;
- bounded resource/lifecycle/scheduling checks relevant to affected execution machinery passed;
- current docs/public API/source maps match implemented V7 authority;
- the three final qualification statuses are reported separately;
- no unresolved material conformance, correctness, persistence, owner-boundary or implementation defect remains.

Only after this gate may the complete V7/P6 candidate be presented for independent **Software Design** review and merge/freeze decision.
