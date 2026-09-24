---
kind: independent-D2-review
protocol_version: 6.4.0
status: NO_PASS
review_target: cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9
review_target_blob: 1ad1ee0374ce1644f72e9ab89121ea47110f35bd
accepted_D2_baseline: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_D2_source_target: a4824d28775164aa942fd29fa97ee0957eb87e6f
handoff_head_reviewed_for_lifecycle_only: a57ca1e17aa2e291814b37932a9a5cfed7635d88
serious_challenge: NONE
earliest_blocking_owner: D2
stage_C_state: BLOCKED_PENDING_REPAIRED_D2_CANDIDATE_AND_FRESH_REVIEW
D3_D4_state: BLOCKED_PENDING_D2_ACCEPTANCE
date: 2026-09-24
---

# Fresh independent Protocol-6.4 D2 Review — TRAIN2 CuEq acceleration equivalence Candidate 4

## 1. Immutable Review binding

This Review targets immutable Candidate 4:

`cd4e0453d0a27ae01f7041c1c9d222fd9d71a0e9`

with canonical candidate blob:

`1ad1ee0374ce1644f72e9ab89121ea47110f35bd`.

The later lifecycle/handoff descendant `a57ca1e17aa2e291814b37932a9a5cfed7635d88` was used only for handoff and lifecycle state. It is not substituted for Candidate 4 as the semantic Review target.

The representation-corrupt predecessor `5d63350dd13929c27fa6c2204238f2f2e8f93cbd` was not reviewed.

## 2. Independent parent reconstruction and Challenge disposition

Accepted-current D2 at `a759e81aa1b4c70c8fb513c569ddce57e99cbdb2` source-imports the exact stakeholder-ratified D2 source target `a4824d28775164aa942fd29fa97ee0957eb87e6f`.

The accepted parent is internally coherent for the present question:

- authoritative optimized execution is admissible only under a source-closed numerical-equivalence relation;
- native backend identity is execution-only only when that relation holds for governed outputs;
- continuation state includes model, optimizer, EMA, scheduler/learning-rate, and RNG lineage where applicable;
- current P5 replay exposure is replay/`pt_head` first, target second in the pre-shuffle combined index space, with accepted seeded shuffle/sampler semantics, no target duplication, exact batch geometry, and `drop_last=true`;
- stochastic training is not required to be bitwise identical across arbitrary backend/runtime realizations, but numerical compatibility must preserve the accepted method and its scientific consequences.

Accepted D1 delegates precision/backend equivalence and numerical failure semantics to D2 without imposing a stronger contradictory scientific requirement.

**SERIOUS CHALLENGE: NONE.** The earliest affected semantic owner is D2 Candidate 4 itself.

## 3. Overall disposition

**NO-PASS for immutable Candidate 4.**

Candidate 4 correctly identifies the backend-specific TRAIN2 state transition as the relevant protected object and correctly separates source/DATA6, TRAIN2, and completed-state projection/EVAL2 roles. It also correctly rejects descriptor/FPS as a TRAIN2 hard gate when TRAIN2 does not consume those quantities.

However, its acceptance functional is not yet adequate to establish the equivalence relation it claims. A semantically wrong CuEq backend can still pass through several independent false-pass constructions.

Any semantic repair requires a **new immutable candidate identity**. Candidate 4 must remain unchanged and historical.

## 4. Blocking findings

### B1 — Claimed full TRAIN2 state transition is under-observed

Candidate 4 defines

`T_b:(theta,q,omega)->(theta',q')`

with `q` containing optimizer, EMA, scheduler, and RNG state, but its hard acceptance consequence observes only the live model function through portable-e3nn E/F/stress displacements. Optimizer and EMA state are required only to remain finite.

This admits a direct false pass:

1. e3nn and CuEq produce live model states whose E/F/stress agree through updates 1 and 2;
2. the CuEq optimizer second moment, momentum, step/counter state, or EMA shadow state differs materially after update 2 while remaining finite;
3. the difference first changes update 3 or the EMA-selected checkpoint/evaluation function.

The current two-update witness therefore proves neither equivalence of the full stated state transition nor absence of latent later divergence.

