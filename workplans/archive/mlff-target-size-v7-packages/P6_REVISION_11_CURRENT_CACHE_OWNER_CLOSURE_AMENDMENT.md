---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6-R11
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6
protocol_version: 5.8.0
revision: 11
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: 61148c14da71e762c5d05e2c0c7dab338639a95d
reviewed_candidate_tree: 6bd795ede89a77cf645f243f084ea951ebdd567e
precedence: this amendment supersedes revision-10 checkpoint-model-cache eviction/liveness acceptance and remaining STOR1 current-surface wording; all unrelated P6 revision-3 through revision-10 obligations remain binding
---

# P6 revision 11 amendment — current cache-owner closure

## 1. Objective and protected concerns

Revision 11 closes the final P6 review blocker without reopening accepted P1-P5 scientific behavior, P5 multi-seed production/restart behavior, or the post-P7 storage-reset architecture.

The protected product outcome is:

```text
P6 cleanup must never delete a cache merely because its pathname looks reconstructible
or because a PID marker is absent.

A P6 destructive storage action requires an actual current semantic owner and an
already-established reconstruction authority.  If that authority does not exist in the
current P3/P5 architecture, P6 retains the bytes and defers eviction to the successor
storage reset.
```

Revision 10 correctly established the general rule that `checkpoint-model-cache` could be a cache-tier candidate only if a current owner proved both inactivity and reconstructibility.  Independent review of the revision-10 implementation showed that the implementation never established that premise.  It instead enumerated `workspace/runs/*/checkpoint-model-cache`, treated absence of a live `active_process.json` PID as sufficient inactivity, and accepted a regression fixture containing no retained checkpoint or authenticated run/model evidence.

That is not merely a missing assertion.  Repository inspection shows that the assumed cache/run topology is not the current P3/P5 ownership topology:

- current P3 target-size execution is rooted canonically under `.mdstats/target-size/g<generation>`;
- current P3 evaluation reconstructs/authenticates the provider directly from the exact TRAIN2 raw checkpoint, continuation companion, runtime summary, and candidate configuration;
- current P3 candidate/coordinator/evaluation owners do not define `checkpoint-model-cache` or `active_process.json` as current execution authority;
- current P5 execution is rooted canonically under `.mdstats/post-selection/g<generation>/runs/<run_identity>`;
- current P5 materialization/TRAIN2/EVAL2 owners do not define `checkpoint-model-cache` or `active_process.json` as current execution authority;
- the revision-10 cache cleanup path instead enumerates the legacy/general `CampaignPaths.runs == workspace/runs` tree.

Therefore the revision-10 reopen condition is met: the positive `checkpoint-model-cache` eviction premise is not supported by the current P3/P5 architecture.  The globally justified P6 correction is conservative retention, not invention of a new ownership registry, lease system, cache manifest, compatibility adapter, or synthetic current producer.

## 2. Frozen design correction

### 2.1 P6 cache-tier destructive authority

For the remainder of P6 and P7, **no current cache family has positive cache-tier deletion authority**.

The current transitional public surface remains:

```text
storage report
storage cleanup --tier safe
storage cleanup --tier cache
```

but the semantic distinction is now deliberately conservative:

```text
safe
    -> independently owner-proven zero-capability-loss cleanup only

cache
    -> includes the same safe cleanup
    -> has no additional current-generation destructive cache candidate in P6/P7
    -> may therefore reclaim exactly the same bytes as safe on a current workspace
```

This is intentional, truthful behavior.  A tier is not required to delete something merely because it exists in the CLI vocabulary.

### 2.2 `checkpoint-model-cache`

`checkpoint-model-cache` is **retained/deferred** in P6/P7.

For current P6/P7 storage policy:

```text
checkpoint-model-cache:
    automatic deletion: prohibited
    safe deletion: prohibited
    cache deletion: prohibited/deferred to CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
```

No current code path may authorize deletion from any combination of:

- directory name `checkpoint-model-cache`;
- location below `workspace/runs`;
- run-directory age;
- absence of `active_process.json`;
- dead/nonexistent PID in `active_process.json`;
- existence of some `.pt`, `.model`, checkpoint-looking, or run-looking neighboring file;
- historical stage completion;
- old evaluate/verify/DATA7/DATA8 semantics;
- an advisory `storage report` classification.

A current cache cannot become deletable in P6 merely by adding a local test fixture that resembles a historical producer.

### 2.3 `frame-cache` and historical cache families

