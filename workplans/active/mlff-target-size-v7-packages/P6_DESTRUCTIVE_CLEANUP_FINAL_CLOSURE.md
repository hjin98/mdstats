---
kind: implementation-package
package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
sequence: 6
status: active
package_revision: 2
amended_date: 2026-08-30
entry_p5_accepted_baseline_commit: 1670275487d29bbcde4c59efafdef9d1f8b0ced7
entry_p5_accepted_baseline_tree: 17e2c5609974712bda1efd3375f09f42da830f68
entry_p5_workplan_revision: 11
compatibility_policy: destructive-generation-reset-current-generation-cutover-no-derived-migration
reconciliation_reason: P6 is rebased onto the accepted P5A6 implementation. The original cleanup outline was scientifically aligned but not snapshot-complete for destructive implementation: it assumed residual old code was already unreachable, did not classify mixed legacy/current ownership before deletion, did not freeze the hardened P4 persistence/currentness/STOR boundaries or the complete P5 real-owner/provider-lifecycle chain, stopped assembled acceptance at final-production entry instead of completed publication and restart reauthentication, and lacked stage-local affected regression after destructive executable edits. Revision 2 closes those implementation-handoff gaps without reopening P1-P5 science.
---

# P6 revision 2 — destructive cleanup and assembled final closure

## 0. Authority, accepted baseline, scope, and precedence

The frozen parent `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict for the target-size reset. P6 is bound to **Protocol 5.8.0** and must not silently reinterpret this package under a later protocol revision.

The exact accepted implementation baseline for destructive cleanup is:

```text
1670275487d29bbcde4c59efafdef9d1f8b0ced7  P5A6
```

with tree:

```text
17e2c5609974712bda1efd3375f09f42da830f68
```

P6 is a **destructive cleanup plus final assembled-closure package**. It is not permission to redesign accepted P1-P5 science, change the selected-set semantics, weaken currentness/restart checks, add compatibility fallbacks, or simplify real-owner acceptance boundaries merely to make deletion easier.

P6 implementation starts from the exact baseline above. If branch HEAD changes before implementation begins, implementation must first reconcile the intervening diff. A material change to any protected owner in Section 3 is a reopen trigger; do not silently apply this cleanup plan to a different semantic baseline.

Full production-scale/long target-machine GPU qualification remains deferred. P6 closure requires bounded functional, regression, integration, determinism, reference-equivalence, and resource-lifecycle evidence. It does **not** require long real-data training or performance qualification on the target GPU.

---

## 1. Frozen assembled product state that P6 must preserve

P6 removes retired topology around the accepted architecture. The following end state is frozen.

### 1.1 Parent scientific architecture

The assembled current path remains:

```text
precise provenance / numerical-label identity
 -> neutral current substrate
 -> one P_train / M3 development split
 -> one canonical pi_train
 -> one canonical pi_eval / M-ladder
 -> paired optimizer-seed target-size screen
 -> one current P4 reducer
 -> N_selected
 -> T_selected = pi_train[:N_selected]
 -> post-selection CV on exact T_selected
 -> fresh final production on exact full T_selected
