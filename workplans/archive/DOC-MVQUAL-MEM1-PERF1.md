---
kind: implementation-workplan
workplan_id: DOC-MVQUAL-MEM1-PERF1
protocol_version: 5.1.0
status: DONE
analysis_base_ref: main@9fdc649289cbf65fe825af8adf958e10bd6dd1ac
predecessor_workplan: DOC-REPAIR2-PERF1
review_status: FINAL_REVIEW_HARDENED
completed_date: 2026-08-21
accepted_source_commit: 9d97569bf3d7802d813d3562a2e34f4409be67ec
raw_qualification_evidence: retired_after_closeout_for_publication_hygiene
---

# DOC-MVQUAL-MEM1-PERF1 — completed bounded exact MVQUAL and progressive sparse optimization

## Terminal decision

DONE. MEM1 is accepted and PERF1 stops at P2/P3.

TARGET-DATA2C-MVQUAL1 completes the full product ladder through 16,384 with strict bounded sparse scratch, exact unchanged scientific authority, zero swap in the measured product runs, and approximately half the accepted M5 warm builder wall time.

The accepted runtime uses the bounded M2 independent-rung implementation as the exact oracle and adds progressive sparse reuse only for truly nested selector ladders. P1 progressive direct TARGET-DATA2B reuse was measured and rejected because it increased the critical path; it is not part of the accepted runtime.

## Preserved scientific invariants

The completed implementation preserves:

- TARGET-DATA2C-MVQUAL1 scientific ownership in `target_multi_view_qualification.py`;
- TARGET-DATA2B as independent coverage/scoring authority;
- MVIDX as exact secondary telemetry and sparse covered-mass cross-check;
- all existing policy/schema/version and persistence identities;
- same-N comparison semantics, tolerances, hard obligations, extent rules, N95 and outcome classification;
- canonical domain/rung/selector/family/stratum/UID ordering;
- canonical full-witness `float64` scientific reductions;
- deterministic scientific content independent of worker count and strict chunk size;
- no approximation, sampling, ANN, reduced family set, weakened cross-check, second persistent graph, or scientific digest migration.

The accepted repeated product digest remains:

`338c336ab6021e0807b9c1d2b5945a29959eeccc3e8a46860e6a11931b893d11`

with outcome `scientific_coverage_qualified`.

## Accepted implementation

### MEM1

The sparse execution path uses a strict canonical CSR edge stream with a configured product limit of 1,048,576 edges. Oversized CSR rows may be split inside the row while preserving canonical row/edge order. Witness multiplicity uses bounded `int32` state, and unique ownership is computed without materializing a full selected-edge owner vector.

The scheduler admission estimate is phase-aware rather than proportional to total graph size, and execution telemetry records strict edge usage, streamed edges, selected-row maxima, phase timings, worker admission and process/resource counters without entering scientific digests.

### P2

For exact nested `(domain, selector)` ladders, progressive sparse telemetry processes only candidate rows newly added between rungs. Per family it carries witness multiplicity, sole-owner state, per-candidate unique-witness counts, exact `0 -> 1` ownership creation, and exact `1 -> 2+` ownership revocation.

Scientific mass reductions are still recomputed in canonical full-witness order at every rung. Families remain parallel work units, preserving four-worker product concurrency. Nonnested ladders fall back to the accepted bounded M2 implementation.

## P1 rejected

P1 reused the existing progressive TARGET-DATA2B scorer and preserved exact science, but failed its performance acceptance gate. The retained closeout facts are:

- accepted M5 warm builder: 00:06:58;
- P1 repeat-1 builder: approximately 00:07:33;
- P1 direct prepass: approximately 00:01:58;
- scientific digest unchanged;
- peak RSS remained bounded and swap remained zero.

The regression occurred because only two selector-level progressive direct tasks ran before the normal MVQUAL queue, while the previous direct work had already overlapped inside the four-worker rung queue. P1 therefore reduced theoretical direct work but lengthened the product critical path. Its executable runtime was retired at closeout.

## P2/P3 product qualification

Product identity:

