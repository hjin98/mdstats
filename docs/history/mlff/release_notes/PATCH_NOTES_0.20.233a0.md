# mdstats 0.20.233a0 - AUDIT-EVAL-PERF1

- Complete MLFF architecture revision 100 / AUDIT-EVAL-PERF1.
- Cache reconstructible EVAL2 species/composition/focus/block indexing metadata across repeated checkpoint reductions.
- Preallocate EVAL2 force-tail storage and replace the 2,000-replicate Python paired-bootstrap loop with deterministic, memory-bounded vector batches.
- Share the FOUNDATION-AUDIT1 DATA3 frame index and per-run species membership across domains; reuse force-square work and batch tail quantiles.
- Preserve exact persisted metric/bootstrap/audit records on qualification fixtures and introduce no additional model inference.
- Same-host evidence: ~1.92x repeated EVAL2 target reduction, ~3.36x paired bootstrap, and ~1.06x Foundation Audit reduction on the available no-inference fixture.
- Keep MACE-MPA-0 medium as active qualification while retaining the same CPU contract for MACE-MH-1.
- Advance the next optimization gate to REPLAY-PERF1.
