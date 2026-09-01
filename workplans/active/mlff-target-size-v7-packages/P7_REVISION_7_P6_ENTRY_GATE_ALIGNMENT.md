---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R7
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 7
status: planned
amended_date: 2026-08-31
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-11 cleanup/cutover functional acceptance PASS
precedence: this amendment changes only the P7 predecessor gate; all prior P7 obligations remain binding
---

# P7 revision 7 amendment — P6 revision-11 entry-gate alignment

Independent review of the P6 revision-10 candidate found one remaining cache-owner authorization blocker. Revision 11 closes that narrow issue by retaining/defering all cache-family eviction in P6/P7 rather than manufacturing a current `workspace/runs` cache owner that does not exist in the accepted P3/P5 architecture.

P7 therefore remains planned and must not begin from a revision-10 P6 candidate.

The only change made by this amendment is:

```text
old P7 entry gate: independent P6 revision-10 PASS
new P7 entry gate: independent P6 revision-11 PASS
```

No P7 scientific, publication, deployment, physical-validation, calibration, locked-test, persistence, no-fallback, storage-handoff, testing, or production-qualification requirement changes.

The revision-11 P6 handoff expected by P7 preserves the accepted P5 completed-production owner and supplies a conservative transitional storage surface in which cache eviction remains deferred until the dedicated post-P7 storage reset establishes explicit cross-owner cache/reconstruction/lease authority.