Revision-10 conservative retention remains unchanged:

```text
frame-cache              -> retained by safe and cache
checkpoint-model-cache   -> retained by safe and cache   [revision-11 change]
data7-cache               -> retained/deferred
data8-fixed-cache         -> retained/deferred
evaluation-graphs         -> retained/deferred
evaluation-predictions    -> retained/deferred
model-sweep               -> retained/deferred
true-label-replay         -> retained/deferred
historical evaluation/materialization cache names without a current owner -> retained
```

No path-name-based cache deletion is current P6 authority.

### 2.4 No new P6 cache-control plane

Do not add any of the following solely to recover the discarded positive cache-deletion case:

- cache leases;
- active-consumer registries;
- new run registration files;
- new `active_process.json` writers in P3 or P5;
- cache ownership manifests;
- a second run-liveness authority;
- a compatibility bridge from `.mdstats/target-size` or `.mdstats/post-selection` into `workspace/runs`;
- duplicated checkpoint/model evidence solely to make a cache reconstructible;
- pathname-to-owner translation tables.

Those mechanisms would increase product complexity and pre-implement parts of `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` without a P6 requirement.

## 3. Required implementation consequences

### R11-A — remove P6 `checkpoint-model-cache` deletion authorization

In `mdstats/training_data/_campaign_cli_core.py` and any directly affected helper:

1. `storage cleanup --tier cache` must not enumerate `checkpoint-model-cache` as an additional deletion candidate.
2. Remove the current call path from manual cache-tier planning into `workspace/runs/*/checkpoint-model-cache`.
3. `_manual_reclamation_add_cache_tier()` may be deleted, simplified to add no destructive candidate, or replaced by equivalent factoring; the externally visible semantics above are frozen.
4. The existing `_cleanup_checkpoint_model_caches()` helper is not a current P6 authorization mechanism.  If source inspection confirms it has no supported current consumer, delete it as dead consequential machinery.  If another independently supported consumer still exists, retain only that consumer-specific behavior and prove it cannot be reached by current P6 automatic/safe/cache cleanup.
5. `_active_training_run_ids()` may remain only for independently justified run/scratch cleanup that already has a current owner.  It must not be treated as proof that a checkpoint model cache is reconstructible, and it must not be wired back into cache deletion.
6. Do not broaden safe cleanup while removing the cache candidate.  Existing safe cleanup remains limited to independently owner-proven zero-capability-loss garbage/staging/runtime cleanup.
7. `cache` planning/reporting must remain valid when it produces zero cache-specific actions.
8. A zero-action `cache` plan is success, not an error and not a reason to invent a candidate.

### R11-B — make capability reporting truthful after removal

The manual cleanup plan/capability report must not claim a cache capability loss that no longer occurs.

Required end state:

- `safe` and `cache` report preserved scientific, restart, diagnostic, and acceleration capabilities for current P6/P7 behavior;
- `declared_capability_losses` is empty unless an independently authorized safe action genuinely records a non-user-visible bookkeeping consequence already allowed by the safe contract;
- there is no `faster_checkpoint_reevaluation` loss caused by P6 cache cleanup because P6 no longer evicts the checkpoint-model cache;
- plan text must not imply that `cache` necessarily reclaims more bytes than `safe`.

Do not fake a semantic distinction by declaring a capability loss when no corresponding deletion occurs.

### R11-C — reconcile advisory storage accounting

In `mdstats/training_data/storage_accounting.py` and its tests, revise the current `checkpoint-model-cache` disposition to match executable policy.

Required current semantics:

```text
family: checkpoint_model_cache
automatic_reclamation_eligibility: prohibited
manual_reclamation_eligibility: prohibited or deferred_to_storage_reset
```

`cache_candidate_owner_guard_required` is no longer truthful current P6 policy and must disappear from current serialized output.

The report remains advisory only.  No report value grants mutation authority.

All revision-10 dispositions for `frame-cache`, historical DATA7/DATA8/evaluation/model-sweep/replay cache paths, content-store, and cold-archive state remain conservative/deferred unless this revision explicitly changes them.  It does not.

### R11-D — remove the remaining current `STOR1` product wording

The current public command is `storage report`, not STOR1.

In current production code and current documentation:

- change `command_storage()`'s current docstring away from `STOR1` terminology;
- change stdout heading `STOR1 campaign storage report` to a current neutral heading such as `MLFF campaign storage report` or `Campaign storage report`;
- do not expose `STOR1` as a current command/policy generation in generated help, guide text, report JSON, or current storage specification;
- historical source comments, archived historical documentation, release patches, and old historical tests may retain STOR identifiers where they are clearly historical and not current product guidance.

