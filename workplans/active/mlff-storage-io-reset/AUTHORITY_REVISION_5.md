---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 5
status: planned
amended_date: 2026-08-31
entry_condition: independent PASS for P6 revision 10 and P7 revision 6, followed by binding to the accepted post-P7 commit/tree
---

# Storage/I-O reset package authority — revision 5

This revision supersedes only the predecessor-gate wording in earlier storage authority files. The substantive storage workplan `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` is unchanged.

The package remains **planned, not active for implementation** and opens only after:

```text
CODE-MLFF-TARGET-SIZE-V7-P6 revision 10 -> independent cleanup/cutover PASS
CODE-MLFF-TARGET-SIZE-V7-P7 revision 6 -> independent publication/qualification PASS
```

The exact accepted post-P7 source commit/tree is then bound at implementation intake and becomes the baseline for the S0 artifact-authority census.

P6 revision 10 deliberately keeps transitional storage simple: safe/cache only, frame-cache retained, inactive-run checkpoint-model-cache eviction guarded by current ownership/liveness, and read-only accounting that does not advertise retired mutation policy. P7 revision 6 then adds the final publication/qualification owner surface. Neither predecessor implements this storage reset.

This package continues to own the later cross-owner inventory, transactional retention/cleanup/cache policy, execution/storage leases, storage/scratch/inode admission, immutable deduplication, archive-v2/restore, and I/O optimization.