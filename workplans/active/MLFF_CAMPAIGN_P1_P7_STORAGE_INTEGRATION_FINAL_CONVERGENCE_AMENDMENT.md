---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING-FINAL-CONVERGENCE
parent_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING-R2
root_workplan_id: CODE-MLFF-CAMPAIGN-P1-P7-STORAGE-INTEGRATION-HARDENING
protocol_version: 5.14.0
status: active
created_date: 2026-09-04
branch: plan/mlff-storage-io-reset-r37-review-closure
reviewed_head: e764f125595f22045540acf56108c699246e423b
scope: final assembled integration convergence including the earlier exact-boundary checkpoint-recovery bug contract, stale-P3 generation races, shared immutable frame-member retention, and execution-policy identity clarification
implementation_verdict: NO-PASS / INTEGRATION-REOPENED
design_disposition: PASS / IMPLEMENTATION-READY
precedence: this final convergence amendment tightens the root integration workplan and second-pass amendment only where stated; every non-conflicting parent/R2 invariant, Frozen decision, obligation, acceptance boundary, simplification rule, and closure criterion remains binding
---

# MLFF campaign integration hardening — final convergence amendment

## 0. Final-pass disposition

**Implementation remains NO-PASS / INTEGRATION-REOPENED.**

**The composed Design handoff is PASS / implementation-ready after this amendment.**

A final independent pass over the current branch, the root integration workplan, the second-pass amendment, the active P4 prepared-generation repair, current P3 exact-boundary/restart owners, Storage Revision 38, and the earlier `select-target-size` exact-boundary failure found four final integration gaps that should be fixed before implementation begins:

1. the earlier exact-boundary checkpoint-recovery bug contract was not explicitly carried into the new V7 assembled acceptance;
2. the concurrency matrix did not explicitly close a stale P3 writer losing a race to a newly adopted generation;
3. the generation-safe normalized-frame design did not explicitly protect immutable members shared by old and new prepared generations during storage reclamation/transformation; and
4. the configuration taxonomy could incorrectly classify `valid_batch_size` as volatile scheduling even though current P3 binds it into candidate execution realization and the active P4 repair uses it as the direct-EVAL2 batch bound.

None requires a new scientific algorithm, workflow engine, checkpoint registry, storage authority, cache, or lifecycle database. All are consequences of already-frozen product semantics. The correct response is to tighten the existing owner boundaries and acceptance, not add parallel machinery.

This amendment deliberately **does not resurrect the old V5 implementation topology** that originally exposed the checkpoint bug. The current V7 P3 architecture has already replaced legacy checkpoint catalogs, target-size label-domain/complement roles, REPAIR2 namespace bridging, and target-only/replay authorization with version-agnostic exact-boundary state, exact P2 memberships, authenticated TRAIN2 continuation, and direct exact-M EVAL2. The earlier repair is folded in at the durable behavioral-invariant level.

The final implementation authority set is therefore:

1. `MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md`;
2. `MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_SECOND_PASS_AMENDMENT.md`;
3. this final convergence amendment;
4. `mlff-target-size-v7-packages/P4_PREPARED_GENERATION_STAGE_BOUNDARY_REPAIR.md` for the prepared-generation/direct-EVAL2 prerequisite; and
5. current Storage Revision 38 authority for storage implementation semantics.

Historical/package-local authorities remain binding only for their still-applicable scientific/product contracts; they do not override the later assembled integration reopen.

---

## 1. Earlier exact-boundary bug fix — durable contract carried forward

### 1.1 Original failure that must not recur

The earlier production path entered exact-boundary target-size screening with the first active completed-epoch boundary and then failed before useful candidate progress with the error:

```text
TrainingDataInputError: Checkpoint catalog cannot be empty.
```

The underlying defect was not that an empty container needed a special case. It was an ownership/state-model error: **"no durable checkpoint has been produced yet" was represented as though a checkpoint authority existed but happened to contain zero members.** Restart then treated absence-of-state as malformed durable state.

