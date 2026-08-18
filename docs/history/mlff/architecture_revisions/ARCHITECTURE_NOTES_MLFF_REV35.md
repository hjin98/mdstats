# MLFF Architecture Revision 35 - MLCV-STOP1 implementation

`mdstats 0.20.133a0` implements MLCV-STOP1, the third gate of the conventional-CV redesign accepted in revision 32.

The lightweight monitor is now strictly training-control evidence. New adaptive-stop policy schema v2 keeps the default 24 meV/A target-success and 36 meV/A replay-exhaustion margins, but neither the target nor replay 30 meV/A full-validation ceiling can disqualify a lightweight epoch. Every completed checkpoint with finite target/replay monitor metrics remains rankable for the later MLCV-RANK1 gate.

A three-completed-epoch floor now protects against premature adaptive termination; the hard maximum epoch budget remains independent. Foundation replay feasibility is evaluated once on complete independent TRUE_DFT `R_full` before epoch 0, frozen with replay artifact identity, and not paid again on exact restart. Historical adaptive-stop v1 policies retain their original digest and historical semantics so old campaign identity is not silently rewritten.

This gate does not yet implement the new run-local top-five record, full checkpoint selection, CV aggregation, or final-only production competition. Those remain MLCV-RANK1 through MLCV-FINAL1.
