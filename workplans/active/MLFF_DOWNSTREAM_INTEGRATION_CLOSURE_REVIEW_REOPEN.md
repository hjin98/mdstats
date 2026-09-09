---
kind: implementation-workplan-review-amendment
workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE-REVIEW-REOPEN-1
parent_workplan_id: CODE-MLFF-DOWNSTREAM-INTEGRATION-CLOSURE
protocol_version: 5.16.0
status: reopened
created_date: 2026-09-08
last_design_closure_review_date: 2026-09-09
reviewed_candidate_head: 12ad13413e7d4a346c80b576be57633914219d97
reviewed_candidate_tree: 4d4209da4d37237493faa8daba4aa3b4fbae54a1
reviewed_implementation_commit: 12ad13413e7d4a346c80b576be57633914219d97
reviewed_generated_docs_commit: 8c0e2426ce6f9248bf6b958d48570c140bcef147
implementation_review_verdict: no-pass
precedence: This file is the current binding implementation-review amendment to MLFF_DOWNSTREAM_INTEGRATION_CLOSURE_WORKPLAN.md. It supersedes its own earlier wording in place. Every non-conflicting product invariant, Frozen architecture decision, preservation requirement, non-goal, acceptance obligation, and redesign trigger in the parent workplan remains binding.
---

# MLFF downstream integration closure — SDP implementation review reopen

## 0. Verdict

**NO-PASS / REOPENED.**

Software Design reviewed executable candidate `12ad13413e7d4a346c80b576be57633914219d97` against the parent workplan plus the current Protocol 5.16.0 handoff and independently challenged the affected P5/P7/replay/recovery surfaces.

The implementation closes most of the prior findings correctly. In particular, the previous broad delete-by-absence recovery path is gone, continuation is now passed through the existing TRAIN2 validator, corrupt materialization is generally preserved as typed failure, the faithful pre-fix foundation-locator counterfactual now authenticates its matching materialization record, `[paths].replay_set` uses the canonical configured-path owner, the foundation path-form test now covers all three spellings through the real upstream P5 request owner, and the structural fallback is materially stronger.

The candidate is nevertheless not safe to accept. The new recovery realization introduced a split between **TRAIN2 continuation authentication** and **materialization/execution-authority authentication**. A durable continuation can currently be accepted before the materialization it belongs to is authenticated, and a full-horizon continuation can then bypass `MacePostSelectionTrainer` entirely. Because `Train2RuntimePlan` does not identify the exact P5 run/materialization, this can attach foreign durable training state to a different current materialization and let it reach EVAL2. That violates the core downstream invariant that each fold/size/final run owns its exact training membership and descendants, and it weakens restart/currentness from exact reauthentication into partial authority matching.

There are also two acceptance blockers: the new three-form foundation test still substitutes the entire `PostSelectionTrainer`, so it does not establish the required dependency-facing MACE projection, and the reviewed commit has no available final pytest/static/integration check evidence.

No Frozen scientific or high-level architecture decision needs reconsideration. Repair the existing owner boundary by **reducing the split recovery logic**, not by adding another recovery record, compatibility layer, state machine, pointer, registry, or wrapper.

---

## 1. Governing product/Frozen invariants

The parent workplan remains authoritative. The repair below specifically protects these already-binding invariants:

1. **Exact run ancestry.** Every P5 CV fold and final-production run executes from its own exact authorized target membership, preparation, method, replay lineage, optimizer seed, budget, and materialization. A checkpoint/continuation from a sibling run may not become evidence for another run merely because coarse runtime-plan fields happen to agree.
2. **Fail-closed restart/currentness.** Durable continuation is reusable only after the product can reauthenticate the execution state it actually descended from. File presence, internal TRAIN2 self-consistency, or an equal method/runtime-plan digest alone is not enough.
3. **One materialization/execution authority.** Recovery may inspect existing state, but it must not create a second synchronized definition of what exact DATA8/configuration a run means.
4. **Foundation locator separation.** Foundation path remains runtime locator only; checkpoint content/head/family own scientific identity and byte-identical relocation remains supported.
5. **Canonical configured paths.** Affected user-configured paths remain `expanduser -> config-directory-relative -> canonical resolve`, independent of invocation CWD.
6. **Replay semantics.** Replay method/lineage identity remains path-free; single-source replay source relocation with identical governed content remains semantically equivalent; generated `pt_train_file` / `pt_valid_file` relocation is not a new product requirement.
7. **Multi-size completeness and publication ownership.** Every frozen size receives its valid CV verdict unless a hard failure prevents one; final production remains collection-wide gated; P5 owns publication/currentness and P7 remains a consumer.
8. **Bounded qualification policy.** Full long-running GPU/CuEq/LAMMPS qualification remains deferred; bounded CPU-safe real-owner regression/integration is required now.

