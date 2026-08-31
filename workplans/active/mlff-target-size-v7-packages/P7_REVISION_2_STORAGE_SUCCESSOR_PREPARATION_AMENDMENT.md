---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R2
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 2
status: planned
amended_date: 2026-08-30
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-6 cleanup/cutover functional acceptance PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
precedence: this amendment overrides the base P7 workplan only where explicitly stated; all other P7 obligations remain binding
---

# P7 revision 2 amendment — storage-neutral publication/qualification handoff

## 1. Purpose

P7 remains the V7-native replacement for post-production deployment, physical, calibration, and locked-test qualification. The storage-management subsystem will be renewed **after** P7, not inside it.

P7 therefore must build its new publication and qualification objects so they have explicit semantic ownership, currentness, immutable publication, restart state, and canonical roots that a later storage subsystem can consume directly. P7 must not create another generation of storage policy special cases that would require path-name inference or lifecycle archaeology.

This amendment does not change P7 scientific qualification semantics, evidence roles, publication-before-qualification rule, no-fallback rule, external-reference boundary, or locked-test one-shot policy.

## 2. Frozen post-P7 storage handoff

The post-P7 architecture must have this dependency direction:

```text
P7 publication / qualification owners
  -> expose canonical roots, identities, currentness, attempt/completion state
  -> own immutable records and restart semantics

future storage subsystem
  -> consumes those owner facts
  -> decides retention / cache eviction / archive / dedup / storage admission

never:
storage path classification -> P7 scientific meaning/currentness/publication membership
```

P7 must not implement the future `StorageInventorySnapshot`, cross-owner retention policy, global execution/storage leases, archive-v2 catalog, or storage I/O optimization workplan.

## 3. P7 implementation obligations

### P7-SH1 — one canonical P7 persistence/root boundary

**Concern / rationale:** The later storage subsystem needs a bounded object to inspect. Scattering deployment, PES, relaxation, dynamics, calibration, locked evidence, and temporary work under ad hoc `runs/`, `models/`, `verification/`, or per-command trees would recreate the path-derived semantic problem being retired.

**Required end state:** P7 has one obvious current-generation descendant persistence boundary for `FinalProductionPublication`, `ProductionQualificationPlan`, component evidence, terminal qualification records, and attempt-local bulk artifacts.

The exact directory/module names are delegated, but the architecture must provide canonical owner functions equivalent to:

```text
qualification root for one selected/publication generation
immutable evidence store / object resolver
attempt/run root locator from typed identity
current publication resolver
current qualification-plan/result resolver
```

Reuse the existing post-selection immutable descendant store when it is the natural owner and does not conflate P5 and P7 semantics; otherwise add one P7-owned descendant root. Do not duplicate the same evidence into multiple current authorities.

### P7-SH2 — make lifecycle facts owner-readable instead of pathname-readable

For every material P7 artifact family, the P7 owner must expose enough structured state to distinguish:

- current versus stale/historical publication lineage;
- immutable accepted evidence versus attempt-local/incomplete state;
- waiting-for-reference versus scientifically rejected versus passed/not-applicable;
- complete terminal component evidence versus partial/corrupt publication;
- exact referenced model/deployment/reference artifact identities;
- whether an attempt may still be resumed.

A future storage adapter must not need to inspect filename suffixes, search logs, or infer meaning from directory names to answer those questions.

**Required consequences / constraints:**

- attempt-local roots are derived from immutable attempt identities;
- completion is represented by validated owner records, never file existence alone;
- immutable P7 records are create-once/validate-existing or equivalent;
- currentness is re-established through P4/P5/P7 owners rather than persisted as a second mutable storage truth;
- stale/historical P7 evidence may remain on disk without becoming current.

### P7-SH3 — publication completeness becomes a real storage-relevant freeze boundary

The base P7 workplan already requires a `FinalProductionPublication` before downstream evidence. This amendment tightens its handoff role:

- the publication owner must expose the exact ordered published member set and authenticated member artifact identities through one resolver;
- publication is not considered complete merely because a final-production plan exists;
- all required P5 production runs and representative/member decisions required by the configured publication policy must be complete before publication;
- after publication, downstream qualification may create descendants but may never mutate publication membership;
- a later storage subsystem may use the immutable publication as the boundary between pre-publication restart-critical production state and post-publication descendant qualification state, but P7 itself does not decide archival/reclamation policy.

### P7-SH4 — qualification completion must be explicit and terminal

`ProductionQualificationRecord` (or an equivalent single terminal owner) must be sufficient for another subsystem to know whether the exact publication's qualification is:

```text
incomplete / waiting_for_reference / passed / rejected / not_applicable-as-policy-allows
```

