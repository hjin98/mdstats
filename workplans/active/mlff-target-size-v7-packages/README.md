# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into six sequential implementation packages. The parent V7 workplan remains the **sole scientific and architectural authority**. Package contracts constrain execution order, package-local scope, acceptance, and verification; omission from a package does not waive a frozen parent requirement.

A package may not reinterpret the frozen parent merely to preserve legacy code/tests. Newly discovered necessary implementation consequences that preserve the parent are incorporated at the owning package. Reopen design only on a parent-listed reopen condition or equivalent material evidence.

## Current sequencing state

P1 and P2 are accepted predecessor authorities. Cumulative P3 revision-7 closure through P3A9 is implemented, validated with canonical lock-identity acceptance, process concurrency races, fresh-child validation, and affected regression, and formally closed at commit `9d195807cff0bb8042f447ac33ceb0586ed708ac`.

P3 revision 7 consists cumulatively of:

- `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md`;
- `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md`;
- `P3_REVIEW3_EXECUTION_OWNER_IMMUTABILITY_CLOSURE_FIX.md`;
- `P3_REVIEW4_FINAL_OWNER_REPLAY_CLOSURE_FIX.md`;
- `P3_REVIEW5_FINAL_IMPLEMENTATION_CLOSURE_FIX.md`;
- `P3_P3A4_IMPLEMENTATION_REPAIR_INSTRUCTIONS.md`;
- `P3_P3A4_FINAL_REVIEW_REPAIR_INSTRUCTIONS.md`;
- `P3_P3A5_EMA_CHECKPOINT_STATE_REPAIR_INSTRUCTIONS.md`;
- `P3_P3A6_FINAL_ACCEPTANCE_REPAIR_INSTRUCTIONS.md`;
- `P3_P3A7_RESTART_OWNER_ACCEPTANCE_REPAIR_INSTRUCTIONS.md`;
- the P3A8 owner-level acceptance implementation state at `472276ee521eb2b19177299c1c9ad660dbd6ad46`;
- `P3_P3A9_HEAD_POINTER_RECONCILIATION_REPAIR_INSTRUCTIONS.md`, closed and accepted at `9d195807cff0bb8042f447ac33ceb0586ed708ac`.

P3A9 repaired the demonstrated execution-head publication crash case where an immutable valid successor is durable while `current_head.json` remains stale, preserving deterministic reducer replay, typed resolver recovery, process-level CAS locking serialization, and fail-closed fork/orphan semantics.

**Cumulative P3 revision 7 is formally closed.** P4 entry authority remains bound to
`9d195807cff0bb8042f447ac33ceb0586ed708ac`.

**P4 revision 7 is REOPENED and active.** Revision-4, revision-5, and revision-6 implementation candidates/evidence are preserved in adjacent baseline files. Revision 6 successfully consolidated execution-root construction into one production owner and repaired the canonical terminal loader so it always validates the current CampaignStore revision. Independent review nevertheless found two remaining semantic-owner/currentness gaps: the mandatory first-publication race still hand-builds the cleanup-side `CampaignOwnershipBoundary`/retention fence and performs direct deletion instead of traversing the real production STOR ownership/removal path; and a legitimately validated terminal snapshot can still be rendered/reported after real `prepare` advances CampaignStore to a newer generation because public exposure does not re-establish currentness at exposure time. Revision 7 therefore reopens only P4-C3, P4-E3, and final P4-G3. Accepted P1-P3 science, revision-6 root ownership, and the revision-6 terminal validation core are preserved subject to affected regression.

**P5 is blocked until P4 revision 7 recloses.** It may not consume target-size terminal state as current authority until production STOR first-publication protection is proven through the real removal owner and all public/current terminal exposure revalidates CampaignStore currentness in the same invocation.

Long GPU/real-production qualification remains deferred to final release.

## Mandatory sequence

```text
P1 neutral scientific substrate
  -> P2 target-size statistical authorities
  -> P3 candidate execution and paired-seed screen
       base revision-3 contract
       + revision-4 Review-2 authenticated-evaluation/restart amendment
       + revision-5 Review-3 execution-owner/immutability amendment
       + revision-6 Review-4 owner/replay closure amendment
       + revision-7 Review-5 final implementation-closure amendment
       + revision-7 P3A4 implementation repair
       + revision-7 P3A4 final-review repair
       + revision-7 P3A5 EMA checkpoint-state repair
       + revision-7 P3A6 final-acceptance repair
       + revision-7 P3A7 restart-owner acceptance repair
       + P3A8 owner-level closure implementation
       + revision-7 P3A9 stale-head successor reconciliation repair
       -> FORMAL P3 CLOSURE COMMIT
  -> P4 atomic runtime/persistence cutover
       revision-4 implemented baseline
       + revision-5 terminal real-owner reload / first-publication attempt
       + revision-6 canonical-root/current-terminal loader repair
       + revision-7 production-STOR owner / exposure-time-currentness reclosure
       -> FORMAL P4 RECLOSURE
  -> P5 post-selection CV and final production
  -> P6 destructive cleanup and assembled closure
```

Do not start dependent executable work until the previous package has both **semantic/conformance closure** and **functional closure**. Package-local evidence may be reused when later changes cannot plausibly invalidate it, but P6 must perform fresh final affected-surface regression and integration on the assembled candidate.

## Cross-package rules

