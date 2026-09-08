---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R7
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
package_revision: 7
status: active
amended_date: 2026-08-30
amends:
  - P6_REVISION_3_BASE.md
  - P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md
  - P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md
  - P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md
precedence: this amendment overrides earlier P6 text only where explicitly stated; all other obligations remain binding
successor_p7_workplan: CODE-MLFF-TARGET-SIZE-V7-P7
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P6 revision 7 amendment — final cleanup/cutover closure contract

## 1. Purpose and closure diagnosis

P6 revision 7 is the final Design closure pass before the next implementation round. It folds the remaining independent-review findings into one implementation contract while preserving the scientific architecture already frozen by P1-P5 and the separate post-P7 storage-renewal boundary introduced by revision 6.

The implementation reviewed at the P6A1 point corrected much of the public V5 leakage, command lifecycle, configurable target-size ladder, and current documentation, but it left several material current-owner defects. Subsequent workplan-only commits did not change executable source, so these defects remain implementation obligations rather than rediscovery targets.

The remaining blockers are:

1. pre-target/per-method CV controls still participate in current preparation/configuration identity even though post-selection CV is supposed to have one canonical owner;
2. generated/current configuration still exposes settings whose owning verification/audit/dynamics implementations were retired, plus stage-named cleanup policy that belongs to the later storage reset;
3. the current public lifecycle can confuse a published final-production **plan** with completed final-production **run evidence**;
4. central storage still contains retired lifecycle semantics and must be made conservative/owner-clean without prematurely implementing the post-P7 storage redesign;
5. the P6 compatibility qualification currently risks conflating the distinct `P5A6 -> P6` and `P6 -> P6` restart claims;
6. current documentation/dependency ownership still contains residual wording in which DATA5/pre-target roles appear to own post-selection CV folds;
7. final structural and affected-regression acceptance must prove the assembled corrected system rather than only individual helpers or historical tests.

These are bounded P6 cleanup/cutover issues. They do **not** reopen target-size science, the paired-seed reducer, `N_selected/T_selected`, post-selection CV acceptance semantics, fresh final-production training semantics, P7 downstream qualification, or the post-P7 storage-reset architecture.

## 2. Frozen P6 end state

P6 is accepted only when the assembled current product has this ownership direction:

```text
current source/configuration
    -> neutral P1 preparation and protected relations
    -> P2/P3 target-size experiment and execution
    -> P4 one frozen N_selected + exact T_selected
    -> P5 post-selection CV policy/partitions inside T_selected
    -> P5 fresh final-production plan
    -> all required P5 final-production run evidence complete

orthogonal transitional storage
    -> may inspect/protect current owners
    -> may reclaim only independently proven disposable state
    -> cannot infer currentness from retired evaluate/verify/DATA7/DATA8 semantics

P7 (later)
    -> freezes FinalProductionPublication and downstream qualification

storage/I-O reset (after P7)
    -> owns cross-owner retention, dedup/archive, storage admission and I/O policy
```

The decisive ownership invariants are:

- target-size ancestors are independent of post-selection CV policy;
- `[post_selection.cv]` is the sole current authoring owner of post-selection fold count, partition seed, CV optimizer seeds, and any CV-only seed/partition mode;
- a final-production plan authorizes work but does not prove that required final-production work finished;
- storage is not a scientific/currentness owner;
- exact accepted P5A6 compatibility, final-P6 self-restart, and V5/V6 rejection are three different evidence claims with different producer lineage;
- current documentation and dependency graphs describe those same owners.

## 3. Implementation obligations

### R7-A — remove pre-target CV authority from current preparation and target-size identity

**Concern / rationale:** Current preparation still carries legacy per-method `cross_validation_folds`, `fold_partition_seed`, and `seed_mode` semantics into DATA4/DATA5 preparation and preparation identity. That permits a post-selection-only policy to influence an ancestor of target-size selection and leaves two apparent CV owners.

**Required end state:** Current P1-P4 target-size preparation, current preparation identity/invalidation, and current generated authoring are independent of post-selection CV controls.

**Required consequences / constraints:**

