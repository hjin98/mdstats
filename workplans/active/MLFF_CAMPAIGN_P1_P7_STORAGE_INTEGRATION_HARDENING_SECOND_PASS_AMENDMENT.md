---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING-R2
parent_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
reviewed_parent_head: c97f4b6399f64b9902443002b63ce007cd589bc3
scope: second-pass assembled integration closure for generation-safe frame persistence, config/currentness taxonomy, P7 public lifecycle, publication races, observation consistency, storage operation coverage, locked-history retention, and numerical acceptance precision
verdict: NO-PASS / INTEGRATION-REOPENED
precedence: this amendment tightens or corrects the parent integration workplan only where stated; every non-conflicting parent invariant, Frozen decision, obligation, acceptance boundary, simplification rule, and closure criterion remains binding
---

# MLFF campaign integration hardening — second-pass amendment

## 0. Second-pass verdict

**NO-PASS / INTEGRATION-REOPENED remains correct.**

The first integration workplan recovered the correct product boundary and is implementation-ready in its main architecture. A second independent pass found additional cross-boundary gaps that would still permit a locally conforming implementation to fail under generation advance, configuration change, public lifecycle routing, storage transformations, or concurrency.

These findings do **not** reopen P1-P7 scientific algorithms, P6 package-local closure, P7 qualification science, CampaignStore CAS architecture, or Storage Revision 38's canonical destructive architecture. They tighten the assembled integration contract and repair Tier-2 persistence/control-plane assumptions before implementation begins.

The controlling integration handoff is now the composition of:

1. `MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md`; and
2. this second-pass amendment, which has precedence only for the corrections below.

## 1. Additional failure families

### F8 — the current normalized frame cache is mutable beneath an allegedly immutable prepared generation

The current frame-cache layout is keyed by `run_id`, not by the complete immutable source/control/content identity. `write_frame_data_cache_entry()` publishes a new temporary directory and then replaces the existing `run-<hash(run_id)>` destination, deleting the previous directory. `finalize_frame_data_cache()` similarly replaces the single top-level `frame-cache.json` manifest.

That behavior was safe while the frame cache was merely reconstructible acceleration state. It is **not** safe if a prepared generation treats the same mutable pathname as a required restart dependency.

A failure sequence is currently possible in the target design if this is not corrected:

```text
g1 is current and consumes normalized frame payload F1
 -> operator changes preparation-owned source/control bytes
 -> new prepare starts constructing future g2
 -> frame-cache writer replaces F1 at the shared run-id path with F2
 -> process crashes, loses CAS, or another writer wins before g2 adoption
 -> CampaignStore still says g1 is current
 -> g1's required prepared dependency has been mutated/deleted
```

This violates immutable-generation semantics, publish-before-adopt failure atomicity, restartability, and Storage R38 ownership truth.

**Required end state:** retain **one** canonical normalized-frame representation, but change its Tier-2 storage realization so an adopted prepared generation binds immutable/versioned/content-addressed frame members or an equivalent generation-safe representation. A later prepare may publish new normalized content without overwriting or deleting any object still required by the current/in-flight generation before successful adoption.

A mutable discovery index or convenience alias is permitted only as an acceleration locator. No prepared generation, currentness decision, or storage-retention decision may depend on that alias remaining unchanged.

Do **not** solve this by copying DATA4 or creating a second full normalized-frame cache per generation. Prefer immutable member reuse keyed by source/content/control identity, with compact prepared-generation membership binding.

### F9 — configuration invalidation is under-specified across the assembled lifecycle

The parent workplan tests source mutation, P5-only policy changes, P7-only policy changes, and execution-only resource changes, but does not explicitly distinguish preparation-scientific changes from P3 execution-context changes. That leaves two unsafe implementation freedoms: over-invalidating P1/P2 for a downstream execution change, or mixing a newly changed preparation/P3 policy with an old persisted generation/attempt.

The integration contract therefore requires an explicit **configuration ownership taxonomy**, derived from existing owner identities rather than a new registry:

1. **Preparation-scientific identity** — configuration that participates in P1/P2/P3-common/prepared scientific identity or target-size experiment definition. A changed current config must never be mixed into old prepared state. Existing g remains immutable historical evidence; consequential work that requires the changed scientific config requires explicit `prepare` and fresh generation according to the accepted P4 identity contract.
2. **P3 execution/evidence identity** — configuration that does not change the prepared scientific substrate but does change accepted P3 execution context/evidence identity. It invalidates/restarts/rejects only the P3-owned attempt/evidence surface according to existing P3 semantics; it does not rebuild P1/P2 unless that setting is also preparation-scientific.
3. **P5-only identity** — changes only P5 descendants as already required by the parent plan.
4. **P7-only identity** — changes only P7 descendants as already required by the parent plan.
5. **Execution scheduling/volatile resources** — worker availability/free memory/concurrency realization that is intentionally excluded from scientific identity changes scheduling only.

The implementation may reuse existing config projections/digests and owner policy objects. A new central config-classification database or duplicated identity table is forbidden.

### F10 — the main public campaign lifecycle currently ends at P5, not P7

The accepted product lifecycle includes qualification after `FinalProductionPublication`, and P7 revision 13.7 explicitly identifies `qualification run` as the next operational validation after final production. The main campaign `PIPELINE` and `_current_public_lifecycle()` currently stop at post-selection final production; `command_advance()` can therefore report `Campaign is already complete.` immediately after P5.

That is a product-level integration defect: the public campaign control plane disagrees with the accepted P1-P7 lifecycle.

**Required end state:** core campaign status must project P7 qualification state after final publication. At minimum it distinguishes:

- qualification not started;
- active/incomplete qualification;
- `waiting_for_reference`;
- nonlocked completion with locked activation pending when required;
- terminal `RELEASE_QUALIFIED` / `REJECTED` or equivalent accepted P7 terminal verdict.

`advance` may route to the ordinary nonlocked `qualification run` when that is the admissible next command. It must **never** auto-activate the locked test. Locked activation remains the explicit irreversible P7 command with its existing confirmation contract. If the final implementation deliberately keeps qualification outside automatic `advance`, then `status`/next-operation guidance must still name `qualification run` and must never call the campaign complete at P5.

P6 is **not** inserted as a runtime stage. Its accepted package-local cleanup/compatibility obligations remain negative/cross-cutting preservation constraints, while Storage R38 is the current storage successor.

### F11 — future-generation publication and concurrent prepare races need an explicit atomicity contract

The parent plan covers immutable prepared publication and stale downstream writers, but not the full race around two prepares or a failed future prepare mutating current-generation dependencies.

**Required end state:** before a future generation wins CampaignStore adoption, it may create only unreachable/new immutable artifacts and run-local scratch. It may not overwrite, delete, retarget, or mutate any artifact required by the still-current generation.

Two concurrent prepares must have deterministic safe outcomes:

- identical preparation identity may converge/idempotently reuse the same immutable content and at most one current adoption transition;
- different preparation identities may not both populate conflicting bytes under the same fixed generation-scoped identity; one wins the current transition and the other rebases/retries at the owner boundary or fails cleanly according to the existing CAS contract;
- no outcome leaves a mixed-generation prepared snapshot.

Do not serialize the entire expensive prepare under one coarse campaign lock merely to avoid designing the publication boundary. Keep expensive construction outside the short adoption critical section where the accepted owner architecture permits it.

### F12 — observational lifecycle reads need a coherent snapshot and typed degraded-state semantics

Making status non-mutating is necessary but not sufficient. A read-only status can still report a state that never existed if it reads the target-size revision, then P5/P7 pointers while a concurrent writer advances the generation or publishes descendants.

**Required end state:** one status/lifecycle projection represents a coherent owner snapshot. An acceptable implementation may use one SQLite read transaction/snapshot across relevant CampaignStore rows or capture/recheck the state revision around pointer resolution. A concurrent writer may make status report either the state before or after the transition, but never a hybrid ancestry.

`advance` uses that snapshot only to choose the candidate next operation. It is **advisory routing, not authorization**: the selected consequential command independently reauthenticates current revision/currentness before doing work.

Corruption semantics must also remain useful operationally:

