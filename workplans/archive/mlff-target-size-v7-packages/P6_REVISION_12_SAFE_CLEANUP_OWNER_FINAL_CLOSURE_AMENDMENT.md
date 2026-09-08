---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6-R12
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6
protocol_version: 5.8.0
revision: 12
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: 79b7cf372df4637d6e8bfccfb31071da4fba8d76
reviewed_candidate_tree: 444e2c8e30be94b2e7a326d80411bb8b4e4c753b
reviewed_executable_commit: a051850f3a0cf1bd6c3392cb097e868b92f382f8
reviewed_executable_tree: ad3e9bb2fb5e1436d2b92cd69f7aa7db41cda3a0
precedence: this amendment supersedes revision-11 delegation that allowed workspace/runs PID-based non-cache safe cleanup and tightens safe cleanup so all remaining destructive actions require a surviving current owner; all unrelated P6 revision-3 through revision-11 obligations remain binding
---

# P6 revision 12 amendment — safe-cleanup current-owner final closure

## 1. Objective and review diagnosis

Revision 12 closes the final source-level P6 blocker found by independent review of the revision-11 implementation. It does not reopen accepted P1-P5 science, revision-9 multi-seed final-production restart, revision-11 cache retention, P7 behavior, or the post-P7 storage-reset architecture.

Revision 11 correctly removed positive cache-family eviction. The reviewed candidate nevertheless leaves a second historical storage authority reachable from both public cleanup tiers because `cache` includes `safe`:

```text
storage cleanup --tier safe/cache
    -> _campaign_cleanup(...)
    -> enumerate CampaignPaths.runs == workspace/runs
    -> _active_training_run_ids(...)
         -> read workspace/runs/<name>/active_process.json
         -> interpret PID liveness
         -> unlink dead/malformed marker as a side effect
    -> _cleanup_obsolete_training_runtimes(...)
         -> for every inactive workspace/runs/<run>/obsolete-runtime-*
         -> _cleanup_remove(...) the entire obsolete-runtime-* subtree
```

That authorization is no longer backed by a surviving current execution owner. The P6 destructive cutover itself classifies `campaign_execution` as retired and requires that module to be physically absent. Current P3 and P5 use their canonical `.mdstats/target-size/g<generation>` and `.mdstats/post-selection/g<generation>` owner trees. Therefore pathname `workspace/runs/*`, marker `active_process.json`, process liveness, age, and `obsolete-runtime-*` naming cannot establish current deletion authority.

A second violation exists in the same safe path. `CampaignStore.compact()` currently calls `prune_sha256_receipts()`. The receipt database is explicitly an optional restart/performance optimization. Deleting receipt rows from `storage cleanup --tier safe` is therefore acceleration-cache eviction, contradicting the frozen revision-11 requirement that safe cleanup perform zero acceleration-cache eviction.

The corrected product outcome is:

```text
P6/P7 public storage cleanup may destructively mutate only artifacts whose surviving
current semantic owner proves the action safe under current lifecycle semantics.
Retired workspace/runs conventions, PID markers, age, and historical names grant no
authority. Safe cleanup evicts no acceleration cache. Ambiguity means retention.
```

## 2. Frozen current ownership and non-goals

### 2.1 Current scientific/execution owners

The following remain frozen:

- P3 target-size execution root: `.mdstats/target-size/g<generation>` through the current target-size path/runtime owners.
- P5 post-selection root: `.mdstats/post-selection/g<generation>` and its authenticated plans/run evidence/completion owners.
- P4 selection, P5 CV, P5 final-production, and revision-9 multi-seed restart semantics are unchanged.
- P6 remains cleanup/cutover functional closure; it does not implement P7 or `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

### 2.2 Retired `workspace/runs` execution authority

For current P6/P7 storage mutation, all of the following are non-authoritative historical conventions:

- `CampaignPaths.runs == workspace/runs` as an execution-liveness authority;
- `workspace/runs/<name>/active_process.json`;
- PID existence/liveness read from such a marker;
- `workspace/runs/<name>/obsolete-runtime-*`;
- absence, corruption, or age of a marker;
- staleness/mtime of the run tree;
- the historical `campaign_execution` module or its old tests/contracts.

Do not restore `campaign_execution`, create a replacement compatibility owner, or add a new writer/lease/registry merely to preserve this cleanup path.

### 2.3 Cache-family rule remains frozen

Revision 11 remains authoritative:

```text
safe  -> zero acceleration-cache eviction
cache -> safe plus no additional destructive cache-family authorization
```

Both tiers retain/defer `frame-cache`, `checkpoint-model-cache`, SHA-256 receipt-cache entries when invoked through storage cleanup, and uncertified historical cache families.

This amendment does not prohibit an independently owned cache from enforcing its own bounded internal retention policy during normal cache writes if that policy already belongs to the cache owner and is independent of `storage cleanup`. It does prohibit public safe/cache cleanup from being the trigger or authorization source for such eviction.

## 3. Required implementation consequences

### R12-A — remove retired `workspace/runs` deletion authority from safe/cache

In `mdstats/training_data/_campaign_cli_core.py`:

1. Remove `_cleanup_obsolete_training_runtimes()` from every current automatic/manual safe/cache route.
2. Preferred realization: delete `_cleanup_obsolete_training_runtimes()` if no supported non-storage caller remains. Do not keep dead consequential deletion machinery merely because it is harmless when uncalled.
3. `_campaign_cleanup()` must stop enumerating `paths.runs`, stop creating `run_roots`, and stop deriving cleanup permission from `_active_training_run_ids()`.
4. Public safe/cache cleanup must not traverse `workspace/runs` merely to identify deletable runtime state.
5. No path named `obsolete-runtime-*` may become deletable merely because it is below `workspace/runs`, old, or apparently inactive.
6. `active_process.json` must not be unlinked by storage cleanup because its PID is dead, malformed, missing, or otherwise non-live.
7. `_pid_alive()` and `_active_training_run_ids()` may remain only if a separately surviving current non-storage/non-cleanup caller genuinely owns them. If their only remaining purpose is the retired cleanup path, delete them and their cleanup-specific diagnostics as ordinary dead-code removal.
8. Do not replace the removed route with a renamed path heuristic, a different marker filename, stage-name inference, or filesystem-age heuristic.

### R12-B — remove acceleration-cache pruning from safe cleanup

`CampaignStore.compact()` currently prunes the SHA-256 receipt cache after event-table/VACUUM work. This is incompatible with safe zero-cache-eviction semantics when called from `_campaign_cleanup()`.

Required end state:

1. `storage cleanup --tier safe` and `--tier cache` do not delete SHA-256 receipt-cache rows.
2. Remove `prune_sha256_receipts()` from the storage-cleanup-triggered compaction path, or split the database maintenance so safe cleanup invokes only the non-cache portion.
3. Do not delete `validation_receipts` or any other validation/authentication receipt as a substitute.
4. If bounded SHA-256 receipt retention is materially required to avoid unbounded cache growth, preserve it as an independently owned `_common.py` cache self-maintenance policy during normal receipt writes/owner operation, not as storage-cleanup authorization. Reuse the existing receipt owner; do not add a new storage registry or lease.
5. Any such self-maintenance must remain correctness-neutral: pruning may create a cache miss/full rehash only and may never make invalid bytes appear valid.
6. Do not weaken the revision-11 public statement that safe/cache storage cleanup performs zero acceleration-cache eviction.

### R12-C — review and retain only current-owner safe actions

After removing the retired run-tree route, re-derive every destructive action still reachable from `_campaign_cleanup()`.

At minimum review:

- orphan external-record storage cleanup;
- CampaignStore event-history bounding / SQLite optimize/VACUUM;
- cleanup report/manifest publication;
- any automatic lifecycle caller of `_campaign_cleanup()`.

Required rules:

1. Orphan external-record deletion may remain only because the current CampaignStore owner proves the object is unreferenced, the ownership boundary permits mutation, the object is stale under the accepted grace window, and deletion cannot remove a referenced current record.
2. Event-history bounding may remain only if source inspection confirms `events` is diagnostic history and is not consumed as scientific identity, currentness, restart, compatibility, or completion authority. The current source should have no semantic reader of old event rows. Add/retain a focused regression protecting current stage/state behavior after compaction.
3. SQLite optimize/VACUUM may remain as database maintenance if it preserves current database records and fails safely under lock/contention. Do not claim retired PID markers are needed to authorize it.
4. If any remaining safe candidate lacks a current semantic owner and zero-capability-loss proof, retain it rather than inventing an owner.
5. `safe` is allowed to become a no-op on a workspace with no independently certified garbage. Reclamation volume is not an acceptance criterion.

### R12-D — reconcile current documentation with actual safe behavior

Update all current normative/user-facing storage wording that still implies historical run cleanup is supported.

At minimum inspect and reconcile:

- `docs/specs/training_data/mlff_storage_management_spec.md`;
- `docs/guides/mlff_campaign_cli_user_guide.md`;
- built-in `GUIDE_TEXT`/generated config/help if they describe safe candidates;
- affected architecture/manual source and generated PDFs.

The current spec must not say safe cleanup targets `obsolete runtime scratch` or generic aborted run trees unless a surviving current owner actually proves that behavior. Describe only actions that remain reachable after R12, for example current-store orphan record reclamation and diagnostic database housekeeping if those actions pass R12-C.

Keep these revision-11 truths unchanged:

- public vocabulary is `storage report`, `storage cleanup --tier safe`, `storage cleanup --tier cache`;
- both cleanup tiers evict no current acceleration-cache family;
- consequential archive/dedup/recompute/compact tiers remain deferred to the post-P7 storage reset;
- P3/P5 scientific/restart evidence is retained.

Regenerate tracked PDFs through the canonical documentation workflow; do not edit generated PDF bytes directly.

## 4. Proxy-proof acceptance

### 4.1 Historical run-tree trap — mandatory

Through the real public parser/dispatcher, construct a bounded campaign workspace containing a historical-looking tree such as:

```text
workspace/runs/legacy-run/
    active_process.json                 # vary by case
    obsolete-runtime-old/
        logs/stdout.log
        tmp/payload
        staging/payload
        scratch/payload
        checkpoint-model-cache/model.pt
        evaluation-graph-cache/payload
        prediction-cache/payload
