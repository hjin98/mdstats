# MVKERNEL1 exact sparse selector/qualification vector-kernel specification

**Release:** `mdstats 0.20.241a0`
**Architecture:** revision 97 / dependency-graph schema 77
**Status:** implemented exact-equivalence performance hardening; production-density scaling maintenance accepted in `0.20.241a0`

## Frozen contract

1. MVSEL sequential rank decisions, tie hierarchy, FP64 gain authority, hard 0.95 coverage predicates, stable UID final tie-break, and persisted scientific schemas remain unchanged.
2. `_select_and_update_reference` remains the scalar MVSEL oracle. The optimized state SHALL compare exactly after each qualification rank, including coverage/representative gains, covered masks, multiplicity, hard gains, obligation counts, unit counts, coverage mass, and pending required-obligation count.
3. Ragged CSR gathers SHALL preserve the supplied row order and each CSR row's canonical edge order. Oversized batching may split only between complete rows.
4. Per-family and domain-total gain updates MAY share one gathered edge stream. Sparse families use ordered `np.add.at`. A family whose complete candidate/witness rectangle is at least 98% populated MAY instead traverse every witness in canonical order and apply the same scalar add once to each candidate through sorted contiguous runs. Both realizations SHALL be bit-exact to the scalar oracle.
5. MVIDX selected-subset coverage and hard-obligation counts MAY use vectorized CSR gather and `bincount`; returned masks/counts must equal the scalar candidate-row traversal exactly.
6. MVQUAL MVIDX telemetry MAY use CSR gather, `bincount`, indexed weights, and one-time per-domain DATA2A provenance coding. The retained scalar telemetry reference SHALL produce the same serialized telemetry dictionary.
7. Execution-kernel choices and temporary batch sizes are not scientific policy and SHALL NOT enter selection/qualification content digests.
8. No parallel rank selection, approximate sparse reduction, GPU graph authority, or change to independent TARGET-DATA2B rescoring is authorized.
9. Selector initialization SHALL reduce every candidate CSR row independently in FP64. Indexed weight gathers SHALL be split only between complete rows and SHALL target at most 512 MiB of FP64 temporary storage; chunk boundaries cannot enter scientific identity.
10. Numerical-guard bookkeeping SHALL retain at most one boolean touched flag per candidate. It SHALL NOT retain or concatenate the complete processed edge stream.
11. Campaign progress SHALL report initialization, selection, and long per-rank family updates at the resolved `[performance].progress_interval_seconds` cadence. Progress and ETA are observational and cannot affect rank order or state.
12. CPU rank parallelism remains unauthorized. The production scatter is memory-bandwidth bound, independent two-/four-thread trials improved only about 1.11x/1.08x, and sequential rank dependence prevents rank concurrency.

## Qualification

The release SHALL demonstrate: exact MVSEL state after every tested rank; byte-identical optimized/reference selection plans; exact MVQUAL telemetry against the scalar reference; unchanged full MVQUAL plan digest against the predecessor release; and measurable throughput improvement on sparse selector and qualification telemetry fixtures. The 16,384-selection stress fixture SHALL complete with the frozen selection digest.

The `0.20.241a0` production-density maintenance qualification uses the restored MPA-0 domain with 36,408 candidates, 165 families, and 9,505,021,522 edges, and stops after rank 0. Relative to the pre-change scoped profile, initialization improves from about 80.3 s to 55.9 s and rank-0 update from about 239.9 s to 49.7 s. Peak RSS improves from about 51.5 GiB to 19.2 GiB; post-rank anonymous RSS is about 0.5 GiB and the remaining resident footprint is reclaimable mmap file cache. Exact chunk-boundary, cancellation, dense-run/scatter, per-rank state-oracle, and plan tests pass. The full campaign is intentionally not part of this maintenance qualification.

The next gate is `REPAIR-PAR1`.
