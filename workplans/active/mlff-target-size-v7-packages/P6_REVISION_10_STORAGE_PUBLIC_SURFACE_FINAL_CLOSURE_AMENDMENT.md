---
kind: implementation-package-amendment
package_id: CODE-MLFF-TARGET-SIZE-V7-P6-R10
parent_package_id: CODE-MLFF-TARGET-SIZE-V7-P6
parent_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
package_revision: 10
status: active
amended_date: 2026-08-31
reviewed_candidate_commit: 93150315466671334bf0ac5ed1f187d8cc304407
reviewed_candidate_tree: bc88d82ae3f9db8996da39d8af0735d9a9e7a25c
reviewed_executable_parent_commit: 2669fbfe25bae3a8aba2c81c1daff37207c88fbb
reviewed_executable_parent_tree: ead2dd491782322117b5d3d7f5690cff8d922da7
amends:
  - P6_REVISION_3_BASE.md
  - P6_REVISION_4_P5A6_COMPATIBILITY_AMENDMENT.md
  - P6_REVISION_5_CLEANUP_CLOSURE_AMENDMENT.md
  - P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md
  - P6_REVISION_7_FINAL_CLOSURE_AMENDMENT.md
  - P6_REVISION_8_BLOCKER_REPAIR_AMENDMENT.md
  - P6_REVISION_9_FINAL_IMPLEMENTATION_CLOSURE_AMENDMENT.md
precedence: this amendment overrides earlier P6 text only where explicitly stated; all other obligations remain binding
successor_p7_workplan: CODE-MLFF-TARGET-SIZE-V7-P7
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P6 revision 10 amendment — final storage/public-surface closure

## 1. Purpose and review disposition

Independent Design review of the revision-9 implementation found **one remaining blocking area**, entirely within the transitional storage/public-surface closure. The revision-9 candidate materially closed the P5 multi-seed final-production/restart acceptance requirement and must preserve that work unchanged unless a storage edit exposes a genuine regression.

The remaining defects are:

1. the generated campaign configuration still advertises retired `recompute|compact|archive` cleanup tiers in its `[cleanup]` comment;
2. the built-in `GUIDE_TEXT` still presents recompute reclamation, archive create/restore, and deduplication as current operations even though the Markdown user guide was corrected;
3. `_normalize_legacy_storage_argv()` still exposes the retired hidden top-level `cleanup` alias without a demonstrated current compatibility contract;
4. `safe` and `cache` cleanup remain semantically inconsistent: automatic/`safe` cleanup removes `checkpoint-model-cache`, while the manual `cache` tier separately identifies the same artifact as an acceleration-loss cache;
5. manual `cache` cleanup unconditionally selects `frame-cache` by pathname even though the current runtime still loads/rebuilds that cache on demand and P6 has no storage lease proving concurrent non-use;
6. the read-only storage report still publishes retired STOR-era reclamation classifications such as `stor3_automatic_safe`, `recompute`, `compact_*`, `stor5_managed`, and protocol-freeze-derived eligibility.

These are **implementation nonconformances against the already accepted P6 architecture**. Revision 10 does not reopen target-size science, DATA5/P5 ownership, final-production completion, A/B/C compatibility, P7, or the successor storage-reset design.

## 2. Accepted revision-9 outcomes that are frozen

The following are accepted and must not regress:

- fresh current DATA5 is CV-plan-free;
- `[post_selection.cv]` is the sole current fold-policy owner and P1-P4 remain independent of CV-only edits;
- final-production plan and completion are distinct authorities;
- completion requires authenticated evidence for every required final seed;
- the dedicated two-seed acceptance path demonstrates plan-only, proper-subset, corrupt-evidence, complete, and process-reopen states;
- after seed 5 is authenticated and seed 6 is interrupted, restart executes **only seed 6**;
- A/B/C qualification remains producer-distinct: exact P5A6 -> P6, fresh P6 -> P6, V5/V6 reject-before-reuse;
- current parser exposes `storage report` and `storage cleanup --tier safe|cache`; consequential storage transformation belongs to `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`;
- P7 remains downstream and is not implemented in P6;
- long GPU/real-data production qualification remains deferred.

No P5 redesign or new persistence authority is authorized by this amendment.

## 3. Frozen final transitional-storage model

P6/P7 transitional storage has exactly this current policy:

```text
storage report
    -> read-only advisory accounting
    -> never grants deletion authority

storage cleanup --tier safe
    -> zero capability-loss cleanup only
    -> temporary/garbage/stale runtime state whose current owner proves disposal safe
    -> NO acceleration-cache eviction

storage cleanup --tier cache
    -> includes the safe tier
    -> may additionally evict only independently reconstructible caches whose
       current owner proves they are not live/current-consumer state
    -> in P6, the supported positive cache candidate is inactive-run
       checkpoint-model-cache

frame-cache
    -> current reusable performance cache
    -> retained by both safe and cache in P6
    -> no P6 lease/consumer registry is added solely to make it evictable

retired historical path families
    -> retained unless a current owner independently certifies them
    -> pathname/report classification alone never authorizes deletion
```

The successor storage reset may later introduce cross-owner inventory, leases, admission, dedup/archive, and broader cache policy. P6 must not implement those mechanisms.

## 4. R10-A — make current configuration and built-in guidance truthful

### 4.1 Generated configuration

In `mdstats/training_data/_campaign_cli_core.py::_config_template()` and the tracked `campaign.toml.example`:

- the `[cleanup]` section must describe the current surface as `storage cleanup --tier safe|cache` only;
- it must not advertise `recompute`, `compact`, or `archive` as current cleanup tiers;
- no retired automatic cleanup key may reappear;
- the generated configuration must remain otherwise semantically unchanged.

The tracked example must be regenerated/reconciled from the canonical configuration source rather than allowed to diverge manually.

### 4.2 Built-in `GUIDE_TEXT`

Replace the current storage section so it agrees with `docs/guides/mlff_campaign_cli_user_guide.md` and the transitional storage specification.

Required current message:

```text
storage report                         read-only inventory
storage cleanup --tier safe --dry-run  inspect zero-loss cleanup
storage cleanup --tier cache --dry-run inspect owner-proven cache cleanup
storage cleanup --tier safe|cache      apply the selected transitional tier
```