Do not perform unrelated version-history rewriting in `_campaign_cli_core.py`; this requirement concerns current executable/product wording, not deletion of historical release commentary.

### R11-E — update current docs to the actual conservative cache contract

Reconcile at minimum:

- `docs/specs/training_data/mlff_storage_management_spec.md`;
- `docs/guides/mlff_campaign_cli_user_guide.md`;
- current architecture/manual text if it states that `checkpoint-model-cache` is P6-evictable;
- generated tracked PDFs derived from changed Markdown sources.

Required wording substance:

1. P6/P7 provide `safe|cache` as the transitional public cleanup vocabulary.
2. `safe` performs only zero-capability-loss cleanup.
3. `cache` is reserved for cache-policy intent but currently has no additional authenticated destructive cache candidate because current P3/P5 do not expose a storage-owner/reconstruction contract suitable for safe eviction.
4. Both tiers retain `frame-cache` and `checkpoint-model-cache` in P6/P7.
5. Consequential cache ownership/eviction, leases, archive, deduplication, admission, and cross-owner storage design remain the successor storage reset's responsibility.
6. Users must not be told that an inactive `workspace/runs/*` cache is automatically safe to delete through the P6 CLI.

Regenerate PDFs through the repository's canonical documentation build workflow; never patch generated PDFs directly.

## 4. Acceptance-boundary correction

Revision 11 explicitly supersedes revision 10 section 9.4's positive inactive-cache/active-PID acceptance model.

That old acceptance boundary was appropriate only if a real current producer existed for the cache family.  Repository evidence shows that the accepted current P3/P5 owners use different canonical roots and direct checkpoint/evidence reconstruction paths.  Therefore a fabricated `workspace/runs/<name>/active_process.json` can no longer establish a current-owner claim.

### 4.1 Forbidden proxy evidence

The following must not be used as P6 acceptance evidence for cache deletion:

```text
mkdir workspace/runs/fake-run/checkpoint-model-cache
write active_process.json with os.getpid()
assert cache survives
unlink active_process.json
assert cache is deleted
```

Nor may a test directly pass fabricated `active_run_ids` or fabricate a retained checkpoint solely to make the deletion pass.

Such tests may exercise a historical/private helper if that helper remains for another supported purpose, but they cannot establish current P6 cache deletion authority.

### 4.2 Required current-owner evidence

Because P6 now authorizes no cache-family eviction, acceptance must prove **non-reachability of cache deletion** and preservation of real current owners.

Required evidence:

1. through the real public CLI, create a bounded workspace containing `workspace/runs/arbitrary/checkpoint-model-cache/payload`; run both `storage cleanup --tier safe` and `storage cleanup --tier cache`; the cache remains after both;
2. the same test must not need `active_process.json` to obtain retention;
3. create representative `frame-cache` and historical-path traps; both tiers retain them;
4. structural/source assertion: current `storage cleanup --tier cache` candidate construction has no path that enumerates `checkpoint-model-cache` for deletion;
5. structural/source assertion: current storage mutation does not consume `cache_candidate_owner_guard_required` or another report eligibility label as authorization;
6. current P3 retention tests continue to exercise the real `.mdstats/target-size/g<generation>` publication/restart owner and show safe/cache cleanup cannot damage required evidence;
7. current P5 plan-only, partial-production, and completed-production retention tests continue to exercise the real `.mdstats/post-selection/g<generation>/...` owner and show safe/cache cleanup cannot damage required evidence;
8. bounded MACE/trainer/inference fakes remain allowed only below those P3/P5 owners; do not replace the owner or directly seed post-transition state for the retention claim.

A real concurrent training process is no longer required solely to prove checkpoint-model-cache liveness because P6 no longer deletes that cache in any liveness state.  Existing concurrency/restart tests remain required where they independently protect P3/P5 execution.

## 5. Focused revision-11 acceptance

### 5.1 Public behavior

Through the real parser/dispatch path:

```text
storage cleanup --tier safe   -> succeeds
storage cleanup --tier cache  -> succeeds
```

For a bounded current workspace in which only cache-like artifacts differ:

- both commands retain `checkpoint-model-cache`;
- both commands retain `frame-cache`;
- both commands retain uncertified historical cache names;
- cache tier may report zero additional actions;
- neither command advertises or performs archive/dedup/recompute/compact behavior.

