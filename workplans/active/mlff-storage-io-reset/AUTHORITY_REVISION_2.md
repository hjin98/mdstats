---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 2
status: planned
amended_date: 2026-08-30
entry_condition: independent PASS for P6 revision 7 and P7 revision 3, followed by binding to the accepted post-P7 commit/tree
---

# Storage/I-O reset package authority — revision 2

This revision supersedes the predecessor-gate wording in `AUTHORITY.md` only. The substantive storage workplan remains `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` unchanged.

The package remains **planned, not active for implementation** and opens only after:

```text
CODE-MLFF-TARGET-SIZE-V7-P6 revision 7 -> independent cleanup/cutover PASS
CODE-MLFF-TARGET-SIZE-V7-P7 revision 3 -> independent publication/qualification PASS
```

The exact accepted post-P7 source commit/tree is then bound at implementation intake and becomes the baseline for the S0 artifact-authority census.

P6 revision 7 and P7 revision 3 prepare owner-level root/currentness/completion entry points only. They do not implement the storage reset. The substantive post-P7 package continues to own cross-owner inventory, transactional retention/cleanup/cache policy, storage/execution leases, storage/scratch/inode admission, immutable deduplication, archive-v2/restore, and I/O optimization.
