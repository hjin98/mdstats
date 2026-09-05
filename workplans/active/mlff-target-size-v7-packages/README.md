# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into seven sequential implementation packages. The frozen parent V7 workplan remains the controlling scientific and architectural authority.

## Current assembled integration status

Package-local closure history remains valid where its own accepted authority says so, but **the assembled P1-P7 + CampaignStore + Storage product remains NO-PASS / implementation-reopened on this branch** after the second independent implementation review.

Current assembled integration authority is the composition of:

1. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md`;
2. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_SECOND_PASS_AMENDMENT.md`, with precedence only where it explicitly tightens/corrects the parent integration plan;
3. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_FINAL_CONVERGENCE_AMENDMENT.md`, which folds the earlier exact-boundary checkpoint-recovery bug contract into current V7 acceptance without restoring retired V5 machinery;
4. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_REVIEW_REOPEN.md`, the first independent implementation-review reopen for branch head `919f848d7f301c50c9341c45106dd862239e165d` / executable head `60edb67bb05a49560b2e0201ab2ab940a867b236`;
5. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_REVIEW_R2.md`, the current second-review authority for branch head `82164476f647b12d00725ff96be93a622ff801a6` / executable head `e72c93a7e09f6b59bdd3e8aa1789176fc50f4474`;
6. `P4_PREPARED_GENERATION_STAGE_BOUNDARY_REPAIR.md` for the prepared-generation and direct-EVAL2 prerequisite where non-conflicting with the later integration amendments;
7. `../mlff-storage-io-reset/AUTHORITY.md` plus Storage Revision 38 for the current storage implementation/review state.

Executable progress against the composed authority is recorded in `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_PROGRESS.md`. That file is evidence/progress, not closure.

The latest implementation materially closes the first review's create-or-verify publication, ordinary `prepare` source-change/terminal-idempotence, concurrent-prepare CAS, stale `M == batch_size` P3 evidence, and bounded P7 conservative-PES defects. The **main campaign lifecycle** now also uses a coherent typed read-only snapshot.

The remaining blockers are narrower:

- the separate public `qualification status` path still reads P7 pointer rows independently and still interprets plan/component/locked/release content through weaker raw-JSON reads instead of the same coherent typed owner boundary; and
- final closure evidence has not yet been recorded on the exact repaired executable candidate, while one existing P5/P7 pointer race test has a non-live/incorrect before-or-after oracle for a two-transaction sequence.

These are observation-consolidation and acceptance-evidence defects. They do **not** justify reopening the parent target-size scientific question, P5 CV/final-production science, P7 qualification science, CampaignStore's current-authority role, the generation-safe prepared/frame design, or Storage Revision 38's canonical destructive architecture. Repair by reducing duplicate observation logic and making the acceptance interleavings deterministic; do not add registries, wrappers, parallel currentness state, a second cache, a second batch policy, or another storage mutation path.

The final convergence contract continues to preserve the earlier `select-target-size` checkpoint-recovery invariant: interruption before the first authenticated exact boundary means **no checkpoint authority yet** and retries fresh, while a claimed durable continuation whose required checkpoint/runtime/companion bytes are missing or corrupt fails closed. Current V7 exact-boundary state owns this behavior; obsolete `CandidateCheckpointCatalog`, REPAIR2/label-domain, development-complement, and target-only/replay authorization machinery must not be reintroduced merely to preserve the historical repair.

P6 remains a completed predecessor package. It is not a runtime stage inserted between P5 and P7; its accepted cleanup/compatibility guarantees are preservation constraints, while the current owner-driven storage successor is `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` Revision 38.

## Package-local sequencing history

P1-P6 remain accepted/reclosed under their package-local authorities. P7 executable source remains frozen at:

- commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`;
- tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`;
- source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`.

**P7 revision 13.7 remains CLOSED / PASS for its package-local software implementation and functional acceptance.** That historical closure does not override the assembled integration reopen. The bounded P7 acceptance model has now been repaired to use one conservative energy/force PES and the assembled lifecycle source covers reference supply, nonlocked completion, explicit locked activation, terminal release, generation advance, and retained reveal history; exact-candidate assembled evidence is still required before integration closure.

### Accepted P7 closure evidence

- all accepted R11/R12/R13/R13.1/R13.2/R13.3 executable/scientific/runtime/resource/currentness repairs;
- exact qualifying interpreter identity (`0.20.242a0`, source digest `7772ad5f...`);
- affected P7 regression `155 passed, 1 skipped`;
- selected KOKKOS/mliappy MACE worker viability on RTX 3090 through the real product callback;
- assembled publication/currentness/reference/reduction/locked/persistence owner coverage within the P7 package-local acceptance boundary;
- fail-closed missing-publication behavior through the real CLI;
- truthful `waiting_for_reference` behavior when independent external DFT is absent;
- terminal/release graph and fresh-process reauthentication mechanics.

### Production qualification is deferred, not waived

The base P7 package explicitly distinguishes P7 software completion from actual-production scientific qualification. Real external DFT is required when qualifying a real frozen production publication, but it is not required to prove P7 software implementation correctness. Long target-machine production/resource/performance qualification remains deferred to the established final-release phase.

After the assembled integration repair closes, the operational lifecycle remains:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> freeze FinalProductionPublication
 -> qualification run
```

If real DFT is unavailable for a real production publication, `qualification run` should truthfully stop at `waiting_for_reference`. When independent DFT is later available, resume the same qualification lineage, complete physical/relaxation/dynamics/calibration evidence, explicitly activate the one-shot locked test, and record `RELEASE_QUALIFIED` or `REJECTED` plus fresh-process reauthentication.

The historical P7 successor gate allowed Storage work to proceed. **Storage Revision 38 design remains accepted, but assembled storage acceptance is still subject to the integration review.** Do not invent archive/restore support for current prepared/frame state when the real owner correctly declares it hot/restart-required and non-cold-replaceable; applicable storage operations must preserve owner capability and remain scientifically neutral.

## Packages

1. `P1_NEUTRAL_SCIENTIFIC_SUBSTRATE.md`
2. `P2_TARGET_SIZE_STATISTICAL_AUTHORITIES.md`
3. `P3_CANDIDATE_EXECUTION_PAIRED_SCREEN.md` plus accepted closure amendments
4. `P4_ATOMIC_RUNTIME_PERSISTENCE_CUTOVER.md` plus accepted closure amendments and the active prepared-generation repair
5. `P5_POST_SELECTION_CV_FINAL_PRODUCTION.md` plus accepted final-publication amendments
6. `P6_DESTRUCTIVE_CLEANUP_FINAL_CLOSURE.md` plus accepted reclosure/rebind amendments
7. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` composed with revisions 2, 10-13.6 and current package-local closing revision 13.7

## Current P7 authority

Read P7 package-local semantics in this precedence order:

1. frozen parent workplan;
2. accepted/reclosed predecessor authorities;
3. `P7_REVISION_13_7_SOFTWARE_CLOSURE_AND_DEFERRED_PRODUCTION_QUALIFICATION_AMENDMENT.md` and `P7_REVISION_13_AUTHORITY.md`;
4. accepted earlier R13.6/R13.5/R13.4/R13.3/R13.2/R13.1/R13/R12/R11/R10/base-P7 contracts where non-conflicting;
5. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` for the storage-neutral successor boundary.

`P7_REVISION_13_7_REVIEW_EVIDENCE.md` records the independent package-local PASS review. For **current assembled campaign implementation/acceptance**, use the integration authority set at the top of this file; package-local PASS evidence cannot substitute for the reopened cross-package acceptance claim.