- the sole enabled training method may own target-screen optimizer seeds and method-specific training semantics, but it does not own post-selection fold count or fold partition seed;
- `[post_selection.cv]` alone owns `fold_count`, `partition_seed`, CV seeds, and any mode whose meaning couples optimizer seeds to CV partitioning;
- current generated method tables must not expose `cross_validation_folds`, `fold_partition_seed`, or a legacy `seed_mode` whose semantics include CV partition coupling;
- changing `[post_selection.cv]` must not alter DATA2/3/4 neutral scientific identity, the P1 neutral statistical base, P2/P3 target-size experiment/current generation, P4 selected binding, or the exact `N_selected/T_selected` result;
- legacy per-method CV fields may be read only when exact accepted-P5A6 compatibility or an independently supported non-target historical contract genuinely requires them. Such reads are compatibility-only: they cannot become current generated authoring, current target-size authority, or a current preparation-invalidation input;
- do **not** delete DATA5 wholesale merely because its historical structure contained CV fields. Preserve still-current neutral role/protected-relation evidence. Refactor the current target-size projection/identity so post-selection fold policy is absent from target-size ancestors;
- do not silently reinterpret an old field under a new meaning to avoid removal.

**Acceptance boundary:** The real current configuration resolver, current `prepare` owner, P1 neutral authority construction, P3 current generation/reconciliation, P4 selected-binding resolver, and P5 post-selection resolver must execute. A test that directly hashes a hand-built dictionary is not sufficient.

**Acceptance evidence:**

1. `init`-generated TOML and `campaign.toml.example` contain no current per-method CV fold/partition authoring;
2. current preparation identity/config projection structurally excludes legacy per-method CV-only fields;
3. mutate only `[post_selection.cv]`: P4 target-size generation and selected binding remain current while P5 CV/final descendants become stale/replanned as appropriate;
4. mutate target-size policy or target-screen optimizer seeds: target-size descendants invalidate through the real P2/P3/P4 owners;
5. exact P5A6 compatibility fixture still reopens unchanged under the compatibility path.

### R7-B — remove orphan current configuration and stage-named cleanup policy

**Concern / rationale:** The generated configuration still contains knobs whose owning implementations were deleted or deferred to P7/storage renewal. Current authoring must not preserve dead policy merely because old parsers still accept it.

**Required end state:** Every setting emitted by current `init`, current `campaign.toml.example`, and current help/docs has one real current owner in P1-P5 or generic runtime infrastructure.

**Known stale surfaces to remove from current generated authoring unless implementation proves an independent surviving current owner:**

- `foundation_audit_temporary_ram_mib` from the deleted foundation-audit path;
- downstream dynamics-only controls such as `parallel_dynamics_jobs`, `maximum_parallel_dynamics_jobs`, `dynamics_estimated_vram_mib_per_job`, `dynamics_estimated_ram_mib_per_job`, `dynamics_pipeline_buffer_jobs`, `dynamics_pipeline_buffer_mib`, `dynamics_prepare_working_memory_mib`, `dynamics_inference_working_memory_mib`, `dynamics_finalize_working_memory_mib`, `dynamics_shared_runtime_residency_mib`, and `estimated_dynamics_output_mib_per_case` while P7 dynamics does not yet exist;
- stage-named storage policy such as `remove_frame_cache_after_prepare`, `remove_shared_data7_cache_after_prepare`, `remove_shared_data8_fixed_file_cache_after_prepare`, `remove_evaluation_graph_cache_after_evaluate`, `prune_unselected_checkpoints_after_evaluate`, `prune_screened_out_checkpoints_after_evaluate`, and other `*_after_evaluate` / `*_after_verify` / DATA7-DATA8 cleanup semantics;
- historical smoke/verification cleanup authoring that has no independent current consumer.

This is an owner test, not a string-only test. Existing generic P3/P5 evaluation concurrency/resource settings may remain if the current P3/P5 runtime actually consumes them. Generic CPU/RAM/VRAM/disk policy may remain under its real current owner.

**Frame-cache lifetime correction:** the normalized mmap frame cache is a current performance artifact reused by later current owners. P6 must not automatically evict it merely because `prepare` committed. Until the post-P7 storage reset installs cost-aware retention, keep it through its current consumers or rebuild it only under an owner-explicit invalidation/recovery path. Do not preserve the stale `remove_frame_cache_after_prepare` default as current policy.

**Compatibility:** exact older TOML may remain readable where the P5A6 compatibility boundary requires it, but removed current-authoring fields cannot alter new current scientific semantics or reappear in freshly generated canonical configuration.

**Acceptance evidence:** generated-template/example parity; current parser/resolution tests; structural owner census over generated keys; no hidden current defaults for deleted owners; affected resource/scheduler tests for settings that remain; compatibility reopen for supported old current-generation TOML.

### R7-C — distinguish final-production planning from final-production completion

**Concern / rationale:** P5 publishes a `FinalProductionPlan` before executing the required final-production run matrix. A plan is authorization and identity, not completion. Current lifecycle/status logic must not report `train-production` complete merely because a plan exists.