The accepted repair established the distinction:

```text
NO AUTHENTICATED CHECKPOINT YET
  interruption before the first durable checkpoint/boundary
  -> no checkpoint authority exists
  -> no scientific boundary evidence exists
  -> retry starts the first rung fresh

AUTHENTICATED CONTINUATION CLAIM EXISTS
  owner says a checkpoint/boundary is durable and resumable
  -> exact required raw checkpoint + runtime summary + continuation companion
     must exist and authenticate
  -> missing/corrupt/mismatched bytes are corruption/execution failure
  -> never silently reinterpret that state as a fresh continuation
```

This distinction is Tier-1 restart/correctness behavior even though the old `CandidateCheckpointCatalog` representation was Tier 2 and is now retired.

### 1.2 Current V7 owner mapping

Current V7 P3 already has the right high-level semantic model:

- fidelity values are completed-epoch boundaries;
- ordinary successful boundary evidence requires the exact active boundary state;
- later rungs continue from the exact predecessor boundary, never from foundation/epoch zero;
- raw checkpoint, TRAIN2 runtime summary, continuation companion, live/EMA/RNG/update/LR ancestry are authenticated through the current TRAIN2/P3 owners;
- missing/corrupt/mismatched restart state is an execution error, not a P2 scientific numerical failure;
- P2 reducer advances only from a complete exact active boundary matrix.

The current real owner class/path is the production P3 sequence materially equivalent to:

```text
current select-target-size coordinator
 -> exact candidate/rung request
 -> TargetSizeBoundaryTrainer / production TRAIN2 launcher
 -> train2_runtime durable state
 -> bind/load exact TargetSizeBoundaryState / boundary snapshot
 -> direct EVAL2
 -> immutable cell completion / boundary batch
 -> P2 reducer / P3 head
 -> P4 CampaignStore adoption
```

Exact callable identities remain Tier 2. If implementation refactors them, acceptance remaps to the final real owners rather than preserving names.

### 1.3 Required first-boundary interruption semantics

For the first active boundary of a candidate there is no accepted predecessor boundary.

If execution is interrupted before a complete authenticated boundary state exists:

- do not publish a boundary state, snapshot, successful cell completion, complete boundary batch, or scientific failure merely because partial MACE/checkpoint files exist;
- do not create an empty placeholder checkpoint/continuation object to mean "nothing yet";
- do not let a stale partial current-rung workspace cause the next attempt to enter a continuation path;
- retry the same first rung from its accepted initial trajectory state after the P3 owner safely discards, replaces, or isolates only the **uncommitted mutable attempt workspace** it owns;
- preserve immutable materialization and other valid reusable parent artifacts rather than deleting/rebuilding them merely to get a clean attempt;
- do not invoke `prepare`, rebuild P1/P2, or advance generation as a recovery mechanism for an ordinary pre-first-boundary interruption.

A fresh retry is not permission to silently reuse arbitrary raw checkpoint files left by the failed attempt. A partial file is scratch until the accepted runtime/boundary owner authenticates the complete durable state required by the current V7 contract.

### 1.4 Required later-boundary continuation semantics

For `n2`/`n3` continuation, the exact predecessor boundary is scientific trajectory ancestry.

If the predecessor boundary/snapshot claims a resumable checkpoint, every required continuation component must authenticate. Missing/corrupt/foreign state must:

- fail closed as an execution/lineage/corruption error;
- leave the P2 reducer scientifically unchanged;
- never become an automatic restart from foundation/epoch zero;
- never become an empty placeholder continuation;
- never be translated into a candidate scientific numerical failure;
- never be repaired from live source/DATA4 or by reconstructing an alternate trajectory.

If the repository already exposes a safe owner-controlled way to invalidate/restart the affected P3 execution, implementation may use it. Do not add a second checkpoint/reset state machine merely to create a recovery command.

### 1.5 Exact-boundary compatibility preservation

Earlier exact-boundary repairs also had to prevent pre-fix screen execution evidence from being treated as current merely because high-level candidate policy looked unchanged.