```

Preserve all of the following:

- provenance is precise and advisory and does not recreate compatibility-domain numerical branching;
- the neutral substrate has no compatibility-domain partition axis and no pre-target-size CV authority;
- common deterministic preparation is shared across candidate sizes and optimizer seeds;
- only optimizer seeds are screening replicates;
- exact continuation/restart and exact `M_i` evaluation semantics remain intact;
- post-selection CV cannot feed back into target-size selection;
- final production is fresh, uses the full exact selected set, and uses `[training].max_num_epochs` as its final horizon authority independently of screening/CV horizons.

### 1.2 Current-generation rule

P6 completes the current-generation cutover. Retired V5/V6 derived topology may be removed rather than migrated. However:

- valid current P1-P5 state produced by the accepted generation must remain reloadable and restart-authenticatable;
- retired derived state must never be inferred, reconstructed, or promoted into current V7 authority through a fallback;
- any retained historical/compatibility reader is read-only/non-authoritative for current selection, CV, final authorization, publication, and current-pointer decisions;
- historical snapshots may remain historical, but they must not appear in current package exports, current source maps, current configuration examples, or current architecture documentation as supported authority.

---

## 2. P6-A — mandatory current-baseline census and disposition ledger

### 2.1 Purpose

The original P6 entry condition assumed every retained old surface was already unreachable. That assumption is removed.

At P6 entry, a legacy surface may still be importable, publicly exported, serialized, tested, documented, or otherwise reachable. That is acceptable **only if it no longer owns or influences current P1-P5 scientific decisions**. P6 must census those residual surfaces and then remove or reclassify them safely.

For example, the P5A6 package still imports legacy target-data-role symbols through `mdstats.training_data`; public reachability is therefore not evidence that the old object remains valid current scientific authority, nor is scientific retirement evidence that the public/API residue has already disappeared.

### 2.2 Census surface

Before destructive executable edits, inspect the P5A6 tree and enumerate all plausible retired/current-mixed surfaces across:

1. Python modules, classes, dataclasses, functions, constants, enums, and schema/version identifiers;
2. `mdstats.training_data` and other package-level imports/exports, including automatically generated `__all__` surfaces;
3. CLI commands/options, configuration keys/defaults, parser branches, and help text;
4. CampaignStore/SQLite fields, state values, serializers/deserializers, JSON/YAML payloads, receipt/manifest keys, current pointers, restart/reopen paths, and reconstruction helpers;
5. filesystem path/layout helpers and cleanup/retention ownership;
6. current call edges and dependency imports from P1-P5 runtime owners;
7. tests, fixtures, golden payloads, benchmarks, and helper factories;
8. architecture manuals/specifications, current source maps, user-facing examples, README/help text, and generated documentation inputs.

Search explicitly for the retired target-size concepts already named by the parent/original P6, including at minimum:

```text
TargetDataRoleFreeze / per-domain role authority
FEAS1
MVIDX1
MVSEL2
REPAIR2
MVSTATE2
MVQUAL / MVQUAL2
fixed target-size / fixed ceiling authority
per-domain target-size candidate maps
per-domain target-size prefix digests
complement/coarse target-size EVAL2 populations
old per-domain target-size evaluation/materialization fields
old DATA5/MLCV preselection target-size coupling
V5 prepare-contract / receipt / migration aliases
legacy target-size reconstruction helpers
compatibility-domain training eligibility/fanout used as current authority
old numerical-label / label-domain partition authority used by target-size selection
```

This list is a minimum search set, not a ceiling. Implementation must add materially equivalent aliases/schemas discovered from the repository.

### 2.3 Required disposition classes

Every material legacy-looking surface must receive exactly one disposition before deletion/refactor:

| Class | Meaning | Required action |
|---|---|---|
| R1 | retired current scientific/authorization authority | delete implementation/current call edge and unexport |
| R2 | current V7/shared neutral implementation | retain under canonical current owner |
| R3 | mixed legacy + current/shared implementation | cut current/shared functionality to canonical owner first, prove cutover, then remove legacy authority |
| R4 | diagnostic/advisory compatibility functionality | retain only if it cannot authorize selection/training/CV/final/current publication |
| R5 | supported persistence/compatibility reader | retain read-only/non-authoritative; no reconstruction/promotion to V7 |
| R6 | independently supported product feature outside target-size V7 | preserve its independent contract; do not delete merely because the module is old |
| R7 | historical-only source/evidence | may remain only in clearly historical/archive context, not current runtime/API/docs |

The implementation evidence must record the disposition and the concrete current caller/purpose for every R2-R6 retention decision. “Tests still import it” is not an independent supported purpose.

### 2.4 Cutover-before-delete rule

If a targeted legacy module contains any R2/R3 functionality, destructive deletion is forbidden until:

1. the legitimate current/shared responsibility is identified;
2. it is moved to or routed through the canonical neutral/current owner without changing scientific behavior;
3. all current callers are updated;
4. focused semantic tests pass through the new owner;
5. stage-local affected regression for the cutover passes;
6. only then is the retired legacy authority/module/export removed.

Do not preserve a dead wrapper solely to make an old test green. Do not delete a shared implementation merely because its filename contains a retired concept.

### 2.5 P6-A acceptance

P6-A closes when the census/disposition ledger is complete enough that every destructive edit in P6-B has an explicit semantic reason and no current/shared owner is being deleted by inference from naming alone.

P6-A is primarily reconciliation/design work. If it makes no executable changes, it needs semantic review evidence rather than an artificial test gate. Any executable cutover performed while completing the census must close with the stage-local tests required by Section 2.4.

---

## 3. Protected P1-P5 owners and invariants during cleanup

The following are task-local preservation requirements. P6 implementation must not rely on rereading historical workplans to rediscover them.

### 3.1 P1/P2 substrate and split authority

Preserve:

- canonical current frame/source/label/provenance identities required by the neutral substrate;
- duplicate/correlation/protected-relation evidence that remains part of the accepted neutral/current scientific base;
- the canonical P1 split-exclusion/protected-relation authority consumed by post-selection CV;
- separation between precise provenance and numerical-label identity;
- absence of compatibility-domain partitioning from current target-size science.

Generic partition/identity machinery with an independent current purpose is not deletable merely because old target-size topology also used it.

### 3.2 P3 target-size execution authority

Preserve the accepted single target-size execution chain:

- one canonical `pi_train` and candidate-size ladder;
- one canonical `pi_eval`/M-ladder evaluation policy;
- paired optimizer seeds only;
- common deterministic preparation shared across `N` and seed;
- exact continuation/restart semantics;
- exact boundary/evaluation semantics;
- retained optimized kernels only where a current caller or independent supported feature actually uses them.

P6 may remove old selector/repair/planning authorities; it may not replace the accepted P3 scientific owner with a compatibility wrapper or a simplified proxy.

### 3.3 P4 persistence, destructive ownership, currentness, and selected authority

P4 `CampaignStore` current-generation/current-terminal authority remains the sole current owner of target-size terminal selection. Preserve:

```text
N_selected
T_selected = pi_train[:N_selected]
```

and the complete currentness model:

- canonical execution-root ownership remains dependency-leaf/current-owner controlled;
- destructive cleanup/removal continues through the production STOR ownership/retention-fence path;
- the canonical terminal loader establishes currentness from the current CampaignStore revision rather than trusting a caller-supplied stale snapshot;
- a previously validated terminal object is not perpetual authority after CampaignStore advances;
- every public/current terminal view/report/downstream current-result consumer re-establishes exposure-time currentness as required by the accepted P4 implementation;
- stale generation/current-pointer evidence fails closed rather than being reconstructed from retired schemas;
- destructive cutover may discard obsolete derived topology, but it must not damage the current P4 execution root or current P1-P5 evidence.

If P6 changes any serializer, schema, store field, store reader, cleanup helper, current-pointer path, or type imported by persisted current evidence, stage-local restart/currentness regression is mandatory.

### 3.4 P5 identity, CV, final, TRAIN2/EVAL2, provider, and lifecycle authority

Preserve all accepted P5 semantics, including:

- P4 current selected binding is the only input selection authority;
- CV starts only from current terminal selection, uses exact selected-only coverage, configured `K >= 2`, full P1 split exclusion, and requires every required fold and seed/variant to pass;
- no mean/majority/best-seed/partial/K0/K1 authorization;
- fold-local fitted preparation/training/checkpoint/replay admissibility cannot see that fold's held-out outer target set;
- held-out outer evaluation occurs only after representative freeze;
- replay training exposure and TRUE_DFT replay admissibility remain distinct;
- TRUE_DFT replay receives zero target ranking/tie/seed/size-selection credit;
- candidate and canonical foundation baseline use the exact same authenticated TRUE_DFT replay monitor;
- the exact supported training-mode topology remains `scratch`, `naive_fine_tuning`, and `multihead_replay`, with no monitor-only fourth mode;
- P5 target/replay head names remain `target_head` / `pt_head`;
- foundation checkpoint head selection remains foundation-owned and separate;
- fail-closed replay/foundation/method/content identity remains current;
- real `MacePostSelectionTrainer` owns TRAIN2 request/config/environment/prelaunch authentication;
- real candidate provider authentication remains in the evaluation chain;
- real `build_post_selection_foundation_baseline_provider()` remains in the chain;
- real `MaceCalculatorProvider.from_model_path()` remains in the chain;
- real EVAL2 reduction/admissibility/target-only representative selection remains in the chain;
- M3 remains development/model-selection evidence only;
- final production is a fresh run over full exact `T_selected` with fresh optimizer/RNG/run state;
- final authorization/publication remains currentness-fenced and restart-authenticatable.

Provider lifetime/resource ownership from P5A6 is also frozen:

```text
candidate provider acquire
 -> target evaluation
 -> candidate TRUE_DFT replay evaluation when applicable
 -> candidate close in exception-safe finally
 -> only then foundation baseline provider construction
 -> foundation TRUE_DFT replay evaluation
 -> foundation close in exception-safe finally

