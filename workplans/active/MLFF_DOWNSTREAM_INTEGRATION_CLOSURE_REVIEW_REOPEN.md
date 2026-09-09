---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
protocol_version: 5.16.0
status: reopened
created_date: 2026-09-08
reviewed_candidate_head: 8c0e2426ce6f9248bf6b958d48570c140bcef147
reviewed_implementation_commit: cbfd43cabfbd5e26095a564b6bb4a9c9f3787638
reviewed_generated_docs_commit: 8c0e2426ce6f9248bf6b958d48570c140bcef147
implementation_review_verdict: no-pass
precedence: This amendment reopens the parent workplan for the bounded repairs and acceptance closure below. Every non-conflicting product invariant, Frozen architecture decision, preservation requirement, non-goal, acceptance obligation, and redesign trigger in MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md remains binding.
---

# MLFF downstream integration closure — implementation review reopen 1

## 0. Review verdict

**NO-PASS / REOPENED.**

The implementation materially improves the downstream architecture and correctly closes most of the original path/identity/orchestration findings. No Frozen MLFF scientific or high-level architecture decision needs to change. The remaining code blocker is a Tier-2 recovery-owner overreach: the new P5 scratch-reclamation helper treats every materialization with no terminal/checkpoint evidence as disposable, so malformed/corrupt immutable materialization is silently deleted instead of failing closed. The current recovery regression then rewards exactly that behavior by constructing checksum-inconsistent state and calling it a faithful pre-repair materialization.

This is an implementation repair, not a redesign. Repair the existing recovery/materialization owner in place. Do not add a migration database, compatibility registry, second materialization pointer, restart state machine, cleanup daemon, or new lock/lease mechanism.

The review also found incomplete acceptance evidence: the explicit absolute/tilde/config-relative P5 execution matrix is only fully executed for the config-relative form, the structural absence oracle does not model all materially relevant raw-path call shapes, and the reviewed implementation commit has only a successful documentation check recorded on GitHub; no final required pytest/static/integration evidence is available for the candidate.

## 1. Accepted implementation surfaces — preserve, do not rework without new evidence

The following parent findings are source-conformant in the reviewed candidate and should be preserved through the repair:

1. **O1/O2 path authority:** `_common.resolve_configured_path()` is now the shared campaign path semantic; `_campaign_cli_core` consumes it and P5 receives `paths.config_dir` for configured foundation resolution.
2. **O3 locator/identity separation:** immutable P5 MACE configuration no longer stores `foundation_model`; it stores the foundation head/scientific configuration while the current locator arrives through the authenticated run request. `MacePostSelectionTrainer` re-hashes the current file against canonical foundation identity before producing the transient dependency-facing executable configuration.
3. **Checkpoint/provider reconstruction:** P5/P7 provider reconstruction receives the authenticated current foundation locator explicitly rather than reading a stale immutable pathname.
4. **O5 replay cleanup:** consumerless `PostSelectionMethodPolicies.replay_context` is removed, single-source policy parsing is config-directory-aware, and replay baseline cache identity now requires canonical foundation content identity rather than falling back to a path digest.
5. **O6 multi-size CV:** methodological rejections are accumulated and later frozen sizes continue to a valid per-size CV verdict before campaign rejection is reduced. Hard execution/corruption/authority failures remain fail-fast.
6. **O7 P7 path semantics:** explicit qualification reference root uses the shared configured-path resolver and preserves the existing multi-size qualification boundary.
7. **O8 documentation:** the authoritative 40/50/80 chapters now state frozen `H_prod_i`, P5 publication ownership/P7 consumer ownership, and ordinary-nonlocked-versus-locked `advance` routing consistently; the assembled manual/PDF was regenerated through the documentation workflow.
8. **O9 replay lineage:** the earlier single-source `source`/`split` lineage rewire remains present and fail-closed.

The repair below must not reopen these surfaces merely because they are nearby.

## 2. Blocking implementation defect R1 — destructive recovery accepts corruption as stale scratch

### 2.1 Evidence

`campaign_post_selection_runtime._reclaim_unaccepted_materialization(run_root, material_directory)` currently behaves conceptually as:

```text
if materialization absent: return
if selected terminal files exist: preserve
if checkpoint directory contains anything: preserve
otherwise: shutil.rmtree(material_directory)
```

It does not authenticate `materialization.json`, the immutable MACE configuration SHA/digest, run/binding/method ownership, or the reason the existing representation differs from the current one before deletion.

That violates parent O4, which explicitly requires:

```text
corrupt state remains a typed failure, not silently discarded as "stale"
```

