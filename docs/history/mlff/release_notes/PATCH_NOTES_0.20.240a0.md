# mdstats 0.20.240a0 - MVIDX bounded-queue backpressure hotfix

This maintenance release fixes a production MVIDX/PARCORE1 integration defect exposed by a 165-family exact-neighborhood domain at 28 inverse workers. The ready queue is intentionally bounded to 56 tasks; MVIDX previously eager-submitted all family inversions and could fail with `PARCORE1 ready queue is full` before entering its completion-drain phase.

MVIDX now uses deterministic producer-side backpressure: submit while ready capacity exists, drain completed tasks, then refill. Queue bounds, RAM admission, canonical sparse-index authority, out-of-core inverse storage, and architecture revision 103 remain unchanged. `FINAL-GPU1` remains next.