```

Set mtimes older than `[cleanup].stale_age_hours` so age cannot accidentally protect the tree.

Exercise at least these marker cases independently:

1. no `active_process.json`;
2. malformed marker;
3. marker containing a definitely dead/nonexistent PID;
4. marker containing the current live test-process PID.

For every case run both:

```text
storage cleanup --tier safe
storage cleanup --tier cache
```

Required result:

- every byte under the historical `workspace/runs` trap remains;
- the marker itself remains and is not unlinked by cleanup;
- changing PID state cannot change cleanup authorization;
- no cleanup action/manifest describes the trap as reclaimed.

A direct call to `_cleanup_remove()`, a fabricated `active_run_ids` set, or testing only `_build_manual_tier_report()` is insufficient. The real public safe path must execute.

### 4.2 Structural absence — mandatory

On the assembled candidate prove:

- `_campaign_cleanup()` contains no destructive candidate construction derived from `paths.runs`;
- current safe/cache dispatch does not call `_active_training_run_ids()` or inspect `active_process.json`;
- no reachable safe/cache function deletes `obsolete-runtime-*` by pathname;
- `campaign_execution.py` remains absent/retired and no replacement compatibility wrapper was introduced;
- no cache deletion was moved into another safe helper;
- storage report classifications remain advisory only.

Scoped source/AST assertions are acceptable and preferred for these absence claims. Do not impose repository-wide keyword bans on historical docs/patches/tests.

### 4.3 SHA-256 receipt retention — mandatory

Create enough deterministic receipt rows to cross the pruning threshold used by the implementation or lower the threshold only through an accepted test seam below the real owner. Then invoke public safe/cache cleanup.

Required:

- receipt rows are not pruned by either storage cleanup tier;
- validation receipts are unchanged;
- subsequent `sha256_file_cached()` calls remain correct;
- if independent cache-owner self-pruning exists outside storage cleanup, test that it only converts old hits into rehashes and cannot alter the resulting SHA-256.

Do not satisfy this by removing receipt caching or by weakening the zero-cache-eviction public contract.

### 4.4 Current owner retention — preserve inherited evidence

Continue to exercise real current owners:

- P3 publication/restart state under `.mdstats/target-size/g<generation>` including publication-before-adoption retention;
- P5 final plan with zero runs;
- P5 proper-subset multi-seed production state;
- P5 completed-production state;
- current P5 evidence corruption/mismatch fail-closed behavior.

Bounded trainer/MACE/inference fakes remain allowed only below these owners.

## 5. Required regression and integration closure

R12 is one coherent executable stage. After implementing R12-A through R12-D, perform stage-local semantic closure and affected regression before declaring the stage complete.

Focused/stage-local checks must cover:

- public safe/cache historical run-tree retention for all marker cases;
- no marker unlink side effect;
- no `paths.runs`/PID/obsolete-runtime destructive authorization;
- SHA-256 receipt retention through storage cleanup;
- orphan external-record positive reclamation and referenced-record retention if that behavior remains;
- event-history/database compaction preserving current stage/state/record semantics if retained;
- physical containment, external-input, and symlink safety;
- revision-11 cache-family retention and neutral report behavior;
- current config/help/guide/spec consistency.

Final assembled P6 acceptance must then freshly include:

1. all revision-8 DATA5/P1-P4 neutrality and ownership cases;
2. all revision-9 P5 multi-seed plan-only/proper-subset/resume-only-missing-seed/corrupt/all-complete/process-reopen cases;
3. all revision-11 cache-family retention/report/public-surface cases;
4. revision-12 historical `workspace/runs` and receipt-cache retention cases;
5. P3 publication-window retention;
6. P5 plan-only/partial/completed cleanup retention;
7. exact P5A6 producer compatibility qualification A;
8. independent fresh final-P6 producer close/reopen/restart qualification B;
9. retired V5/V6 reject-before-reuse qualification C;
10. real parser/dispatch lifecycle `prepare -> select-target-size -> cross-validate -> train-production` with close/reopen/currentness;
11. documentation source/PDF generation;
12. complete affected-surface CPU-safe regression. Because `_campaign_cli_core.py`, CampaignStore, and shared receipt handling are central surfaces, run the broader/full CPU-safe suite unless a genuinely complete smaller bound is demonstrated.

The final review must have executable evidence tied to the exact assembled candidate. The presence of test source files or a successful documentation-only workflow is not substitute evidence. A required check that did not execute is not a pass.

Long GPU, target-machine, and real-data production qualification remains deferred and is not part of R12/P6 closure.

## 6. Implementation authority

### Frozen

- All accepted P1-P5 scientific and revision-9 restart behavior remains unchanged.
- Revision-11 no-cache-family-eviction behavior remains unchanged.
- `workspace/runs`, `active_process.json`, PID liveness, age, and `obsolete-runtime-*` naming are not current cleanup authorities.
- Safe/cache storage cleanup must not prune SHA-256 receipt-cache entries.
- Ambiguous/unowned artifacts fail toward retention.
- No historical execution owner or compatibility wrapper may be resurrected to justify cleanup.
- No successor-storage lease/registry/cache-control plane may be introduced in P6.
- P7 and the post-P7 storage reset remain gated.

### Delegated

- deletion versus retention of now-dead private helpers after reachability is removed;
- exact factoring of CampaignStore diagnostic event-table compaction versus receipt-cache maintenance;
- exact bounded fixture sizes and receipt-pruning test seam;
- exact truthful documentation wording;
- exact neutral cleanup-report messages when a tier has no actions.

### Reopen only on evidence

Reopen Design only if one of the following is demonstrated by current source/behavior:

1. a surviving current P3/P5/current-generation producer genuinely owns `workspace/runs/obsolete-runtime-*` and its deletion is materially required for correctness/resource feasibility;
2. a remaining safe candidate cannot be expressed through its current owner without a material new ownership architecture;
3. CampaignStore `events` rows or receipt rows are discovered to be authoritative scientific/restart/compatibility state rather than diagnostic/cache state;
4. removing the retired run-tree gate makes an independently required current database operation unsafe in a way that cannot be handled by existing SQLite ownership/locking semantics.

Otherwise this is implementation repair, not another architecture search.

## 7. Anti-shortcuts

The following do not satisfy R12:

- merely excluding `checkpoint-model-cache` while keeping `obsolete-runtime-*` subtree deletion;
- renaming `active_process.json` or the obsolete-runtime prefix;
- keeping marker deletion but claiming it is not cleanup because it is small;
- treating a dead PID as permission to delete historical runtime bytes;
- moving the same path heuristic into `storage_accounting.py` or another helper;
- deleting receipt rows while calling them database maintenance rather than cache eviction;
- disabling receipt caching entirely to make the pruning test vacuous;
- adding a new P3/P5 PID marker solely to legitimize the old cleanup path;
- weakening the historical-path trap or inherited P3/P5 retention tests;
- replacing required executable regression with source inspection or docs CI;
- implementing successor storage machinery early.

## 8. Revision-12 PASS definition

P6 revision 12 is eligible for independent PASS only when:

```text
all accepted revision-11 science/P5/cache/public behavior preserved
+ no current safe/cache workspace/runs path-derived deletion authority
+ active_process/PID state has zero storage-cleanup authorization effect
+ obsolete-runtime-* historical trees are retained
+ safe/cache storage cleanup does not prune SHA-256 receipt cache
+ every remaining safe destructive action has a surviving current owner and zero-capability-loss proof
+ real P3/P5 owners remain protected
+ A/B/C compatibility qualification PASS
+ real lifecycle integration PASS
+ stage-local affected regression PASS
+ final broader/full CPU-safe regression/integration executed on the exact assembled candidate
+ affected documentation/PDFs are current
```

Only an independently reviewed **P6 revision-12 PASS** opens P7.