The same defect appears in `S1`: Candidate 4 requires a non-initial **model** state, but does not require the corresponding non-initial optimizer/EMA/scheduler/RNG state. Resetting those recurrence states at S1 can remove precisely the stateful regime the witness claims to cover.

#### Required repair

A replacement candidate must do all of the following.

1. Define the governed full-state consequence explicitly.
2. Observe EMA through its own portable physical-function E/F/stress channel whenever EMA can control checkpoint/evaluation/publication behavior.
3. For optimizer state, either:
   - define a canonical, parameterization-safe state equivalence for every optimizer quantity that can affect a later update; or
   - use a predeclared backend-neutral continuation/readout that consumes the resulting optimizer state and therefore exposes latent divergence.
4. Treat scheduler/counter/RNG state by exact identity where parameterization does not require tolerance.
5. Bind every non-initial `S1` to an authenticated **full** `(theta,q)` state, including non-initial optimizer and EMA state when those mechanisms are active.
6. Do not infer equivalence over all reachable states from one convenient S1. Either define a source-closed qualified state class with falsification points, or narrow applicability to explicitly qualified state classes.
7. If a longer horizon is used, justify it from recurrence observability. Do not increase update count merely because more is safer.

**Judgment:** two updates plus current S0/S1 coverage are **not sufficient as written**. EMA requires its own physical-function observation. Optimizer state requires a stronger equivalence consequence or a continuation oracle that consumes it.

### B2 — TRAIN2 centroid tolerance is transferred from forward inference without a numerical warrant

Candidate 4 reuses the source-calculator constants

- FP32: `rtol=1e-5, atol=1e-6`;
- FP64: `rtol=1e-10, atol=1e-12`;

as componentwise tolerance on **centroids of update-induced training displacements**.

Those constants are valid historical calculator scales, but Candidate 4 supplies no conditioning, sensitivity, or accumulation argument showing that the same envelope bounds a training operator.

The near-zero regime is the clearest counterexample. If the reference update displacement is close to zero, the absolute term dominates. A coherent signed backend update bias just below `atol` can pass every local centroid comparison and accumulate over many training updates. Forward-calculator agreement does not establish that this accumulated optimizer trajectory error is immaterial.

Energy/atom, force, and stress remain separately dimensioned in Candidate 4, which is correct; the defect is not unit mixing but **unsupported transfer of an inference tolerance to a state-transition error budget**.

#### Required repair

Derive the persistent TRAIN2 bias budget from the accepted training-state consequence itself, before Stage-C outcomes are inspected. A valid replacement may use, for example:

- a source-closed bound on accumulated physical-function drift over a bounded paired adaptation;
- a normalized update-error relation with an independently justified absolute floor; or
- another conditioning/sensitivity-derived state-transition envelope.

Whatever relation is chosen must explicitly reject a coherent small backend bias whose repeated accumulation becomes material. The constants may not be selected or widened from Candidate-bound Stage-C CuEq results.

**Judgment:** the current centroid relation is **not numerically justified**.

### B3 — The stochastic estimator contradicts the declared independent experimental unit

Candidate 4 correctly declares the **fresh process** to be the independent experimental unit, with three retained observations inside each process treated as nested measurements. But its variance definitions operate directly on all 60 retained observations:

`V_b = (1/N) sum ||x_{b,h,p,r}-mu_b||^2`, with `N=60`.

This pools within-process and between-process variation as though one scalar variance were sufficient for both. It does not preserve the hierarchy established by the Stage-A diagnostics, which explicitly analyzed fresh-process means for process-level variability.

There is also a stronger algebraic defect in the order-cell guard:

`V_C,h <= V_R + T^2`.

The candidate cell-local variance is compared against the **global reference variance**, not the corresponding reference-cell variance. A candidate can therefore become much noisier in a previously quiet order cell and still pass by borrowing reference variance contributed by another cell.

A concrete false pass exists whenever the reference has heterogeneous cell variances: redistribute candidate variance into a quiet cell while preserving the same global variance. The stated global and cell inequalities can all remain true even though one order condition has materially degraded.

The additive form `V_C <= V_R + T^2` is not intrinsically ill-defined at `V_R=0`, and its extra budget is candidate-independent. The blocking issue is the wrong stochastic level and wrong local comparator.

