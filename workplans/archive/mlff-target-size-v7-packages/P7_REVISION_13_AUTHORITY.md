---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 13.7
status: closed-pass
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
frozen_source_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
reviewed_evidence_head: b82e122decd528450c616e571a47b8ed3d058e4c
review_verdict: PASS
current_amendment: P7_REVISION_13_7_SOFTWARE_CLOSURE_AND_DEFERRED_PRODUCTION_QUALIFICATION_AMENDMENT.md
current_review_evidence: P7_REVISION_13_7_REVIEW_EVIDENCE.md
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 13.7 — authoritative closure

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains controlling.

P7 software implementation and functional acceptance are **CLOSED / PASS** at executable commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`.

R13.7 corrects an acceptance drift introduced by R13.4-R13.6. The base P7 package explicitly distinguishes software functional acceptance from actual-production scientific qualification: real external DFT is required for a real production qualification campaign, not for routine P7 software closure, and long target-machine production qualification is deferred to the established final-release phase.

## Accepted P7 closure evidence

- exact executable/interpreter identity (`0.20.242a0`);
- affected P7 regression `155 passed, 1 skipped`;
- bounded real RTX 3090 KOKKOS/mliappy MACE callback execution;
- real publication/currentness/deployment/reference-matching/reduction/locked/persistence owners under assembled integration;
- fail-closed missing-publication behavior through the production CLI;
- truthful `waiting_for_reference` behavior when external DFT is absent;
- stress provenance/canonicalization, resource lineage, exact PBC/cell evidence, no-fallback semantics, one-shot locked machinery, terminal/release-index persistence, and fresh-process reauthentication.

No executable source change is required.

## Production qualification disposition

The user's actual campaign should now be run through its normal real lifecycle:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> freeze FinalProductionPublication
 -> qualification run
```

It is legitimate for normal campaign operation to create its own P1-P5/P5 publication state. The previous prohibition against creating campaign state applied only to attempts to present a newly manufactured fixture campaign as pre-existing evidence for P7 closure.

If independent external DFT is unavailable, `qualification run` should stop truthfully at `waiting_for_reference` with the immutable actionable request. This does not reopen P7 software implementation.

When real DFT later becomes available, resume the same campaign qualification, complete physical/relaxation/dynamics/calibration evidence, explicitly activate the one-shot locked test, produce `RELEASE_QUALIFIED` or `REJECTED`, and reauthenticate the final graph in a new process. Long target-machine production/resource/performance qualification remains deferred to final release.

## Successor disposition

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` is **unblocked** by P7 implementation closure. It must preserve P7 publication/qualification/reference/locked evidence and currentness semantics.

A future actual campaign may expose a genuine executable defect. Such a defect reopens only the affected software surface and invalidates only qualification evidence plausibly affected by the repair. A scientific rejection or missing external reference is not itself a software defect.
