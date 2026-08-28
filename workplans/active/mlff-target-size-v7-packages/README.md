# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into six sequential implementation packages. The parent V7 workplan remains the **sole scientific and architectural authority**. These package contracts only constrain execution order, package-local scope, acceptance, and verification.

A requirement omitted from a package is **not waived** if it is frozen by V7. A package may not reinterpret V7 to preserve legacy code/tests. Newly discovered necessary implementation consequences that preserve V7 are incorporated locally; reopen design only on a V7-listed reopen condition or equivalent material evidence.

P3 is governed by `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` together with the mandatory `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN_REVIEW1_AMENDMENT.md`. The Review-1 amendment has precedence only where it makes the P3 execution-boundary, lineage, failure, or restart contract more specific; all unaffected P3 revision-2 obligations remain mandatory.

## Mandatory sequence

```text
P1 neutral scientific substrate
  -> P2 target-size statistical authorities
  -> P3 candidate execution and paired-seed screen
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
- Real-owner acceptance may use bounded scientific fixtures and fake expensive training/prediction below the owner boundary, but may not mock or bypass the orchestration/persistence/state-transition owner being accepted.
- Full long GPU/real-production qualification remains deferred to final release; bounded functional, reference-equivalence, and resource checks remain required where affected.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md` — DATA2/DATA3/neutral statistical identity and provenance reset.
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md` — configurable N/M ladders, one split, one training order, one evaluation order, and pure target-size state.
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` + mandatory `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN_REVIEW1_AMENDMENT.md` — common preparation, exact candidate materialization, paired optimizer seeds, exact TRAIN2 boundary continuation, exact-M EVAL2, crash-safe reducer commit, and restart closure.
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` — atomic current-runtime, state-schema, receipt, restart and invalidation transition.
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` — exact-T_selected CV and fresh final-production path.
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` — remove retired architecture and perform assembled final acceptance.
