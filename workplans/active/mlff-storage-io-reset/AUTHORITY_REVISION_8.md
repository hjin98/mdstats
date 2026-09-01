---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 8
status: planned
amended_date: 2026-08-31
entry_condition: independent PASS for P6 revision 13 and P7 revision 9, followed by binding to the accepted post-P7 commit/tree
---

# Storage/I-O reset package authority — revision 8

This revision supersedes only the predecessor-gate wording in earlier storage authority files. The substantive storage workplan `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md` is unchanged.

The package remains **planned, not active for implementation** and opens only after:

```text
CODE-MLFF-TARGET-SIZE-V7-P6 revision 13 -> independent acceptance-closure PASS
CODE-MLFF-TARGET-SIZE-V7-P7 revision 9 -> independent publication/qualification PASS
```

The exact accepted post-P7 source commit/tree is then bound at implementation intake and becomes the baseline for the S0 artifact-authority census.

P6 revision 13 does not alter the conservative transitional storage design accepted in revision 12. It only repairs non-discriminating proxy-proof tests and binds fresh executable acceptance evidence to the exact candidate. Transitional `safe|cache` remains current-owner based, cache-family eviction remains deferred, retired `workspace/runs`/PID/pathname conventions do not authorize destructive cleanup, and safe/cache storage cleanup does not evict the SHA-256 receipt acceleration cache.

P7 revision 9 then adds the final publication/qualification owner surface. Neither predecessor implements this storage reset.

This package continues to own the later cross-owner inventory, transactional retention/cleanup/cache policy, explicit cache/reconstruction ownership, execution/storage leases, storage/scratch/inode admission, immutable deduplication, archive-v2/restore, and I/O optimization.
