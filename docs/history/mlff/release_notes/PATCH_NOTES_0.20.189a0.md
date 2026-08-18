# mdstats 0.20.189a0

## CUEQ-PHASE1 training-only qualification control plane

- Add `CueqPhase1Policy.v1`, trajectory, paired-assessment, and gate-level qualification schemas.
- Freeze e3nn as the source/DATA6/pseudolabel/source-evaluation authority while permitting only the EXTRACT1-derived training realization to vary to pure CuEq.
- Require exact paired protocol identity across starting checkpoint, DATA8, seed/order/splits, precision, objective/LR/stopping/replay policy, and validation/EVAL2 protocols.
- Require a 5-10 epoch short pair (default 8) plus at least one representative full pair before CuEq training can be authorized.
- Compare existing scientific decisions rather than final checkpoint bytes; record target/replay metric deltas and wall/update/VRAM telemetry without introducing or relaxing scientific tolerances.
- Add `tools/qualify_mlff_cueq_phase1.py` for pair, qualification, and fail-closed deferred evidence generation.
- Export the CUEQ-DEP1 and CUEQ-PHASE1 public authority symbols through the top-level `mdstats.__all__` contract.
- Advance FINAL-GPU1 preflight to v3 so the final workstation handoff includes CUEQ-PHASE1 schema/state.
- Advance canonical MLFF architecture to revision 56 and dependency-graph schema 38.

No GPU qualification is performed in this release. Positive CUEQ-PHASE1 paired short/full evidence remains scheduled for FINAL-GPU1.