#### Required repair

1. Make a process-level summary the primary independent observation for stochastic qualification. With balanced nested repeats, averaging retained repeats within each process is a natural candidate.
2. If within-process stochasticity is also protected, represent it as a separate hierarchical component rather than using nested repeats as independent replicates.
3. Define reference **cell-local** variability `V_R,h` and compare candidate cell-local variability against that corresponding reference cell, with a separately defined cell-local tolerance scale.
4. Keep global and order-cell bias guards, since they correctly prevent opposite cell biases from canceling globally.
5. Do not reuse the Stage-A five-process-per-cell cardinality merely because it was used for a forward diagnostic. The transition observable is new.
6. Predeclare a qualification-classification stability rule before Stage C. At minimum, two independently realized complete 20-process ensembles are sufficient to expose between-ensemble classification instability: every hard predicate must pass in each ensemble; pooling may not rescue a failing ensemble; no outcome-selected rerun is allowed. Another rule is acceptable only if it is equally explicit and independently justified.

**Judgment:** fresh process and four counterbalanced order cells are appropriate; the present variance estimator and one-ensemble cardinality are **not sufficient for authorizing qualification**.

### B4 — The 0.01 Huber transition scale is not a backend-equivalence catastrophic bound

Candidate 4 uses the existing property Huber transition scales

- 0.01 eV/atom;
- 0.01 eV/angstrom;
- 0.01 eV/angstrom^3

as a hard per-observation catastrophic backend-discrepancy ceiling.

Those numbers govern the robust training loss branch transition. They are not, by that fact, numerical backend-equivalence error budgets.

The roles are materially different:

- near a Huber branch boundary, a much smaller backend difference can alter the optimizer contribution by moving one realization across the branch;
- away from the boundary, a backend discrepancy of 0.009 in a physical channel can be far larger than any defensible numerical-equivalence error while still passing the proposed catastrophic guard.

The loose guard also fails to close a rare-component false pass when aggregate RMS moments dilute a single large component that remains below 0.01.

#### Required repair

Remove the Huber scale as the generic catastrophic backend-equivalence guard.

If loss-branch behavior is a protected consequence, test that consequence directly: require identical property masks and robust-loss branch classification where backend arithmetic could alter it, or directly bound the resulting per-sample optimizer contribution.

If a rare-outlier physical hard guard is retained, derive it independently from the D2 backend-error/materiality budget, make it channel-specific and non-dilutable, and freeze it before Stage-C outcomes.

**Judgment:** the current catastrophic guard is **not legitimate D2 numerical authority**.

### B5 — Real TRAIN2 exposure is used, but the window-selection rule can systematically undersample difficult regimes

Candidate 4 correctly requires the real accepted loader/exposure owner and rejects hand-built target-only, replay-only, target-first, duplicated, or otherwise reconstructed lookalike batches.

However, selecting the **smallest deterministic metadata-covering set** of consecutive two-update windows guarantees branch presence, not numerical exposure adequacy. Without inspecting CuEq outcomes, it can still repeatedly choose the earliest or least-conditioned occurrence of each branch and omit boundary/state regimes that materially alter recurrence.

#### Required repair

Preserve the real-loader consecutive-window rule and metadata-only preselection, but add predeclared exposure classes where applicable. The replacement candidate should include, at minimum:

- the first native consecutive two-update window;
- the last complete consecutive two-update window of an epoch;
- a native window crossing an epoch/shuffle boundary when one exists;
- a window bracketing every scheduler-state discontinuity/change that can alter update semantics;
- metadata-extreme native windows for target/replay fraction and total atom/edge count, plus every active head/property-mask branch.

All such windows must be selected before any CuEq outcome is inspected. Supplemental boundary windows may not replace native consecutive exposure.

**Judgment:** Candidate 4 exercises the correct real owner, but its minimum-window coverage rule is too weak for the claimed operator domain.

### B6 — The state-transfer measurement transform still has unclosed common-mode and mutation risk

Candidate 4's direct transient-CuEq versus mapped-portable-e3nn E/F/stress comparison for every measured state is a useful and necessary oracle. Exact portable-shell architecture identity is also appropriate.