outer representative provider acquire
 -> outer evaluation
 -> close in exception-safe finally
```

Do not replace this with garbage-collection timing, a new P6 VRAM manager, or a provider cache that changes residency semantics.

---

## 4. P6-B — cut over mixed owners, then destructively remove retired runtime/API/schema surfaces

### 4.1 Deletion scope

After P6-A classification and any required R3 cutover, delete or unexport as applicable:

- compatibility-domain training eligibility/fanout paths that no longer serve a supported advisory/diagnostic purpose;
- old DATA3 compatibility-domain numerical-label identity/current schemas used only by retired topology;
- old label-domain partition condition/unit schemas used only as retired target-size authority;
- `TargetDataRoleFreeze` target-size authority and equivalent per-domain role authorities;
- public/persisted FEAS1/MVIDX1/MVSEL2/REPAIR2/MVSTATE2/MVQUAL target-size plan/state authorities;
- fixed target-size/ceiling authorities;
- target-size `domain_prefix_digests` and retired per-domain candidate maps;
- complement/coarse target-size EVAL2 population authorities;
- old target-size candidate per-domain prefix/evaluation/materialization fields;
- old preselection DATA5/MLCV target-size/CV coupling;
- V5 prepare-contract/receipt/migration aliases and reconstruction helpers that have no current supported reader role;
- current package imports/exports that advertise retired plans as supported authority;
- CLI/config/help surfaces that advertise retired current behavior;
- current documentation/source-map entries that point to retired authority.

The current `mdstats.training_data` package builds public exports from imported globals. Removing a legacy implementation while leaving its package import is not sufficient: the import/export surface must be reconciled so the retired symbol is no longer advertised as current.

### 4.2 Retained implementation rule

Retain/refactor optimized sparse/vectorized selector/repair/EVAL2/DATA8/TRAIN2 kernels, reference oracles, and useful benchmarks **only** if the P6-A ledger identifies:

- a concrete current P1-P5 caller; or
- an independently supported non-target-size product feature.

If retained implementation currently lives in a retired-authority module, move the retained implementation to a neutral/current owner first when that improves ownership clarity and removes the retired semantic namespace. Avoid gratuitous relocation when the module is already a legitimate neutral owner.

### 4.3 MLCV rule

Do not interpret “remove old DATA5/MLCV coupling” as permission to delete independently supported MLCV functionality.

- remove preselection target-size/CV coupling and any MLCV path that can authorize or influence current target-size selection;
- retain independent MLCV functionality if it has a supported current product purpose outside this retired coupling;
- retained MLCV must not recreate a pre-target-size CV authority through an alias, helper, or compatibility path.

### 4.4 Persistence/deserialization rule

When deleting schemas/types:

- current P5A6-generation persisted evidence must continue to deserialize/reopen where the accepted product contract requires it;
- obsolete derived V5/V6 evidence may fail closed under destructive generation reset;
- do not add fallback inference from old payload shape to current V7 authority;
- do not silently accept an old schema by dropping unknown fields or synthesizing missing current identity;
- if a compatibility reader is retained, prove that it cannot mutate current state or authorize selection/CV/final publication.

### 4.5 Test disposition rule

Classify tests by contract, not by filename/age:

```text
obsolete-authority-only test
    -> delete