Under current V7 this means:

- retired V5/V6 target-size screen/checkpoint evidence is not current V7 P3 evidence;
- incompatible P3 boundary/runtime/schema ancestry is rejected rather than rehashed/rebound into a current generation;
- a current V7 exact boundary remains exactly:

```text
completed_epochs      == n_i
execution_epoch_limit == n_i
raw_checkpoint_epoch  == n_i - 1
```

plus the current required raw/runtime/companion/model-state ancestry;
- existing P6 obsolete-V5/V6 rejection guarantees remain affected regression requirements after integration changes.

No old exact-boundary receipt or compatibility registry is to be restored.

### 1.6 Earlier EVAL2 follow-up fixes are preserved by **not** restoring their retired topology

The earlier bug-fix chain later repaired two V5-specific EVAL2 problems: source-label versus REPAIR2 final-development namespace confusion, and target-only authorization being incorrectly coupled to a target-monitor override.

Those mechanisms are no longer the current target-size architecture. Current V7 direct `TargetSizeEval2Role` is intentionally defined without label-domain, CV-fold, development-complement, coarse-fallback, excluded-training-prefix, replay-admissibility, or target-only-override semantics.

Therefore the correct final integration requirement is structural preservation of the V7 reduction:

- do not port the old REPAIR2 source-label bridge into current P3;
- do not port the old generic `allow_target_only_evaluation` authorization into current P3;
- exact P2 M-membership + exact boundary identity remain the only target-size EVAL2 population/checkpoint authority;
- the final structural/semantic scan must continue to prove that legacy complement/label-domain/replay-selection machinery cannot control current target-size evidence.

This folds in the earlier fixes without ossifying the old mechanisms that created them.

---

## 2. Final additional integration gaps

### F18 — current assembled acceptance does not distinguish no-checkpoint-yet from corrupted claimed continuation

The parent/R2 plans require restart, corruption tests, and exact P3 ancestry, but they do not explicitly encode the earlier bug's critical three-way state distinction:

```text
no accepted checkpoint/boundary yet
vs
complete authenticated predecessor boundary
vs
claimed predecessor whose required bytes are missing/corrupt
```

Without this distinction an implementation could satisfy generic restart tests while reintroducing an empty placeholder, incorrectly fresh-starting a later rung, or interpreting partial first-rung files as continuation authority.

**Required end state:** the current V7 P3 owner represents absence as absence, authenticated continuation as exact durable ancestry, and corruption as corruption. No placeholder object/state conflates them.

**Simplicity rule:** use the existing boundary snapshot/runtime summary/companion ownership. Do not add a checkpoint catalog, recovery registry, `has_checkpoint` database, or compatibility wrapper around partial files.

### F19 — stale P3 writers must lose generation-advance races

The parent concurrency matrix explicitly covers stale P5 and P7 writers but not a long-running P3 cell/head that finishes after a new `prepare` adopts a fresh generation.

A material race is:

```text
g1 current
 -> P3 work for g1 starts
 -> source/config change is prepared
 -> g2 becomes current through CampaignStore adoption
 -> old g1 P3 work finishes and publishes immutable evidence/head
```

The old evidence may remain valid **historical g1 evidence**, but it cannot become current, update g2 state, rebind to g2, or make the public lifecycle regress to g1.

**Required end state:** final P3/P4 adoption uses the same current-generation/revision fencing principle already required for P5/P7. The stale writer loses at the adoption/currentness boundary. If an existing accepted owner policy instead refuses generation advance while P3 is active, prove that refusal through the real owner; do not leave the race ambiguous.

Do not prevent the race by holding a coarse campaign lock across long TRAIN2/EVAL2 work.

### F20 — immutable normalized-frame members shared across generations need multi-generation reachability safety

R2 correctly requires one immutable/versioned/content-bound normalized-frame representation with reuse across prepared generations. That reuse creates a necessary storage consequence not stated explicitly enough.

Example:

```text
g1 -> members A, B1, C
g2 -> members A, B2, C
```

