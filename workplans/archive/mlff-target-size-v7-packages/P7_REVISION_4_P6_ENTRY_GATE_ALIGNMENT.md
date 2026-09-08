---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R4
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 4
status: planned
amended_date: 2026-08-31
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-8 cleanup/cutover functional acceptance PASS
precedence: this amendment changes only the P7 predecessor gate; all P7 revision-3 obligations remain binding
---

# P7 revision 4 amendment — P6 revision-8 entry-gate alignment

Independent review found P6 revision 7 did not satisfy its final cleanup/cutover contract. P6 revision 8 now owns the required repair of pre-selection DATA5 CV ownership, final-production completion evidence, transitional storage quarantine, and independent compatibility/restart qualification.

P7 therefore remains planned and **must not begin from a revision-7 P6 candidate**.

The only change made by this amendment is:

```text
old P7 entry gate: independent P6 revision-7 PASS
new P7 entry gate: independent P6 revision-8 PASS
```

No P7 scientific, publication, deployment, physical-validation, calibration, locked-test, persistence, no-fallback, storage-handoff, testing, or production-qualification requirement changes.

The revision-8 P6 handoff expected by P7 includes a fresh current DATA5 with no pre-selection CV plans, one P5 selected-only CV owner, an evidence-authenticated completed final-production projection distinct from plan-only state, and clean current owner entry points not dependent on retired STOR lifecycle semantics.