---

## 2. Accepted implementation surfaces — preserve

The following implementation results are source-conformant and should not be reopened without new evidence:

- `_common.resolve_configured_path()` remains the canonical affected configured-path semantic.
- `single_source_replay_config_from_campaign(..., base_directory=...)` now fails closed for an unanchored relative replay source and otherwise reuses the shared resolver.
- P5 method-policy resolution supplies the campaign configuration directory to replay-source resolution.
- immutable P5 MACE configuration remains free of `foundation_model`; the current foundation locator reaches the trainer request separately and is authenticated by SHA/head before transient projection.
- replay source/split lineage remains path-free and the earlier runtime `source` / `split` adapter repair remains intact.
- path-derived replay-foundation baseline identity fallback remains removed.
- multi-size CV still accumulates methodological rejections rather than stopping at the first rejected size.
- P7 explicit reference-root canonicalization remains intact.
- current architecture documentation already reflects P5 publication ownership, frozen per-size production horizons, and ordinary-nonlocked versus locked qualification routing.
- the revised recovery path now parses and authenticates the final materialization record/config/artifacts before classifying ordinary corrupt completed state, rather than blindly deleting any unaccepted tree.
- partial/corrupt checkpoint state is routed through the real TRAIN2 continuation validator instead of `any(checkpoint_dir.iterdir())` resumability.
- the faithful pre-fix recovery test now updates both old config bytes and the matching immutable materialization record rather than manufacturing checksum-inconsistent corruption.
- the bounded AST/source fallback now has known-positive/known-negative checks for raw configured-path resolution, checkpoint-presence resumability, path-derived identity, and delete-before-authenticate ordering. Generated replay execution-view fields remain deliberately outside that forbidden family.

These accepted results remain subject to final executable evidence in Section 5.

---

## 3. BLOCKER R1 — continuation and materialization are authenticated as separate authorities

### 3.1 Current failure mechanism

The repaired execution path currently performs, conceptually:

```text
resolve current method/replay/optimizer
build current Train2RuntimePlan
authenticate checkpoint directory against Train2RuntimePlan
classify/authenticate materialization separately
possibly rebuild materialization
if continuation already reached the full epoch horizon:
    skip trainer and use the continuation summary directly
else:
    call trainer
then evaluate checkpoint candidates through EVAL2
```

This ordering is unsafe because `Train2RuntimePlan` is intentionally a **runtime policy/budget plan**, not exact run/materialization identity. It contains method protocol digest, optimizer policy digest, budget/LR policies, structures-per-epoch, replay-monitor identity, heads, and execution limit; it does not contain `run_plan_digest`, `run_identity`, materialization digest, target frame UID set, or immutable MACE-config digest.

The real MACE execution owner already carries the missing exact execution facts. `MacePostSelectionTrainer` builds `MACE_EXECUTION_AUTHORITY` with `config_digest=request.materialization.mace_config_digest` and target/replay UID-set evidence; resolved MACE evidence persists `authority_config_digest` and those UID-set identities into the TRAIN2 summary/companion. The normal `_Train2Runtime._restore_continuation()` path compares persisted `mace_execution_evidence` with the current launch evidence before applying restart state.

The new pre-recovery `_authenticate_post_selection_continuation()` validates the continuation internally against the current `Train2RuntimePlan`, but it does not reconcile the persisted MACE execution evidence with the current materialization before declaring the continuation resumable. The full-horizon optimization then bypasses `MacePostSelectionTrainer`, so the normal execution-authority comparison never runs.

### 3.2 Two concrete unsafe states

#### A. Durable continuation plus absent/incomplete materialization

