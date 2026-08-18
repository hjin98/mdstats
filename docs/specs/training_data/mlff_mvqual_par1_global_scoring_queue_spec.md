# MVQUAL-PAR1 global same-N scoring queue specification

## Status

Implemented in mdstats 0.20.232a0 / MLFF architecture revision 99.

## Scientific invariants

MVQUAL-PAR1 is an exact-equivalence execution gate. It MUST NOT change:

- TARGET-DATA2B independent coverage reports for any selector/rung;
- MVIDX covered-mass cross-checks or hard-obligation state;
- MVKERNEL1 selector telemetry;
- same-N comparison arithmetic, thresholds, N95 logic, learning-control sizes, outcome, or persisted plan schema;
- canonical domain and target-size comparison order;
- target-data membership, model-family semantics, training, or GPU authority.

## Execution contract

One immutable scoring job is formed for each materializable `(label domain, selector, target size)` tuple. A job computes the existing TARGET-DATA2B coverage report, MVKERNEL1 telemetry, hard-obligation state, and MVIDX/direct covered-mass consistency check.

When `scoring_workers > 1`, jobs execute on the PARCORE1 `DeterministicWorkQueue`. Nested cKDTree, BLAS/OpenMP, and PyTorch CPU work are one native lane per campaign job. Completed jobs may arrive in arbitrary order, but comparison construction and progress emission MUST be reduced in historical domain/size order.

Per-job temporary-memory estimates participate in queue admission. Automatic campaign mode uses at most four outer scoring workers; explicit positive configuration may request more subject to the existing CPU/RAM resource budget.

Direct API callers that do not supply `StageResourceScope` retain their historical process native-thread environment. Explicit campaign scopes retain BLAS=1. This distinction is required because changing only BLAS thread count can shift the Wasserstein diagnostic at ~1e-16 and therefore change coverage-report cryptographic digests.

## Configuration

`[performance].target_multi_view_qualification_workers = 0` selects automatic execution. Positive values request an explicit outer scoring-worker count, clipped by available and budgeted CPU resources.

## Acceptance authority

Under the production BLAS=1 contract, untouched 0.20.231a0 and 0.20.232a0 MUST produce the same complete MVQUAL plan on the frozen 16,000-reference / six-size / 12-job benchmark. The canonical plan digest is:

`2ebd7f5dc2b560e3150fe4849e7098be2eff56469779f15b2befda74059fc90b`

The paired cloud-CPU benchmark records approximately 0.866 s median for the old serial same-N driver using four native cKDTree workers and approximately 0.409 s for four outer MVQUAL-PAR1 workers using one native tree worker/job, about 2.12x faster. New 1/2/4-lane medians are approximately 0.828/0.451/0.458 s. Timing is execution evidence only; complete record equality is scientific authority.

The next optimization gate is `AUDIT-EVAL-PERF1`.
