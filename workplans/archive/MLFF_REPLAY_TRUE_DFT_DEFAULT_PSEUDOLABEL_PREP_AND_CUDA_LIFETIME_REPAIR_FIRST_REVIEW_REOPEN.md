---
kind: implementation-workplan-review-reopen
workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-REPLAY-TRUE-DFT-DEFAULT-PSEUDOLABEL-PREP-CUDA-LIFETIME
protocol_version: 6.2
status: active-reopened
review_verdict: no-pass
implementation_branch: fix/mlff-p5-train2-cuda-lifetime-zero-safe-admission
semantic_candidate: 2385d6ae985a7e848a6ea40e463b9830f2dfae90
assembled_candidate: 98246216cb6c32374c71b4c1d653e8f8dd6c5d28
highest_affected_domain: D3 replay stage ownership/currentness/concurrency/resource architecture -> D4 implementation and evidence
serious_challenge: none
precedence: This review supersedes only the implementation-readiness disposition of the parent workplan. Every non-conflicting parent requirement R1-R28, final acceptance criterion 1-36, related TRAIN2 invariant, and frozen D1/D2 scientific meaning remains binding. The work is reopened only for the blockers and evidence closure specified here.
---

# Replay TRUE_DFT default / pseudolabel PREP / CUDA lifetime repair - first implementation Review reopen

## 0. Review disposition

Candidate `2385d6ae985a7e848a6ea40e463b9830f2dfae90` plus generated-documentation follow-up `98246216cb6c32374c71b4c1d653e8f8dd6c5d28` is **NO-PASS / REOPENED** under SSDP 6.2.

The implementation closes substantial parts of the parent design: omitted single-source replay resolves to `true_dft`; conflicting/unsupported selector spellings fail; doctor no longer constructs single-source replay science; public `prepare` owns single-source realization; TRUE_DFT preparation performs zero foundation inference; explicit pseudo preparation uses a same-key publication fence and one cold-build executor; prediction inputs are label-blind; per-consumed-frame geometry identity is checked; current alias replacement is grouped through `CampaignStore.replace_records_atomically`; post-selection read paths no longer directly reach the replay prediction/split construction owners; and lifecycle target/replay/P5/P7 rows are read inside one SQLite read transaction.

Those closures are not sufficient for PASS. Four executable blockers and one required-evidence blocker remain. They are all within the already-frozen D3/D4 scope; no D1/D2 method redesign is requested.

## 1. Blocker B1 - provider retirement still has post-acquisition escape paths

### Finding

`_cold_build_replay_foundation_prediction_cache()` constructs the internally owned provider before the ASE import and before the executor. It special-cases `ModuleNotFoundError` from the ASE import, then transfers ownership to `StaticMaceInferenceExecutor`. After that transfer it creates/chmods the attempt-local scratch directory **before** entering the `try/finally` whose `finally` calls `executor.close()`.

Therefore the frozen R21 invariant, "one terminal retirement owner on every exit after acquisition", is not yet true. At minimum:

- an ASE import failure/cancellation other than the one special-cased `ModuleNotFoundError` can escape after provider construction without retirement;
- `tempfile.mkdtemp(...)` failure after executor acquisition can escape without closing the executor/provider;
- `os.chmod(work, ...)` failure after executor acquisition can escape without closing the executor/provider.

The existing success, executor-construction-failure, prediction-time `KeyboardInterrupt`, and caller-owned-provider tests do not falsify these gaps.

### Owning-layer repair

Alter the existing cold-build control flow; do **not** add a cleanup wrapper, secondary provider owner, process-exit fallback, or another executor.

1. Establish one cleanup scope immediately after an internally constructed provider is acquired.
2. Keep exactly one ownership transition: provider owner -> executor owner when executor construction succeeds.
3. Put every subsequent operation that can raise - imports needed after acquisition, provider validation, executor construction, scratch creation/chmod, graph-cache use, source iteration, prediction, shard/audit I/O, publication, and catchable cancellation - inside that ownership scope.
4. If transfer never completes, the provider owner retires the provider exactly once. If transfer completes, the executor owner closes exactly once. Caller-supplied providers remain caller-owned.
5. Preserve the single executor for the whole cold build so OOM learning still spans all outer batches.

