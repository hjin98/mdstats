---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R6
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
package_revision: 6
status: active
amended_date: 2026-08-30
amends:
  - P6_REVISION_3_BASE.md
  - P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md
  - P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md
precedence: this amendment overrides earlier P6 text only where explicitly stated; all other obligations remain binding
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P6 revision 6 amendment — clean storage-neutral handoff for the post-P7 storage reset

## 1. Purpose and scope

The storage-management subsystem predates several major target-size, post-selection, persistence, and downstream-qualification architecture revisions. Independent Design review found that its low-level ownership and integrity primitives remain useful, but its STOR1-STOR5 semantic policy still contains retired `evaluate` / `verify` / DATA7-DATA8 / old checkpoint-selection assumptions and path-derived artifact meaning.

The accepted response is **not** to rebuild storage inside P6. The storage renewal is a separate successor package, `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`, which may begin only after both P6 and P7 pass their own independent verification cycles.

P6 therefore has one additional responsibility: leave the current P1-P5 architecture in a **storage-neutral, owner-clean state** so the later storage package can consume clear semantic owners rather than reverse-engineer old stage names or path conventions.

This amendment does not reopen P1-P5 scientific semantics, target-size selection, post-selection CV, fresh final production, the P5A6 compatibility boundary, or P7 downstream-qualification design. It does not authorize implementation of the future storage inventory, policy resolver, archive-v2, storage leases, or I/O optimization package inside P6.

## 2. Frozen handoff principle

P6 must enforce the following separation:

```text
P1-P5 scientific/runtime owners
  own identity, currentness, restartability, immutable publication and root location

transitional storage surface during P6/P7
  may inspect and protect those owners
  may reclaim only state proven disposable without retired lifecycle assumptions
  may not infer scientific meaning from legacy stage names or pathname folklore

post-P7 storage reset
  owns cross-owner inventory, retention/reclamation policy, dedup/archive policy,
  storage admission, storage-operation leases, and I/O optimization
```

The later storage package must receive **objects and owner entry points**, not a partially renewed STOR1-STOR5 policy embedded in P6.

## 3. P6 implementation obligations

### P6-SH1 — remove storage dependence on retired lifecycle semantics

**Concern / rationale:** Current central storage logic still contains conditions such as authoritative `evaluate` completion, `verify` completion, DATA7/DATA8 rematerialization, old evaluation-capsule lifetime, and old verification replay. Renaming those predicates to current commands would preserve the wrong architecture.

**Required end state:** No P1-P5 current scientific operation and no automatic current-generation cleanup decision may depend on a retired `evaluate`, `verify`, `preflight`, SELECT2, per-domain DATA7/DATA8, old protocol-freeze, or equivalent renamed lifecycle predicate.

**Required consequences / constraints:**

- do not implement `evaluate -> cross-validate` or `verify -> train-production` substitutions;
- current `prepare`, `select-target-size`, `cross-validate`, and `train-production` completion/currentness remain owned by their actual P1-P5 records and resolvers, not storage stage aliases;
- cleanup invoked from current execution may remove only attempt-local/stale scratch or exact reconstructible cache state whose safety is established independently of the retired lifecycle;
- ambiguous current-generation P3/P5 evidence fails toward retention;
- no storage decision may make a stale historical generation current, mutate `N_selected/T_selected`, alter CV acceptance, or alter final-production evidence.

**Acceptance evidence:** structural absence checks over current storage predicates plus focused current lifecycle tests proving current operations do not read retired stage names for scientific or destructive authorization.

### P6-SH2 — expose clean P3 and P5 owner entry points without creating a storage-specific authority

**Concern / rationale:** The post-P7 storage implementation must not classify current evidence by matching `.mdstats/target-size`, `.mdstats/post-selection`, `runs`, `models`, filename suffixes, or other layout conventions.

**Required end state:** Current P3/P5 owners expose stable, generation-neutral programmatic entry points sufficient for another subsystem to locate and authenticate their state.

At minimum the current product must have one obvious owner path for each of the following facts:

```text
current campaign target-size revision / generation
current P3 execution root for that generation
P3 reconciliation / reachability / retention protection
current selected binding (N_selected + exact T_selected)
current P5 post-selection root for that selected generation
current P5 immutable evidence store and current pointer resolution
P5 run identity and completed-run evidence resolution
```

Existing accepted functions such as target-size execution-root locators, the P3 retention/reconciliation owner, selected-training context, post-selection root/store, and current post-selection record resolvers should be consolidated/reused rather than wrapped behind a duplicate storage registry.

**Required consequences / constraints:**

- storage policy itself remains outside those scientific owners;
- P3/P5 modules must not gain `safe/cache/recompute/compact/archive` enums or deletion policy merely to satisfy this handoff;
- the root/currentness functions must be usable without parsing human-readable logs or scanning arbitrary workspace trees;
- immutable records must carry enough lineage that a future storage adapter can distinguish current, stale/historical, corrupt, and incomplete state through the owner.

**Acceptance boundary:** The real P3/P5 currentness/reconciliation/persistence owners must execute. A test-only artifact registry that mirrors their answers is not acceptance.

### P6-SH3 — quarantine stale consequential STOR semantics during the transition

**Concern / rationale:** The complete storage redesign is intentionally deferred until after P7, but known-stale destructive semantics must not remain free to mutate the newly cleaned P1-P5 generation in the meantime.

**Required end state:** Until `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` is implemented, central storage operations are conservative on current-generation P3/P5 artifacts.

**Required consequences / constraints:**