- consequential consumers hard-fail on a missing/corrupt required current artifact;
- observational status, when CampaignStore itself remains readable, reports a typed blocked/corrupt/incomplete state from compact evidence rather than silently treating corruption as `not_started`, repairing it, or executing science;
- if CampaignStore itself is unreadable/corrupt, status may hard-fail because no authoritative current state exists;
- status does not full-read/recompute large scientific artifacts merely to claim execution-level authentication. Its wording must distinguish compact persisted/pointer state from a full consequential reauthentication where material.

### F13 — Storage R38 acceptance must cover every affected storage operation, not cleanup alone

Storage Revision 38 covers report/inventory, cleanup/eviction, deduplication, archive, restore, and maintenance, with archive/restore/dedup deliberately specialized where their semantics differ. The parent integration matrix emphasizes cleanup and dry-run, which is insufficient after the prepared representation becomes a durable restart dependency.

The repaired prepared/frame representation must therefore be exercised through the affected Storage R38 operation family:

- report/inventory and plan construction;
- safe/cache cleanup/eviction;
- owner-certified deduplication;
- archive creation and any authorized hot-reclaim transition;
- archive verification and restore;
- CampaignStore/storage maintenance when it can touch records/references relevant to prepared state.

Required results:

- current or in-flight prepared/frame objects required for a valid next command are never transformed into an unavailable hot representation unless the consumer contract explicitly supports that representation without source/DATA4 regeneration;
- eligible historical/redundant normalized members may be deduplicated/archived/reclaimed only under owner authority;
- dedup preserves exact content identity and every current reference;
- restore reproduces the archived representation/integrity but never makes a historical generation current or edits CampaignStore scientific pointers;
- an eligible prepared/cache archive/restore round trip, when supported, does not require live-source or DATA4 scientific reconstruction;
- storage never acquires scientific authority from archive/dedup metadata.

The storage interleaving matrix additionally includes the **prepared-object/frame-payload publication-before-CampaignStore-adoption window**, not only P3/P5/P7 publication windows.

### F14 — locked-test disclosure is historical, not merely current-binding state

P7 correctly treats one-shot locked disclosure history separately from current qualification pointers: an already revealed cohort remains revealed even if the current binding later changes. The parent integration plan requires one-shot activation but does not explicitly test generation advance plus storage retention of this fact.

**Required end state:** after locked cohort activation under g1, a later `prepare`/g2 and new P7 binding cannot make the same cohort appear unrevealed. The immutable disclosure evidence needed to enforce the one-shot rule remains retained independently of whether the old P7 result is current. Storage cleanup/archive/dedup must preserve or equivalently represent that irreversible history under P7's accepted owner semantics.

Acceptance must exercise:

```text
g1 -> final publication -> locked activation
 -> fresh prepare g2
 -> new downstream publication/qualification using an overlapping/same locked cohort
```

and prove the accepted P7 owner refuses a second fresh reveal or recognizes the prior reveal exactly as its contract requires.

### F15 — chunked numerical equivalence must not require impossible floating digest equality

The parent workplan correctly requires exact scientific membership/order/model/checkpoint identities and numerical equivalence within the accepted dtype/backend tolerance, but wording that can be read as requiring the **old unchunked prediction content digest** to remain byte-identical is too strong. Different batch partitioning can produce scientifically equivalent floating values with tiny accepted backend arithmetic differences.

Correct acceptance is:

- **exact:** role identity, evaluation membership and order, checkpoint/model state, dtype/device/backend policy, output cardinality, frame-to-prediction association, discrete lineage, and reducer input ordering;
- **tolerance-based:** energy/force/stress predictions and derived floating metrics according to the project's existing numerical contract;
- the chunked result's prediction digest must self-authenticate the actual exact concatenated prediction payload it records, but it need not equal a legacy unchunked digest if the accepted floating payload differs within tolerance;
- reducer/scientific terminal decisions must remain invariant on the representative acceptance fixtures. A near-threshold case is judged under the existing numerical decision/tolerance contract, not by weakening thresholds to force equality.

This is an acceptance correction, not permission to change scientific precision or metrics.

### F16 — old-format compatibility must be checked through the whole downstream graph

The P4 repair already requires a current old-format generation without prepared artifacts to reject `select-target-size` and require explicit fresh `prepare`. The assembled integration contract must extend the same rule to P5/P7/status/storage exposure.