Component evidence may remain separately typed, but there must not be six independent mutable “current” state machines that storage would need to reconcile.

A later storage subsystem may use the terminal record to determine that certain attempt-local artifacts are no longer needed hot, but only through P7's owner graph; it must not infer completion from absent processes or directory contents.

### P7-SH5 — keep temporary and bulk work attempt-scoped

P7 numerical/deployment/external-reference work may create substantial temporary or bulk files. Required execution structure:

- temporary/staging state lives under an owner-identifiable attempt root;
- final immutable evidence references only validated durable outputs;
- interruption leaves either resumable owner-recognized attempt state or disposable owner-local scratch, never ambiguous files mixed with accepted evidence;
- a failed/rejected qualification keeps the durable evidence necessary to explain the verdict;
- provider/process cleanup does not delete accepted evidence;
- no P7-private storage reclamation tier is introduced.

Owner-local removal of a failed attempt's clearly disposable temporary files remains valid and is not the future cross-owner storage subsystem.

### P7-SH6 — do not couple P7 to stale STOR1-STOR5 semantics

P7 must not:

- gate cleanup on retired `evaluate`, `verify`, DATA7/DATA8, SELECT2, or old protocol-freeze records;
- add new cases to pathname-based `_family_for()`-style central classification as the semantic source of truth;
- use old `recompute`/`compact` capability vocabulary to describe P7 qualification state;
- re-enable old checkpoint-capsule/verification-replay retention rules;
- require storage dedup/archive completion for a scientific qualification pass.

During P7 implementation the transitional central storage system remains conservative: current P7 roots are protected unless P7's own attempt owner proves a local scratch candidate disposable. The post-P7 storage workplan owns wider reclamation, deduplication, archival, admission, and I/O policy.

### P7-SH7 — document the successor integration points

At P7 closure, current architecture/source documentation must make these entry points unambiguous without defining the future storage policy:

```text
CampaignStore/current campaign state owner
P3 target-size generation/root/reconciliation owner
P4 selected binding owner
P5 post-selection root/store/run-completion owner
P7 final-publication owner/root/resolver
P7 qualification root/store/terminal-result owner
current cache/index owners
```

This may be described in the existing ownership/execution architecture manuals. Do not create a separate storage registry document merely for handoff.

## 4. P7 acceptance additions

The base P7 functional/scientific acceptance remains binding. Add these storage-handoff checks:

1. **Publication root/currentness:** real P4/P5/P7 owners close/reopen the exact `FinalProductionPublication` without path scanning or seeded post-decision state.
2. **Qualification root/currentness:** incomplete, waiting, rejected and passed terminal states are resolved through real P7 records; file presence alone cannot produce completion.
3. **Attempt crash boundary:** interruption during P7 artifact publication leaves no partial file that is accepted as durable evidence on reopen.
4. **No storage selection authority:** storage/cleanup helpers cannot mutate publication membership or qualification verdict.
5. **Transitional protection:** central pre-reset storage cleanup/dedup/archive cannot delete current P7 durable evidence based on stale generic tiers.
6. **Structural absence:** no new P7 semantic dependence on retired STOR-era stage names/path families.
7. **Assembled integration:** the full bounded P7 integration path still passes with current P1-P7 owner/currentness semantics while storage remains orthogonal.

These additions do not require production-scale storage benchmarks or the future storage subsystem itself.

## 5. Implementation authority

### Frozen

- P7 must leave canonical owner-level root/currentness/completion entry points for successor storage.
- P7 does not implement cross-owner storage policy.
- Publication membership remains immutable and downstream/storage evidence has no selection authority.
- Attempt-local, durable immutable, and terminal qualification state must be owner-distinguishable.
- P7 cannot depend on retired STOR1-STOR5 lifecycle predicates.

### Delegated

- Whether P7 shares the P5 immutable store or uses a new descendant store, provided ownership remains unambiguous and no evidence is duplicated as current authority.
- Exact root/helper names and internal attempt-directory layout.
- Owner-local cleanup of clearly disposable P7 temporary state.

### Reopen only on evidence

Reopen only if:

- the accepted P7 publication/qualification architecture cannot expose currentness/completion without introducing duplicated mutable state;
- a material runtime requires a persistence layout incompatible with safe immutable publication/restart;
- or P7 cannot protect its in-flight/durable artifacts during the transitional pre-storage-reset period without implementing a portion of the successor storage architecture.

## 6. Sequence and successor gate

The sequence is binding:

```text
P6 cleanup/cutover + storage-neutral handoff PASS
 -> P7 publication/qualification + storage-neutral handoff PASS
 -> freeze accepted P7 baseline
 -> CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1 implementation
```

The storage package must not begin against an unaccepted or still-changing P7 persistence model.
