---
kind: independent-D2-review
protocol_version: 6.4.0
status: NO_PASS
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
reviewed_candidate: 6e73fbb7af9b8d46f61cf81113259584ffed8527
reviewed_candidate_blob: 4bfd2451cc1835e82e303cc9a597b69b8f8deda9
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
serious_challenge: false
highest_blocking_owner: D2
date: 2026-09-25
---

# Fresh independent D2 Review R2 — Candidate 5

## 1. Disposition

Immutable Candidate 5 at

`6e73fbb7af9b8d46f61cf81113259584ffed8527`

with canonical blob

`4bfd2451cc1835e82e303cc9a597b69b8f8deda9`

receives **NO-PASS**.

There is **no SERIOUS CHALLENGE** to accepted D1/D2 parent authority. The earliest defective owner remains the proposed D2 acceleration-equivalence overlay itself.

Candidate 5 materially improves Candidate 4, but its authorizing TRAIN2 relation still admits genuine false passes.

## 2. Blocking findings

### B1 — proposed `delta*sqrt(u)` TRAIN2 scale is not numerically derived

Candidate 5 proposes

$$
\epsilon_{c,d}=\delta_c\sqrt{u_d}.
$$

Dimensional consistency, precision refinement, and prospective declaration do not establish that exponent or magnitude as a training-operator error budget.

There is no conditioning, operation-count, backward-error, perturbation, or state-transition sensitivity argument that yields \(\sqrt{u}\).

The force import is also not exact. Accepted D2 uses a force-magnitude-dependent Huber threshold. The base value is \(0.01\ \mathrm{eV/\mathring A}\), but the accepted transition reaches \(0.001\ \mathrm{eV/\mathring A}\) in the highest-force regime. Candidate 5's single \(\delta_F=0.01\) is therefore not the exact accepted force materiality relation it claims to import.

**Required repair:** remove this heuristic from authorizing TRAIN2 semantics. Derive numerical acceptance from a source-closed error relation or from a predeclared reference-only stochastic numerical envelope whose uncertainty semantics are explicit.

### B2 — finite optimizer-action probes are not injective over optimizer state

Zero-gradient plus a finite set of selected real gradients does not identify all optimizer state capable of changing a later reachable update.

For an Adam-like optimizer, two states can agree under every selected probe while differing in second-moment state on a coordinate absent from those probes. A later nonzero gradient can then produce a different update.

The same issue applies to inactive heads, delayed activations, running extrema, and other latent recurrence.

**Required repair:** either compare a complete canonical optimizer state under a valid parameterization-safe equivalence, prove an injective complete action basis, or narrow the claimed relation so future unobserved optimizer actions are not part of the authorization. A finite convenient probe family cannot carry the complete-state claim.

### B3 — finite EMA function observation does not establish complete EMA-state equivalence

Two EMA states can agree on a finite witness corpus and disagree elsewhere. If EMA controls checkpoint evaluation or publication, that is an authorizing state difference.

**Required repair:** add a canonical structural EMA-state relation, or narrow the protected consequence to a bounded functional domain and stop claiming complete state equivalence.

### B4 — recurrence horizon and secant extrapolation are not conservative propagation bounds

The e-folding count

$$
\left\lceil\frac{1}{1-\beta_{\max}}\right\rceil
$$

is a useful recurrence timescale, but it is not an error-propagation theorem for the coupled optimizer/EMA/scheduler/model dynamics.

Likewise,

$$
\|d(H)\|+(U_{\rm rem}-H)g\le\epsilon
$$

cannot conservatively bound future divergence unless future discrepancy growth is known to be bounded by the largest observed earlier secant.

A delayed scheduler transition, nonlinear state-region change, moment-history threshold, or ordinary loss-landscape change can remain quiet through every observed point and diverge later.

**Required repair:** observe the complete authorizing horizon directly, or supply a genuine source-closed propagation theorem whose assumptions cover the actual coupled recurrence.

### B5 — entry/mid/late e3nn anchors do not define an authorizing state class

Candidate 5 explicitly avoids claiming a theorem over all reachable states, but then uses entry/mid/late e3nn anchors to authorize a broader TRAIN2 state class that is never formally defined.

A CuEq trajectory can agree around all three e3nn anchors and later enter a state not represented by any anchor.

**Required repair:** define a source-closed state neighborhood plus an online applicability predicate, or bind qualification to the exact realized full training trajectory/horizon.

