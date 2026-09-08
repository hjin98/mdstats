---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 2
status: planned
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-6 cleanup/cutover functional acceptance PASS
successor_storage_workplan: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
---

# P7 revision 2 — authoritative composed workplan

Read the following as one current P7 authority:

1. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` — base V7-native publication, deployment, physical, calibration, and locked-test qualification design.
2. `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` — additional requirement that P7 persistence/runtime owners expose clean canonical root/currentness/completion entry points and remain independent of the stale STOR1-STOR5 semantic policy so the storage subsystem can be renewed only after P7 passes.

Revision 2 overrides the base only where explicit. All base P7 scientific, statistical, no-fallback, external-reference, locked-test, persistence, testing, and production-qualification obligations remain binding.

P7 remains `planned` until P6 revision-6 cleanup/cutover receives independent PASS. After P7 receives independent PASS, the accepted P7 candidate becomes the entry baseline for `CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1`.