The built-in guide must explicitly state that recompute/compaction/archive/deduplication are deferred to `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.

It must not instruct users to run:

```text
storage cleanup --tier recompute
storage cleanup --tier compact
storage cleanup --tier archive
storage archive create
storage archive restore
storage deduplicate --apply
```

Read-only historical archive verification need not be documented as a current workflow unless it is actually exposed by the current parser.

### 4.3 One current public contract

The following surfaces must agree:

- parser/help;
- `_config_template()` comments;
- `campaign.toml.example`;
- `GUIDE_TEXT` / `guide` command;
- `docs/guides/mlff_campaign_cli_user_guide.md`;
- `docs/specs/training_data/mlff_storage_management_spec.md`;
- affected architecture/manual storage wording.

Do not preserve contradictory wording for compatibility. Documentation compatibility is not a product requirement.

## 5. R10-B — remove the unsupported top-level cleanup alias

No current compatibility contract has been demonstrated for the hidden pre-unification top-level `cleanup` command. Therefore the final P6 implementation must remove it rather than carry an unnecessary adapter.

Required consequences:

1. delete `_normalize_legacy_storage_argv()` from the current CLI;
2. `main()` passes the caller argv directly to the current parser using normal argparse semantics;
3. `cleanup ...` at top level is rejected by argparse;
4. `storage cleanup ...` remains the sole cleanup namespace;
5. do not add another alias, warning shim, or compatibility wrapper.

If repository evidence demonstrates a real still-supported external contract that requires the alias, stop this specific removal and reopen only that compatibility decision. Existing tests or historical release notes alone are not such a contract.

## 6. R10-C — separate safe cleanup from cache eviction

### 6.1 Safe tier invariant

`safe` means **zero user-visible capability loss**. It must not delete an acceleration cache merely because that cache is reconstructible.

Consequently:

- `_campaign_cleanup()` as used by automatic lifecycle cleanup and the `safe` tier must not call `_cleanup_checkpoint_model_caches()` or another cache-eviction helper;
- automatic lifecycle cleanup is safe-only in P6;
- safe cleanup may continue to remove independently owner-proven garbage/stale staging/obsolete runtime state where doing so loses no current scientific, restart, diagnostic, or acceleration capability;
- if an existing safe candidate actually removes a supported acceleration/reanalysis capability, move it out of safe or retain it.

The current implementation's claim that `checkpoint-model-cache` is zero-loss in automatic cleanup but acceleration-loss in manual cache cleanup is invalid and must disappear.

### 6.2 Cache tier positive candidate

The P6 `cache` tier may remove `checkpoint-model-cache` only when all of the following hold through the real current owner path:

1. the candidate is under a campaign-owned contained run root;
2. the run root is not a currently active training run according to the existing current run-liveness owner (`_active_training_run_ids()` or its accepted replacement);
3. raw restart checkpoints / authoritative model or run evidence required for reconstruction and restart remain retained;
4. the P3 retention fence and other current ownership checks do not deny mutation;
5. symlink handling preserves the existing unlink-without-external-traversal guarantee.

Do not decide inactivity from directory age or pathname alone.

Implementation should reuse the existing run-root/liveness discovery already used by current cleanup rather than create a second liveness authority.

### 6.3 Frame-cache disposition — frozen conservative choice

For P6, **remove `frame-cache` from both automatic and manual cache deletion candidates.**

Rationale:

- the current runtime still loads and rebuilds `.mdstats/frame-cache` on demand;
- no current storage lease or active-consumer registry proves safe concurrent eviction;
- adding such a registry solely for this cleanup feature would duplicate or pre-implement successor-storage architecture;
- retaining a reconstructible performance cache is operationally cheaper than introducing an ownership race or new control plane at P6 closure.

Therefore:

```text
safe  -> retain frame-cache
cache -> retain frame-cache
```

The successor storage reset may reconsider eviction with proper owner/lease semantics.

Do not replace this with a new P6 lease system or a stage-name heuristic such as "prepare complete means frame-cache safe".

### 6.4 Historical-path trap remains fail-toward-retention

Current cleanup must continue to retain uncertified historical names including, at minimum:

- `data7-cache`;
- `data8-fixed-cache`;
- `evaluation-graphs`;
- `evaluation-predictions`;
- `model-sweep`;
- `true-label-replay`;
- historical evaluation capsules/materialization roots where no current owner grants cleanup.

No current deletion path may infer eligibility from these names.

## 7. R10-D — make `storage report` advisory and current-generation truthful

`storage report` is read-only, but its classifications are still current product information and must not claim retired policies are active.

### 7.1 Remove retired policy labels from current report output

In `mdstats/training_data/storage_accounting.py` and affected tests, current report records must not advertise policy values containing or equivalent to:

```text
STOR1
stor2_*
stor3_*
stor5_*
recompute
compact_*
*_after_protocol_freeze
protocol_freeze
```

Historical source files/release patches may retain those names; current report output may not.

### 7.2 Required current dispositions

At minimum, classify these current/historical families consistently with executable policy:

- `checkpoint-model-cache`: automatic eligibility prohibited; manual status may identify it only as a **cache candidate subject to current owner/liveness authorization**, not as unconditional deletion permission;
- `frame-cache`: automatic prohibited; manual prohibited/deferred in P6;
- `data7-cache`, `data8-fixed-cache`, `evaluation-graphs`: automatic prohibited; manual prohibited/deferred;
- `model-sweep`, `evaluation-predictions`, `true-label-replay`: automatic prohibited; manual prohibited/deferred;
- evaluation capsules, training checkpoints, run models, current scientific/persistence evidence: prohibited unless a separate current owner explicitly says otherwise;
- cold archive/content-store historical state: no current mutation eligibility; read-only inspection can remain descriptive.

The report may use neutral values such as `prohibited`, `deferred_to_storage_reset`, or `cache_candidate_owner_guard_required`. Exact strings are delegated, but they must be semantically unambiguous and tested.

### 7.3 Report is not deletion authority

Add/retain a clear code-level invariant that `StorageFamilyRecord` classification is advisory accounting only. Current cleanup candidate selection must not consume a report eligibility string as authorization. Physical deletion still requires the real cleanup owner plus containment/retention/liveness checks.

If changing the report's public fields/value vocabulary materially breaks a supported external consumer, preserve the schema shape where practical but change the values to truthful current semantics. A schema-version bump is required only if the serialized structure itself changes incompatibly.

## 8. R10-E — remove dead consequential CLI machinery where it no longer has a current consumer

The current parser exposes only `storage report` and `storage cleanup`. Consequential archive/dedup handlers and imports that are no longer reachable from any supported current command should not remain in `_campaign_cli_core.py` merely to preserve historical implementation history.

Preferred final state:

- remove unused imports for archive create/restore/dedup/prune operations from `_campaign_cli_core.py`;
- remove unreferenced `_stor5_*` current-CLI helpers and `command_archive` / `command_deduplicate` if no supported current consumer remains;
- preserve generic low-level archive verification/hash primitives in their owning storage module for future successor use; do not delete reusable lower-level implementation merely because the current CLI no longer exposes it.

This is a complexity cleanup, not authorization to implement the successor storage reset.

If a hidden internal test imports one of these private CLI helpers, update the test to the current public contract rather than treating test reachability as a supported API contract.

## 9. Required focused acceptance — exact structural checks

Add or strengthen narrowly scoped tests so the prior misses cannot recur.

### 9.1 Current configuration/help contract

Assert against the **raw generated text**, not only TOML parsing:

- the `[cleanup]` section names only `safe|cache`;
- no line in the current cleanup guidance advertises `recompute|compact|archive`;
- `campaign.toml.example` matches the same current wording;
- `GUIDE_TEXT` contains `storage report`, `safe`, and `cache` guidance;
- `GUIDE_TEXT` contains explicit successor-storage deferral;
- `GUIDE_TEXT` does not instruct `recompute`, `compact`, archive create/restore, or dedup apply.

Scope negative assertions to current storage guidance so unrelated scientific words such as "recompute" elsewhere do not create false failures.

### 9.2 CLI namespace

Assert:

```text
top-level parser choices do not include cleanup/archive/deduplicate
storage subcommands == {report, cleanup}
cleanup tier choices == {safe, cache}
```

and through the real CLI entrypoint:

- `cleanup --tier safe` is rejected by argparse;
- `storage cleanup --tier safe` succeeds on a bounded workspace;
- `_normalize_legacy_storage_argv` is absent from the current module.

### 9.3 Safe/cache behavioral split

Use real `storage cleanup` dispatch:

1. create an inactive-run `checkpoint-model-cache` under a campaign-owned run root;
2. run `storage cleanup --tier safe` -> cache remains;
3. run `storage cleanup --tier cache` -> cache is removed;
4. create `frame-cache`; run both safe and cache -> frame-cache remains;
5. historical-path trap directories remain under both tiers.

The test must not call `_cleanup_remove()` directly for the success claim.

### 9.4 Active-run cache retention

Exercise the existing real run-liveness owner rather than monkeypatching cache eligibility.

Preferred bounded test:

1. start a real current training/production run through the existing campaign owner with a deterministic trainer seam that blocks after the run is registered/current;
2. create or observe that run's `checkpoint-model-cache` under its real run root;
3. while the run remains live, invoke `storage cleanup --tier cache` through the public CLI from another thread/process;
4. assert the active run's cache remains;
5. release/finish the run;
6. once the run is no longer active, a later `cache` cleanup may remove that reconstructible cache if it otherwise satisfies current ownership rules.

A test that directly passes a fabricated `active_run_ids` set to a helper is useful as a unit check but cannot substitute for this real-owner acceptance boundary.

### 9.5 Read-only report semantics

For representative families, assert current output contains no retired STOR policy strings.

Required representatives:

- `evaluation-graphs` retained/deferred, not automatic-safe;
- `frame-cache` retained/deferred in P6;
- inactive `checkpoint-model-cache` is at most an owner-guarded manual cache candidate, not automatic-safe;
- content-store/cold-archive rows do not advertise current STOR5 mutation;
- report remains read-only and performs no deletion.

## 10. Documentation reconciliation

Update current durable documentation only where it is stale:

- `docs/specs/training_data/mlff_storage_management_spec.md` must state that P6 retains `frame-cache` and that `cache` eviction is limited to current-owner-proven candidates such as inactive-run checkpoint-model caches;
- `docs/guides/mlff_campaign_cli_user_guide.md` must match the same behavior;
- any architecture/manual line that says frame-cache is currently evictable or old STOR eligibility is current must be corrected;
- historical STOR documents stay historical and need not be rewritten.

Regenerate tracked PDFs from their canonical Markdown sources through the repository's established documentation build chain. Do not patch generated PDFs directly.

## 11. Implementation stage and closure

Revision 10 is one coherent material stage: **R10-1 final transitional-storage/public-surface closure**.

Implementation order:

```text
1. current public text/config/alias cleanup
2. safe-vs-cache execution split
3. frame-cache conservative retention
4. storage-report classification reconciliation
5. focused structural + real-owner storage tests
6. affected docs/PDF regeneration
7. final assembled P6 acceptance
```

Before final acceptance, stage-local closure requires:

- source/conformance review proving the current storage contract is singular and current;
- focused tests in sections 9.1-9.5;
- affected storage accounting/reclamation/CLI/configuration regression;
- P3/P5 retention, containment, external-input and symlink regression;
- documentation source-chain regeneration/checks.

## 12. Final assembled P6 revision-10 acceptance

After the R10 executable edits are assembled, run fresh final acceptance on the same candidate.

Required final evidence:

1. all revision-8 DATA5/P1-P4 ownership tests remain green;
2. all revision-9 two-seed final-production interruption/resume/integrity/process-boundary cases remain green;
3. current generated configuration and `campaign.toml.example` expose only safe/cache storage policy;
4. parser/help, `GUIDE_TEXT`, Markdown guide, storage spec, and architecture wording agree on the same transitional surface;
5. hidden top-level `cleanup` alias is absent and top-level invocation fails parsing;
6. safe cleanup retains acceleration caches;
7. cache cleanup removes an owner-proven inactive-run checkpoint-model cache but retains an active-run cache;
8. both safe and cache retain frame-cache in P6;
9. historical-path traps remain retained;
10. current storage-report output contains no retired STOR/recompute/compact/protocol-freeze mutation eligibility;
11. external inputs, containment and symlink protections remain green;
12. P3 publication-window and P5 plan-only/proper-subset retention tests remain green;
13. independent A/B/C compatibility qualification reports PASS separately;
14. real parser/dispatch lifecycle remains functional through `prepare -> select-target-size -> cross-validate -> train-production` with close/reopen/currentness;
15. directly affected docs/PDFs regenerate successfully;
16. complete affected-surface CPU-safe regression passes; because `_campaign_cli_core.py` and storage accounting are central public surfaces, use the broader/full CPU-safe suite unless a complete smaller bound is independently demonstrated.

No GPU or long real-data qualification is required for this P6 closure.

## 13. Anti-shortcuts

The following do not satisfy revision 10:

- changing only the Markdown guide while leaving `GUIDE_TEXT` or generated config stale;
- hiding an alias from help while `_normalize_legacy_storage_argv()` still routes it;
- making `safe` and `cache` both delete checkpoint-model-cache;
- deleting frame-cache merely because its pathname contains `cache`;
- using `prepare complete`, elapsed time, or a retired stage marker as proof that frame-cache is unused;
- adding a new lease/registry solely to permit frame-cache eviction in P6;
- changing storage-report labels while cleanup still consumes pathname/history as authority;
- keeping STOR-era report eligibility strings because the report is read-only;
- mocking `_active_training_run_ids()` in the only active-run acceptance test;
- deleting/weakening the already-green two-seed P5 tests to reduce final-suite cost;
- implementing archive/dedup/admission redesign from the successor storage package.

## 14. Frozen / delegated / reopen-only authority

### Frozen

- P6 remains implementation cleanup/cutover, not P7 and not the successor storage reset.
- Revision-9 P5 multi-seed behavior is accepted and preserved.
- Current storage public mutation is `safe|cache` only.
- Safe does not evict acceleration caches.
- Frame-cache is retained by both safe and cache for P6.
- Inactive-run checkpoint-model-cache may be a cache-tier candidate only through current owner/liveness checks.
- Active-run cache state fails toward retention.
- Current storage report is advisory and cannot grant deletion authority.
- Unsupported top-level cleanup alias is removed absent real compatibility evidence.
- Ambiguous/historical P3/P5/storage state fails toward retention.
- GPU/long-production qualification remains deferred.

### Delegated

- exact neutral storage-report eligibility strings;
- exact helper factoring used to share run-root/liveness discovery between safe/cache paths;
- exact deterministic blocking trainer fixture for active-run cleanup acceptance;
- whether unused private archive/dedup CLI helpers are deleted in one edit or alongside import cleanup, provided no current route remains;
- exact documentation prose and generated-PDF mechanics under the repository's canonical build chain.

### Reopen Design only on evidence

Reopen only the affected surface if evidence proves one of these conditions:

1. a genuine supported external compatibility contract requires top-level `cleanup` routing;
2. `checkpoint-model-cache` is not in fact independently reconstructible from retained current artifacts for inactive runs;
3. current frame-cache consumers cannot safely tolerate conservative retention and a material storage/resource requirement forces P6 eviction before the successor reset;
4. separating safe from cache breaks an accepted current restart/compatibility guarantee that cannot be repaired locally;
5. exact P5A6 compatibility is broken by these storage/public-surface changes despite no scientific-state mutation.

If none fires, do not reopen Design. Implement this contract directly.

## 15. Revision-10 PASS definition

P6 revision 10 is eligible for independent PASS only when:

```text
all accepted revision-9 scientific/P5 behavior preserved
+ one truthful current storage/config/help/documentation contract
+ no hidden top-level cleanup alias
+ safe has zero acceleration-cache eviction
+ cache uses current owner/liveness authorization
+ frame-cache retained in P6
+ inactive checkpoint-model cache removable only by cache
+ active-run cache retained
+ current report contains no retired STOR mutation policy
+ P3/P5 fail-toward-retention preserved
+ A/B/C compatibility PASS
+ stage-local and final affected regression/integration closure
```

Only an independently reviewed **P6 revision-10 PASS** opens P7.