### 5.2 Report behavior

Run `storage report` through the real CLI and inspect both stdout and serialized `results/storage-report.json`.

Required:

- stdout does not identify the command as `STOR1`;
- current report JSON contains no `STOR1`, `stor2_*`, `stor3_*`, `stor5_*`, recompute, compact, protocol-freeze, or retired mutation eligibility;
- `checkpoint_model_cache` is prohibited/deferred, not owner-guarded deletable;
- `frame-cache` is prohibited/deferred;
- report creation itself deletes nothing.

Negative string checks must be scoped to current report output/current storage guidance so unrelated historical documentation or version-history comments do not create false failures.

### 5.3 Dead/current authorization structure

Inspect the assembled current source and prove:

- no public automatic/safe/cache route reaches `_cleanup_checkpoint_model_caches()` or equivalent checkpoint-model cache deletion;
- no manual cache-tier route walks `workspace/runs/*/checkpoint-model-cache` as a deletion candidate;
- no current storage mutation asks old evaluate/verify/DATA7/DATA8/protocol-freeze state for authorization;
- no current storage mutation infers P3/P5 cache disposability from pathname;
- no new lease/registry/cache-owner subsystem was added in P6.

If an obsolete private helper becomes unreferenced after this correction, remove it rather than keeping dead consequential machinery without an owner.

### 5.4 Regression required for directly affected surfaces

At stage closure run the focused revision-11 tests plus affected regression covering at minimum:

- storage accounting;
- storage cleanup planning/apply/dry-run;
- ownership containment and external-input protection;
- symlink unlink-without-target-traversal behavior;
- current safe cleanup/stale-runtime behavior that still uses `workspace/runs`, if any;
- P3 publication-window retention;
- P5 plan-only/proper-subset/completed-production retention;
- current config/help/generated guidance;
- current storage spec/user guide documentation assertions.

Do not delete or weaken a test merely because it encodes the revision-10 positive cache deletion case.  Replace that expectation because the accepted product contract has now changed: the new test must explicitly prove conservative retention and absence of deletion authorization.

## 6. Final assembled P6 revision-11 acceptance

Revision 11 is a narrow storage amendment, but P6 final acceptance remains assembled acceptance of the complete composed P6 contract.

After all executable/documentation edits are assembled on one candidate, Implementation must freshly reconcile and execute the required affected acceptance, including:

1. revision-8 DATA5/P1-P4 ownership and CV-neutrality cases remain green;
2. revision-9 multi-seed P5 final-production plan/partial/corrupt/complete/process-reopen/reuse cases remain green;
3. current generated config, example, parser, help, guide text, Markdown guide, and storage spec expose one `safe|cache` transitional contract;
4. top-level legacy `cleanup` alias remains absent;
5. safe and cache both retain `checkpoint-model-cache` and `frame-cache`;
6. historical-path traps remain retained;
7. report output is current-generation truthful and contains no retired mutation policy;
8. external inputs, physical containment, and symlink protections remain green;
9. P3 publication-window retention remains green through the real current owner;
10. P5 plan-only/proper-subset/completed-production retention remains green through the real current owner;
11. exact P5A6 unchanged compatibility qualification A remains PASS;
12. independent fresh final-P6 production/restart qualification B remains PASS;
13. V5/V6 reject-before-reuse qualification C remains PASS;
14. real parser/dispatch lifecycle remains functional through `prepare -> select-target-size -> cross-validate -> train-production` with close/reopen/currentness;
15. directly affected docs/PDFs regenerate successfully;
16. complete affected-surface CPU-safe regression passes; because `_campaign_cli_core.py` and storage accounting are central public surfaces, use the broader/full CPU-safe suite unless a complete smaller bound is independently demonstrated.

A required check that does not execute is not a pass.  Long GPU/real-data production qualification remains deferred and is not required to close P6.

## 7. Implementation sequence

Revision 11 is one coherent material stage: **R11-1 conservative cache-owner closure**.

Implement in this order:

```text
1. remove checkpoint-model-cache mutation authorization from cache tier
2. remove/deactivate dead consequential cache helper paths without disturbing independently owned safe cleanup
3. reconcile capability-plan and storage-report semantics
4. remove current STOR1 report wording
5. replace revision-10 positive cache-deletion tests with retention/non-reachability tests
6. reconcile current docs and regenerate PDFs
7. run stage-local affected regression
8. run final assembled P6 acceptance
```