old test containing still-valid neutral numerical/reference behavior
    -> rewrite/move against the canonical current owner

supported compatibility-reader test
    -> retain as explicitly non-authoritative compatibility evidence

current P1-P5 regression
    -> preserve and rerun when affected

historical-only artifact/test
    -> retain only if clearly historical and excluded from current acceptance
```

Never weaken production validation to preserve an old helper/test shape.

### 4.6 P6-B stage-local verification

After the material executable cleanup/cutover stage, run all of the following before proceeding:

1. package import/public-export tests;
2. structural absence checks for forbidden retired names/concepts/current call edges;
3. focused tests through each canonical owner touched by a cutover;
4. current caller tests proving retained optimized/shared kernels remain reachable through current owners;
5. affected persistence/restart/currentness tests if any persisted/store surface was touched;
6. affected CLI/config tests if parser/help/config surfaces were touched;
7. a **stage-local affected regression** across every module/package materially changed or transitively affected by the cleanup.

A green import/grep test is not sufficient functional closure. A failure in current-owner regression must be repaired before P6-C.

Record the exact commands, counts, failures/skips, and disposition of every failure in P6 implementation evidence.

---

## 5. P6-C — test/spec/document/public-surface reconciliation

### 5.1 Current tests and specifications

Replace obsolete topology assertions rather than weakening V7 to keep them green. Delete/rewrite assertions whose only contract is:

- fixed target-size universe/ceiling;
- prepare must run MVSEL2 -> REPAIR2 -> MVQUAL2 -> target-size;
- old prepare receipt keys;
- label-domain namespace resolution for target-size;
- per-final/CV-domain target-size materialization;
- complement/coarse target evaluation;
- preselection CV/MLCV ownership of target-size choice.

Preserve or strengthen behavioral coverage for:

- one public target-size scheduler/execution authority;
- paired optimizer seeds;
- exact continuation/restart;
- exact selected-data freeze before CV;
- final-production horizon independence;
- real DATA8/TRAIN2/EVAL2 semantic owners;
- P4 currentness, destructive-ownership, and stale-generation rejection;
- P5 replay/foundation/mode identity;
- P5 provider construction and explicit provider retirement;
- numerical failure semantics;
- optimized-kernel reference/performance equivalence for retained kernels only.

### 5.2 Documentation and source maps

Reconcile current architecture manuals, specifications, source maps, CLI help, and config examples with the assembled implementation.

Requirements:

- no current document presents retired target-size topology as current authority;
- current source maps point to actual P1-P5 owners after cleanup;
- current examples expose only current supported configuration;
- historical snapshots remain clearly historical and need not be rewritten into current architecture;
- generated documentation inputs remain reproducible;
- do not delete useful historical rationale merely to make a search for retired terms empty; structural absence applies to current authority/runtime surfaces, not clearly marked historical records.

### 5.3 P6-C verification

Run:

1. documentation link/reference/lint/build checks applicable to touched docs;
2. test collection/import checks after test deletions/moves;
3. public API/source-map review against the P6-A disposition ledger;
4. any stage-local affected functional tests required by executable changes made during P6-C.

Documentation-only edits do not require artificial executable stages, but any code/test-helper/config change does.

---

## 6. P6-D — final accepted-contract reconciliation before broad tests

Before final broad regression, inspect the complete assembled P6 diff against the frozen parent plus the protected owner snapshot in Sections 1 and 3.

Explicitly verify, from current source/call edges rather than test names alone:

1. provenance is advisory and separate from numerical-label identity;
2. neutral substrate has no compatibility-domain partition axis or pre-target CV authority;
3. there is one current `P_train/M3`, one `pi_train`, one `pi_eval/M` ladder, and one P4 target-size reducer;
4. common deterministic preparation is shared across `N`/seed;
5. only optimizer seeds are screening replicates;
6. exact continuation and exact `M_i` evaluation remain intact;
7. current persistence/runtime authority is current-generation only;
8. P4 `CampaignStore` currentness and selected binding remain authoritative;
9. stale validated snapshots cannot be exposed as current after generation advancement;
10. CV consumes exact current `T_selected`, full protected-relation exclusion, and cannot feed back into selection;
11. final production is fresh on full exact `T_selected`;
12. P5 replay/foundation/mode/head/lineage semantics remain fail closed;
13. real TRAIN2/provider/EVAL2 owners remain in the assembled path;
14. P5 provider close/non-overlap semantics remain intact;
15. retired scientific authorities are absent from current runtime/API instead of hidden behind wrappers;
16. every retained legacy-looking surface has an R2-R6 justification in the disposition ledger.

A material omission is repaired before P6-E. Green tests do not substitute for this conformance pass.

If this review discovers that current accepted behavior still genuinely depends on a supposedly retired scientific authority, stop destructive deletion for that surface and apply the reopen rules in Section 10 rather than masking the dependency.

---

## 7. P6-E — fresh final affected-surface regression

### 7.1 Re-derive the final affected surface

Derive the affected regression surface from the **final P6 candidate diff**, including deleted modules and transitive import/caller effects. Do not reuse only the original P6 deletion list.

At minimum include every still-material affected area across:

- DATA2/DATA3/current identity/provenance;
- duplicate/protected-relation/neutral statistical base;
- current target-size preparation and selection;
- current P3 screen/restart;
- P4 CampaignStore/state/currentness/retention/destructive ownership/terminal selection;
- DATA7/DATA8;
- TRAIN2 and wrapper/prelaunch authentication;
- EVAL2/provider authentication/reduction/provider lifetime;
- CLI/config/public imports;
- persistence/restart/reopen;
- post-selection CV and any independently supported MLCV surface touched;
- fresh final production and publication.

### 7.2 Required final regression

Run:

1. all focused tests material to retained P1-P5 behavior touched by P6;
2. complete affected regression derived above;
3. broader/full repository CPU-safe suite because P6 crosses package exports, foundational identities, persistence, and orchestration boundaries unless the implementation can independently demonstrate a smaller complete bound;
4. repository/project-required static/type/lint/build checks that apply to changed files;
5. documentation build/lint/reference checks where applicable.

A required check that does not execute is not a pass. Attribute only demonstrably pre-existing unrelated failures, with evidence.

Long production-scale GPU/real-data qualification is not part of this gate. Existing intentionally deferred/target-machine qualification remains explicitly reported as deferred rather than silently counted as passing.

---

## 8. P6-F — bounded assembled real-owner integration through completed final publication and restart

### 8.1 Required assembled path

Execute a bounded end-to-end semantic path on the same final P6 candidate:

```text
real config/source ingestion
 -> current neutral substrate
 -> current preparation authorities
 -> bounded real P3 target-size paired screen
 -> real P4 reducer
 -> real CampaignStore current terminal selection
 -> persist exact N_selected / T_selected
 -> close and reopen store/process context
 -> reauthenticate current terminal selected authority
 -> create/run real post-selection CV orchestration
 -> all-required bounded CV campaign acceptance
 -> reauthenticate method/foundation/replay/current selected binding
 -> fresh full-T_selected final-production orchestration
 -> final run completes through real final semantic owner
 -> final evidence/current publication completes
 -> close providers/store/process context
 -> reopen CampaignStore/current context
 -> reauthenticate current selected binding + CV + final publication
