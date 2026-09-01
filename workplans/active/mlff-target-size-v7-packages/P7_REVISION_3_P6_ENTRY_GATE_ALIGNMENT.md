---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R3
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 3
status: planned
amended_date: 2026-08-30
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-7 cleanup/cutover functional acceptance PASS
precedence: this amendment changes only the P6 entry gate; all P7 revision-2 behavior and obligations remain binding
---

# P7 revision 3 — align entry gate with final P6 revision 7

P6 revision 7 supersedes revision 6 as the current P6 cleanup/cutover authority. P7 therefore remains blocked until **P6 revision 7** receives independent cleanup/cutover PASS.

No P7 scientific, publication, qualification, persistence, storage-handoff, testing, or production-qualification behavior changes in this amendment. `P7_POST_PRODUCTION_QUALIFICATION_REPLACEMENT.md` plus `P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md` remain fully binding.

The only corrected sequence is:

```text
P6 revision 7 independent PASS
 -> P7 revision 3 implementation authority opens
 -> P7 independent PASS
 -> post-P7 storage/I-O reset entry gate opens
```