### Required falsification

Add fault-injection tests that fail **after provider acquisition but before the present build `try`**, including scratch-directory creation/chmod and a catchable import/setup failure. For each path assert exactly one terminal retirement for an internally constructed provider, zero retirement for a caller-supplied provider, no reusable partial cache, and no attempt scratch left behind.

## 2. Blocker B2 - lifecycle currentness fails open when the compact replay lineage is absent or malformed

### Finding

`campaign_owner_snapshot()` correctly reads the compact replay lineage and P5/P7 pointers in one transaction. However `_current_replay_lineage_digest()` maps a missing, malformed, or non-mapping `replay_current_lineage` record to `None`, and `_replay_lineage_stale()` explicitly treats `current_replay_lineage is None` as "do not ask the question" and returns `False`.

The new test `test_stale_replay_lineage_makes_post_selection_evidence_historical()` codifies that behavior. For a campaign whose current configuration requires prepared single-source replay, deletion/corruption of the compact current-lineage alias can therefore leave pre-existing P5 acceptance/final-production pointers observationally COMPLETE and can let that false currentness propagate toward P7. This contradicts parent R26/R28 and final acceptance criterion 31: when compact evidence cannot establish currentness, public observation must block/wait rather than declare historical descendants current.

### Owning-layer repair

Repair the existing lifecycle/currentness projection; do **not** reconstruct replay science, parse the corpus, load a model, or invent a second lifecycle authority.

1. Preserve the single coherent SQLite snapshot.
2. Make the snapshot/projection distinguish these cases using already-owned compact state: (a) no single-source replay is applicable, where no single-source lineage comparison is required; (b) single-source replay is applicable and a valid compact current lineage exists; (c) single-source replay is applicable but its required compact lineage is missing, unreadable, or malformed.
3. Case (c) must fail closed: public `prepare`/P5/P7 observation must report blocked/waiting/not-current and must never treat existing CV/final/qualification evidence as current.
4. Preserve no-replay and legacy-split behavior; they must not be falsely blocked merely because a single-source lineage row is absent.
5. Keep `status`, `advance`, and qualification status read-only and cheap.

### Required falsification

Start from a prepared single-source campaign with accepted P5/final descendant evidence, then delete and separately corrupt `replay_current_lineage`. Prove status/advance no longer report those descendants current and do not route beyond the owning repair stage. Also prove legacy/no-replay campaigns remain observationally unchanged and the whole path performs no corpus parse, provider construction, prediction, materialization, or write.

## 3. Blocker B3 - replay publication and public-prepare completion are not bound to one command-start configuration/currentness generation

### Finding

`_publish_single_source_replay_authority()` captures the database `replay_current_lineage`, performs the long build, rehashes only the replay source **before** `store.writer_exclusion()`, and inside the writer boundary compares only the prior/current database lineage before replacement. It does not commit-time revalidate the canonical replay configuration or the foundation/prediction parent used by the long build.

Separately, `_mark_stage(..., COMPLETE)` computes `_stage_config_digest(paths, name)` from the **live configuration file at completion time**, not from the command-start `cfg` whose target/replay work was actually constructed. A mid-run `campaign.toml` edit can therefore let an old build be marked COMPLETE against a newer configuration digest. A source/checkpoint change in the final pre-commit window likewise is not covered by one coherent compare-and-recheck fence.

This is the exact stale-builder/currentness class frozen by parent R11/R14/R24/R25. The existing test only simulates another prepare changing `replay_current_lineage`; it does not falsify a live config edit, foundation checkpoint replacement, or final source change around publication/completion.

### Owning-layer repair

Rewire the existing `prepare`/publication currentness owners; do **not** add a second campaign-state database, shadow config, background monitor, or long-lived global lock.