But the method does not explicitly guarantee that applying the mapping after update 1 cannot mutate the live CuEq state subsequently used for update 2. It also does not require an exact inventory/bijection of every model tensor/buffer capable of influencing the portable function; a dropped state item that happens to be quiescent on the finite witness corpus can evade a physical-output check.

The additional "dependency-native differential route against pinned MACE conversion semantics/state values" reduces common-mode risk only if it is genuinely independent of the same transfer implementation. Candidate 4 does not establish that independence.

#### Required repair

1. Make transition measurement non-invasive:
   - snapshot states after the training sequence and perform transfer/evaluation only from immutable snapshots; or
   - prove exact source-state digest/value identity before and after every mapping call.
2. Define the complete transferable state inventory and require exact structural correspondence for every tensor/buffer affecting the portable forward, in addition to physical E/F/stress parity.
3. Require the anti-common-mode differential to use an independently implemented/source-owned route that does not call the same `P_C` transfer machinery. If pinned MACE ultimately reuses the same transfer owner, it is corroboration, not independent evidence.
4. Keep exact architecture identity and the direct physical parity oracle on every measured state.
5. Do not reintroduce source/DATA6 descriptor/FPS acceptance into TRAIN2 through the transform.

**Judgment:** the measurement transform is improved over prior candidates but is **not yet sufficiently independent/non-invasive**.

### B7 — Adjacent source/DATA6 and projection/EVAL2 siblings are not actually source-closed D2 relations yet

The accepted Protocol-6.4 D2 source at `a4824d28775164aa942fd29fa97ee0957eb87e6f` does not itself define a CuEq source/DATA6 calculator equivalence relation or trained-state CuEq projection relation. The FP32/FP64 numbers exist in historical D4/specification/release behavior, but repository history cannot promote them into D2 authority.

Candidate 4 therefore cannot characterize D2.CUEQ.DEF.003-004 as merely "preserved current numerical semantics" without independently supplying the D2 warrant. They are proposed source-closure/promotions of historical behavior.

Likewise D2.CUEQ.DEF.023 invokes "the existing dtype-appropriate post-transfer calculator parity relation" without naming an exact D2 owner/relation or restating the exact comparison semantics. That is not definition-closed enough for Protocol 6.4.

#### Required repair

For source/DATA6 FP32 and FP64, either:

1. explicitly propose them as new D2 sibling relations, with exact provenance and an independent numerical adequacy argument for the protected source/pseudolabel E/F/stress and descriptor/FPS selection consequences; or
2. remove them from the Candidate-4 successor and leave the historical D4 guards non-authoritative until separately reviewed.

Do not state or imply that accepted-current D2 already owns those CuEq thresholds.

For completed-state projection/EVAL2:

1. state the exact post-transfer E/F/stress comparison relation, dtype values, applicability, and owner/source;
2. retain exact architecture/state authentication;
3. retain an independent transfer oracle; and
4. explicitly identify EVAL2 as the actual portable **e3nn** numerical forward after authenticated projection.

**Judgment:** source/DATA6 FP32, source/DATA6 FP64, and trained-state projection/EVAL2 are not independently source-closed by Candidate 4 as written.

## 5. Non-blocking conclusions and preserved good decisions

### Descriptor/FPS removal from TRAIN2

**Accepted in principle.** Current TRAIN2 does not consume invariant descriptors or FPS selection, while accepted source/DATA6 selection does. Descriptor/FPS drift with an equivalent physical TRAIN2 transition must therefore not fail TRAIN2 solely because the latent representation moved.

Exact descriptor/FPS protection remains appropriate where source/DATA6 selection actually consumes that consequence.

### Role separation

The separation of:

1. source/DATA6 calculator equivalence;
2. TRAIN2 state-transition equivalence; and
3. trained-state projection/EVAL2 equivalence

is correct and must be preserved. A pass in one role cannot authorize another.

### Qualification versus routine doctor

The numerical split is legitimate:

- expensive target-host qualification establishes a bounded backend/model/runtime/state applicability relation;
- routine doctor execution may authenticate that current record and perform a cheap bounded real forward/backward reachability/finiteness witness.