For an old-format current generation with valid historical P3/P5/P7 descendants but no repaired prepared snapshot:

- status remains read-only and reports the incompatibility/actionable fresh-prepare requirement;
- select/P5/P7 consequential current consumers do not live-reconstruct/retrofit the old generation;
- storage does not infer missing prepared representation as reclaimability or manufacture it;
- explicit `prepare` creates a fresh complete generation under the new contract;
- old P3/P5/P7 objects remain historical and are never rebound to the new generation.

P6's package-local closure remains accepted; this is successor integration compatibility, not a P6 redesign.

### F17 — prepared persistence must not solve restart by duplicating the dataset

The prepared snapshot needs durable restart state, but a naive implementation could satisfy logical persistence by copying the entire normalized frame dataset per generation, causing avoidable storage and I/O amplification.

**Required end state:** one canonical immutable/versioned normalized-frame representation is reused across generations when content identity matches. Prepared generations bind compact exact membership/identity to those members. Persist only additional P1/P2/P3-common state that is materially needed for restart.

Acceptance records incremental prepared-generation footprint, file/member count, warm-load I/O and RAM behavior. Warm loading preserves the existing mmap/read-only sharing benefit and does not materialize all normalized arrays into private RAM merely because the snapshot is now generation-safe.

No universal size percentage is imposed; the structural requirements are no second normalized dataset, no DATA4-scale per-generation copy solely for snapshot semantics, and bounded/reasonable metadata growth.

## 2. Frozen integration corrections

The following additions are now Frozen for this implementation cycle:

1. **Adopted-generation dependency immutability.** Nothing required by current generation g may be overwritten/deleted by construction of future g+1 before adoption.
2. **One generation-safe normalized-frame representation.** The existing frame-cache role remains singular, but required prepared dependencies are immutable/versioned/content-bound; mutable aliases are non-authoritative acceleration only.
3. **Configuration ownership separation.** Preparation-scientific, P3 execution/evidence, P5, P7, and execution-only resource changes invalidate only their owning semantic layers.
4. **P7 is part of the public campaign lifecycle.** Main status cannot declare the campaign complete at P5; locked activation remains explicit and is never auto-routed.
5. **Coherent observation.** One lifecycle/status response corresponds to one coherent current ancestry snapshot; routing is not authorization.
6. **Affected Storage R38 operations compose with prepared state.** Cleanup, dedup, archive/restore, and maintenance preserve the repaired owner lifetime and never create scientific authority.
7. **Locked disclosure survives current-generation change.** Irreversible one-shot history is retained according to P7 owner semantics even when its publication is no longer current.
8. **Numerical exactness is type-appropriate.** Discrete identity/order is exact; floating scientific equivalence uses the accepted tolerance and the new payload authenticates itself.
9. **P6 stays a closed predecessor, not a runtime stage.** Its compatibility/cleanup requirements are preservation constraints under current Storage R38 and integration acceptance.

Exact cache directory names, content-addressing scheme, status snapshot implementation, lifecycle view types, archive representations, and helper/API factoring remain Tier 2.

## 3. Additional implementation obligations

### R2-A — make frame persistence safe for immutable prepared generations

Alter the existing frame-cache representation rather than adding a second cache. Future prepare publication must not mutate current-generation frame members. Prepared state binds exact immutable frame-member identities/paths/digests. Reconcile all readers, storage owner views, retention, and cache reuse with that representation.

**Acceptance boundary:** execute the real frame normalization/cache publisher plus prepared-generation publisher/adopter. Do not patch either owner for the atomicity claim.

**Required failpoint:** after all future-generation frame members are published but before CampaignStore adoption, abort. Reopen and prove the old current generation loads exactly its prior frame bytes/identities and runs the next valid consumer with no DATA4/source reconstruction.

### R2-B — close configuration-domain invalidation

Re-derive which existing configuration projections feed preparation, P3 execution, P5, P7, and scheduling identity. Test one representative material change in each class plus at least one combined change. No new central identity registry.

### R2-C — integrate P7 into core status/next-operation routing

Extend the pure persisted-state lifecycle projection to include P7 without constructing a `QualificationSession`. Read compact P7 pointer/attempt/verdict/locked state sufficient for truthful guidance. Preserve explicit locked activation.

