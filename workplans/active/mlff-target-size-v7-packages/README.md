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

**Cumulative P3 revision 7 is formally closed.** P4 entry authority remains bound to `9d195807cff0bb8042f447ac33ceb0586ed708ac`.

**P4 revision 8 is formally closed and independently accepted at commit `145388e5ad11733be1c19539886e34b82cc7d7d2`.** Revision-4 through revision-7 implementation candidates/evidence remain preserved in adjacent baseline files. Revision 8 sealed the last public terminal snapshot-only result-view escape hatch while preserving the accepted production-STOR first-publication owner path, canonical execution-root owner, CampaignStore-first terminal loader, and full P1-P3 authority-validation chain. Fresh assembled P4/P3A9 regression closed with 170 passing tests.

**P5 revision 2 is active and implementation-ready.** The P4 dependency gate is cleared. Revision 2 reconciles P5 against the implemented P1-P4 authority surface: every current P5 start/resume/exposure must reauthenticate the current `SELECTED` terminal through the CampaignStore-backed P4 loader; `T_selected` means the exact selected target dataset `pi_train[:N_selected]`, never an epoch; post-selection CV authority descends from exact selected membership plus neutral correlation groups rather than legacy DATA5 label-domain/CV lineage; and fresh final production resolves its epoch horizon from `[training].max_num_epochs`, independently of screening `n3`.

P6 remains blocked until P5 implementation has semantic/conformance closure, functional closure, fresh assembled affected regression, and formal independent acceptance.

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
       + revision-7 production-STOR owner / exposure-time-currentness repair
       + revision-8 public terminal snapshot-API sealing / final reclosure
       -> FORMAL P4 CLOSURE COMMIT 145388e5ad11733be1c19539886e34b82cc7d7d2
  -> P5 revision 2 post-selection CV and fresh final production
       -> FORMAL P5 CLOSURE COMMIT
  -> P6 destructive cleanup and assembled closure
```

Do not start dependent executable work until the previous package has both **semantic/conformance closure** and **functional closure**. Package-local evidence may be reused when later changes cannot plausibly invalidate it, but P6 must perform fresh final affected-surface regression and integration on the assembled candidate.

## Cross-package rules

- Implement on one dedicated V7 implementation branch with a committed checkpoint after every accepted package.
- P1-P3 may coexist with the old runtime only as **unreachable/test-only scaffolding**. No public runtime flag, fallback, dual write, or schema reinterpretation is permitted.
- P3 owns scientific execution evidence/replay; P4 may consume/adopt that authority but may not recreate its replay/reducer semantics.
- P4 is the indivisible production ownership cutover. Current `prepare`/`select-target-size` orchestration, canonical campaign generation/current-state authority, restart authentication, and current authority lookup switch together.
- P4 must not contain predecessor repair work needed to make P3 acceptable; such repair closes under P3 before P4 activation.
- P4 revision 8 preserves the single canonical execution-root construction owner shared by runtime and retention/STOR and the accepted revision-7 production-STOR first-publication race.
- P4 revision 8 preserves the canonical terminal loader: current terminal validation begins from the actual current CampaignStore revision and performs the full P1/P2/common/P3/head/reducer/projection validation chain.
- A `ValidatedTargetSizeTerminalResult` is a validated snapshot, not perpetual current authority. Every public/current terminal view/write/report/P5 consumer must re-establish CampaignStore currentness at exposure time before exposing terminal authority.
- No exported/public snapshot-only terminal renderer or arbitrary-path terminal writer may accept historical `revision + validated_result` objects and expose them as current authority. Terminal-capable pure formatting must be private/internal, or retained public generic helpers must be strictly nonterminal-only.
- P5 consumes `T_selected = pi_train[:N_selected]` as immutable selected target membership. `T_selected` is not a screening epoch or production horizon.
- P5 current CV roles descend from exact selected-frame identity and neutral correlation groups; legacy DATA5 label-domain/CV lineage is not current authority.
- P5 must not feed CV evidence or configuration back into target-size selection.
- P5 final production starts fresh; its production horizon is the resolved `[training].max_num_epochs` and is independent of target-size screening `n3`.
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
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` — revision-8 implementation is formally closed and independently accepted at `145388e5ad11733be1c19539886e34b82cc7d7d2`; revision-4 through revision-7 baselines/evidence remain preserved adjacent.
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` — revision-2 active implementation contract: CampaignStore-backed current selected-data entry, exact `T_selected` post-selection CV, legacy DATA5-CV authority cutover, fresh final production, downstream-only invalidation/restart, and `[training].max_num_epochs` production-horizon independence from `n3`.
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` — blocked on formal P5 closure; remove retired architecture and perform assembled final acceptance.
