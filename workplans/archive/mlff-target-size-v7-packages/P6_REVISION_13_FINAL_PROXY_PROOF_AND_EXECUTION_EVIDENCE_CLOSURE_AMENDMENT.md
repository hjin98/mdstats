---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6-R13
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P6
protocol_version: 5.8.0
revision: 13
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: e1eb4911069a5003c9d4195a52daf36dc0f813e1
reviewed_candidate_tree: d8ea290af256a0f6938206e26c12b0398b7a8d2f
reviewed_executable_commit: 3212201e70335724fd0fa345842b6949587b931e
reviewed_executable_tree: c1638420a073ebcc5310da4be765202846375f21
precedence: this amendment supersedes revision-12 acceptance-evidence details only; all accepted revision-3 through revision-12 runtime, scientific, storage, restart, public-surface, and documentation semantics remain binding
---

# P6 revision 13 amendment — final proxy-proof acceptance and executable-evidence closure

## 1. Independent review disposition

Independent review accepts the substantive revision-12 runtime correction in the reviewed executable candidate `3212201e70335724fd0fa345842b6949587b931e` / tree `c1638420a073ebcc5310da4be765202846375f21`:

- `_campaign_cleanup()` no longer enumerates `workspace/runs` or derives deletion authority from PID/path/age/`active_process.json` conventions;
- `_pid_alive()`, `_active_training_run_ids()`, `_cleanup_obsolete_training_runtimes()`, and their cleanup-only diagnostic helpers are removed;
- `CampaignStore.compact()` no longer calls `prune_sha256_receipts()`;
- safe/cache retain the historical `workspace/runs` trap and current cache families;
- current storage documentation describes safe cleanup as current-store orphan reclamation plus bounded diagnostic database housekeeping and states zero acceleration-cache eviction;
- the built-in guide now uses neutral `inspect cache tier cleanup` wording rather than advertising owner-proven cache deletion.

No new scientific, lifecycle, or storage-architecture defect was identified in those source changes.

P6 nevertheless remains **NO PASS** because two mandatory revision-12 proxy-proof tests are non-discriminating and the exact revision-12 candidate does not carry fresh executable evidence for the assembled acceptance boundary.

This revision reopens only test adequacy and final executable evidence. It does **not** reopen P1-P5 science, revision-9 multi-seed production/restart, revision-11/12 conservative storage behavior, P7 behavior, or the post-P7 storage-reset design.

## 2. Blocking acceptance defects

### 2.1 SHA-256 receipt retention test does not cross the real pruning boundary

`test_p6_r12_sha256_receipt_retention_through_storage_cleanup` creates only 20 receipt rows. The real retained owner `mdstats.training_data._common.prune_sha256_receipts()` defaults to `maximum_rows=100_000` and clamps the limit to at least 1,000 rows.

Therefore the pre-revision-12 defect — `storage cleanup -> CampaignStore.compact() -> prune_sha256_receipts()` — would also leave 20 rows unchanged. The current test can pass while the exact rejected cleanup-triggered pruning route is present.

The revision-12 requirement to cross the pruning threshold or use an equivalent discriminating seam is not satisfied.

### 2.2 Referenced external-record retention test does not create a real external pointer

`test_p6_r12_orphan_record_positive_reclamation_and_referenced_record_retention` creates `records/referenced_record` manually and then calls:

```python
store.put_record("custom_referenced", {"file": str(ref_obj)})
```

That small generic mapping is stored inline in SQLite. It does not use `EXTERNAL_RECORD_POINTER_SCHEMA`, DATA4 sharded-pointer authority, or DATA6 sharded-pointer authority, and `CampaignStore.storage_references()` therefore does not own `ref_obj` through that record. The object also remains younger than the cleanup grace interval, so the test passes because of age rather than because the current CampaignStore owner protects a stale referenced external artifact.

The revision-12 requirement for proxy-proof referenced-record retention through the real external-record owner is not satisfied.

### 2.3 Exact-candidate assembled execution evidence is absent

The tracked `P6_IMPLEMENTATION_EVIDENCE.md` still identifies revision 4 and contains no revision-12 candidate binding or fresh revision-12 execution results. For implementation commit `3212201e70335724fd0fa345842b6949587b931e`, the attached GitHub workflow is documentation-PDF generation only; it is not functional regression evidence.

Revision 12 explicitly requires fresh exact-candidate evidence for the focused storage checks, inherited P3/P5 cases, compatibility A/B/C, the real parser lifecycle, and the broader/full CPU-safe affected regression. Test source existing in the repository is not evidence that those checks executed.

## 3. Frozen implementation semantics

Revision 13 is acceptance-only unless a corrected test exposes a real defect. Preserve all of the following exactly:

```text
safe  -> current-owner zero-capability-loss cleanup only
cache -> safe + zero currently authorized cache-family eviction
```

In particular:

- no `workspace/runs`, `active_process.json`, PID, age, or historical-name deletion authority;
- no `checkpoint-model-cache`, `frame-cache`, SHA-256 receipt-cache, or uncertified historical cache eviction through public safe/cache cleanup;
- no new cache lease/registry/reconstruction owner in P6;
- current P3 `.mdstats/target-size/g<generation>` and P5 `.mdstats/post-selection/g<generation>` owners remain authoritative;
- CampaignStore orphan external-record reclamation may remain only for truly unreferenced current-store external artifacts after the grace interval and ownership-boundary checks;
- diagnostic event-history bounding plus SQLite optimize/VACUUM may remain only as the already-reviewed correctness-neutral CampaignStore housekeeping;
- P1-P5 scientific semantics and revision-9 multi-seed restart are frozen;
- no P7 or successor-storage implementation enters this stage.

Do not change production source merely to make the revised tests easier. If the corrected proxy-proof tests expose an actual runtime defect, repair that defect under these frozen semantics and rerun all invalidated evidence.

## 4. R13-A — make SHA-256 receipt retention genuinely discriminating

Replace or strengthen `test_p6_r12_sha256_receipt_retention_through_storage_cleanup` so it would fail if the rejected revision-12 route were restored.

### Required setup

Use the real receipt database configured by a real `CampaignStore`. Before public cleanup, populate **more than 100,000** deterministic rows in the real `receipts` table so the population exceeds the default pruning threshold. The preferred bounded test seam is one batched SQLite `executemany`/transaction directly below the existing receipt owner; do not create 100,001 physical files or add a production configuration knob solely for testing.

At minimum:

1. create/open a real bounded campaign and `CampaignStore` so the normal receipt database is configured;
2. insert at least 100,001 syntactically valid, unique receipt rows into that database in one bounded transaction;
3. create at least two real small files and authenticate them through `sha256_file_cached()` so the test also exercises the actual public cache API;
4. write representative validation receipts and record their exact values;
5. commit/close any direct setup transaction before cleanup.

### Required execution

Invoke, through the real public parser/dispatcher:

```text
storage cleanup --tier safe
storage cleanup --tier cache
```

### Required assertions

After each tier:

- the receipt-row count is unchanged from the pre-cleanup count;
- the exact sentinel receipt rows remain;
- validation receipts are byte/value unchanged;
- the real files still return exactly the same SHA-256 through `sha256_file_cached()`;
- no cleanup action/manifest claims receipt-cache reclamation.

Also retain a scoped structural assertion that the current safe/cache cleanup path and `CampaignStore.compact()` do not call/import `prune_sha256_receipts()` as cleanup authority.

A 20-row population, a population below 100,001 rows, a dry-run-only check, or checking only function-source absence is insufficient by itself.

## 5. R13-B — exercise the real external-record owner

Replace the false proxy in `test_p6_r12_orphan_record_positive_reclamation_and_referenced_record_retention` with a real current CampaignStore external pointer.

### Required setup

1. create a real campaign and `CampaignStore`;
2. publish a unique test record through **`CampaignStore.put_record()`** with a deterministic mapping whose encoded size exceeds `EXTERNAL_RECORD_THRESHOLD_BYTES`, so the normal owner emits `EXTERNAL_RECORD_POINTER_SCHEMA`; do not hand-author the pointer;
3. read the raw stored pointer or `store.storage_references()` and assert that the referenced path is inside `store.external_record_directory` and is actually owned by that record;
4. set the referenced external file's mtime older than `[cleanup].stale_age_hours` so age cannot protect it;
5. create a separate unreferenced sibling artifact under `external_record_directory`, also older than the grace interval;
6. close/reopen the store as needed so no incidental open transaction is the retention mechanism.

### Required execution and assertions

Through the real public parser/dispatcher, run safe cleanup and then cache cleanup. For both tiers:

- the old referenced external file remains;
- reopening `CampaignStore` and `get_payload()` for the owning record returns the original exact mapping;
- the old unreferenced sibling is reclaimed by the safe portion of cleanup;
- no keep-list, mocked `storage_references()`, youthful mtime, or manually fabricated pointer supplies the result.

A generic inline record containing a pathname string is not a valid substitute.

Retain the existing external-root and symlink-containment tests as separate physical-safety evidence.

## 6. R13-C — fresh exact-candidate executable acceptance

After R13-A/B test changes and after any runtime correction they genuinely force, execute the full P6 acceptance on one assembled executable candidate.

### 6.1 Focused revision-13 stage-local closure

At minimum execute together:

- `tests/test_mlff_target_size_p6_destructive_closure.py`;
- `tests/test_mlff_stor1_storage_accounting.py`;
- `tests/test_mlff_stor3_safe_reclamation.py`;
- `tests/test_mlff_stor4_manual_reclamation.py`.

The result must be zero failures/errors/skips for required R11-R13 acceptance cases.

### 6.2 Inherited P6 functional acceptance

Freshly execute on the same executable tree:

1. revision-8 DATA5/P1-P4 neutrality/ownership cases;
2. revision-9 two-seed P5 plan-only, proper-subset, resume-only-missing-seed, corruption/mismatch fail-closed, all-complete, and process-reopen cases;
3. revision-11 cache-family retention/report/public-surface cases;
4. revision-12 historical `workspace/runs` marker/PID retention and the corrected receipt-retention case;
5. real P3 publication-before-adoption retention;
6. P5 plan-only, partial multi-seed, and completed cleanup retention;
7. exact accepted-P5A6 producer compatibility **A**;
8. independent fresh final-P6 close/reopen/restart **B**;
9. retired V5/V6 reject-before-reuse **C**;
10. real parser/dispatch lifecycle `prepare -> select-target-size -> cross-validate -> train-production`, including close/reopen/currentness.

A, B, and C must be reported separately. One case may not stand in for another.

### 6.3 Final broader/full CPU-safe regression

Because the revision-12 implementation changed `_campaign_cli_core.py`, `CampaignStore`, cleanup behavior, and shared receipt interactions, run the repository's broader/full CPU-safe regression on the final executable tree. The established command is:

```bash
conda run -n mace python -m pytest -n 16 -q -p no:randomly
```

If the repository-wide result contains pre-existing/environment-specific nonpasses, they do not automatically fail P6, but they must be classified rather than ignored:

- every required P6/R8-R13 test must pass;
- every final nonpass must be shown pre-existing/environmental by exact node-ID comparison against an appropriate baseline;
- if the existing recorded baseline is insufficient to classify a final nonpass, run the same command in a detached worktree at reviewed executable parent `3212201e70335724fd0fa345842b6949587b931e` and compare node IDs;
- **zero new final nonpasses attributable to P6/R13** is required.

Do not reduce the final regression surface merely because the focused tests pass.

Long GPU, target-machine, or real-data production qualification remains deferred and is not part of this gate.

## 7. R13-D — bind evidence to the exact tested tree

Reconcile the existing `workplans/active/mlff-target-size-v7-packages/P6_IMPLEMENTATION_EVIDENCE.md` rather than creating an unrelated evidence ledger.

It must state at minimum:

- package revision 13;
- exact tested executable commit/tree;
- exact commands and results for R13 focused tests;
- separate A/B/C results;
- real lifecycle result;
- final broader/full CPU-safe command, counts, and nonpass classification;
- confirmation that no required acceptance test was skipped;
- documentation/PDF workflow result for the final documentation source;
- explicit statement that GPU/long production qualification is deferred rather than claimed.

It is acceptable for the evidence-only commit and the documentation-PDF bot commit to occur after the tested executable commit, provided a compare proves **no executable source or test files changed** after the tested executable tree. Any executable/test edit after the recorded run invalidates affected evidence and requires rerun before review.

## 8. PASS boundary

Revision-13 P6 PASS requires all of the following on one final assembled candidate:

```text
revision-12 runtime/storage/public semantics preserved
+ receipt-retention test exceeds the real 100,000-row prune threshold
+ real stale CampaignStore external pointer retained while stale orphan sibling is reclaimed
+ historical workspace/runs trap retained for absent/malformed/dead/live marker cases
+ current P3/P5 owner retention PASS
+ revision-9 multi-seed restart/integrity PASS
+ A PASS separately
+ B PASS separately
+ C PASS separately
+ real parser lifecycle PASS
+ final broader/full CPU-safe affected regression executed with zero new attributable nonpasses
+ exact tested commit/tree and commands/results recorded in reconciled P6_IMPLEMENTATION_EVIDENCE.md
+ docs/PDF generation PASS
```

Only an independent **P6 revision-13 PASS** opens P7.

## 9. Anti-shortcuts

The following do not satisfy revision 13:

- keeping the 20-row receipt test;
- lowering the production pruning threshold merely so the test crosses it;
- mocking cleanup so `CampaignStore.compact()` is bypassed;
- replacing behavioral receipt evidence only with a source-string assertion;
- treating an inline `{file: path}` mapping as an external-record pointer;
- leaving the real referenced file young enough for age alone to retain it;
- hand-authoring an external pointer instead of publishing through `CampaignStore.put_record()`;
- reporting test source presence as execution evidence;
- citing the documentation-only GitHub workflow as functional regression;
- reusing revision-4 full-suite results as if they were a fresh revision-13 run;
- weakening or skipping A/B/C or the revision-9 multi-seed cases for runtime economy;
- reopening accepted science/storage architecture without a corrected test exposing a real defect.

## 10. Reopen triggers

Implementation should proceed directly under this amendment. Reopen Design again only if corrected proxy-proof testing demonstrates one of these material facts:

1. safe/cache still reaches SHA-256 receipt pruning through a path not visible in the reviewed source;
2. a real stale external pointer can be reclaimed despite an owning current CampaignStore record;
3. the final broader/full regression exposes a new P6-attributable functional failure outside the frozen correction envelope;
4. A/B/C or the current P3/P5 lifecycle fails because revision-12 cleanup changed scientific/restart state.

Otherwise this is a bounded acceptance closure: fix the tests/evidence, execute the frozen acceptance, and return the exact final candidate for independent review.