After g2 adoption, historical g1 may become reclaimable according to owner policy. Storage must not delete/detach shared members A or C merely because they are reachable from the historical g1 manifest being retired; they are still required by g2.

**Required end state:** cleanup/dedup/archive/restore decisions for normalized members are based on actual owner reachability from all protected current/in-flight prepared manifests, including shared content identities. A historical generation may release only objects not required by another protected owner.

**Simplicity rule:** derive reachability from existing prepared manifests/owner views. Do not add a persistent reference-count database, garbage-collector registry, or second frame index solely for this purpose.

Acceptance must include unchanged-run reuse plus one changed run across generations and then execute real storage operations followed by a real g2 downstream consumer.

### F21 — `valid_batch_size` is execution-policy identity, not volatile resource pressure

R2's configuration taxonomy correctly separates scientific identity from execution-only scheduling, but one field requires explicit classification because the active resource repair depends on it.

Current P3 candidate realization includes `optimizer_policy.valid_batch_size` in `loader_geometry_digest`, and the active P4 repair uses the accepted positive `valid_batch_size` as the deterministic direct-EVAL2 device-batch bound. It is therefore **not** equivalent to transient free VRAM, current worker availability, queue order, or telemetry.

Required classification:

- `valid_batch_size` remains non-scientific in the sense that it does not change P2 membership, M, labels, metric definition, precision, model state, or prepared P1/P2 science;
- but it is an accepted configured **P3/P5 execution-policy identity** wherever the current owner binds it;
- changing it explicitly after an OOM may preserve the same prepared generation/P1/P2 scientific authority while invalidating/rebinding the affected P3/P5 execution evidence according to the existing execution owner;
- implementation may not silently mutate it mid-attempt as an unrecorded OOM fallback;
- transient free RAM/VRAM and proven scheduling-only worker realization remain non-identity runtime observations.

Do not create a second `eval_batch_size` policy to express this distinction. The existing owner identity is sufficient.

---

## 3. Final Frozen corrections

In addition to all parent and R2 Frozen decisions, this implementation cycle now freezes:

1. **Absence is not an empty checkpoint authority.** Before the first authenticated boundary, no continuation authority exists; interruption retries from the accepted initial trajectory without a placeholder record.
2. **Claimed continuation is strict.** Once an exact predecessor boundary/snapshot claims resumable state, all required checkpoint/runtime/companion ancestry must authenticate or the continuation fails closed.
3. **Partial current-rung files are not science.** Uncommitted mutable attempt files never become boundary/reducer authority through existence or pathname.
4. **Stale P3 cannot become current after generation advance.** Immutable historical publication is allowed; current adoption under the newer generation is not.
5. **Shared normalized members use owner reachability, not generation-local deletion.** A member referenced by any protected prepared owner remains available.
6. **`valid_batch_size` is explicit execution-policy identity where bound, not volatile pressure.** Changing free VRAM does not rewrite identity; changing the configured accepted batch bound follows the P3/P5 execution-owner invalidation contract.
7. **Retired V5 bug-fix machinery stays retired.** No checkpoint catalog, REPAIR2 target-size namespace bridge, target-only replay bypass, or old exact-boundary receipt is reintroduced into current V7 P3 solely to preserve historical fixes.

Exact scratch-directory cleanup, attempt-directory naming, whether a failed first-rung workspace is removed or replaced, exact CAS exception type, and exact manifest reachability implementation remain delegated Tier 2.

---

## 4. Final implementation obligations

### FINAL-A — preserve exact-boundary interruption/restart semantics through the current P3 owner

**Concern.** The earlier production bug proved that generic "restart works" coverage is insufficient when absence and malformed continuation are conflated.

**Required end state.** Current P3 distinguishes cleanly between no boundary yet, valid exact predecessor boundary, and corrupt/missing claimed continuation. First-boundary retry is fresh; later-boundary continuation is exact; corruption is fail-closed.

