---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R5
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 5
status: planned
amended_date: 2026-08-31
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-9 cleanup/cutover functional acceptance PASS
precedence: this amendment changes only the P7 predecessor gate; all P7 revision-4 obligations remain binding
---

# P7 revision 5 amendment — P6 revision-9 entry-gate alignment

Independent review of the P6 revision-8 implementation found two remaining implementation blockers: reachable transitional storage cleanup still retained retired STOR-era destructive semantics, and final-production acceptance had not yet proved the required two-or-more-seed partial-completion/resume behavior.

P6 revision 9 now owns only those final closure repairs and preserves the accepted revision-8 architecture.

P7 therefore remains planned and **must not begin from a revision-8 P6 candidate**.

The only change made by this amendment is:

```text
old P7 entry gate: independent P6 revision-8 PASS
new P7 entry gate: independent P6 revision-9 PASS
```

No P7 scientific, publication, deployment, physical-validation, calibration, locked-test, persistence, no-fallback, storage-handoff, testing, or production-qualification requirement changes.

The revision-9 P6 handoff expected by P7 includes the already accepted CV-plan-free fresh DATA5/P5-only CV ownership and evidence-authenticated final-production completion, plus a current storage boundary whose supported safe/cache cleanup no longer uses retired STOR lifecycle/path/capability authorization and a demonstrated partial multi-seed final-production restart that executes only missing required runs.