```

Do not stop acceptance at “final-production entry”. P6 final closure must exercise completed bounded final production, publication/currentness, and reopened-store reauthentication.

### 8.2 Owners that must remain real

The assembled acceptance must traverse the actual current semantic owners, including as applicable:

- production config parser/resolution;
- real CLI/current orchestration entry points;
- real CampaignStore/SQLite and P4 state/currentness transitions;
- current P3 screen owners and P4 reducer/terminal projection;
- real selected binding from CampaignStore;
- real P5 method/foundation/replay identity resolution;
- real CV/final currentness and authorization;
- real DATA7/DATA8 materialization ownership;
- real `Train2RuntimePlan` construction;
- real `MacePostSelectionTrainer` request/prelaunch authentication/config/env/cwd ownership;
- canonical TRAIN2 summary/checkpoint authentication;
- real candidate provider authentication;
- real `build_post_selection_foundation_baseline_provider()`;
- real `MaceCalculatorProvider.from_model_path()`;
- real EVAL2 reduction/admissibility/target-only checkpoint/representative selection;
- real provider acquisition/retirement orchestration from P5A6;
- real final evidence/current publication;
- real restart/currentness reauthentication after reopen.

### 8.3 Allowed bounded fakes

To keep P6 functional closure CPU-safe and bounded, expensive scientific numerical work may be substituted only **below** the semantic owners listed above:

- external MACE numerical training may use the existing accepted bounded fake/wrapper seam below `MacePostSelectionTrainer`;
- low-level MACE model-load/forward numerical dependency may be bounded/faked only where existing P5 acceptance already permits it while retaining the real mdstats provider owner;
- tiny synthetic scientific datasets/checkpoints may be used when they exercise the real owner and identity checks.

Forbidden substitutions include:

- injected/precomputed selected authority;
- injected/precomputed replay lineage;
- seeded CV acceptance or seeded final authorization;
- replacing `MacePostSelectionTrainer`;
- replacing `build_post_selection_foundation_baseline_provider()`;
- replacing `MaceCalculatorProvider.from_model_path()`;
- bypassing CampaignStore/currentness/restart;
- fabricated post-decision EVAL2 metrics;
- bypassing provider close scopes;
- helper-only/proxy execution that stays green when the real current owner is broken.

### 8.4 Counterfactual acceptance

Focused and/or assembled tests must collectively demonstrate failure for representative broken current-owner cases affected by cleanup, including where applicable:

- stale generation/current terminal exposure after CampaignStore advances;
- retired derived state attempting to masquerade as current V7 authority;
- missing/corrupt current persisted identity required for restart;
- broken TRAIN2 authentication/summary;
- provider construction/authentication failure;
- provider evaluation exception still triggering explicit close;
- final publication/currentness mismatch on reopen.

These counterfactuals need not all live in one monolithic integration test. Prefer focused owner tests plus one readable assembled lifecycle test.

---

## 9. P6-G — deterministic/reference/resource closure

Run bounded non-production checks needed to show that cleanup did not degrade engineering fitness.

### 9.1 Determinism and restart

Verify:

- deterministic reproduction of current selection/evidence for fixed bounded inputs/seeds;
- exact restart/reopen behavior at affected P3/P4/P5 boundaries;
- no retired fallback changes current identity/digest/currentness decisions.

### 9.2 Reference equivalence

For every optimized selector/repair/EVAL2/etc. kernel retained under R2/R3/R6 because it has a concrete current/independent caller, run its applicable reference-oracle/equivalence tests.

Do **not** retain a dead kernel merely because the original P6 mentioned a reference test for it.

### 9.3 Resource and algorithmic closure

Where P6 changes execution/resource machinery, check bounded CPU/RAM/VRAM/I/O behavior and ensure no accidental regression to repeated per-domain/scalar work.

Always rerun the affected P5 provider-lifecycle guards if cleanup touches provider execution/imports so that:

- candidate provider retirement remains exception-safe;
- candidate is closed before foundation-provider construction;
- foundation and outer providers close on success/failure;
- no new residency cache/GC-only behavior defeats the accepted lifecycle.

M-ladder decision-preservation/performance qualification on representative production evidence may be reported `deferred/unavailable` if the required representative evidence is not available. Do not manufacture a pass from synthetic timing.

Long target-machine GPU/real-data production qualification remains deferred to final release.

---

## 10. Reopen/stop conditions and delegated implementation decisions

### 10.1 Reopen triggers

Implementation must stop destructive removal of the affected surface and amend/reconcile the workplan if any of the following occurs:

1. a supposedly retired authority is still a genuine current P1-P5 scientific/authorization dependency;
2. cleanup would require changing frozen target-size/CV/final scientific semantics rather than only removing retired topology;
3. a valid current P5A6 persisted state cannot be reopened without a material schema migration not already authorized here;
4. an independently supported non-target-size public feature would be broken and cannot be preserved by a bounded neutral-owner refactor;
5. the exact P5A6 baseline has materially changed before implementation;
6. a new product-level compatibility policy is required rather than the existing destructive-generation/current-generation cutover.

Do not solve these by adding broad compatibility fallbacks, rebuilding old plans from partial evidence, or weakening current validation.

### 10.2 Delegated implementation choices

Implementation may choose, based on current repository evidence:

- exact neutral module/file placement for R3 shared-kernel cutovers;
- exact grouping of related deletions into commits/stages;
- exact bounded synthetic fixtures and low-level numerical fakes within Section 8.3;
- exact test file organization after obsolete-test deletion;
- exact documentation file set derived from current source maps.

These choices are delegated only when they preserve the frozen semantic owners and acceptance requirements above. Equivalent implementation preferences with no material engineering benefit do not require a design amendment.

---

## 11. Implementation evidence and stage ledger

P6 implementation must maintain auditable evidence, preferably in an adjacent P6 progress/evidence record or equivalent protocol-approved implementation record, containing at minimum:

1. exact starting commit/tree;
2. P6-A disposition ledger, including retained R2-R6 justification;
3. materially deleted modules/symbols/schemas/public exports and why each was retired;
4. any R3 cutover and its old/new owner mapping;
5. stage-local test commands/results after executable cutover/cleanup stages;
6. final affected-surface derivation;
7. final focused/affected/broader regression commands and results;
8. assembled real-owner integration command/result and bounded fake seams used;
9. deterministic/reference/resource checks and results;
10. documentation/build checks;
11. explicit deferred production/GPU qualification items;
12. unresolved failures, if any, with classification as new implementation issue, pre-existing unrelated issue, or reopen trigger.

Do not report a check as passed when it was not executed. Do not use absent CI status as either failure or success; report the actual commands/results executed for P6 closure.

---

## 12. Final P6 exit gate

P6 and the complete V7 implementation are accepted only when all of the following are true on one final candidate:

- implementation started from/reconciled against the exact accepted P5A6 baseline;
- the P6-A census/disposition ledger is complete for material retired/current-mixed surfaces;
- all R3 current/shared cutovers were proven before destructive deletion;
- retired current scientific authorities, aliases, migration/reconstruction helpers, and unsupported public exports are structurally absent rather than hidden behind wrappers;
- independently supported/shared current functionality survived under a legitimate owner;
- P1-P5 frozen scientific semantics remain unchanged;
- P4 CampaignStore/STOR/currentness/restart/selected-set ownership remains intact;
- P5 identity/CV/final/TRAIN2/provider/EVAL2/provider-lifecycle ownership remains intact;
- valid current-generation state reopens and authenticates correctly;
- obsolete derived state cannot be promoted into current V7 authority;
- stage-local affected regression passed after material executable cleanup;
- final affected-surface regression and required broader CPU-safe checks passed;
- assembled real-owner integration passed from config/source through selection, reopen, CV, **completed fresh final production**, publication, and a second reopen/currentness reauthentication;
- retained optimized kernels passed applicable reference-equivalence checks;
- bounded resource/lifecycle checks relevant to changed execution machinery passed;
- current documentation/public API/source maps match the implemented architecture;
- unavailable production-scale/target-GPU qualification is explicitly separated from functional acceptance;
- no unresolved material conformance or implementation defect remains.

Only after this gate may the complete P6/V7 candidate be presented for independent **Software Design** review and merge/freeze decision.
