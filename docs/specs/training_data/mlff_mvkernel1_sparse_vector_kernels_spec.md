# MVKERNEL1 exact sparse selector/qualification vector-kernel specification

**Release:** `mdstats 0.20.230a0`  
**Architecture:** revision 97 / dependency-graph schema 77  
**Status:** implemented exact-equivalence performance hardening

## Frozen contract

1. MVSEL sequential rank decisions, tie hierarchy, FP64 gain authority, hard 0.95 coverage predicates, stable UID final tie-break, and persisted scientific schemas remain unchanged.
2. `_select_and_update_reference` remains the scalar MVSEL oracle. The optimized state SHALL compare exactly after each qualification rank, including coverage/representative gains, covered masks, multiplicity, hard gains, obligation counts, unit counts, coverage mass, and pending required-obligation count.
3. Ragged CSR gathers SHALL preserve the supplied row order and each CSR row's canonical edge order. Oversized batching may split only between complete rows.
4. Per-family and domain-total gain updates MAY share one gathered edge stream, but each authority array SHALL receive its own ordered `np.add.at` operation so arithmetic order is unchanged.
5. MVIDX selected-subset coverage and hard-obligation counts MAY use vectorized CSR gather and `bincount`; returned masks/counts must equal the scalar candidate-row traversal exactly.
6. MVQUAL MVIDX telemetry MAY use CSR gather, `bincount`, indexed weights, and one-time per-domain DATA2A provenance coding. The retained scalar telemetry reference SHALL produce the same serialized telemetry dictionary.
7. Execution-kernel choices and temporary batch sizes are not scientific policy and SHALL NOT enter selection/qualification content digests.
8. No parallel rank selection, approximate sparse reduction, GPU graph authority, or change to independent TARGET-DATA2B rescoring is authorized.

## Qualification

The release SHALL demonstrate: exact MVSEL state after every tested rank; byte-identical optimized/reference selection plans; exact MVQUAL telemetry against the scalar reference; unchanged full MVQUAL plan digest against the predecessor release; and measurable throughput improvement on sparse selector and qualification telemetry fixtures. The 16,384-selection stress fixture SHALL complete with the frozen selection digest.

The next gate is `REPAIR-PAR1`.