1. Capture the canonical command-start prepare/replay semantic identity from the already-loaded `cfg` and the exact source/foundation identities actually consumed.
2. Immediately before current-alias replacement, re-resolve/revalidate the current campaign replay semantics and all long-build parents whose mutation can make the result stale: replay source bytes, effective replay label/split semantics, and for pseudo mode the foundation checkpoint/prediction identity and doctor-frozen acceleration parent.
3. Under the existing short campaign writer/currentness boundary, compare the database current lineage/generation against the build baseline and refuse publication if a newer incompatible authority won. Use the parent workplan's allowed compare-and-recheck form where filesystem hashing cannot safely be held under a database writer lock; do not hold the campaign writer across GPU work.
4. A command that detects any command-start/current mismatch must not publish the stale alias set as current and must not mark public `prepare` COMPLETE for the newer configuration.
5. Bind the COMPLETE stage record to the configuration identity that was actually constructed. Do not recompute a different completion identity from a changed file and label the old build with it.
6. Preserve physical content-addressed caches produced by a losing/stale builder when they independently authenticate; only mutable current aliases/stage currentness are rejected.

### Required falsification

Add deterministic race tests with barriers/failpoints around the final publication boundary for: campaign replay semantic edit, foundation checkpoint replacement at the same locator, replay source change, and competing prepare publication. In every case the stale builder must lose without hybrid aliases or false COMPLETE state. A semantically identical spelling/identical-byte relocation must retain the accepted equivalence behavior.

## 4. Blocker B4 - replay execution-domain integers still use coercive `int(...)` shortcuts

### Finding

The parent workplan explicitly preserved exact-domain validation and prohibited new truthiness/int-cast shortcuts for replay execution controls. The new prepare path passes

- `batch_size=int(_cfg(cfg, "replay", "prediction_batch_size", 32))`
- `shard_size=int(_cfg(cfg, "replay", "prediction_shard_size", 256))`

and `_cold_build_inference_executor()` again applies `max(1, int(batch_size))`. A TOML float such as `1.5` or boolean can therefore be silently coerced to a different execution request instead of rejected by its validation owner. The invalidation planner likewise compares split seeds via `int(old_split_seed)` / `int(new_split_seed)` rather than the exact split-seed normalizer.

The new R2 tests cover exact split seed/ratio domains but do not cover these execution controls, so the implementation and evidence agree on an incomplete subset of R2.

### Owning-layer repair

Use the existing replay exact-integer validation logic as the one domain owner; generalize/reuse it if necessary rather than layering another parser.

1. `prediction_batch_size` and `prediction_shard_size` must be exact positive integers before the expensive prepare path starts; reject booleans, non-integral floats, NaN/Inf, and other coercible values instead of truncating/coercing them.
2. Once validated, downstream cold-build/executor code may assume the exact integer and must not silently clamp it with `max(1, int(...))`.
3. Compare invalidation split seeds through the same exact seed normalization already used by `ReplaySingleSourceConfig`.
4. Keep batch/shard controls execution-only: correcting their validation must not add them to scientific replay identity or stage currentness.

### Required falsification

Add public-preflight/config tests proving malformed batch/shard domains fail before replay source parsing/model construction, plus direct owner tests proving no downstream coercion. Preserve the existing test that changing valid batch/shard values does not stale prepared scientific replay.

## 5. Blocker B5 - required final qualification/evidence is incomplete

### Finding

The branch contains a useful real RTX 3090 / CUDA E1 proof. It drives `build_replay_foundation_prediction_cache(..., provider=None)` through two disjoint cold builds in a live process and records non-accumulating post-close residency. Accept and preserve that evidence, subject to rerun only if B1 changes the relevant lifetime implementation materially.

However the parent workplan's final criterion 35 requires **both** target-host cases:

- E1: provider retirement while the process remains alive;
- E2: assembled `doctor -> prepare -> P5` route proving expensive pseudo construction is prepare-owned and pre-TRAIN2 CUDA ownership is clean.

`qualification/replay-provider-lifetime/` contains E1 evidence/readme/script only; no E2 artifact is present. The branch's GitHub Actions realization for the semantic candidate is documentation-PDF generation only, not the required focused/affected/final Python regression. Under SSDP 6.2 an explicitly required real-owner check that is unexecuted or unavailable remains blocking rather than being deferred by Review.

