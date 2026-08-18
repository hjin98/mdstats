# mdstats 0.20.99a0 patch notes

## OPT-EVAL3: monitor graph and immutable evaluation-view caching

0.20.99a0 implements the third recorded MLFF evaluation optimization stage.

Checkpoint evaluation now supplies stable ordered monitor geometry identities to the
MACE native batching path. Prepared CPU graph shards are model-weight-independent and
are reused across epoch/fold calculators when cutoff, species/head/key policy, dtype,
and dependency identity match. Small graph sets remain in a byte-bounded in-memory
cache; persistent SHA-256-authenticated graph shards are stored under the campaign
internal `evaluation-graphs/` directory for restart/large-monitor reuse. Corrupt or
incompatible graph cache entries are misses and rebuild from the frozen source monitor.
Parallel workers single-flight a shared graph miss.

Graph ownership is cheaper: graph batches are constructed and cached on CPU rather than
moved to the accelerator and cloned back to CPU solely for caching. Single-model MACE
prediction also avoids a redundant device-batch clone; ensemble isolation is retained.

Metric reduction now uses an immutable, read-only evaluation view that pre-extracts
reference energy/force/stress arrays, force offsets, atomic numbers, focus-species
indices, condition IDs, and stress-valid masks once per authenticated monitor/policy.
This removes repeated ASE dictionary/species-mask/condition extraction across
checkpoints without changing metric definitions.

No new TOML setting is required and no evaluation/prediction/checkpoint record schema is
changed. Existing 0.20.98a0 campaigns resume in place. The previously requested
`plot_lta_mixed_alkali_density.py` multi-format trajectory-reader update is included in
this release source tree as well.

Focused qualification covers real MACE graph persistence and exact output reuse,
corruption recovery, geometry-key invalidation, concurrent single-flight construction,
metric-definition equivalence, and the existing OPT-EVAL1/2, true-label replay,
checkpoint, CuEq, and native batching contracts.