**Preferred reduction.** Treat failed first-rung mutable workspace as disposable owner-local attempt state once no accepted boundary references it. Remove/isolate that stale scratch before fresh execution rather than creating a checkpoint catalog or fallback mode. Preserve valid immutable materialization and parent state.

**Acceptance boundary.** Execute real current `select-target-size` P3 scheduling/rung preparation, the real TRAIN2 launcher/runtime persistence contract, and the real boundary bind/load/reconciliation owner. Expensive MACE arithmetic may be bounded/faked only below the state owner; the test may not inject a fabricated boundary/checkpoint result above it.

Required failpoints/cases:

1. interrupt before any raw/runtime checkpoint state exists;
2. interrupt with non-authoritative partial files but without a complete authenticated boundary state;
3. restart after a complete accepted first boundary and continue to the next rung;
4. delete/corrupt the predecessor raw checkpoint;
5. delete/corrupt the TRAIN2 runtime summary;
6. delete/corrupt the continuation companion;
7. supply a foreign N/seed/context/protocol/boundary predecessor;
8. ordinary resource/process interruption must leave the P2 reducer unchanged.

The first two cases must retry the first rung without a continuation flag/path. Cases 4-7 fail closed and must not silently fresh-start a later rung.

### FINAL-B — add P3 to currentness/concurrency fencing acceptance

**Concern.** A stale long-running screen worker can outlive its generation.

**Required end state.** Generation/revision fencing prevents any old P3 head/terminal projection from becoming current after newer prepare adoption.

**Acceptance boundary.** Real P3 publication plus real P4/CampaignStore adoption/currentness owner. A fake may bound TRAIN2/EVAL2 computation below the publication owner but may not bypass the stale-adoption check.

Required race:

```text
open g1 P3 work
 -> block immediately before final P3/P4 adoption
 -> adopt g2 through real prepare/current-generation owner
 -> release g1 writer
```

Expected: g1 evidence is historical/unreachable-current; g2 remains current; no g1 pointer/head is rebound to g2; next lifecycle/status is g2-consistent.

### FINAL-C — make shared normalized-frame retention reference-safe without a new registry

**Concern.** R2 content reuse can become unsafe if historical-generation cleanup treats a shared immutable member as exclusively owned by the old generation.

**Required end state.** Owner inventory/revalidation sees protected references from current/in-flight prepared manifests before cleanup/dedup/archive/hot reclaim. Shared members stay available until all protected owners release them.

**Acceptance.** Prepare g1, change one run only, prepare g2, prove unchanged run members are reused by content identity, then retire/transform g1 through real Storage R38 operations. g2 must still load all required frame members and run the next valid consumer with zero source/DATA4 reconstruction.

No reference-count DB or second cache is permitted merely for this acceptance.

### FINAL-D — make resource/config invalidation taxonomy executable

**Concern.** Treating all execution resources alike can either over-invalidate science or let a changed accepted execution policy reuse stale evidence.

**Required end state.** Tests distinguish:

- changed preparation-scientific policy -> fresh prepare/generation;
- changed `valid_batch_size` or another bound P3 execution-policy field -> prepared P1/P2 remains reusable, affected P3 execution identity/current attempt follows its owner invalidation/restart rules;
- P5-equivalent bound execution-policy change -> P5-only descendant invalidation according to P5 identity;
- changed transient free RAM/VRAM/worker availability -> no scientific/prepared identity change.

A hidden OOM retry that silently rewrites the accepted configured batch bound remains forbidden.

### FINAL-E — preserve the architectural removal achieved by the later V7 reset

**Concern.** Folding an old bug fix literally would recreate obsolete machinery and enlarge the system.

**Required end state.** Current target-size P3 remains based on exact P2 membership, version-agnostic trajectory/boundary state, exact continuation, and direct exact-M EVAL2. The implementation must not reintroduce old V5 checkpoint-catalog/label-domain/REPAIR2/complement/replay-authorization machinery to satisfy the earlier regression.

**Acceptance.** Structural/semantic inspection of the final current V7 P3 path proves those retired mechanisms do not control target-size execution/evidence. Existing obsolete-version rejection regression remains green.

