# MLFF architecture revision 98 - REPAIR-PAR1

Revision 98 completes the exact-equivalence `REPAIR-PAR1` performance gate.

- Preserves sequential repair iteration, objective/tie authority, accepted/rejected trace, terminal order, and winner application.
- Fuses removal unique-coverage and representative-loss scans.
- Vectorizes replacement-frontier sparse scoring with canonical CSR gathers and thread-private epoch/stamp witness membership.
- Adds an execution-only O(1) candidate-rank inverse map for future displacement lookup.
- Uses PARCORE1 for immutable proposal tasks only when a sparse-work estimate exceeds the measured threading break-even point; small batches remain serial.
- Reduces arbitrary task completion in historical removal-shortlist order and recomputes the winning representative contribution with historical scalar arithmetic before persistence.
- Retains the scalar proposal path as the exact qualification oracle.
- Advances the optimization program to `MVQUAL-PAR1`.