**Required end state:** P5 exposes one real current completion resolver/projection that verifies all required final-production run evidence for the exact current final plan and selected binding.

**Required consequences / constraints:**

- `resolve_current_final_production_plan()` or equivalent plan resolution remains a plan/currentness operation and does not itself mean complete;
- completion requires every `required_final_seed`/required run in the current plan to have authenticated completed run evidence belonging to that exact run plan;
- partial publication after plan creation, interruption before the first run, interruption between required runs, missing/corrupt run evidence, or stale run-plan identity must remain resumable/incomplete or fail closed as appropriate;
- `status`, `advance`, `_current_lifecycle_is_complete`, transitional storage protection, and any public completion projection must consume the real P5 completion owner rather than plan existence;
- the durable stage marker may summarize completion only after the P5 owner has established it; the marker is not a substitute for owner reauthentication;
- do not implement P7 `FinalProductionPublication` inside P6. P6 needs only truthful completion of fresh final-production work; P7 later freezes the deployable publication/member set.

**Acceptance boundary:** Exercise real P5 planning, run-evidence persistence, current pointer/currentness, public `status`, and `advance`. Expensive MACE work may be bounded/faked below the accepted P5 trainer seam; the test may not seed a fake completion record or bypass the P5 run loop.

**Acceptance evidence:**

1. crash/stop after final plan publication but before first run: close/reopen reports final production incomplete and `advance` routes to `train-production`;
2. stop after a proper subset of required final runs: reopen resumes only missing runs and does not report lifecycle complete;
3. all required runs complete: status/advance report terminal P6 lifecycle completion;
4. corrupt/mismatched required run evidence cannot satisfy completion;
5. P5 completion identity is stable across close/reopen.

### R7-D — close the transitional storage boundary without implementing the successor storage system

Revision 6 remains binding. This section tightens the implementation consequence required for P6 PASS.

**Required end state:** Current P6 storage behavior is conservative and semantically honest while leaving clean P3/P5 owner entry points for the later post-P7 storage package.

**Required consequences / constraints:**

- no destructive/current cleanup decision uses retired `evaluate`, `verify`, `preflight`, SELECT2, DATA7/DATA8, old protocol-freeze, verification replay, or equivalent renamed stage predicates;
- do not substitute `evaluate -> cross-validate` or `verify -> train-production`;
- P3 current-generation execution evidence and P5 current/in-progress post-selection evidence fail toward retention unless their semantic owner independently proves an exact artifact disposable;
- P5 protection must include the object/run publication window before a current pointer or terminal completion projection is installed;
- old generic `recompute` / `compact` capability-loss semantics cannot act on current P3/P5 evidence;
- read-only reporting may remain, but pathname-derived classifications are advisory only and cannot widen deletion authority;
- existing `archive`/`deduplicate` operations must either restrict themselves to independently safe/owner-certified material or fail closed for current P3/P5 state. They must not claim that the old STOR1-STOR5 roadmap is the fully aligned current storage architecture;
- remove obsolete hidden top-level storage-command aliases if no explicit compatibility contract requires them; do not carry pre-0.20.117 routing complexity solely for historical convenience;
- preserve existing campaign ownership/containment, protected-input and symlink safety, P3 retention protection, immutable-publication helpers, frame-cache/DATA4/DATA6 codecs, shared hash receipts, and generic archive integrity primitives where independently current;
- expose clean generation-neutral P3/P5 owner entry points identified in revision 6; do not create a second storage registry that mirrors their state.

**Current storage documentation:** the old STOR1-STOR5 roadmap may remain only as history. The current normative storage/user documentation during P6/P7 must state the conservative transitional contract and the deferred post-P7 renewal. A current `mlff_storage_management_spec` cannot continue to state that the old roadmap is the fully complete/current architecture without an explicit historical boundary.

**Acceptance evidence:** structural absence of retired destructive predicates; P3 publication-race protection; P5 partial/completed-run protection; external/symlink ownership tests; current storage command/help behavior; bounded lifecycle integration with storage unable to change scientific/currentness outcomes.

### R7-E — make the three compatibility/restart claims genuinely independent

**Concern / rationale:** Reopening the same P5A6-produced workspace twice under final P6 proves repeated P6 reading of a P5A6 workspace. It does **not** prove that final P6 can create its own current workspace and later reopen it.

**Required end state:** The mandatory qualification driver establishes three distinct claims with producer lineage appropriate to each claim:

```text
A. exact accepted P5A6 producer -> final P6 unchanged reopen
B. final P6 producer            -> final P6 close/reopen/restart
C. retired V5/V6 producer/state -> final P6 reject-before-reuse
```