The broad deletion is not necessary to satisfy the product requirement. The actual compatibility need is narrower: an **internally valid, unaccepted pre-fix materialization whose only relevant representation drift is the retired foundation pathname** must not permanently block retry after the locator is removed from the immutable config.

### 2.2 The current recovery test is not a faithful pre-fix counterfactual

`tests/test_mlff_downstream_integration_closure.py::test_pre_repair_materialization_recovers_in_the_same_workspace` first publishes a current materialization, then edits only `post_selection_mace_config.yaml` to insert the old `foundation_model` key. It does **not** update the already-published `materialization.json` fields that authenticate that config's SHA256/content digest.

The historical pre-fix materializer published the old configuration and the corresponding `PostSelectionMaterialization` record together, so a real pre-fix workspace is internally self-consistent. The current test instead creates checksum/digest-inconsistent corruption, then passes only because `_reclaim_unaccepted_materialization()` deletes the evidence before any owner authenticates it.

This test therefore cannot establish parent acceptance 8.3 and currently enforces behavior that O4 forbids.

### 2.3 Required end state

Keep reclamation inside the existing `post_selection_run_activity_lease(run_root)` ownership boundary. Before destructive reconciliation, classify the existing materialization through the existing P5 materialization/config authorities sufficiently to distinguish these cases:

1. **Accepted or restart-authenticatable progress exists** — preserve and authenticate/reuse through existing owners. Never delete to force a fresh representation.
2. **Another live writer owns the run root** — existing activity lease prevents destructive interference; do not add another liveness mechanism.
3. **Existing unaccepted materialization is malformed, checksum/digest-inconsistent, foreign to the logical run, or differs for a reason other than the retired locator representation** — raise the repository's existing typed P5/input/serialization failure and leave the evidence intact for diagnosis. Do not silently turn corruption into absence.
4. **Existing unaccepted materialization is internally authentic for this logical run and is equivalent to the corrected representation except for the retired foundation-locator field/representation** — it may be reclaimed/rebuilt or locally reconciled under the existing owner so the same workspace proceeds without operator deletion.
5. **No materialization exists** — ordinary current materialization proceeds unchanged.

The exact comparison/factoring remains delegated. Prefer a direct bounded comparison using the existing `PostSelectionMaterialization` schema and immutable config digest/contents. Do not create a durable migration format or generalized compatibility chain. If the cleanest realization can reuse already-correct target/monitor artifacts rather than deleting the entire directory, that is permitted, but no new cache/pointer authority is required.

### 2.4 Required recovery tests

Replace/repair the current counterfactual so all of these are exercised through the real P5 run owner with expensive MACE arithmetic bounded below it:

- **faithful pre-fix materialization:** construct an internally self-consistent old configuration **and matching materialization record** with the retired locator field; no accepted/checkpoint progress; corrected retry succeeds in the same workspace without harness deletion;
- **corrupt config bytes:** mutate the immutable config without updating its record; corrected retry fails typed and does not delete/rewrite the corrupt evidence;
- **foreign internally valid materialization:** create internally consistent state whose method/run/head/membership or another protected semantic differs beyond the retired locator-only representation; retry fails typed and preserves it;
- **current unaccepted materialization:** current internally valid scratch remains idempotent/reusable or safely reconstructible under the normal owner;
- **accepted/restartable progress:** retain the existing terminal/checkpoint preservation cases;
- **live-writer exclusion:** reuse existing run-activity-lease evidence if it already exercises the exact destructive boundary; otherwise add one bounded concurrency case at the production owner. Do not add a second lock.

A regression that simply calls `_reclaim_unaccepted_materialization()` on arbitrary directories is not enough for the corruption/legacy claims; the real materialization/retry owner must execute.

## 3. Blocking acceptance gap R2 — complete the P5 path-form execution matrix

Parent O1/8.1 requires absolute, tilde, and config-relative spellings to agree through `doctor`, P5 identity/context, **P5 trainer request, and dependency-facing launch** from a foreign CWD.

The new test `test_configured_foundation_path_forms_agree_across_owners_from_any_cwd` checks all three spellings through the path helper, policies, and method identity. The real P5 execution/relocation test exercises only the config-relative spelling.

Do not add a new path harness. Parameterize/reuse the existing real-owner foundation-backed campaign test so all three spellings reach the trainer/dependency projection and assert the same canonical locator. Keep expensive numerical work below the accepted trainer/inference seam.

## 4. Acceptance-strength gap R3 — structural absence rule must cover the diagnosed family, not one spelling