Do not split this into micro-stages by file.  The behavior is meaningful only as one coherent storage-policy correction.

## 8. Frozen / delegated / reopen-only authority

### Frozen

- P6 remains cleanup/cutover functional closure only; it does not implement P7 or the successor storage reset.
- All accepted revision-8 and revision-9 scientific/P5 behavior remains frozen and must be preserved.
- The current public storage mutation vocabulary remains `safe|cache` only.
- `safe` performs only independently owner-proven zero-capability-loss cleanup.
- P6/P7 authorize **no cache-family eviction** beyond safe cleanup.
- `checkpoint-model-cache` is retained/deferred by both safe and cache.
- `frame-cache` is retained/deferred by both safe and cache.
- Historical cache/path names do not grant deletion authority.
- PID liveness alone is not reconstructibility or cache ownership.
- Current P3 ownership is `.mdstats/target-size/g<generation>` and current P5 ownership is `.mdstats/post-selection/g<generation>/...`; do not manufacture a parallel `workspace/runs` cache authority for them.
- `storage report` is advisory and uses current neutral product wording, not STOR-era policy names.
- No new P6 lease/registry/cache-manifest subsystem is introduced.
- Ambiguous state fails toward retention.
- GPU/long-production qualification remains deferred.

### Delegated

- whether the now-unused cache-tier helper is deleted or folded into existing planning code, provided no cache deletion route remains;
- whether `_active_training_run_ids()` remains for independently justified non-cache safe cleanup;
- exact neutral `storage report` stdout heading;
- exact prohibited/deferred eligibility string for `checkpoint_model_cache`;
- exact test fixture sizes and bounded trainer/inference seams below the real P3/P5 owners;
- exact documentation prose and canonical PDF-generation mechanics.

### Reopen only on evidence

Reopen only this narrow cache-eviction decision if repository evidence demonstrates **all** of the following for a supported current P6/P7 execution path:

1. a real current semantic owner actually creates and consumes `checkpoint-model-cache` (or an equivalent cache family);
2. its canonical owner/run identity is explicit and not inferred from pathname;
3. its cache-validity identity is explicit;
4. every artifact needed for deterministic reconstruction is already authoritative, retained, and integrity-authenticated;
5. deletion cannot race an active consumer using already-existing current ownership/concurrency semantics;
6. enabling eviction does not require inventing successor-storage leases/registries/admission/transaction machinery in P6.

If any condition is absent, retain the cache and leave eviction to `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

Discovery of a historical producer, release patch, dormant helper, old test fixture, or dead `workspace/runs` convention is not sufficient evidence to reopen.

## 9. Anti-shortcuts

The following do not satisfy revision 11:

- keeping inactive `workspace/runs/*/checkpoint-model-cache` deletion and merely adding `checkpoint.pt` to the test fixture;
- treating an `active_process.json` PID as proof of cache ownership or reconstructibility;
- moving the fabricated active-run test under a differently named helper;
- adding a P3/P5 `active_process.json` solely so the storage test passes;
- creating a new cache manifest/lease solely to preserve revision-10 eviction behavior;
- making `cache` fail because it has zero additional candidates;
- deleting `frame-cache` instead as the positive cache candidate;
- moving historical cache names into safe cleanup;
- changing only report labels while a hidden deletion route remains;
- removing the public `cache` tier to avoid implementing its conservative semantics;
- weakening P3/P5 retention or revision-9 production-restart tests;
- implementing successor-storage archive/dedup/admission/lease behavior early.

## 10. Revision-11 PASS definition

P6 revision 11 is eligible for independent PASS only when:

```text
all accepted revision-9 scientific/P5 behavior preserved
+ revision-10 truthful public/config/help surface preserved
+ no hidden top-level cleanup alias
+ safe remains zero-capability-loss
+ cache has no additional destructive cache authorization in P6/P7
+ checkpoint-model-cache retained by safe and cache
+ frame-cache retained by safe and cache
+ historical cache names retained
+ current P3/P5 owner trees protected without fabricated workspace/runs ownership
+ report is advisory and free of current STOR-era mutation semantics
+ no new cache lease/registry/control plane
+ exact P5A6 compatibility PASS
+ fresh-P6 restart PASS
+ V5/V6 reject-before-reuse PASS
+ stage-local and final affected regression/integration closure
```

Only an independently reviewed **P6 revision-11 PASS** opens P7.