**Required consequences / constraints:**

- case A uses the exact accepted P5A6 commit/tree and baseline import-root authentication already frozen by revision 5;
- case B creates a **fresh final-P6 current workspace** through final-P6 real current owners. It must execute current preparation, current target-size selection, post-selection CV, and fresh final production through the actual final-P6 orchestration/currentness/persistence owners, with only expensive numerical MACE work substituted below accepted seams;
- case B then closes the process/store and reopens that P6-created workspace under final P6, reauthenticating current selected binding, CV acceptance, final-production completion, and current lifecycle state;
- case A's second reopen cannot be labeled or counted as case B;
- case C remains a separate obsolete-generation rejection fixture and must establish reject-before-reuse, not migration;
- report PASS/FAIL separately. Failure/unavailability of one case cannot be replaced by another.

**Acceptance evidence:** non-skipping qualification command, authenticated baseline P5A6 producer, distinct fresh-P6 workspace path/producer evidence, exact current-owner reopen assertions, V5/V6 rejection, and authoritative-content stability where the claim requires unchanged reopen.

### R7-F — finish current documentation and dependency ownership reconciliation

**Concern / rationale:** Most current documentation was corrected in P6A1, but residual ownership language can still make DATA5/pre-target partitioning appear to own current post-selection CV.

**Required current semantic model:**

```text
P1/DATA5 and neutral substrate
    own source-bound correlation/protected-relation and neutral evidence-role facts

P4
    freezes one global N_selected and exact T_selected

P5 post-selection CV
    constructs K fold-local training/monitor/held-out partitions only inside T_selected
    owns fold count, partition seed, CV seeds and CV acceptance
```

**Required consequences / constraints:**

- current Part I/III/V/VI/VII wording, assembled manual, current user guide, source maps, and dependency graph must not place `post_selection_cv_folds` in a pre-selection preparation role;
- dependency-graph/current ownership for held-out post-selection CV must point to the P5 post-selection CV owner (or an equivalent current owner), not ambiguous `DATA5/CV` ancestry that implies pre-target fold authority;
- DATA5 may remain the owner of neutral role/protected-relation evidence needed to make later folds leakage-safe, but it does not preconstruct target-size-authoritative CV folds;
- current storage docs must describe the revision-6/7 transitional contract, not a completed old STOR roadmap;
- P7 capabilities remain future/planned in P6 docs; do not document them as already implemented;
- chronology and superseded STOR/V5/V6 semantics belong in history/release material.

**Acceptance evidence:** focused semantic documentation assertions where robust; dependency-graph owner checks; current source-map/reference checks; documentation build/PDF regeneration; final Design conformance inspection of the affected current chapters/specs.

### R7-G — strengthen structural absence/current-owner checks

Structural tests must cover the actual current affected surface rather than only old top-level exports.

At minimum cover:

- public exports/facades and current schema/receipt constants from revision 5;
- generated config template and `campaign.toml.example`;
- absence of current per-method CV fold/partition authority and old CV-coupled `seed_mode` authoring;
- absence of known orphan verification/dynamics/audit/current cleanup keys from fresh current authoring;
- absence of retired `evaluate`/`verify`/DATA7-DATA8 destructive predicates in current storage authorization;
- real final-production completion resolver use by status/advance rather than plan-existence completion;
- current documentation/dependency graph owner names;
- exact allowlists for reject-only/historical identifiers rather than indiscriminate repository-wide string bans.

Do not weaken/delete previously valid affected tests merely because their old expected architecture changed. Replace historical-current assertions with tests for the newly accepted current semantics, and move pure chronology checks to history-oriented scope where useful.

## 4. Coherent next implementation round

Implement the revision-7 closure in four material stages. Do not split these into per-file micro-gates.

### Stage R7-1 — current configuration, preparation ownership, and P5 completion

Implement R7-A, R7-B, and R7-C together where their currentness/configuration projections interact.

Stage-local closure requires:

- focused config/identity/currentness tests;
- target-size preparation/P3/P4 regression;
- P5 CV/final-production partial-completion/restart tests;
- parser/status/advance regression;
- affected resource/scheduler/precision tests for retained configuration keys.

Dependent storage/public documentation work does not proceed with a hard failure in this stage.

### Stage R7-2 — transitional storage handoff and owner boundaries

Implement R7-D plus revision-6 P3/P5 owner-entry obligations against the accepted R7-1 candidate.

Stage-local closure requires:

- storage ownership/symlink/external-input regression;
- P3 publication-before-adoption protection;
- P5 object/run in-progress protection;
- storage command fail-closed/restriction tests;
- current lifecycle regression proving cleanup cannot change selected/CV/final currentness;
- affected frame-cache lifetime/reuse test.

