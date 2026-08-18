# mdstats 0.20.211a0

REPLAY-UNIFY1B implements source-true-label cache and lazy materialization for the new single replay-source architecture.

- adds order-independent `ReplayTrueLabelCache` geometry-to-source-label authority;
- adds authenticated train/monitor `ReplayTrueLabelViewArtifact` receipts;
- lazily materializes only requested true-label views using MACE `REF_*` transport fields;
- generates missing train+monitor views in one bounded-memory source pass;
- validates cache hits without reopening the replay source;
- reconstructs deleted views without pseudo-label inference;
- fails closed on missing requested true labels and same-geometry/different-label cache masquerading;
- removes an accidental per-frame whole-corpus digest recomputation hot path;
- validates the supplied 12,000-frame LTA source as 10,000/2,000 under the default 5:1 split;
- keeps historical replay execution and true-label APIs unchanged until REPLAY-UNIFY1D.