The current classifier permits a missing materialization or a materialization lacking `materialization.json` to be rebuilt even when a valid continuation has already authenticated.

That contradicts the prior binding recovery contract: run-owned incomplete publication is disposable only when **no accepted/restart-authenticatable progress exists**. The normal lifecycle publishes materialization before TRAIN2 can persist an epoch, so a durable valid continuation whose materialization authority is absent/incomplete is an integrity break, not ordinary pre-training scratch.

Required outcome: **typed fail closed and preserve the continuation; do not reconstruct/delete materialization beneath durable continuation.**

#### B. Foreign continuation whose coarse runtime plan matches the current run

Two CV folds (or another pair of P5 runs) can have the same method, optimizer seed, epoch budget, LR policy, replay monitor, head namespace, and structures-per-epoch while having different target memberships/materializations. Their `Train2RuntimePlan` may therefore be identical.

A complete checkpoint directory copied from run A into run B can pass the new continuation precheck. If run B has its own valid current materialization, materialization classification also passes independently. When the copied summary is already at the full horizon, the fast path skips `MacePostSelectionTrainer` and reaches EVAL2. Provider reconstruction checks checkpoint/config architecture and state, but it does not reconstruct the missing causal fact that this model was trained from run A's target materialization.

That is a scientific/currentness blocker: a sibling fold can effectively lend trained state to another fold without the exact run ancestry being authenticated.

### 3.3 Required end state

Treat **materialization + continuation as one coupled recovery decision**, while keeping their existing canonical record owners.

Required behavior:

1. **No durable continuation**
   - no materialization -> ordinary current materialization;
   - owner-proven incomplete run-owned materialization -> safe rebuild permitted;
   - current valid materialization -> idempotent reuse;
   - faithful pre-fix foundation-locator-only materialization -> bounded same-workspace reconciliation permitted;
   - corrupt/foreign completed materialization -> typed failure, preserve.
2. **Durable continuation exists**
   - materialization must also be present as a completed internally authentic record;
   - it must belong to the exact current run plan/run identity/preparation/artifacts;
   - the continuation's persisted execution authority must be compatible with that materialization before any resume, trainer skip, or EVAL2 use;
   - absent/incomplete materialization with durable continuation -> typed failure, preserve both sides; no rebuild;
   - foreign/corrupt continuation -> typed failure, preserve;
   - current valid materialization + matching continuation -> resume/reclose normally;
   - faithful pre-fix locator-only materialization + matching continuation, if retained as supported recovery, must satisfy the same exact execution-authority binding without deleting accepted progress.
3. **Full-horizon continuation** may skip an actual zero-epoch training workload only after an equivalent existing execution-authority check proves it belongs to the current materialization. The optimization is Tier 2; it may be removed if routing through the existing trainer/continuation owner is simpler and correct.

Use existing evidence. In particular, prefer the already-persisted MACE execution evidence (`authority_config_digest`, target/replay UID-set identities, and current execution semantics) and existing materialization/artifact authorities rather than adding a new restart/materialization digest or another persistence record.

### 3.4 Active-simplicity requirement

The current repair added a substantial recovery subsystem to `campaign_post_selection_runtime.py`: an explicit materialization filename allowlist, materialization-tree ownership inspection, role-artifact validation, expected-config reconstruction through private `_post_selection_mace_config`, and independent continuation classification.

The immediate correctness defect is caused by those two classifications being joined too late. **Do not fix this by adding a third compatibility state/helper/record.** Reduce the split:

- prefer one owner-local compatibility decision at the boundary where both existing materialization and continuation are available;
- reuse or move canonical materialization derivation/validation toward the existing `post_selection_execution` materialization owner if that eliminates duplicated layout/config knowledge from the campaign orchestrator;
- delete/narrow any recovery-only file registry or duplicated validation path that is no longer needed after the joint decision is established;
- keep `campaign_post_selection_runtime` as orchestration rather than a parallel materialization schema owner.

Exact factoring remains delegated. A small direct owner rewire is preferable to a new abstraction if it removes the split cleanly.

### 3.5 Required real-owner counterfactuals

Add/repair bounded tests through `execute_post_selection_run` or the equivalent final real P5 owner. Expensive MACE arithmetic may remain below the accepted seam.

