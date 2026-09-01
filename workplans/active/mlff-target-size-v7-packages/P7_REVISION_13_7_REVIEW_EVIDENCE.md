---
kind: review-evidence
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R13.7
protocol_version: 5.8.0
reviewed_evidence_head: b82e122decd528450c616e571a47b8ed3d058e4c
frozen_executable_commit: 97fa48fc4a8e5be0da8cbcd22ba10248fa37acee
frozen_executable_tree: 9e4be0fc9d23c4036413a2ced86dc19d98ad9ed6
review_verdict: PASS
review_date: 2026-09-01
---

# P7 revision 13.7 — independent closure review evidence

## Verdict

**PASS for P7 software implementation and functional acceptance.**

No executable-source blocker remains. The R13.6 evidence correctly demonstrates that missing production publication/reference inputs are represented as unavailable/waiting rather than fabricated success. Those remaining dependencies are external production-qualification inputs, not software-implementation defects.

## Review correction

The preceding R13.4-R13.6 reviews over-constrained package closure by requiring an operator pre-existing completed production publication and independent external DFT results before P7 itself could PASS.

That requirement conflicts with the base P7 acceptance disposition, which explicitly separates:

- mandatory functional acceptance and assembled integration for P7 software completion;
- actual-production scientific qualification using real external DFT;
- long target-machine GPU/resource/performance qualification deferred to the established final-release phase.

Therefore R13.7 restores the governing package/parent distinction rather than weakening scientific requirements.

## Accepted evidence

1. Frozen candidate identity is exact and internally consistent: `97fa48fc...`, tree `9e4be0fc...`, source digest `7772ad5f...`, package `0.20.242a0`.
2. Complete affected regression: `155 passed, 1 skipped`.
3. Selected KOKKOS/mliappy MACE runtime executed successfully on RTX 3090 through the actual product callback.
4. Publication/currentness/deployment/reference/reduction/locked/persistence semantic owners are exercised by assembled integration; expensive training/DFT work is substituted only below accepted boundaries.
5. Missing external references produce `waiting_for_reference`; missing current publication produces a blocking public CLI result rather than synthetic state.
6. Locked activation, terminal record/release index, resource lineage, exact PBC/cell evidence, stress provenance, no-fallback semantics, and fresh-process reauthentication have all been exercised and accepted.

## Deferred production qualification

The following remain required when qualifying a real frozen publication, but are not P7 software-package blockers:

- run the actual user campaign through normal P1-P7 operation;
- obtain independent DFT for its exact frozen reference request;
- resume physical qualification and explicitly activate the locked test only when preconditions are satisfied;
- record `RELEASE_QUALIFIED` or `REJECTED` for that publication;
- perform final target-machine production/resource/performance qualification at the established final-release phase.

A real campaign may correctly stop at `waiting_for_reference` until those data exist.

## Successor disposition

`CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1` is unblocked by P7 implementation closure. Its implementation must preserve the now-accepted P7 authoritative publication/qualification/reference/locked persistence and currentness semantics.
