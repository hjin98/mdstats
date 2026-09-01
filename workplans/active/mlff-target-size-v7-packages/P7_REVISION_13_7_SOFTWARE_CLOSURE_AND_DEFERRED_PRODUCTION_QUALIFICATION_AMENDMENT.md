---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.7
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.6
parent_scientific_workplan_id: CODE-MLFF-TARGET-SIZE-SCIENTIFIC-SIMPLIFICATION-V7
protocol_version: 5.8.0
revision: 13.7
status: accepted-closure
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
frozen_source_digest: 7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6
reviewed_evidence_head: b82e122decd528450c616e571a47b8ed3d058e4c
review_verdict: PASS
amended_date: 2026-09-01
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
scope: correct R13.4-R13.6 acceptance drift by restoring the base P7 distinction between software functional acceptance and later actual production scientific qualification; close P7 implementation while deferring unavailable external DFT and long real-production qualification to the established final-release qualification phase
precedence: revision 13.7 supersedes revisions 13.4-13.6 only where they made external production data or a pre-existing operator campaign mandatory for P7 software-package closure; all accepted executable/runtime/scientific/currentness/resource/locked contracts remain binding
---

# P7 revision 13.7 — software closure with deferred actual-production qualification

## 1. Design correction and verdict

Independent review of R13.6 evidence reveals that the remaining NO-PASS state is caused by **acceptance drift in the review amendments**, not by an unresolved software defect.

The frozen parent V7 workplan states that full long GPU/real-production qualification is deferred to the established final-release phase while functional regression/integration is mandatory during implementation. The base P7 package is more explicit:

- functional acceptance is required before P7 completion;
- real external DFT scientific qualification is required for an **actual production qualification campaign**, but not for routine software regression/implementation closure;
- bounded matched analytic/synthetic reference data are allowed below the external-reference semantic owner for functional tests;
- long target-machine GPU/VRAM/performance/MD qualification is deferred to final release;
- mandatory assembled integration is allowed to execute the real publication/currentness/reference-matching/reduction/locked/persistence owners while substituting expensive numerical work only below those owners.

R13.4-R13.6 incorrectly promoted two external operational prerequisites into P7 software-package closure requirements:

1. an operator pre-existing real campaign with a completed P5 publication;
2. independently generated real DFT results for the final physical-reference request.

Those are legitimate requirements for an **actual production scientific qualification result**, but they are not prerequisites for deciding whether the P7 software implementation is complete and correct.

Therefore P7 receives **PASS for software implementation and functional acceptance** at the frozen executable candidate. Actual production scientific qualification remains a separate, explicit deferred activity and may truthfully stop at `waiting_for_reference` until independent DFT data exist.

## 2. Accepted implementation evidence

The following evidence is sufficient for P7 software closure and remains accepted:

- frozen executable identity: commit `97fa48fc4a8e5be0da8cbcd22ba10248fa37acee`, tree `9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6`, source digest `7772ad5f0329aa1d42f96cf89bbf178252981902e9d4d5468f10ff1312da9ed6`, package version `0.20.242a0`;
- focused and complete affected P7 regression result: `155 passed, 1 skipped`;
- real selected KOKKOS/mliappy MACE child-worker execution on the target RTX 3090 with actual product callback and clean failure semantics;
- real publication/currentness/deployment-parity semantic-owner integration using bounded publication fixtures below the accepted expensive-training boundary;
- real reference-request publication, request/bundle authentication, geometry matching, stress provenance/canonicalization, waiting semantics, and physical reducers using bounded analytic reference fixtures below the external-DFT boundary;
- real relaxation/dynamics/calibration/locked orchestration and no-fallback/no-selection semantics;
- explicit one-shot locked activation mechanics and terminal release record/index behavior;
- immutable resource/currentness/reference/release graph and genuine fresh-process reauthentication;
- R13.6 proof that, against an existing campaign without a current P5 publication, the public production CLI fails closed rather than manufacturing a publication;
- R13.6 proof that absent real DFT input remains `WAITING_FOR_REFERENCE` rather than becoming synthetic success.

