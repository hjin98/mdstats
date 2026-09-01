---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 4
status: planned
amended_date: 2026-08-31
entry_condition: independent PASS for P6 revision 9 and P7 revision 5, followed by binding to the accepted post-P7 commit/tree
---

# Storage/I-O reset package authority — revision 4

This revision supersedes only the predecessor-gate wording in earlier storage authority files. The substantive storage workplan `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` is unchanged.

The package remains **planned, not active for implementation** and opens only after:

```text
CODE-MLFF-TARGET-SIZE-V7-P6 revision 9 -> independent cleanup/cutover PASS
CODE-MLFF-TARGET-SIZE-V7-P7 revision 5 -> independent publication/qualification PASS
```

The exact accepted post-P7 source commit/tree is then bound at implementation intake and becomes the baseline for the S0 artifact-authority census.

P6 revision 9 is intentionally limited to conservative transitional storage behavior: supported safe/cache cleanup must use current owner semantics and must not retain retired STOR lifecycle/path/capability authorization. P7 revision 5 then adds the final publication/qualification owner surface. Neither predecessor implements this storage reset.

This package continues to own the later cross-owner inventory, transactional retention/cleanup/cache policy, execution/storage leases, storage/scratch/inode admission, immutable deduplication, archive-v2/restore, and I/O optimization.