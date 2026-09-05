# MLFF target-size V7 implementation packages

These files decompose `../MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` into seven sequential implementation packages. The frozen parent V7 workplan remains the controlling scientific and architectural authority.

## Current assembled integration status

Package-local closure history remains valid where its own accepted authority says so, but **the assembled P1-P7 + CampaignStore + Storage product remains NO-PASS / implementation-reopened on this branch** after the latest independent implementation review.

Current assembled integration authority is the composition of:

1. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_WORKPLAN.md`;
2. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_HARDENING_SECOND_PASS_AMENDMENT.md`, with precedence only where it explicitly tightens/corrects the parent integration plan;
3. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_FINAL_CONVERGENCE_AMENDMENT.md`, which folds the earlier exact-boundary checkpoint-recovery bug contract into current V7 acceptance without restoring retired V5 machinery;
4. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_REVIEW_REOPEN.md`, the first independent implementation-review reopen for branch head `919f848d7f301c50c9341c45106dd862239e165d` / executable head `60edb67bb05a49560b2e0201ab2ab940a867b236`;
5. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_REVIEW_R2.md`, the second-review authority that identified the qualification-observation consolidation and exact-candidate acceptance gaps;
6. `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_REVIEW_R2_POSITION_INTEGRITY_AMENDMENT.md`, the current residual review authority for branch head `57f8f408d1693f18a891e4209de6af8a62c03a20` / executable head `84868eccd5dec74f07d4aa1917037d57e032249d`;
7. `P4_PREPARED_GENERATION_STAGE_BOUNDARY_REPAIR.md` for the prepared-generation and direct-EVAL2 prerequisite where non-conflicting with the later integration amendments;
8. `../mlff-storage-io-reset/AUTHORITY.md` plus Storage Revision 38 for the current storage implementation/review state.

Executable progress against the composed authority is recorded in `../MLFF_CAMPAIGN_P1_P7_STORAGE_INTEGRATION_IMPLEMENTATION_PROGRESS.md`. That file is evidence/progress, not closure.

The latest implementation closes the R2 qualification-status problem in its main form: both public status paths use the shared coherent CampaignStore snapshot, content-addressed P7 records are typed/authenticated before interpretation, attempt identity comes from the authenticated qualification plan, and the probabilistic combined-pointer race has been replaced by deterministic single-owner transaction races. Exact-candidate acceptance is also recorded on executable `84868ecc...`: the required closure selection is `690 passed, 0 failed, 0 skipped`, and the affected regression has identical baseline/candidate failure sets with the persistent failures mapped outside this integration surface.

One narrower blocker remains. The shared mutable component-position reader still treats **any** parseable payload lacking `position_object` as the old direct representation. The current `mdstats.qualification-component-position-locator.v1` writer always emits `position_object` plus its digest, so a malformed current locator can delete that mandatory field and fall through the legacy/direct branch. `qualification status` may then follow its `evidence_digest` and report semantic component state instead of degrading the schema-inconsistent locator to `unreadable_position`.

The repair is bounded to tightening the existing shared position reader with an explicit current-versus-legacy discriminator and validating the locator/object claims. It does **not** justify reopening the parent target-size scientific question, P5 CV/final-production science, P7 qualification science, CampaignStore's current-authority role, the generation-safe prepared/frame design, or Storage Revision 38's canonical destructive architecture. Do not add a position registry, new CAS authority, second observer, cache, batch policy, or storage mutation path.

The final convergence contract continues to preserve the earlier `select-target-size` checkpoint-recovery invariant: interruption before the first authenticated exact boundary means **no checkpoint authority yet** and retries fresh, while a claimed durable continuation whose required checkpoint/runtime/companion bytes are missing or corrupt fails closed. Current V7 exact-boundary state owns this behavior; obsolete `CandidateCheckpointCatalog`, REPAIR2/label-domain, development-complement, and target-only/replay authorization machinery must not be reintroduced merely to preserve the historical repair.

P6 remains a completed predecessor package. It is not a runtime stage inserted between P5 and P7; its accepted cleanup/compatibility guarantees are preservation constraints, while the current owner-driven storage successor is `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` Revision 38.

## Package-local sequencing history

P1-P6 remain accepted/reclosed under their package-local authorities. P7 executable source remains frozen at:

- commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`;
- tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`;
- source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`.

**P7 revision 13.7 remains CLOSED / PASS for its package-local software implementation and functional acceptance.** That historical closure does not override the assembled integration reopen. The bounded P7 acceptance model uses one conservative energy/force PES and the assembled lifecycle evidence covers reference supply, nonlocked completion, explicit locked activation, terminal release, generation advance, and retained reveal history. The remaining assembled blocker is the public observation handling of malformed mutable component-position state, not P7 science or the qualification execution owner.

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