No executable source change is authorized or required by this revision.

## 3. Correct acceptance-layer separation

### 3.1 P7 software implementation closure — CLOSED / PASS

P7 implementation is complete when the software can correctly perform the full lifecycle and represent unavailable production evidence truthfully:

```text
real current P1-P5 owners / bounded expensive numerical seams
 -> immutable FinalProductionPublication
 -> real deployment export/artifact/runtime owner
 -> bounded real supported LAMMPS/ML-IAP execution
 -> candidate-independent physical plan
 -> reference request/publication/import authentication
 -> passed/rejected/waiting semantics
 -> PES / relaxation / dynamics reducers
 -> calibration or explicit not_applicable
 -> explicit one-shot locked activation
 -> immutable terminal/release evidence
 -> close/reopen/currentness/restart authentication
```

This layer is now PASS.

### 3.2 Actual campaign end-to-end test — NEXT OPERATIONAL VALIDATION

Run the user's actual campaign from its current legitimate state through the real public lifecycle. It is valid—and desirable—to let that campaign itself create the selected binding, CV result, final production, and P5 publication through normal product operation:

```text
prepare
 -> select-target-size
 -> cross-validate
 -> train-production
 -> freeze FinalProductionPublication
 -> qualification run
```

This is **not** the forbidden R13.6 shortcut. The prohibition applied only to manufacturing a campaign solely to masquerade as pre-existing production evidence for final P7 closure. Once software closure is correctly separated from production qualification, running a genuine campaign through its normal lifecycle is the correct next test.

At `qualification run`:

- deployment parity and every component that does not require missing external data should execute normally;
- if real external DFT is absent, the correct terminal operational state is `waiting_for_reference` with an actionable immutable request;
- do not fabricate reference data merely to continue;
- do not auto-activate locked evidence until the production qualification preconditions are actually satisfied.

The actual campaign run is therefore useful even without DFT: it tests the real P1-P7 orchestration, persistence, training/publication transition, target GPU/runtime path, resource behavior, and truthful external-data boundary.

### 3.3 Final actual-production scientific qualification — DEFERRED

When independent DFT results for the real campaign are later available, resume the same qualification lineage:

```text
waiting_for_reference
 -> import/authenticate independent external DFT bundle
 -> complete physical PES / relaxation / dynamics
 -> calibration as applicable
 -> explicit one-shot locked activation/result
 -> RELEASE_QUALIFIED or REJECTED
 -> fresh-process reauthentication
```

This activity establishes scientific release fitness of that particular frozen publication. It is not required to prove that the P7 implementation exists and behaves correctly.

Long target-machine GPU/VRAM/performance/MD qualification remains part of the established final-release qualification phase, consistent with the parent V7 authority.

## 4. Successor sequencing

Because P7 software implementation is now PASS, `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` is no longer blocked by unavailable external DFT or by the absence of a pre-existing P5 publication in a test workspace.

The storage successor may proceed, subject to its own workplan gates. It must preserve P7 authoritative publication/qualification/reference/locked evidence and currentness semantics exactly as already specified.

A later actual campaign/final-release qualification may discover a genuine executable defect. If so:

1. reopen only the affected software surface;
2. repair under Software Implementation;
3. rerun affected regression/integration;
4. freeze a new candidate;
5. invalidate and repeat only the production qualification evidence plausibly affected by that edit.

A scientific rejection of a real frozen publication is not, by itself, a software defect.

## 5. Closure disposition

P7 is **CLOSED / PASS** for implementation and functional acceptance.

Deferred—not waived—activities:

- full actual campaign execution on the user's real data/workspace;
- independent real external DFT fulfillment for that campaign's exact reference request;
- final locked scientific qualification and terminal `RELEASE_QUALIFIED`/`REJECTED` disposition;
- long target-machine production/resource/performance qualification at the established final-release phase.

These deferred activities must be reported truthfully when run, but their current unavailability does not reopen or block the completed P7 software package.
