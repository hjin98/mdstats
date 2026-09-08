---
kind: implementation-workplan-authority
workplan_id: CODE-MLFF-CAMPAIGN-STORAGE-IO-RESET1
protocol_version: 5.10.0
revision: 10
status: active
amended_date: 2026-09-01
current_authority_pointer: true
implementation_intake_commit: 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
implementation_intake_tree: 3efc6297c31c1d233a733ec792f0fba08aea10a1
entry_condition: satisfied by P6 revision 13 independent PASS and P7 revision 13.7 software/functional closure PASS
precedence: this authority supersedes prior mlff-storage-io-reset authority pointers; read the revision-2 substantive workplan and final-closure amendment below as one current snapshot-complete implementation contract; the frozen parent target-size V7 workplan remains the scientific and architectural verdict
---

# Storage/I-O reset package authority — revision 10

The current implementation handoff is the composed pair:

1. `STORAGE_IO_MANAGEMENT_RESET_WORKPLAN_REVISION_2.md` — complete P1-P7 owner-driven storage reset contract and stage sequence;
2. `STORAGE_IO_MANAGEMENT_RESET_FINAL_CLOSURE_AMENDMENT.md` — final independent-review tightening for cross-owner dependency closure, race-safe owner/storage mutation, archive hot-removal boundaries, storage-native control-plane ownership, canonical storage-policy identity, bounded archive verification/restore, hardlink metadata safety, and interrupted-operation terminality.

The amendment has precedence only where it explicitly tightens or narrows revision 2. All other revision-2 obligations remain binding. These two files are the supplied current authority; earlier storage workplans and authority revisions are historical provenance only and are not required for implementation.

The package remains **active / implementation-ready** at merged intake commit:

```text
commit 45b85e5dfb98bed4abbfee47cdb020bb2bd401c8
tree   3efc6297c31c1d233a733ec792f0fba08aea10a1
```

The final review accepted the global owner-driven architecture and found no parent-science redesign requirement. It closed the remaining storage-specific gaps with these additional binding invariants:

- retention is computed across the transitive dependency closure of all current/restartable semantic owners, not independently per nominal owner;
- current P7 publication/release semantics continue to pin the exact P5 representative checkpoint bytes after active P7 attempt references have ended;
- a destructive or representation-changing storage action must be race-safe against the semantic owner's concurrent publication/use, not merely preceded by a snapshot currentness check;
- current P1-P7 resolvers are not given transparent archive fallbacks solely to reclaim bytes; hot removal is limited to owner-declared cold-replaceable state with no current/restart hot dependency;
- archive catalogs, restore journals, audits, and operation-serialization state have explicit storage ownership and never become scientific currentness authority;
- one canonical resolved operational storage-policy identity is bound into every consequential plan;
- archive verification/restore bounds member paths, types, counts, expanded bytes, and per-member streaming before dangerous writes;
- hardlink deduplication requires owner-certified metadata compatibility and forbids in-place mutation of shared inode content/material metadata;
- partial cleanup/dedup/archive/restore execution has truthful explicit terminality and idempotent recovery; partial work cannot masquerade as completion;
- the real P5 immutable-object-before-pointer publication race and the post-terminal P7 -> P5 dependency are mandatory acceptance cases.

No target-size, CV, publication, qualification, calibration, locked-test, or release-science decision is reopened. Full external-DFT scientific qualification, long GPU production qualification, and environment-specific HPC storage qualification remain deferred under the frozen parent/P7 authority and are not entry or routine implementation gates for this package.

Implementation proceeds through S0 -> S6 under the composed current handoff. Reopen Design only on the evidence triggers stated in the two current authority files.