- label domains: 1;
- candidates: 36,408;
- required families: 165;
- forward MVIDX edges: 9,505,021,522;
- full MV ladder through 16,384;
- effective scoring workers: 4.

Repeated P2 builder results:

- repeat 1: 00:03:27 (207.172 s);
- repeat 2: 00:03:29 (209.313 s).

Repeated total benchmark results including authority load:

- repeat 1: 00:03:47 (227.034 s);
- repeat 2: 00:03:49 (228.718 s).

The accepted M5 warm builder was 418.325 s (00:06:58). P2 therefore reduces the comparable builder wall by approximately 50% and is comfortably below the workplan's approximately five-minute stop target.

P2 execution recorded:

- progressive groups: 2/2;
- fallback groups: 0;
- family tasks: 330;
- reports: 15;
- progressive sparse wall: 00:01:52 and 00:01:53;
- streamed edges: 6,621,378,654;
- maximum chunk edges: 1,048,576.

Memory/safety evidence:

- sampled peak RSS: 31,985,088 KiB and 31,981,944 KiB;
- both peaks within the stage RAM budget;
- process swap growth: 0 KiB in both repeats;
- system swap-in/out: 0/0 in both repeats;
- builder major faults: 0 in both repeats;
- no persistent second graph or product-scale generated scratch;
- full scientific validation passed in both repeats;
- repeated final plan digest identical.

## Gate status

| Gate | Terminal status | Result |
|---|---|---|
| M0 | PASS | Scalar/reference behavior frozen before optimization. |
| M1 | PASS | Strict canonical CSR edge streaming established; every product chunk remained <= 1,048,576 edges. |
| M2 | PASS | Exact bounded sparse telemetry replaced unbounded selected-edge gathers while preserving the independent oracle. |
| M3 | PASS | Phase-aware memory admission and execution telemetry established bounded product headroom. |
| M4 | PASS | Scientific/deterministic contracts preserved across the optimized implementation lineage. |
| M5 | PASS | Full 16,384 product qualification completed repeatedly with exact digest, bounded RSS and zero swap. |
| P0 | OPENED PERF1 | Warm 00:06:58 builder exceeded the approximately five-minute target; sparse telemetry dominated measured lane time. |
| P1 | REJECTED | Exact science, but product builder regressed to approximately 00:07:33. |
| P2 | PASS | Progressive sparse telemetry reduced repeated nested-rung rescans while preserving M2 as exact oracle. |
| P3 | PASS | Repeated product builder 00:03:27/00:03:29, unchanged digest, bounded RSS, zero swap, strict chunking. |

## Evidence-retention decision

The raw `qualification/mvqual-mem1/` host/run receipts were retired after final closeout as part of pre-publication repository hygiene. They contained no continuing product authority beyond the accepted facts preserved above and included machine-specific provenance unsuitable for the public repository. This archived workplan is the durable compact record for the accepted scientific digest, performance measurements, memory/swap observations, P1 rejection, P2/P3 acceptance, and gate disposition.

No permanent architecture/specification delta is required. The accepted change is execution-only and does not alter a durable scientific, public API, persistence, policy, schema, or content-digest contract.

## Test-evidence note

No GitHub CI status or machine-readable local pytest receipt is attached to the accepted source commit. This archive does not invent one. The full product qualification independently exercised and validated the accepted scientific path twice; any future regression investigation should still run the focused MVQUAL/MVIDX test set in the executable checkout.

## Accepted extension boundary

Do not reopen MVQUAL merely for incremental tuning. Reopen only if product evidence demonstrates one of:

- scientific/report/digest parity failure;
- strict bounded-memory or swap regression;
- material I/O/refault regression attributable to MVQUAL;
- a changed product envelope that invalidates the current witness-state admission model;
- a downstream requirement that changes the current authority interface;
- a new whole-system profile showing MVQUAL again dominates preparation wall time.

Further direct TARGET-DATA2B progressive regrouping is specifically not justified by this workplan: P1 already demonstrated that reducing isolated work can worsen the critical path when it destroys queue overlap.

## Handoff

`DOC-MVQUAL-MEM1-PERF1` is closed. No additional PERF1 gate is authorized by this workplan.