At minimum:

- valid partial continuation + intact current materialization resumes from the exact authenticated epoch;
- valid full-horizon continuation + intact current materialization re-closes/evaluates only after exact materialization/execution-authority compatibility is established;
- valid continuation + absent materialization -> typed failure; checkpoints preserved; no new materialization published;
- valid continuation + materialization directory lacking final `materialization.json` -> typed failure; no destructive rebuild;
- **foreign sibling continuation:** create two real P5 run plans with the same relevant `Train2RuntimePlan` shape but different run/materialization membership, move/copy an authenticated full-horizon continuation from A under B, and prove B rejects it before EVAL2/publication;
- mismatched persisted `authority_config_digest` versus current materialization config digest rejects;
- mismatched target/replay UID-set execution evidence versus current authenticated materialization rejects where those fields are present;
- faithful pre-fix locator-only materialization with no progress still recovers as already required;
- faithful/current materialization with a genuinely matching continuation remains reusable;
- existing corrupt config/final record/partial checkpoint/corrupt continuation/live-writer/external-input-safety cases remain green.

For the foreign-continuation case, prove the bounded inference/EVAL2 seam did not execute after the mismatch is detected.

---

## 4. BLOCKER R2 — foundation path-form acceptance still stops before the dependency-facing owner

The new parameterized test for `absolute`, `~/...`, and config-relative foundation forms is an improvement: it executes the real campaign/P5 request owner and proves every captured `PostSelectionRungRequest.foundation_model_path` is canonical.

However, it passes `fx.PostSelectionHarness` as the complete `PostSelectionTrainer`. That means the test never executes `MacePostSelectionTrainer`, which is the real owner that:

```text
reauthenticates current foundation bytes/head
-> injects foundation_model_path into post_selection_mace_run_configuration(...)
-> writes mace_run_config.yaml
-> launches the dependency-facing wrapper
```

A regression that drops, rewrites, or reuses the wrong foundation locator inside `MacePostSelectionTrainer` could therefore leave the three-form test green. Existing direct trainer guard tests exercise the trainer, but they do not establish this three-form campaign-to-projection relation and do not assert that generated `mace_run_config.yaml["foundation_model"]` equals the current canonical request path.

### Required acceptance repair

Do not create another path harness. Reuse the existing real campaign request fixture and existing real `MacePostSelectionTrainer`/dummy-wrapper technique.

For each foundation spelling:

1. obtain the request from the real campaign/P5 path from a foreign CWD;
2. execute **that request** through real `MacePostSelectionTrainer` (or an equivalent real owner if legitimately refactored);
3. bound subprocess/MACE cost below the trainer with the existing dummy-wrapper/test seam;
4. assert the generated dependency-facing `mace_run_config.yaml` contains `foundation_model == str(canonical_current_locator)`;
5. assert the immutable internal config still contains no `foundation_model`;
6. retain same-bytes relocation and changed-bytes fail-closed evidence.

Do not manually construct a second request in the test to prove this chain.

---

## 5. BLOCKER R3 — final functional evidence is not established for the reviewed candidate

GitHub exposes no check runs for implementation commit `12ad13413e7d4a346c80b576be57633914219d97`, and this review environment cannot clone/run the repository because outbound DNS to GitHub is unavailable. Serena and Semgrep are also unavailable locally, so this review used the SDP-approved bounded source/AST fallback rather than claiming those tools executed.

Source-conformant tests are not execution evidence. A required check that did not execute is not a pass under Protocol 5.16.

After R1-R2 are repaired, run and retain evidence for the exact final executable candidate. At minimum:

```bash
pytest -q \
  tests/test_mlff_downstream_integration_closure.py \
  tests/test_mlff_target_size_p5_r7_guards.py \
  tests/test_mlff_target_size_p5_r8_guards.py \
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

Also execute:

- relevant TRAIN2 continuation/restart tests, including content-authentication and restart-epoch handoff;
- P5 storage/run-activity-lease integration touched by the recovery change;
- current single-source and legacy replay-unification/lineage/path tests;
- P5 final-production/publication/currentness/reclosure tests;
- repository-configured fast Python lint/type/static checks where available;
- final re-derived broader affected P5/P7/campaign/storage/replay regression.

Each material executable repair stage requires focused plus affected stage-local regression before dependent work. Final affected regression/integration must be rerun after the last material executable/test-harness change.

Long real-data/GPU/CuEq/LAMMPS qualification remains deferred.

---

## 6. Repair sequence

### Stage A — collapse recovery into one exact materialization/continuation decision

Fix R1 first. Preserve the accepted corruption/partial-state improvements, but remove the ability to authenticate continuation independently and later attach it to a rebuilt or merely separately valid materialization. Reduce duplicated recovery/materialization authority while doing so.

Run focused recovery/materialization/TRAIN2/run-lease tests, including the sibling-continuation counterfactual, before proceeding.

### Stage B — close the dependency-facing foundation path oracle

Execute the three configured foundation path forms through real `MacePostSelectionTrainer` with expensive execution bounded below it. No new production machinery is expected.

Run the affected P5/MACE/path subset plus Stage A shared-owner regression.

### Stage C — final assembled acceptance

Re-derive the affected surface from the final assembled candidate; run the complete required regression/integration/static surface; regenerate documentation only if authoritative behavior/documentation actually changed; hand off one exact unchanged executable candidate for independent Software Design review.

Do not request another broad closure review before Stages A-C are complete unless a genuine Frozen redesign trigger appears.

---

## 7. Re-review PASS criteria

Software Design may close the parent workplan only when all are true:

```text
[ ] accepted canonical foundation/replay/P7 configured-path behavior remains intact
[ ] accepted foundation locator-vs-identity separation remains intact
[ ] accepted replay source/split lineage and path-free scientific identity remain intact
[ ] accepted multi-size CV completeness and collection-wide production barrier remain intact
[ ] accepted P5 publication/currentness and P7 consumer-only boundary remain intact
[ ] corrupt/foreign completed materialization still fails typed and is preserved
[ ] no durable continuation is reused with absent/incomplete materialization
[ ] no materialization is rebuilt/destructively replaced beneath authenticated durable continuation
[ ] continuation reuse requires exact current run/materialization execution-authority compatibility
[ ] foreign sibling continuation with a coincidentally equal Train2RuntimePlan is rejected before EVAL2/publication
[ ] full-horizon continuation fast path cannot bypass materialization/execution-authority authentication
[ ] current valid continuation resumes/recloses correctly
[ ] faithful pre-fix no-progress foundation-locator materialization still recovers in the same workspace
[ ] partial/corrupt/foreign checkpoint state remains typed and diagnostic
[ ] live-writer exclusion remains through the existing run activity lease
[ ] recovery cannot delete externally configured foundation/replay/source inputs
[ ] recovery repair reduces/consolidates split materialization authority rather than adding another state/compatibility layer
[ ] absolute/tilde/config-relative foundation forms reach real MacePostSelectionTrainer dependency projection from a foreign CWD
[ ] generated mace_run_config.yaml uses the current authenticated canonical foundation locator
[ ] immutable internal P5 config remains path-free for foundation
[ ] single-source replay_set path-form/relocation/mutation behavior remains green
[ ] structural absence checks remain known-positive/known-negative and reject raw-path, checkpoint-presence, and delete-before-authenticate families
[ ] final required pytest/static/integration evidence executed on the exact final executable candidate
[ ] no new migration database, compatibility registry, materialization pointer, recovery state machine, path registry, cleanup daemon, replay identity, or lock layer was introduced
```

No Frozen architecture reconsideration is warranted on current evidence. If exact safe continuation reuse cannot be established with the existing materialization and persisted execution authorities without inventing a new durable migration/identity system, stop and return to Software Design rather than adding such machinery silently.

---

## 8. Snapshot-complete handoff and closeout

The current implementation handoff is the parent workplan plus this amendment plus the current referenced MLFF architecture/P5/P7 authorities under Protocol 5.16.0. No still-binding task-specific requirement should depend on prior chat, superseded amendment wording, or Git archaeology.

After a later independent Software Design review passes, archive/retire the completed parent/amendment according to repository policy and reconcile `workplans/active/README.md`. Closeout must not mutate executable product behavior.