### B6 — metadata-only window selection can omit numerically difficult ordinary batches

First/last/boundary, target-fraction, atom/edge, and branch coverage is structurally useful but does not cover numerical conditioning.

A metadata-ordinary batch can carry near cancellation, extreme gradient dynamic range, a near-Huber-transition residual, a tiny update, or a difficult contraction regime.

**Required repair:** either add backend-blind reference-only numerical-conditioning classes or execute the full accepted loader trajectory rather than sampling windows.

### B7 — five processes and `SE <= epsilon/2` have no authorizing finite-sample semantics

Fresh process is the correct independent unit and Candidate 5 correctly separates nested repeats. However, five processes per cell plus an ordinary sample standard error does not establish a population-level backend-equivalence claim.

The rule has neither a finite-sample coverage guarantee nor a predeclared false-authorization rate. Two complete ensembles are a replication guard, not a substitute for those semantics.

**Required repair:** state the actual population claim and use a sample-size/decision rule derived from explicit confidence/coverage or another source-closed uncertainty model. Candidate observations may not select a rescue sample size.

### B8 — the rare-component guard lets a small reference sample mint candidate tolerance

The rule

$$
M_C\le M_R+\epsilon
$$

uses the maximum of only three reference repeats inside one process as an authorizing allowance. One unusual reference repeat can therefore widen the candidate hard limit.

Same-index pairing is also not an independent stochastic justification unless common-random-number coupling is actually guaranteed.

**Required repair:** replace the three-repeat maximum with a predeclared reference-only population/tolerance construction having explicit finite-sample coverage, and keep zero-reference-variation cases exact.

### B9 — source/DATA6 forward thresholds remain insufficiently warranted as generic D2 siblings

Candidate 5 correctly reclassifies historical source/DATA6 FP32/FP64 behavior as proposed rather than accepted. It still bundles several protected consequences under one historical `allclose` envelope.

In particular, the FP32 relative term can permit a high-force absolute discrepancy larger than the accepted high-force Huber transition while still calling the source outputs equivalent. That cannot authorize pseudolabel materialization without a downstream sensitivity warrant.

**Required repair:** split or narrow source/DATA6 roles. Exact descriptor/FPS decisions may be protected directly. Pseudolabel or other downstream numerical consumers require their own consequence-specific relation. Historical D4 tolerances remain evidence only.

## 3. Confirmed Candidate-5 improvements

The following Candidate-5 directions are retained:

- fresh process is the independent stochastic unit;
- nested repeats are not independent replicates;
- cell-local reference variability must not be borrowed from unrelated cells;
- TRAIN2 descriptor/FPS hard-gating is removed when TRAIN2 has no descriptor/FPS consumer;
- Huber branch-name identity is not itself an authorizing consequence;
- real accepted TRAIN2 loader/exposure ownership is mandatory;
- transfer must be snapshot-only and non-mutating;
- an anti-common-mode transfer oracle cannot call the same mapper or consume the same generated mapping table;
- routine doctor cannot recreate or widen an expensive qualification;
- FP64 CuEq TRAIN2 remains unsupported/fail-closed.

## 4. Explicit role dispositions

| Relation | R2 disposition |
|---|---|
| source/DATA6 FP32 proposed sibling | **NO-PASS** as generic bundled D2 authority |
| source/DATA6 FP64 proposed sibling | **NO-PASS** as generic bundled D2 authority |
| TRAIN2 FP32 | **NO-PASS** |
| TRAIN2 FP64 | **unsupported/fail-closed narrowing confirmed** |
| completed-state projection/EVAL2 | **NO-PASS as complete C5 sibling**, because it inherits the rejected physical scale and still requires a genuinely independent structural transfer oracle |

## 5. Common-mode transfer finding

Pinned MACE 0.3.16 `convert_cueq_e3nn.py` and `convert_e3nn_cueq.py` are not two independent mapping algorithms. They share the same correlation-pair logic, `symmetric_contraction_proj` machinery, and closely mirrored state-key transfer structure.

A round-trip through those two scripts is therefore correlated evidence and cannot satisfy Candidate 5's independent anti-common-mode oracle requirement.

## 6. Evidence/currentness consequence

Candidate 5 remains immutable historical proposed authority.

Any repair creates a new candidate identity.

Stage-A MH-1 and MPA-0 evidence remains method-design evidence only. Candidate-5 Stage-C evidence must not be run and then used to tune a replacement method.

No D2-to-D3 handoff exists from Candidate 5.