### R2-D — close prepare concurrency/publication races

Add bounded failpoint and two-writer tests for identical and differing prepare identities. Prove no current-generation dependency mutation, no mixed snapshot, CAS exclusivity, and correct unreachable-residue behavior.

### R2-E — make read-only projection coherent and diagnostically truthful

Use one coherent CampaignStore snapshot/revision fence for target/P5/P7 projection. Define typed observational states for missing/corrupt current descendants without performing repair or heavy reauthentication. Consequential owners retain the stronger full validation.

### R2-F — compose all affected Storage R38 operations

Extend owner/integration tests from cleanup to dedup/archive/restore/maintenance wherever the prepared/frame representation is in scope. Add the prepared-publication window to required storage barriers/retention reasoning. Do not modify R38's canonical destructive topology.

### R2-G — preserve irreversible locked disclosure across generation/storage transitions

Exercise a real P7 locked activation followed by generation advance and storage operations. The same locked cohort cannot become fresh merely because its former binding is historical.

### R2-H — extend repaired-generation compatibility to P5/P7/status/storage

Old current generations lacking prepared state are never retrofitted by downstream reconstruction. Fresh prepare is the sole conversion boundary.

### R2-I — bound prepared-state storage/RAM amplification

Measure representative prepared snapshot incremental footprint and warm reload. Preserve mmap/shared-read-only access and content reuse; reject designs that duplicate the full normalized dataset per generation without measured necessity.

### R2-J — correct chunked inference equivalence assertions

Update tests/spec wording so exact lineage/order remains exact while floating predictions/metrics use accepted tolerance. Require the newly produced content digest to authenticate its actual payload, not to equal a legacy digest by fiat.

## 4. Acceptance additions to the parent contract

The parent section 6 remains binding with these additions/corrections.

### 4.1 Preparation failure-atomicity matrix

Test interruption after:

1. normalization of one changed run but before all future frame members exist;
2. all future frame members published but before prepared manifest/component publication;
3. prepared components published but before CampaignStore adoption;
4. CampaignStore adoption committed but before non-authoritative cleanup of unreachable residue.

At every pre-adoption failure, the old generation remains complete and usable. After adoption, the new generation is complete; cleanup may only remove prior objects under owner/storage rules.

### 4.2 Configuration matrix

Test representative preparation-scientific, P3-execution, P5-only, P7-only, scheduling-only, and combined changes. Assert the minimal owning layer changes and unrelated upstream authority remains untouched.

### 4.3 Public lifecycle matrix correction

The fresh-workspace lifecycle continues after final production through P7. After P5 publication, core `status` must show qualification as next/not-started rather than `complete`. Exercise `advance` policy explicitly: ordinary qualification may be routed automatically if supported; locked activation must never be.

### 4.4 Coherent-observation concurrency

Race status with:

- prepare adoption;
- P5 pointer publication;
- P7 qualification pointer publication.

Each response must correspond to a valid before-or-after ancestry. No mixed generation/binding/pointer combination is allowed. Managed state remains unchanged by observation.

### 4.5 Prepare-writer concurrency

Test two identical prepares and two differing prepares with bounded synchronization failpoints. The real CampaignStore/prepared publisher remains under test. No duplicate conflicting generation namespace, overwrite, or mixed artifact graph is accepted.

### 4.6 Storage operation matrix expansion

For representative current, in-flight, historical, archived, and restored prepared/frame objects, run real owner inventory plus applicable cleanup, dedup, archive, verify, restore, and maintenance paths. Re-run a real downstream consumer after each allowed transformation.

### 4.7 Locked-history transition

After real locked activation, advance generation and exercise storage report/cleanup/archive/dedup as applicable. A later P7 owner must still detect the prior reveal.

### 4.8 Numerical assertion correction

Do not require legacy prediction digest equality solely across a different batch partition. Require exact discrete lineage/order, tolerated floating equivalence, self-authenticating new evidence, and unchanged representative scientific decisions.

### 4.9 Prepared representation efficiency

Record at least:

- bytes written for one fresh prepared generation;
- incremental bytes for unchanged repeated prepare;
- incremental bytes for one changed run/source;
- file/member count;
- warm load bytes/time where practical;
- peak RAM of warm prepared load;
- mmap/read-only behavior for large normalized arrays.

The evidence must demonstrate reuse rather than hidden full-dataset duplication.

## 5. Affected-surface additions

In addition to the parent census, explicitly inspect/reconcile:

- `mdstats/training_data/frame_cache.py` and every maintained normalized-frame cache reader/writer;
- frame-cache paths referenced from prepared state and storage inventory;
- core `PIPELINE`, `_current_public_lifecycle`, `_next_public_operation`, `command_status`, and `command_advance`;
- compact P7 pointer/attempt/verdict/locked-history readers in `qualification/store.py` and related owner modules;
- P7 historical locked-disclosure resolver/retention owner;
- Storage R38 archive, restore, dedup, maintenance and owner-view surfaces, not only cleanup;
- compatibility fixtures containing valid pre-repair P3/P5/P7 descendants without prepared snapshots;
- documentation that describes frame cache as merely mutable/reconstructible acceleration after it becomes a bound recovery dependency.

## 6. Implementation sequence corrections

The parent stage order remains sound with these changes:

1. **Parent Stage 1 cannot close until R2-A and R2-D close.** Prepared generation ownership and generation-safe normalized-frame persistence are one atomic lifecycle concern.
2. **Parent Stage 2** retains P3/P5 bounded direct inference, with R2-J's corrected numerical acceptance.
3. **Parent Stage 3** includes R2-C and R2-E: the pure public lifecycle must include P7 and use coherent read-only projection.
4. **Parent Stage 4** includes R2-B, R2-G, and R2-H: currentness/invalidation must be correct across config domains, irreversible locked history, and old-format generations.
5. **Parent Stage 5** includes R2-F and R2-I: exercise all affected Storage R38 transforms and prove the new representation does not create storage/RAM bloat.
6. Parent Stages 6-7 remain final assembled acceptance and authority/documentation reconciliation.

## 7. Tool-assisted second-pass closure

When a local checkout is available:

- **Serena:** follow `write_frame_data_cache_entry` / `finalize_frame_data_cache` callers and all frame-cache consumers; core lifecycle callers; compact P7 status readers; prepare/adoption callers; archive/dedup/restore consumers.
- **Semgrep:** add focused variant rules for mutable shared frame-cache replacement beneath prepared/current consumers, create-on-observe, unbounded P3/P5 batch calls, downstream prepare fallbacks, and noncanonical destructive paths. Validate each acceptance-critical rule on known-positive/negative examples.
- **Hypothesis:** expand stateful actions with concurrent/failed prepare, configuration-domain edits, P7 status/locked reveal, archive/restore/dedup, and old-format generation transition. Real production owners remain under test.

These tools were not available as a branch-local executable analysis surface during this connected-repository review; the absence does not weaken the required claim.

## 8. Revised closure criteria

All parent closure criteria remain binding. Additionally, the integration workplan cannot close until:

- future `prepare` cannot mutate any dependency of the current generation before adoption;
- normalized frame payload is generation-safe without introducing a second full cache or per-generation dataset copy;
- preparation/P3/P5/P7/resource configuration changes invalidate only their owning layers;
- core campaign status includes P7 and never declares completion at P5 while qualification remains applicable;
- `advance` never auto-activates locked evidence;
- read-only lifecycle projection is coherent under concurrent writes and reports current-artifact corruption truthfully without repair/execution;
- identical/differing concurrent prepares are safe and CAS-consistent;
- affected Storage R38 cleanup/dedup/archive/restore/maintenance operations preserve the prepared representation and scientific neutrality;
- locked-test disclosure remains irreversible across generation advance and storage transformation;
- old-format current generations lacking prepared state cannot reach P5/P7 through live reconstruction;
- chunked inference acceptance uses exact discrete identity plus justified floating tolerance, not legacy digest equality;
- prepared-state storage/RAM evidence shows content reuse and bounded metadata rather than duplicated full datasets.

**Second-pass design disposition:** no new scientific or high-level storage redesign is required. The corrected integration design remains the minimum justified architecture and is ready for implementation once this amendment is composed with the parent workplan.