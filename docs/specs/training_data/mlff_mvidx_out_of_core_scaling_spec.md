# MVIDX multi-billion-edge out-of-core scaling hardening

Implemented in mdstats 0.20.238a0 under MLFF architecture revision 103 and dependency schema 83. This is exact-equivalence execution/storage maintenance; `FINAL-GPU1` remains the next scientific release gate.

For campaign execution, an MVIDX family whose inverse uint32 edge payload is at least 8 MiB is eligible for file-backed inversion. Candidate counts are accumulated in bounded chunks. Source witness rows are then partitioned into ascending row chunks, each chunk is transposed with the same deterministic SciPy counting transpose, and candidate columns are appended into their preallocated final ranges. Since row chunks are strictly ascending and each local CSC column is sorted, the resulting candidate-to-witness arrays are byte-identical to the full in-memory transpose.

The final inverse edge payload is an NPY memmap. PARCORE1 admission charges bounded transpose scratch and O(C) counters rather than the complete file-backed edge payload. The explicit campaign RAM budget remains fail-closed. Whole NPY-backed arrays may be hard-linked into the native MVIDX record on the same filesystem. Campaign persistence reloads the durable native record before removing transient build files.

The campaign SHALL preflight free disk space for the exact inverse edge payload plus at least 5% or 1 GiB safety headroom, whichever is larger. Missing space fails before inversion. Large-row validation is chunked to bounded temporary memory. Progress uses the common MLFF grammar with `HH:MM:SS` elapsed/ETA.

Scientific schemas, edge membership, index dtypes, canonical ordering, MVIDX content digests, target selection/repair/qualification, MPA-0/MH-1 semantics, and GPU authority are unchanged.
