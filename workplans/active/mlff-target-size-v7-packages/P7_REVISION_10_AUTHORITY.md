---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 10
status: planned
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-13 independent acceptance-closure PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 10 — authoritative composed workplan

The frozen parent `MLFF_TARGET_SIZE_TRAINING_PRIORITY_EVALUATION_LADDER_ARCH_RESET_WORKPLAN.md` remains the sole scientific and architectural verdict. P7 revision 10 changes no frozen parent requirement.

Read the following as one current P7 implementation authority, in precedence order:

1. frozen parent workplan — controlling scientific/architectural verdict;
2. accepted P1-P6 executable and closure authorities, culminating in P6 revision-13 completion authority;
3. `P7_REVISION_10_IMPLEMENTATION_REALIGNMENT_AMENDMENT.md` — current implementation-state reconciliation and explicit overrides;
4. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base V7-native qualification design, except where revision 10 explicitly supersedes stale predecessor assumptions;
5. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — storage-neutral successor handoff, interpreted through revision 10's preservation of accepted P6 cache/safe-cleanup ownership;
6. revisions 3-9 — historical predecessor-entry alignment records only.

## Current predecessor baseline

P7 is based on the independently accepted P6 revision-13 state:

- accepted executable P1-P6 commit: `f55d59b28c9db890dcb6a3c167a067ef5f37e8a2`;
- accepted executable P1-P6 tree: `e9a6d5f9d1a798f07dab88bd56dafcc73fe0e491`;
- frozen P6 evidence commit: `82371ecdab5f981255d0853a11477596be2623d3`;
- P6 documentary acceptance/closure branch head: `fe78ebf238147f0766c150ca8985fe6dc152d321`.

The executable commit/tree, evidence commit, and documentary closure head are distinct identities and must not be conflated.

## Revision-10 controlling corrections

Revision 10 supersedes older P7 assumptions in the following material respects:

- P7 does **not** create a second `FinalProductionPublication`; it consumes/authenticates the existing accepted final-publication owner implemented by P5/P6.
- P7 does **not** own fresh production, CV, target-size selection, checkpoint/seed/member selection, or publication membership.
- P7 does **not** redesign the accepted P6 current-cache or safe-cleanup owners and does not implement the successor storage reset.
- P7 qualification evidence binds the exact P7 executable candidate/tree, exact frozen publication, qualification spec/policy, target-machine environment, runtime/deployment artifacts, protected/reference evidence, and terminal results.
- P6 bounded proxy/device evidence proves development functionality only and cannot satisfy final target-machine/release qualification.
- long-running qualification must use authenticated resumable attempt identity and protect exact referenced artifacts without creating a new global storage/lease authority.
- source/runtime changes after evidence collection stale affected executable evidence and require affected regression/reclosure/requalification according to the revision-10 invalidation matrix.
- downstream physical/calibration/locked evidence remains strictly non-selective: failure rejects/blocks the exact product and cannot trigger fallback or retuning through P1-P6.

All non-conflicting base-P7 scientific obligations remain binding, including deployment parity, candidate-independent physical validation, relaxation/dynamics, calibration when applicable, explicit one-shot locked activation, immutable terminal qualification evidence, real-owner acceptance, and final target-machine qualification.

## Status

P7 revision 10 is **planned**, not PASS. Independent P7 acceptance is required after implementation, regression/integration closure, and final target-machine qualification on one frozen P7 executable candidate.

Only after independent P7 PASS may the accepted post-P7 executable commit/tree become the baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.