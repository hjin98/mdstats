# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into six sequential implementation packages. The parent V7 workplan remains the **sole scientific and architectural authority**. These package contracts only constrain execution order, package-local scope, acceptance, and verification.

A requirement omitted from a package is **not waived** if it is frozen by V7. A package may not reinterpret V7 to preserve legacy code/tests. Newly discovered necessary implementation consequences that preserve V7 are incorporated locally; reopen design only on a V7-listed reopen condition or equivalent material evidence.

P3 revision 7 consists of the consolidated base contract in `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` **plus** the mandatory Review-2 amendment in `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md` **plus** the mandatory Review-3 amendment in `P3_REVIEW3_EXECUTION_OWNER_IMMUTABILITY_CLOSURE_FIX.md` **plus** the mandatory Review-4 amendment in `P3_REVIEW4_FINAL_OWNER_REPLAY_CLOSURE_FIX.md` **plus** the mandatory Review-5 precision amendment in `P3_REVIEW5_FINAL_IMPLEMENTATION_CLOSURE_FIX.md`. Review-2/3/4 remain authoritative; Review-5 is cumulative and closes under-disclosed implementation escape hatches found at `d054c719a2a4a37f38cf200ef5918f39a128a592` (`P3A3`). P1/P2 and P3-A/B/C scientific semantics remain frozen except for validator/persistence consequences required by the amendments. P4 remains blocked until the cumulative revision-7 P3 exit gate passes.

## Mandatory sequence

```text
P1 neutral scientific substrate
  -> P2 target-size statistical authorities
  -> P3 candidate execution and paired-seed screen
       base revision-3 contract
       + mandatory revision-4 Review-2 authenticated-evaluation/restart amendment
       + mandatory revision-5 Review-3 execution-owner/immutability amendment
       + mandatory revision-6 Review-4 owner/replay closure amendment
       + mandatory revision-7 Review-5 final implementation-closure amendment
  -> P4 atomic runtime/persistence cutover
  -> P5 post-selection CV and final production
  -> P6 destructive cleanup and assembled closure
```

Do not start dependent executable work until the previous package has both **semantic/conformance closure** and **functional closure**. Package-local evidence may be reused when later changes cannot plausibly invalidate it, but P6 must perform fresh final affected-surface regression and integration on the assembled candidate.

## Cross-package rules

- Implement on one dedicated V7 implementation branch with a committed checkpoint after every accepted package.
- P1-P3 may coexist with the old runtime only as **unreachable/test-only scaffolding**. No public runtime flag, fallback, dual write, or schema reinterpretation is permitted.
- P4 is the indivisible ownership cutover. Current prepare/select-target-size orchestration, persistence generation, restart authentication, and current authority lookup switch together.
- P5 must not feed CV evidence or configuration back into target-size selection.
- P6 deletes unreachable retired topology only after the V7 current runtime is functionally closed.
- Stage-local affected regression is required after every material behavior-changing pass before dependent work proceeds.
- Real-owner acceptance may use bounded scientific fixtures and fake expensive training/prediction only below the owner boundary, after provider/model reconstruction, state loading, provenance/input validation, and all other accepted semantic-owner behavior has executed.
- Full long GPU/real-production qualification remains deferred to final release; bounded functional, reference-equivalence, and resource checks remain required where affected.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md` — DATA2/DATA3/neutral statistical identity and provenance reset.
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md` — configurable N/M ladders, one split, one training order, one evaluation order, and pure target-size state.
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` — canonical common preparation, exact candidate realization/materialization, paired optimizer seeds, exact completed-epoch TRAIN2 continuation, exact-checkpoint M-ladder EVAL2, complete-boundary crash-safe reducer commit, and restart closure.
   - `P3_REVIEW2_AUTHENTICATED_EVAL_RESTART_FIX.md` — mandatory revision-4 corrective authority: exact ordered M_i input authentication, exact boundary live/EMA inference provenance, immutable historical TRAIN2 boundary snapshots, per-cell execution-proof records, completion-bound batches, and deterministic full-history restart replay.
   - `P3_REVIEW3_EXECUTION_OWNER_IMMUTABILITY_CLOSURE_FIX.md` — mandatory revision-5 cumulative closure authority: real validator execution inside direct inference, shared static-MACE inference reuse, policy-faithful live/EMA state, self-authenticating predictions, re-derivation validators, create-or-verify immutable publication, explicit success/TRAIN2-failure/EVAL2-failure cell evidence, resolvable full restart graph, conflict-safe concurrency, and fresh-process assembled replay.
   - `P3_REVIEW4_FINAL_OWNER_REPLAY_CLOSURE_FIX.md` — mandatory revision-6 closure authority: no optional accepted-path validation, immutable-snapshot-only direct inference, shared provider/state loading with actual loaded-state digest proof, ExtXYZ byte-order authentication for exact M, mandatory prediction-to-metric/failure linkage, complete resolver coverage for snapshot/rung/continuation/failure ancestry, non-destructive idempotent publication, exclusive logical-cell commit, fixed full scientific replay algorithm, and fresh-process success/TRAIN2-failure/EVAL2-failure acceptance.
   - `P3_REVIEW5_FINAL_IMPLEMENTATION_CLOSURE_FIX.md` — mandatory revision-7 final precision authority: one authenticated provider/model must both own the loaded live/EMA state and execute forward; exact role parents are non-optional; exact-M validation is sealed to the bytes/labels actually consumed and view provenance cannot be spoofed; full optimizer/export/materialization re-derivation is required; all immutable writers use crash-safe create-or-verify; logical-cell plus reducer-head publication use CAS/locking semantics; failure completions accept raw immediate evidence only; every resolver load is typed/content-address verified; restart has no optional authority or serialized-outcome fallback; and fresh-process acceptance must prove mid-screen continuation plus terminal/failure replay.
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` — atomic current-runtime, state-schema, receipt, restart and invalidation transition.
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` — exact-T_selected CV and fresh final-production path.
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` — remove retired architecture and perform assembled final acceptance.