---

## 5. Acceptance additions and final campaign matrix corrections

All root-workplan and R2 acceptance remains binding. Add the following to the exact-candidate final assembled suite.

### 5.1 P3 interruption matrix

At the first active boundary:

```text
fresh current prepared generation
 -> select-target-size
 -> first candidate/rung starts
 -> interrupt before authenticated boundary
 -> close/reopen process
 -> select-target-size again
```

Require:

- no empty placeholder checkpoint authority;
- no P2 reducer advancement;
- no scientific failure evidence;
- no reuse of uncommitted current-rung checkpoint bytes as authoritative continuation;
- same exact trajectory identity and membership;
- fresh first-rung execution under the same accepted policy;
- successful later boundary may continue normally from its exact authenticated predecessor.

Repeat with each required predecessor component missing/corrupt after a committed boundary; these cases fail closed rather than fresh-starting the later rung.

### 5.2 P3 stale-writer generation race

Add generation advance versus stale P3 publisher/adopter to the parent concurrency matrix, alongside the existing P5/P7 stale-writer cases.

### 5.3 Shared-frame reachability matrix

Use at least two prepared generations with overlapping normalized content:

```text
g1 = A + B1 + C
g2 = A + B2 + C
```

Prove owner/storage operations may retire g1-only `B1` when otherwise eligible but cannot remove/retarget shared `A`/`C` while g2 remains protected. Reopen and consume g2 after each applicable Storage R38 operation.

### 5.4 Resource-policy identity matrix correction

The configuration matrix explicitly contains separate cases for:

- `valid_batch_size` change;
- transient free VRAM change;
- worker/concurrency realization change proven execution-only;
- P3 scientific/preparation policy change.

Assertions must match the owner classification above rather than treating all four as equivalent resource changes.

### 5.5 Earlier-bug regression preservation

The final suite must contain an understandable regression whose failure mode is equivalent to the earlier `Checkpoint catalog cannot be empty` incident, but expressed through current V7 owners. It must fail if the implementation once again represents "no checkpoint yet" as an empty/malformed continuation authority.

Do not retain an old V5-only test that can pass while current V7 restart is broken; the regression must execute the current real P3 owner.

### 5.6 Stateful/property actions

Extend the parent Hypothesis state machine with bounded actions/properties for:

- interrupt first P3 rung before an accepted boundary;
- retry first P3 rung;
- corrupt one required predecessor continuation component;
- advance generation while old P3 publication is blocked;
- create two generations sharing normalized frame members;
- reclaim/transform historical generation state;
- change `valid_batch_size` separately from transient resource pressure.

The real CampaignStore/P3/storage transitions remain under test; the stateful model is only an oracle.

---

## 6. Final implementation sequence

The final converged order is:

1. **Prepared-generation + normalized-frame ownership first.** Close parent Stage 1 plus R2 generation-safe frame publication/concurrent prepare atomicity.
2. **P3 execution integrity as one stage.** Before declaring the resource repair closed, implement FINAL-A checkpoint/interruption semantics, parent P3/P5 bounded direct inference, corrected numerical equivalence, and FINAL-B stale-P3 adoption fencing. These all affect the same current P3 execution/restart boundary.
3. **Observation/public lifecycle.** Close pure coherent status/advance projection including P7.
4. **Dependency-local currentness/configuration.** Close R2 config domains, FINAL-D explicit `valid_batch_size` classification, P5/P7 currentness, locked-history retention, and old-format compatibility.
5. **Storage R38 composition.** Exercise cleanup/dedup/archive/restore/maintenance including FINAL-C shared-member reachability and failed/in-flight P3 attempt ownership. Do not create another destructive path or reference registry.
6. **Final assembled lifecycle + stateful acceptance.** Run all parent/R2/final matrices on one exact candidate after material executable edits.
7. **Authority/documentation reconciliation + independent Design review.** Record exact candidate SHA/tree and only then close active integration/storage authorities if no blocker remains.

