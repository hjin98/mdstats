# MLFF architecture revision 104 - MVSEL2 forward/lazy chain

Revision 104 makes MVSEL2, MVSTATE2, and REPAIR2 the current execution chain for new multi-view target-data campaign records. It preserves the frozen MVSEL1/REPAIR1 scientific policy while replacing complete eager candidate marginal state and inverse propagation with exact candidate-forward scans, certified lazy representative bounds, compact authenticated continuation state, and forward-only repair mutation.

MVIDX1 remains the exact persisted graph authority and retains both orientations for legacy consumers. V2 opens a candidate-forward runtime view without mapping inverse witness arrays. MVSEL1, MVSTATE-REUSE1, and REPAIR1 schemas remain readable historical identities and are never silently interpreted as v2.

The accepted production evidence covers the 36,408-candidate, 165-family, 9,505,021,522-edge graph, a 69.06-fold conservative full-order selector projection, zero sampled Phase-B fallback, compact checkpoint recovery, forward-only production-prefix repair, independent DATA2B/MVIDX qualification, and clean wheel installation. GPU qualification remains deferred.