The added AST fallback is useful but its raw-CWD detector is narrower than the defect family: it recognizes direct forms such as `Path(f_model_raw).resolve()` but can miss equivalent wrappers such as `Path(str(raw)).resolve()`, subscript/attribute-fed raw values, or renamed variables. A structural oracle that would stay green after a trivial spelling change is not strong evidence for the plan's "no second raw configured-path interpreter" claim.

If Semgrep is available in the implementation environment, use a focused rule over the affected P5/P7 configuration owners. Otherwise strengthen the AST/source fallback to model representative direct and wrapped `Path(...)` raw-config forms and validate it against known-positive examples for both the former P5 and former P7 patterns plus known-negative canonical-resolver usage.

Do not introduce a repository-wide linter or path registry. This is a bounded acceptance check for the affected owner family.

## 5. Blocking functional-evidence gap R4 — required regression/integration has not been established for the reviewed candidate

For implementation commit `cbfd43cabfbd5e26095a564b6bb4a9c9f3787638`, the available GitHub check record contains only the successful `docs` job. No required pytest/static/integration check is recorded. The generated-docs child commit `8c0e2426ce6f9248bf6b958d48570c140bcef147` changes derived documentation only, so executable evidence may be run on the repaired executable parent and then the generated-doc descendant must remain mechanically derived; however the evidence must correspond to the final repaired executable tree.

After R1-R3 are complete, execute and record the parent workplan's minimum suites, including the new downstream closure tests, then the broader affected P5/P7/campaign/storage surface. At minimum include:

```bash
pytest -q \
  tests/test_mlff_downstream_integration_closure.py \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r9_guards.py \
  tests/test_mlff_target_size_p5_r10_guards.py \
  tests/test_mlff_target_size_p5_r11_guards.py \
  tests/test_mlff_mace_executable_config.py \
  tests/test_mlff_mace_execution_semantics.py \
  tests/test_mlff_mace_execution_semantics_assembled.py

pytest -q \
  tests/test_mlff_target_size_multi_selection.py \
  tests/test_mlff_target_size_multi_size_integration.py \
  tests/test_mlff_campaign_assembled_lifecycle.py \
  tests/test_mlff_p7_post_production_qualification.py
```

Then run the final re-derived affected regression, including the relevant storage/run-lease tests if R1 touches their boundary, and the repository's configured fast static/lint/type checks where available. A required slow/real-owner test that did not execute is incomplete acceptance, not a pass.

Long real-data/GPU/CuEq/LAMMPS production qualification remains deferred exactly as in the parent plan.

## 6. Repair sequence

### R1-A — narrow the existing recovery owner

Repair the broad unaccepted-materialization reclamation behavior and its faithful/corrupt/foreign counterfactuals first. Run the focused same-workspace/restart/P5 materialization tests before touching unrelated code.

### R1-B — close path-form and structural acceptance

Parameterize the existing assembled P5 execution test across absolute/tilde/config-relative spellings and strengthen the bounded structural absence oracle. No new production mechanism is expected.

### R1-C — final assembled acceptance

Re-derive the affected surface after R1-A/R1-B, run the parent minimum suites plus broader affected regression/static checks, regenerate documentation only if executable repair changes documented semantics (it should not), and hand off one unchanged executable candidate for independent review.

## 7. Re-review PASS criteria

Software Design may close the parent workplan only when all are true:

```text
[ ] O1/O2/O3/O5/O6/O7/O8/O9 accepted source behavior remains intact
[ ] recovery no longer deletes arbitrary unaccepted materialization solely because terminal/checkpoint evidence is absent
[ ] faithful internally consistent pre-fix locator-only materialization recovers in place
[ ] checksum/digest-corrupt materialization fails typed and is preserved
[ ] internally valid foreign/non-locator semantic mismatch fails typed and is preserved
[ ] accepted/restartable progress remains reusable and live-writer exclusion remains effective
[ ] absolute/tilde/config-relative forms all reach the real P5 trainer/dependency projection from a foreign CWD
[ ] structural absence check can reject representative former P5 and P7 raw-path patterns and accept canonical resolver usage
[ ] baseline single-source replay-lineage behavior remains green
[ ] multi-size CV completeness and production barrier remain green
[ ] P5 publication/currentness and P7 consumer-only qualification remain green
[ ] final affected pytest/static/integration evidence executed on the final repaired executable candidate
[ ] no new migration database, compatibility registry, materialization pointer, state machine, cleanup daemon, or lock layer was introduced
```

No Frozen architecture reconsideration is currently warranted. If implementation evidence shows the only way to distinguish the supported pre-fix workspace is a durable migration mechanism, stop and return to Software Design under parent redesign trigger 3 rather than adding one silently.