### Required evidence after B1-B4 repair

1. Rerun the focused replay ownership/currentness/concurrency/lifecycle tests on the repaired semantic candidate.
2. Run the complete affected regression surface required by the parent workplan, including existing replay unification/invalidation/P5 integration and target-size/P5 lifecycle guards.
3. Run repository-required static/build/package checks applicable to the changed files.
4. Reconcile materially affected evidence from `MLFF_P5_TRAIN2_CUDA_LIFETIME_AND_ZERO_SAFE_ADMISSION_*`; do not inherit stale passes after executable changes.
5. Run target-host E1 if B1 materially changes the provider-retirement path and record process-local plus device-level before/peak/after evidence while the process remains alive.
6. Run target-host E2 through the **assembled public CLI route** with explicit `foundation_pseudolabel`: doctor must perform no replay-wide prediction, prepare must be the only expensive pseudo realization owner and retire it before return, P5 must consume prepared authority read-only, and the pre-TRAIN2 scheduler observation must show no prepare-owned model-scale CUDA residency. Record cache disposition and the resulting P5 routing/currentness identities.
7. Every required unavailable/unexecuted check remains explicitly blocking; do not convert absence of evidence into PASS.

## 6. Preserved invariants and non-repair scope

The repair must preserve, not redesign:

- omitted single-source label mode -> `TRUE_DFT`; pseudo labels remain explicit opt-in;
- exact source TRUE_DFT training in true mode and independent TRUE_DFT monitor in pseudo mode;
- no weakening of TRAIN2 zero-safe admission, scheduler memory envelope, or occupancy observation;
- doctor validation-only ownership; no replay-wide inference, prediction-dependent qualification, scientific split, materialization, or prepared alias publication there;
- public `prepare` as the only owner of single-source scientific replay construction;
- TRUE_DFT prepare with zero foundation inference and no pseudo fallback;
- same-key cold prediction build single-flight through the existing narrow publication fence, never the campaign writer across GPU work;
- one cold-build executor/OOM-learning lifetime and device-correct CUDA cleanup;
- prediction input label blindness;
- per-consumed-frame geometry binding plus end-of-operation source authentication;
- pseudo label-only source mutation preserves geometry-bound foundation predictions when their parent identities still authenticate, while mandatory TRUE_DFT monitor lineage refreshes;
- exact atomic current-alias replacement and retirement of inapplicable aliases without deleting historical/content-addressed artifacts;
- P5/P7 scientific consumers are read-only with respect to replay prediction, qualification, and split science; only reconstructible transport may rematerialize;
- target-size scientific generation independence from replay-only semantics;
- one coherent lifecycle SQLite read snapshot; status/advance remain cheap, read-only observation;
- no gratuitous replay schema, invalidation-version, or post-selection method-version bump;
- no new wrapper, fallback, shadow authority, compatibility layer, global cache, or compensating machinery where control-flow correction/removal/reuse of the existing owner is sufficient.

## 7. Final PASS criteria for this reopen

PASS requires all of the following on one final semantic candidate:

1. B1-B4 are repaired at their existing owning layers with the reduction/rewiring constraints above.
2. The parent R1-R28 and final criteria 1-36 remain satisfied without D1/D2 scientific drift.
3. Lifecycle fails closed when required single-source compact currentness evidence is absent/corrupt and remains cheap/read-only.
4. Stale builders/config/source/checkpoint races cannot publish current aliases or a false COMPLETE prepare state.
5. Provider retirement is exactly once on every catchable exit after acquisition; caller-owned provider semantics and single-executor OOM learning remain intact.
6. Exact replay execution domains reject coercible invalid values without adding execution knobs to scientific identity.
7. Focused, affected, and final regression plus applicable repository checks pass on the final candidate.
8. Required target-host E1/E2 evidence is complete and applicable; E2 demonstrates clean ownership at the assembled doctor -> prepare -> P5 -> pre-TRAIN2 boundary.
9. Related TRAIN2 evidence is reconciled after the final executable delta.

Until all nine hold, the parent work remains **NO-PASS / ACTIVE-REOPENED**. No Serious Challenge is active.