- Implement on one dedicated V7 implementation branch with a committed checkpoint after every accepted package.
- P1-P3 may coexist with the old runtime only as **unreachable/test-only scaffolding**. No public runtime flag, fallback, dual write, or schema reinterpretation is permitted.
- P3 owns scientific execution evidence/replay; P4 may consume/adopt that authority but may not recreate its replay/reducer semantics.
- P4 is the indivisible production ownership cutover. Current `prepare`/`select-target-size` orchestration, canonical campaign generation/current-state authority, restart authentication, and current authority lookup switch together.
- P4 must not contain predecessor repair work needed to make P3 acceptable; such repair closes under P3 before P4 activation.
- P4 revision 7 preserves the revision-6 single canonical execution-root construction owner shared by runtime and retention/STOR; no duplicate root path authority may be reintroduced.
- P4 revision 7 first-publication retention acceptance must traverse real `select-target-size`, the real P3 initializer, an independent process, the actual production STOR ownership-boundary constructor, and the actual production destructive cleanup/removal helper. Direct boundary/fence construction or direct filesystem deletion is helper coverage only and cannot close C3.
- The mandatory C3 race must challenge the actual observed runtime root directory and first-publication files and prove an unrelated reclaimable control is deleted through the same production STOR path.
- P4 revision 7 preserves the revision-6 canonical terminal loader: current terminal validation begins from the actual current CampaignStore revision and performs the full P1/P2/common/P3/head/reducer/projection validation chain.
- A `ValidatedTargetSizeTerminalResult` is a validated snapshot, not perpetual current authority. Every public/current terminal view/write/report/P5 consumer must re-establish CampaignStore currentness at exposure time before exposing terminal authority.
- P5 must not feed CV evidence or configuration back into target-size selection.
- P6 deletes unreachable retired topology only after the current runtime is functionally closed.
- Stage-local affected regression is required after every material behavior-changing pass before dependent work proceeds.
- Real-owner acceptance may use bounded scientific fixtures and fake expensive training/prediction only below the owner boundary, after required production owner behavior executes.
- Full long GPU/real-production qualification remains deferred to final release; bounded functional, reference-equivalence, restart, storage, concurrency, and resource checks remain required where affected.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md` — DATA2/DATA3/neutral statistical identity and provenance reset.
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md` — configurable N/M ladders, one split, one training order, one evaluation order, and pure target-size state.
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` — canonical common preparation, exact candidate realization/materialization, paired optimizer seeds, exact completed-epoch TRAIN2 continuation, exact-checkpoint M-ladder EVAL2, complete-boundary crash-safe reducer commit, and restart closure.
   - `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md` — exact ordered M_i authentication, exact boundary live/EMA inference provenance, immutable TRAIN2 boundary snapshots, execution-proof records, completion-bound batches, deterministic full-history restart replay.
   - `P3_REVIEW3_EXECUTION_OWNER_IMMUTABILITY_CLOSURE_FIX.md` — real validator execution, shared inference owner, self-authenticating predictions, typed resolver coverage, immutable publication, explicit success/failure evidence, conflict-safe concurrency, fresh-process replay.
   - `P3_REVIEW4_FINAL_OWNER_REPLAY_CLOSURE_FIX.md` — mandatory validation, immutable-snapshot-only inference, provider/state proof, exact-M byte authentication, complete ancestry resolution, exclusive logical-cell commit, fixed scientific replay, fresh-process success/failure acceptance.
   - `P3_REVIEW5_FINAL_IMPLEMENTATION_CLOSURE_FIX.md` — single authenticated provider/model execution owner, non-optional role parents, sealed exact-M validation, full optimizer/export/materialization re-derivation, crash-safe writers, raw failure evidence, typed resolver replay, no serialized-outcome fallback.
   - `P3_P3A4_IMPLEMENTATION_REPAIR_INSTRUCTIONS.md` — remove two-model/fake-owner bypasses, seal exact-M parsing, extend typed publication owner, make failure completion raw-evidence-only, complete restart authority, production durable ancestry acceptance.
   - `P3_P3A4_FINAL_REVIEW_REPAIR_INSTRUCTIONS.md` — real MACE 0.3.16 provider reconstruction/raw-state authentication, complete variant parent graph, bounded real-owner CPU/restart acceptance.
   - `P3_P3A5_EMA_CHECKPOINT_STATE_REPAIR_INSTRUCTIONS.md` — distinguish raw EMA-saved checkpoint state from live continuation state while preserving provider ownership and checkpoint-save provenance.
   - `P3_P3A6_FINAL_ACCEPTANCE_REPAIR_INSTRUCTIONS.md` — restore canonical `target_size_evaluation_model_state(optimizer_policy)` (`EMA -> ema`, otherwise `live`) and prove pinned MACE checkpoint-owner acceptance.
   - `P3_P3A7_RESTART_OWNER_ACCEPTANCE_REPAIR_INSTRUCTIONS.md` — prove durable noncanonical EMA/LIVE state rejects through the real `resolve_target_size_candidate_for_resume(...)` owner.
   - `P3_P3A9_HEAD_POINTER_RECONCILIATION_REPAIR_INSTRUCTIONS.md` — final revision-7 predecessor closure: recover only a unique authenticated linear successor chain after stale-pointer crash, preserve deterministic reducer replay, reject forks/orphans/corruption, and formally close P3 before P4 begins.
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` — active revision-7 overlay reopening production-STOR first-publication owner acceptance, exposure-time terminal currentness, and assembled P4 closure; revision-4/revision-5/revision-6 baselines are preserved adjacent.
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` — exact-T_selected CV and fresh final-production path; **blocked until P4 revision 7 recloses**.
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` — remove retired architecture and perform assembled final acceptance.
