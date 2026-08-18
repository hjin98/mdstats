# MLFF Architecture Revision 95

**Gate:** `MVIDX-REUSE1`  
**Release:** `mdstats 0.20.228a0`  
**Date:** 2026-08-17

Revision 95 closes the residual cached-MVIDX CPU hotspot after NEIGHBOR1 removed duplicate geometry. Required-family inverse adjacency builds and the hard-obligation inversion are independent immutable tasks scheduled through the PARCORE1 deterministic queue under a bounded stage resource scope. Each individual CSR-to-CSC operation remains a deterministic compiled SciPy counting transpose with one native execution lane; canonical family ordering is restored after task completion.

Profiling also identified the historical row-by-row strict-order validator as the dominant remaining Python overhead. It is replaced by one vectorized adjacent-index predicate with CSR-row-boundary masking, which is mathematically identical to validating every row independently.

An experimental Python-threaded intra-family degree/prefix/range-fill transpose was exact but slower than the compiled sparse kernel on the frozen authority and was not promoted. This revision changes execution only: the MVIDX scientific digest, inverse arrays, obligations, TARGET-DATA2 semantics, MACE-MPA-0/MACE-MH-1 model semantics, and GPU authority remain unchanged.

`COVREF-PAR1` is the next optimization gate.
