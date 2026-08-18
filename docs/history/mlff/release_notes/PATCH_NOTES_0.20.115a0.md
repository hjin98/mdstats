# mdstats 0.20.115a0 patch notes

- Implement MLFF STOR4 manual retention tiers: `safe`, `cache`, `recompute`, `compact`, and `archive`.
- Every manual cleanup invocation first emits/writes a dry-run capability plan. `recompute` and `compact` require explicit `--apply`; `archive --apply` fails closed until STOR5 exists.
- `recompute` may remove authenticated scientific prediction/DATA6 caches only after authoritative evaluation and only while configured reconstruction inputs remain available.
- `compact` requires full verification, a protocol freeze, and a protected production model; it may remove nonselected evaluation capsules, per-run model copies, and hot DATA7/DATA8 materializations while retaining selected raw checkpoints, production models, logs, and provenance.
- Extend cleanup audit events to carry intentional manual capability loss while STOR3 automatic events remain zero-loss.
- Storage accounting now names the qualified STOR4 manual tier for cache/scientific-cache/capsule/materialization families.
- STOR5 immutable deduplication/cold archival is the next gate.
