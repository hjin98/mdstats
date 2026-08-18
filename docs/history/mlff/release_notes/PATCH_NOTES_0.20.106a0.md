# mdstats 0.20.106a0 patch notes

## MLFF EVAL-MF1 nested multi-fidelity checkpoint evaluation

This release implements the first gate of the post-0.20.105 MLFF evaluation/precision/storage roadmap.

### New evaluation strategy

`[evaluation].checkpoint_strategy = "multi_fidelity"` enables deterministic successive-halving checkpoint evaluation while the generated campaign configuration continues to default to the established `"bounded"` strategy until EVAL-MF2 qualification is complete.

The default EVAL-MF1 ladder is `10% -> 33% -> 100%`. The same nominal fraction is applied independently to target and true-label replay monitors. Every saved checkpoint enters round 1. Non-final round metrics are screening evidence only; only final-round checkpoints evaluated against complete authoritative monitor data publish ordinary checkpoint-evaluation records used for scientific selection.

### Deterministic nested monitor ladders

Monitor subset ordering is label-independent and balances available condition/source/trajectory metadata with deterministic temporal spreading. Round subsets are immutable prefixes, so later rounds extend earlier work rather than resample unrelated configurations.

### Incremental prediction reuse

OPT-EVAL2 prediction artifacts now support authenticated coverage composition. Each newly added round delta is stored as an ordinary immutable prediction shard. Later cumulative rounds reuse valid shards exactly and infer only missing geometry identities. Corrupt/missing shards are rejected and selectively recomputed.

The implementation reuses the existing OPT-EVAL3 monitor graph/view cache and OPT-EVAL4 staged prepare/infer/finalize pipeline.

### Evidence and restart semantics

Partial round records carry explicit fidelity and `screening_partial` evidence identity. Survivor records persist deterministic rank, primary metric input, replay-degradation input, retained/screened-out outcome, and reason code for every checkpoint. Only the 100% round may publish `authoritative_full` evidence.

Checkpoint-retention authority is intentionally unchanged in this gate. A checkpoint screened out by partial evidence is not treated as a fully evaluated scientific rejection and is not newly eligible for deletion. Storage compaction remains reserved for the later STOR gates.

### Compatibility

The existing `bounded` and `exhaustive` evaluation strategies remain available. Frozen DATA8/training scientific identities are unchanged. The MLFF dependency graph advances to architecture revision 25; EVAL-MF2 is the next implementation gate.
