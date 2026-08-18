# mdstats 0.20.107a0 patch notes

## MLFF EVAL-MF2

This release completes the second nested multi-fidelity checkpoint-evaluation gate.

- Add conservative source/temporal-block survivor guards. The nominal one-third survivor fraction is a resource target rather than a hard cap; candidates statistically unresolved from the cutoff are retained using the frozen paired 2%-plus-2-SE rule.
- Preserve plausible true-label replay-retaining checkpoints through a minimum-finalist reserve so target-only ranking cannot prematurely eliminate all replay-compatible candidates.
- Expand rather than force-prune when common-candidate rankings invert substantially between partial rounds.
- Add normative per-epoch JSON evaluation reports plus CSV and Markdown derivatives combining MACE training history, every independent evaluation round, replay degradation, survivor reasons, full-fidelity admissibility, and selected status.
- Qualify the default 10% -> 33% -> 100% strategy against a representative 30-checkpoint exhaustive reference. The qualified case selects the same epoch and uses 10.89 versus 30 full-checkpoint-equivalent candidate inference (63.7% reduction in that case).
- Re-run supplied MACE 0.3.16 checkpoint-restoration and monitor-graph/cache regressions.
- Make `checkpoint_strategy = "multi_fidelity"` the generated campaign default. Existing configs that omit the field retain `bounded` behavior for restart compatibility; `bounded` and `exhaustive` remain explicit modes.
- Keep partial evidence non-authoritative and preserve existing checkpoint-retention/deletion authority for the later STOR gates.

The MLFF dependency graph advances to architecture revision 26. Frozen DATA8/training scientific identities remain unchanged. `PREC1` is the next implementation gate.
