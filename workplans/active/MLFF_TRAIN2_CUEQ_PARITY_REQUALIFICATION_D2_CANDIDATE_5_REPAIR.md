---
kind: D2-candidate-repair-record
protocol_version: 6.4.0
status: AUTHOR_REPAIR_COMPLETE_AWAITING_FRESH_INDEPENDENT_REVIEW
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R1.md
superseded_candidate: cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9
replacement_candidate: 6e73fbb7af9b8d46f61cf81113259584ffed8527
replacement_candidate_blob: 4bfd2451cc1835e82e303cc9a597b69b8f8deda9
date: 2026-09-24
representation_correction_of_candidate5: be57964c15ed24e30372de407534efd8173d6bc5
---

# Candidate-5 D2 repair record

Candidate 4 received a fresh independent Protocol-6.4 D2 Review NO-PASS. Candidate 5 repairs the seven blocking findings without mutating Candidate 4 and without implementing D3/D4.

## B1 — complete state under-observed

Repaired by:

- defining complete TRAIN2 state over model, optimizer, EMA, scheduler/counters, RNG, and backend mutable state;
- exact comparison of discrete scheduler/counter/RNG consequences;
- portable EMA physical-function observation;
- canonical optimizer-action probes using identical assigned gradients;
- independent optimizer-state transfer inventory/value checking;
- full-state entry/mid/late reference anchors rather than model-only S1.

Two committed backend updates remain the local recurrence witness, but they no longer carry the whole proof. Latent state is observed through explicit readouts.

## B2 — unsupported transfer of calculator tolerance to TRAIN2 centroids

Repaired by deleting the TRAIN2 use of source-calculator `rtol/atol`.

Candidate 5 introduces a new prospective physical numerical budget

`epsilon_(c,d) = delta_c * sqrt(u_d)`

from the accepted property residual scale and machine epsilon. It is explicitly a proposed D2 precision-scaled materiality heuristic, not an inherited authority or floating-point theorem.

Near-zero update displacements receive no relative-tolerance escape.

The local witness is supplemented by:

- a recurrence-horizon bounded paired adaptation tied to the slowest active recurrence timescale;
- full remaining-horizon treatment for non-decaying carried state when local action probes do not close it;
- a conservative coherent-drift secant-growth extrapolation over the remaining accepted TRAIN2 horizon.

A locally sub-tolerance coherent bias therefore cannot pass merely because only two updates were observed.

## B3 — stochastic estimator used nested repeats as independent and borrowed global variance

Repaired by:

- fresh process remaining the independent unit;
- process means as the primary observations;
- separate between-process and within-process stochastic coordinates;
- candidate cell variance compared against the corresponding reference cell, never the global reference variance;
- two independently launched complete four-cell ensembles;
- no pooled rescue;
- explicit reference and candidate process-resolution sufficiency checks, returning typed `INSUFFICIENT_*_RESOLUTION` rather than authorizing an under-resolved experiment.

## B4 — 0.01 Huber scale used as catastrophic backend threshold

Repaired by removing `0.01` as a direct discrepancy ceiling.

Rare-component protection is now a non-dilution guard controlled by:

- same-process reference self-repeat maximum; plus
- the fixed Candidate-5 physical numerical budget.

The Huber value remains only where it owns semantics: as the accepted property residual scale behind the proposed precision-scaled numerical coordinate. Huber branch-name identity is not an independent hard gate; the governed state-transition consequence decides.

## B5 — minimum metadata-covering exposure could avoid difficult regimes

Repaired by requiring the deterministic union of applicable:

- first native window;
- last complete window before epoch boundary;
- epoch/shuffle-boundary window;
- scheduler-discontinuity window;
- target-fraction extrema;
- atom/edge-count extrema; and
- all active head/property-mask branch coverage.

Every window remains consecutive and comes from the real accepted TRAIN2 loader. Selection remains outcome-blind.

## B6 — state-transfer common mode and mutation risk

Repaired by:

- snapshot-only transfer;
- exact source-state identity before/after mapping;
- complete parameter/buffer inventory and one-to-one transfer correspondence;
- direct transient-CuEq versus mapped-portable-e3nn physical comparison;
- an independent model-state transfer route that cannot call the same transfer owner/mapping generator;
- independent optimizer-state transfer inventory/value checking;
- fail-closed treatment when an independent route is unavailable.

Descriptor/FPS acceptance is not imported into TRAIN2.

## B7 — source/DATA6 and projection siblings were historical D4 behavior presented as accepted D2

Repaired by explicitly marking source/DATA6 FP32, source/DATA6 FP64, and trained-state projection/EVAL2 as **new proposed D2 sibling relations**.

Historical operational behavior is evidence only.

Each sibling requires its own current/applicable evidence and exact protected consequence.

EVAL2 is explicitly the portable **e3nn** numerical forward after qualified projection.

## Additional scope repair

Candidate 5 narrows TRAIN2 CuEq support to **FP32 only**.

FP64 source/DATA6 remains a separate proposed forward relation. FP64 CuEq TRAIN2 must fail closed until a future accepted D2 operator relation qualifies it.

## Evidence boundary

No Stage-C evidence was used to tune Candidate 5.

Stage-A MH-1 and MPA-0 evidence remains method-design evidence only.

Fresh Candidate-5 Stage-C evidence remains blocked until:

1. fresh independent D2 Review PASS;
2. stakeholder ratification of the exact passing candidate; and
3. an unchanged candidate/method identity.

No D3/D4 implementation is authorized by this repair.


## Representation correction

The first frozen Candidate-5 representation at `be57964c15ed24e30372de407534efd8173d6bc5` contained two single-dollar display delimiters around the candidate-resolution inequality. The correction to `6e73fbb7af9b8d46f61cf81113259584ffed8527` changes only display delimiters. The mathematical expression, numerical budget, acceptance logic, scope, and all B1-B7 repairs are unchanged.