Do not implement status wrappers, storage exceptions, or compatibility shims around the old reconstruction/restart model before Stages 1-2 are semantically closed.

---

## 7. Final structural/semantic review contract

When a local branch analysis surface is available:

### Serena

Use semantic caller/reference inspection for:

- first-rung versus later-rung P3 checkpoint-directory/continuation callers;
- boundary snapshot/runtime summary/companion readers and writers;
- P3 head -> P4/CampaignStore adoption callers;
- normalized-frame immutable member readers/owners across generations;
- `valid_batch_size` identity consumers in P3/P5;
- final current V7 EVAL2 role/caller closure proving no legacy V5 role owner controls it.

### Semgrep

Use focused structural checks for current V7 production paths, with known-positive/negative rule validation, including:

- empty placeholder checkpoint/continuation creation used to mean absence;
- later-rung fresh-start fallback after missing claimed continuation;
- stale P3 adoption lacking current-generation/revision fencing;
- generation-local deletion of shared normalized members without owner reachability;
- hidden mutation/override of accepted `valid_batch_size` after OOM;
- current P3 calls into retired label-domain/complement/REPAIR2/target-only authorization topology;
- previously required parent/R2 absence claims.

Do not require global absence of legacy symbols that remain in supported non-current compatibility code; the claim is that they cannot control the **current V7 target-size production path**.

### Hypothesis

Use the final stateful actions in section 5.6 with real production state/persistence owners and bounded numerical work.

If these local analyzers are unavailable, preserve the same claims through exact-branch source/caller inspection plus real-owner runtime acceptance; do not weaken the acceptance contract.

---

## 8. Final closure criteria

The integration workplan closes only when one exact assembled candidate satisfies **all** root-workplan, R2, active P4, applicable P3/P5/P7, and Storage R38 closure requirements plus every item below:

- interruption before the first exact P3 boundary is represented as **no accepted checkpoint/boundary**, not an empty checkpoint authority;
- first-boundary retry cannot inherit uncommitted partial current-rung bytes as scientific continuation state;
- a claimed predecessor continuation with missing/corrupt raw checkpoint/runtime summary/companion fails closed and never silently fresh-starts a later rung;
- exact-boundary completed-epoch/raw-checkpoint semantics remain unchanged;
- stale g1 P3 publication/adoption cannot become current after g2 adoption;
- immutable normalized-frame members shared across protected generations survive historical-generation cleanup/dedup/archive/reclamation;
- `valid_batch_size` changes follow P3/P5 execution-policy currentness while transient free-memory/worker pressure remains execution-only observation;
- no new checkpoint registry, refcount database, second normalized cache, second lifecycle authority, or new storage destructive path was introduced;
- retired V5 checkpoint-catalog/REPAIR2/complement/target-only machinery does not regain authority over current V7 P3;
- the current-owner regression reproducing the earlier empty-checkpoint failure class passes;
- P3 stale-writer, first-boundary interruption, shared-member storage, configuration, observation, resource, corruption, restart, and full P1-P7 lifecycle matrices pass on the exact candidate;
- final affected-surface regression and repository-required checks pass after all material executable changes;
- current navigation identifies this final composed authority and the true implementation disposition.

## 9. Final Design conclusion

No further high-level redesign is justified by the final pass. The target architecture remains the minimum justified system:

```text
one CampaignStore current-generation authority
+ one immutable prepared generation
+ one generation-safe reusable normalized-frame representation
+ one exact P3 boundary/continuation model
+ one bounded direct-inference execution concept
+ existing immutable P3/P5/P7 descendant stores
+ one pure coherent lifecycle projection through P7
+ one Storage-R38 owner-driven mutation architecture
```

The earlier checkpoint bug is now part of the final acceptance contract **without restoring the obsolete machinery that caused it**.

**Final Design disposition: PASS / implementation-ready.**

**Current implementation disposition: NO-PASS / integration-reopened until the composed workplan is implemented and exact-candidate acceptance closes.**