- read-only accounting/reporting may remain available, but any classification derived from old path families is advisory and cannot widen deletion authority;
- current-generation P3 execution evidence and P5 post-selection evidence are protected unless their semantic owner independently proves the exact candidate disposable;
- old generic `recompute` / `compact` capability-loss logic must not be applied to current P3/P5 state by analogy;
- deduplication or cold archival must not newly include P3/P5 evidence merely because it is large or immutable-looking; successor storage design owns that admission decision;
- if an existing consequential storage command cannot establish current-generation safety without retired semantics, it must fail closed or clearly restrict itself to independently safe legacy/non-current material rather than pretending current support;
- external configured user/reference inputs remain non-destructible under the existing ownership boundary.

This transitional conservatism is intentional. It trades reclamation opportunity for a clean handoff and must not be treated as the final storage design.

### P6-SH4 — preserve proven low-level storage primitives as implementation substrate

P6 cleanup must not delete or rewrite proven generic primitives merely because their old STOR orchestration is stale. Preserve, when still independently used and conforming:

- campaign ownership/containment and protected-input checks;
- safe symlink unlink-versus-traversal distinction;
- append-only cleanup-event integrity helpers;
- P3 publication-race retention protection;
- content-addressed immutable publication helpers;
- frame-cache mmap representation and other current cache codecs;
- DATA4/DATA6 sharded persistence that remains current;
- shared SHA/validation receipt machinery;
- generic archive byte-authentication helpers when not coupled to stale candidate-selection policy.

P6 may locally refactor imports/locations if needed for its own cleanup, but must not prematurely redesign these primitives around the future storage workplan.

### P6-SH5 — leave current configuration and documentation semantically honest

**Required end state:** Current P6 surfaces must not claim that the old STOR1-STOR5 semantic roadmap is the fully aligned current-generation storage architecture.

Required P6-level corrections are limited to truthful handoff state:

- current architecture/user documentation states that storage is orthogonal to P1-P5 and that the old storage policy requires a post-P7 renewal;
- historical STOR1-STOR5 chronology may remain in history/release material, but must not override current architecture;
- current generated configuration must not use retired `remove_*_after_evaluate`, `*_after_verify`, DATA7/DATA8 or equivalent old lifecycle keys as authoritative current cleanup policy;
- do not add the future storage package's final configuration schema inside P6. Remove/disable stale current-authoring keys where necessary and leave future policy to the successor package.

### P6-SH6 — produce a clean post-P6 storage handoff surface

At P6 closure, Design/Implementation must be able to identify the current P1-P5 persistent/runtime roots without interpreting old storage tiers:

```text
CampaignStore/current campaign state
P3 current generation + execution root + reconciliation/retention owner
P4 current selected binding
P5 selected-generation evidence root + immutable object store + run roots
current cache/index owners that remain independently supported
```

This is not a new persisted manifest. Source/API structure and current architecture documentation are sufficient when unambiguous.

The P6 handoff is unacceptable if a later storage implementation would still have to ask questions such as “is `evaluate` complete?”, “has `verify` passed?”, “is this DATA8?”, or “does this pathname look like the selected checkpoint?” in order to determine the meaning of current P1-P5 state.

## 4. P6 task-specific acceptance additions

Add these checks to the revision-5 final affected-surface closure where applicable:

1. **Structural retirement:** no current P1-P5 destructive authorization path uses retired `evaluate`/`verify`/DATA7-DATA8 lifecycle semantics.
2. **P3 owner boundary:** publish/reconcile/current-generation tests prove current P3 roots/evidence remain protected during the publication-before-adoption window.
3. **P5 owner boundary:** completed and in-progress post-selection state reopens through real P5 owners; central storage cannot delete its current run/evidence roots under stale generic tiers.
4. **External ownership:** existing configured-input and symlink-escape protection remains green.
5. **Current lifecycle integration:** bounded real-owner `prepare -> select-target-size -> cross-validate -> train-production` continues to pass with storage cleanup unable to change scientific/currentness outcomes.
6. **Public/config honesty:** current help/config/docs do not advertise stale STOR-era lifecycle predicates as current authority.

Long storage throughput/footprint tuning, archive codec choice, dedup expansion, storage ledger implementation, HPC/shared-filesystem benchmarking, and post-P7 artifact retention are explicitly **not P6 acceptance obligations**.

## 5. Implementation authority

### Frozen

- Storage renewal is a separate successor after P7; P6 must not absorb it.
- P1-P5 semantic owners, not storage, own scientific identity/currentness/restartability.
- Retired lifecycle predicates cannot be rebound to new command names.
- Ambiguous current-generation artifacts fail toward retention.
- Proven generic ownership/integrity primitives are preserved unless independently obsolete.
- P6 must leave clear P3/P5 owner entry points for later storage adapters.

### Delegated

- Exact helper names and module placement for consolidating existing P3/P5 root/currentness access.
- Whether stale consequential storage commands are hidden, rejected, or restricted, provided current-generation safety and truthful UX are preserved.
- Exact wording of the transitional storage limitation in current docs/config help.

### Reopen only on evidence

Reopen this amendment only if repository evidence shows that:

- a current P1-P5 correctness/restart requirement materially depends on one of the stale storage policies;
- a required current-generation cleanup capability cannot be made safely conservative without implementing part of the future storage architecture; or
- the existing P3/P5 owners cannot expose an unambiguous currentness/root boundary without changing their frozen scientific semantics.

Reopen only the affected handoff surface; do not reopen target-size or CV science by default.

## 6. Sequencing

This amendment belongs to P6 cleanup/cutover closure. The intended product sequence is now:

```text
P6 revision-6 cleanup/storage-neutral handoff
 -> independent P6 cleanup/cutover PASS
 -> P7 V7-native publication + downstream qualification
 -> independent P7 PASS
 -> CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1 implementation
```

P7 has a companion storage-successor preparation amendment. The successor storage workplan is not an alternate P6/P7 implementation path and must remain `planned` until both entry gates pass.
