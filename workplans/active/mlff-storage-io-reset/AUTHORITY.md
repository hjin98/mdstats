---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
status: planned
created_date: 2026-08-30
entry_condition: independent PASS for P6 revision 6 and P7 revision 2, followed by binding to the accepted post-P7 commit/tree
---

# Storage/I-O reset package authority

The authoritative workplan for this package is:

- `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN.md`

The package is intentionally **planned, not active for implementation**. It must not begin until:

```text
CODE-MLFF-TARGET-SIZE-V7-P6 revision 6 -> independent cleanup/cutover PASS
CODE-MLFF-TARGET-SIZE-V7-P7 revision 2 -> independent publication/qualification PASS
```

The exact accepted post-P7 source commit/tree is then bound at implementation intake and becomes the baseline for the S0 artifact-authority census.

The companion predecessor amendments are:

- `../mlff-target-size-v7-packages/P6_REVISION_6_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md`
- `../mlff-target-size-v7-packages/P7_REVISION_2_STORAGE_SUCCESSOR_PREPARATION_AMENDMENT.md`

Those amendments do not implement this package. They require P6/P7 to leave clean owner-level root/currentness/completion entry points and to keep stale STOR-era policy out of current scientific semantics.

This storage package owns the later cross-owner retirement/renewal: owner-driven inventory, transactional cleanup/cache policy, storage/execution leases, storage/scratch/inode admission, immutable deduplication, archive-v2/restore, and I/O optimization.