The cheap witness may not recreate the equivalence relation, widen a failed record, retry until pass, authorize a new model/runtime/state, or revive an obsolete Rev86 `passed=true` record.

Exact persistence and routing remain D3/D4 concerns.

## 6. Explicit scope dispositions

| Relation | Candidate-4 disposition | Required future treatment |
|---|---|---|
| source/DATA6 FP32 | **NO-PASS as D2 sibling authority** | Explicitly source-close and justify as proposed D2, or defer it; do not claim prior D2 acceptance. |
| source/DATA6 FP64 | **NO-PASS as D2 sibling authority** | Same as FP32; historical D4 tolerance is not self-authorizing. |
| TRAIN2 FP32 | **NO-PASS** | Repair B1-B6, freeze a new candidate, fresh independent Review, then fresh Stage-C evidence and stakeholder ratification. |
| TRAIN2 FP64 | **NO-PASS / no inherited support** | Qualify under the repaired training-operator consequence or explicitly narrow CuEq TRAIN2 support to exclude FP64. Forward-only evidence is insufficient. |
| trained-state projection/EVAL2 | **NO-PASS as source-closed D2 relation** | Exact relation/owner plus independent, non-mutating state-transfer oracle required. EVAL2's actual portable forward should remain e3nn. |

## 7. Counterexample closure

| Counterexample | Candidate 4 |
|---|---|
| coherent small backend bias repeated over many updates | **False-pass remains possible** — no accumulation/conditioning bound |
| equal means with inflated candidate variance | Partially detected globally; **process/cell hierarchical false pass remains** |
| opposite cell biases cancel globally | Rejected by cell-centroid guard |
| one rare large component error | **False-pass can remain below unrelated 0.01 guard and be RMS-diluted** |
| update-2-only live-model divergence | Rejected if it changes measured portable E/F/stress |
| EMA-only divergence | **False-pass** |
| optimizer-state divergence not yet visible in live predictions | **False-pass** |
| target-first exposure | Rejected |
| hand-built synthetic batch | Rejected |
| dropped/misrouted transient state during projection | May be rejected by direct physical oracle, but **quiescent/common-mode false pass remains** |
| state-transfer mapping mutates source model | **Not explicitly rejected** |
| descriptor-only drift with preserved TRAIN2 transition | Correctly does not fail TRAIN2 |
| source/DATA6 descriptor drift that changes FPS | Exact selection consequence should reject once the source relation is source-closed |
| zero-reference-variance | Additive variance form remains finite, but hierarchy/comparator still defective |
| near-zero transition displacement dominated by atol | **False-pass risk** |
| stale qualification after runtime/source/config change | Candidate currentness design is broadly adequate |
| nominally different but numerically trivial S1 | Current output-change rule rejects exact triviality, but state-domain overclaim remains |

## 8. Evidence and currentness impact

Stage-A MH-1 and MPA-0 evidence remains valid **method-design evidence** for the earlier forward diagnostic and its process/order observations. It does not qualify Candidate 4's new training-state-transition relation.

No Candidate-4 Stage-C acceptance evidence may be used to repair the method after seeing outcomes. The replacement D2 relation must be frozen first.

Because the required repairs change semantic acceptance definitions, the repaired method must receive a **new immutable candidate identity**. Any future Stage-C evidence must bind that new candidate/method digest.

Historical Candidate 4 and this NO-PASS Review remain evidence of the failed proposal and its falsification findings; they do not authorize execution.

## 9. D2 -> D3 disposition

There is **no D2 -> D3 implementation handoff from Candidate 4**.

D3/D4 remain blocked until a repaired immutable D2 candidate:

1. closes B1-B7;
2. passes a fresh independent D2 Review;
3. receives the required stakeholder ratification; and
4. then obtains fresh Stage-C target-host qualification under the exact accepted method.

When that later gate passes, the architectural handoff should preserve reduction over addition: replace rather than stack on Rev86, use the real loader/exposure owner, retain distinct source/TRAIN2/projection relations, authenticate full state/currentness, and reuse one independently qualified state-transfer owner rather than inventing parallel projection machinery.
