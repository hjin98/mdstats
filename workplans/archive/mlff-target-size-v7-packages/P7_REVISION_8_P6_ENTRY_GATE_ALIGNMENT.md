---
kind: implementation-workplan-amendment
workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7-R8
parent_workplan_id: CODE-MLFF-TARGET-SIZE-V7-P7
protocol_version: 5.8.0
revision: 8
status: planned
amended_date: 2026-08-31
entry_condition: CODE-MLFF-TARGET-SIZE-V7-P6 revision-12 cleanup/cutover functional acceptance PASS
precedence: this amendment changes only the P7 predecessor gate; all prior P7 obligations remain binding
---

# P7 revision 8 amendment — P6 revision-12 entry-gate alignment

Independent review of the P6 revision-11 candidate accepted the revision-11 cache-family/public-surface correction but found a remaining safe-cleanup owner blocker: the current safe path still used retired `workspace/runs`/`active_process.json`/PID/`obsolete-runtime-*` conventions to authorize deletion and also pruned the SHA-256 receipt acceleration cache.

P6 revision 12 owns that final cleanup-owner closure. P7 therefore remains planned and must not begin from the revision-11 candidate.

The only change made by this amendment is:

```text
old P7 entry gate: independent P6 revision-11 PASS
new P7 entry gate: independent P6 revision-12 PASS
```

No P7 scientific, publication, deployment, physical-validation, calibration, locked-test, persistence, no-fallback, storage-handoff, testing, or production-qualification requirement changes.

The P6 revision-12 handoff expected by P7 preserves accepted P5 final-production ownership/restart behavior and supplies a conservative transitional storage surface in which destructive actions are current-owner based and cache eviction remains deferred to the dedicated post-P7 storage reset.