This stage must **not** implement the post-P7 storage inventory/policy/lease/archive-v2 design.

### Stage R7-3 — compatibility qualification and documentation reconciliation

Implement R7-E, R7-F, and R7-G. The executable compatibility driver must distinguish the three producer lineages. Documentation is reconciled against the assembled executable semantics, not vice versa.

Run:

- mandatory non-skipping compatibility qualification A/B/C;
- structural/currentness checks;
- current docs/source-map/dependency-graph checks;
- documentation build/PDF generation.

### Stage R7-4 — final assembled P6 cleanup/cutover acceptance

Re-derive the affected surface from the complete P6 implementation plus revisions 5-7 and run fresh final acceptance on one candidate:

1. focused tests for all changed P1-P5/current public/storage-handoff mechanisms;
2. complete affected-surface regression;
3. real parser/dispatch assembled lifecycle `prepare -> select-target-size -> cross-validate -> train-production`, including close/reopen and currentness reauthentication, with only accepted bounded numerical seams below the real owners;
4. final-production interruption cases before/within required run completion;
5. the independent A/B/C compatibility/restart/reject cases;
6. storage cannot delete/proclaim current P3/P5 evidence through stale lifecycle semantics;
7. structural absence/current-owner checks;
8. repository-required static/build/documentation/PDF checks;
9. broader/full CPU-safe repository suite unless the final affected surface is independently and completely bounded smaller.

New hard failures or regressions plausibly intersecting this surface block P6 PASS. Demonstrably pre-existing unrelated failures may be attributed with baseline evidence. A skipped mandatory owner/compatibility check is not a pass.

Long target-machine GPU/real-data production qualification, exhaustive M-ladder decision-preservation qualification, P7 downstream physical qualification, and the post-P7 storage/I-O optimization package remain outside P6 functional acceptance.

## 5. Implementation authority

### Frozen

- P6 remains cleanup/cutover functional closure; P7 and storage renewal remain separate successors.
- Post-selection CV policy cannot influence target-size ancestors/current selected binding.
- `[post_selection.cv]` is the sole current post-selection CV authoring owner.
- Current generated configuration contains only settings with a real current owner.
- Final-production plan existence is not final-production completion.
- P6 completion requires all required current P5 final-production run evidence.
- Storage cannot use retired lifecycle semantics or become a second scientific/currentness authority.
- Ambiguous current P3/P5 artifacts fail toward retention during the transitional period.
- `P5A6 -> P6`, `P6 -> P6`, and `V5/V6 -> reject` are independent qualification claims.
- Current docs/dependency graph reflect P1/P4/P5 ownership accurately.
- Long GPU/production qualification remains deferred as previously authorized.

### Delegated

- Internal helper/module names used to remove old method-CV fields from current preparation.
- Exact shape of a P5 final-production completion resolver, provided it is owner-authenticated and not a duplicate mutable authority.
- Exact transitional storage UX for stale consequential operations: hide, reject, or restrict are all acceptable when behavior is fail-closed and honest.
- Exact wording/location of current transitional storage documentation.
- Test fixture sizes and bounded numerical fake implementation below accepted MACE seams.

### Reopen only on evidence

Reopen Design only if implementation evidence shows that:

- exact P5A6 compatibility materially requires a legacy CV field to participate in current target-size scientific identity rather than compatibility-only reading;
- a P1 neutral scientific invariant genuinely requires post-selection CV partition policy before target selection;
- final-P6 current workspace creation cannot exercise the real P1-P5 owners without changing frozen scientific semantics;
- safe transitional storage cannot protect current P3/P5 evidence without implementing a material part of the post-P7 storage architecture; or
- the P5 final-production evidence model cannot distinguish plan from complete required-run evidence without a material persistence redesign.

Reopen only that affected surface. Do not reopen target-size science, P7, or storage-reset architecture by default.

## 6. P6 PASS definition after revision 7

A P6 cleanup/cutover PASS requires all of the following on one assembled candidate:

```text
retired V5/V6 current-authority leakage removed/reject-only
+ current public lifecycle/config/docs coherent
+ target-size ancestors independent of post-selection CV policy
+ one canonical post-selection CV owner
+ truthful completed-final-production owner
+ storage-neutral/conservative P3/P5 handoff
+ exact P5A6 unchanged compatibility
+ independent final-P6 self-restart
+ V5/V6 reject-before-reuse
+ stage-local and final affected regression/integration closure
```

Only after that independent P6 PASS may P7 implementation begin.
