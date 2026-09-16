---
kind: D1-D2-reconstruction-evidence
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
workplan_revision: 8
gate: R1
protocol_version: 6.3.0
lifecycle: PROPOSED
current_authority_unchanged: true
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_carrier: 3937881ef00222e80845aa81f5471d89a4a7736c
branch: design/mlff-pi-train-fps-diversity-restoration
---

# R1 D1/D2 reconstruction evidence — latest mature `pi_train` / MVSEL2 method

## 1. Disposition and authority state

This artifact reconstructs the scientific (D1) and numerical/algorithmic (D2) semantics of the latest mature pre-P6 multi-view target-training selection path, then maps those semantics onto the accepted current one-`P_train` target-size architecture.

It is **not accepted-current authority**. Until independent D1/D2 falsification and stakeholder ratification complete, the accepted owners remain:

- `docs/methods/mlff_scientific_method.md` at `e72090e21cec5311ce87745b03603f8783cd15a7`;
- `docs/methods/mlff_numerical_algorithmic_method.md` at the same accepted project state.

The proposed authority overlays are:

- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D1_METHOD_AMENDMENT.md`;
- `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_D2_METHOD_AMENDMENT.md`.

No D4 restoration is authorized by this reconstruction alone.

## 2. Governing reconstruction question

The current D1 permits candidate-independent priority evidence but does not require genuine multi-view coverage. Current D2 concretizes that weak contract as condition round-robin with UID ordering whenever explicit priority evidence is absent. That implementation is compatible with the current papers but not with the stakeholder-directed restoration of the latest mature selection method.

R1 therefore asks:

> What exact scientific role and numerical method did the final mature pre-P6 `TargetCoverageReference -> FEAS1 -> NEIGHBOR1/MVIDX1 -> MVSEL2 -> REPAIR2 -> MVQUAL` chain implement, and which parts remain semantically compatible with the current single-`P_train`, configurable-ladder, one-P2/prepared-generation architecture?

## 3. Historical evidence basis

### 3.1 Primary recovered implementation carrier

The recovery carrier is:

`hjin98/mdstats@3937881ef00222e80845aa81f5471d89a4a7736c`

Material recovered implementation owners include:

- `mdstats/training_data/target_coverage.py`;
- `target_coverage_feasibility.py`;
- `target_coverage_exact_neighborhood.py`;
- `target_coverage_sparse_index.py`;
- `target_multi_view_selector_v2.py`;
- `target_multi_view_repair_v2.py`;
- `target_multi_view_qualification_v2.py`;
- `_target_multi_view_scoring.py`;
- the optimized execution/kernel/state/history owners enumerated by Revision 8.

Revision 8 separately requires R2 to reconcile this accessible carrier against the P6-recorded accepted P5A6 executable identity. R1 uses the carrier to reconstruct semantics; it does not claim that the carrier SHA alone is the accepted P5A6 integration identity.

### 3.2 Historical method/specification evidence

The main semantic records used in reconstruction are:

- `docs/history/mlff/retired_specs/mlff_target_data2c_mvsel2_forward_lazy_chain_spec.md`;
- `docs/history/mlff/retired_specs/mlff_data7_fitted_metrics_selection_spec.md`;
- `docs/history/mlff/retired_specs/mlff_target_subset_size_study_spec.md`;
- the accepted performance/qualification workplans identified in Revision 8.

Historical records are evidence for reconstruction, not current authority.

## 4. Reconstructed D1 scientific meaning

### 4.1 One pre-candidate labeled training population

The current exact `P_train` is the sole target-order domain. It is frozen before target-size candidate training. All restored membership evidence is fitted or projected only from candidate-independent evidence belonging to this population and its accepted ancestors.

The following never enter restored membership construction:

- `M3` labels or predictions;
- diagnostic `M1/M2` outcomes;
- target-size candidate training results;
- reducer state;
- post-selection CV or replay-monitor outcomes;
- calibration, locked, challenge, deployment or downstream physical evidence.

Use of **labels inside `P_train`** is intentional training-design evidence, not held-out validation. The historical method explicitly treated target force/energy/stress response channels as target-development coverage dimensions.

### 4.2 Four distinct measures must not be conflated

The reconstructed method distinguishes:

1. **cardinality measure** — target size `N` counts selected configurations;
2. **coverage reference mass** — within each multi-view family, empirical mass is balanced by P1 correlation unit and then by participating frame, preventing a temporally dense unit from dominating scientific coverage;
3. **training-loss influence** — P3 objective/weights/masks, fitted only after the order, do not choose membership;
4. **evaluation estimand** — the current P3 evaluation ladder and target-force reducer remain separate from membership coverage.

The historical correlation-balanced coverage measure does not redefine `N` as an effective-sample count.

### 4.3 Multi-view coverage dimensions

The latest mature method covered several scientifically distinct views of the same `P_train` population:

- universal local-structure/environment summaries;
- raw pair geometry and coordination summaries;
- target-development response/physical channels derived from the labeled training population;
- profile-specific selection features and profile environment classes when an accepted current profile provider supplies them;
- foundation-model residual/weakness channels when the target-size scientific protocol itself uses a frozen authenticated foundation checkpoint.

The last class is conditional in the current architecture. A from-scratch target-size protocol has no scientifically relevant foundation residual and must not acquire an unrelated model merely to satisfy the selector.

### 4.4 Hard coverage and hard support are membership admissibility, not model accuracy

A configured prefix is scientifically admissible only if independent qualification establishes both:

- sufficient reference-mass coverage in every required family, including required distributional extents; and
- every required membership-support obligation.

The restored baseline hard family threshold is 0.95 reference mass. Extent-bearing channels require support reaching the lower and upper 1% reference quantiles. These predicates characterize **training-set support**. They do not assert that a trained model meets a target-force accuracy threshold and do not rank two already-qualified target sizes.

Target-size ranking remains owned by the current P3 target-force response, practical-equivalence rule and reducer. MVQUAL may exclude an inadmissible membership; it may not rank or tie-break admissible memberships.

### 4.5 Required support concepts

The historical chain treated the following as hard support dimensions:

- condition support;
- structural-event support;
- profile-environment support when such a provider is active;
- lower/upper extent support for extent-bearing family channels;
- every P1 correlation interval/unit represented in the target-order domain.

The current P2 additionally supports explicit user hard-support obligations. Current reconciliation therefore requires one canonical obligation authority containing the restored automatic obligations plus current explicit obligations. Distinct semantic obligations remain distinct even when their incidence sets overlap; duplicate IDs or contradictory definitions fail closed.

The current P2 `condition_id` remains the sole target-size **condition** identity. P1 correlation-unit identity remains a separate protected-relation/provenance concept used for coverage weighting, mandatory correlation-unit support and balance. Historical `label_domain_id` fan-out is not restored.

### 4.6 Scientific ordering intent

Before hard requirements are satisfied, the order preferentially:

1. closes required support deficits;
2. advances the worst-covered multi-view family;
3. advances total required-family coverage;
4. balances correlation-unit representation;
5. improves representative mass coverage;
6. favors sparse diversity.

After hard coverage/support is satisfied, the same one order continues by representative gain, correlation balance, sparse diversity and deterministic final tie-breaking.

This is a **candidate-independent, coverage-progressive master order**. It is not one selector per target size.

### 4.7 Repair and qualification roles

REPAIR2 is part of the reconstructed membership method. At each configured target-size shell it may replace only members of the active shell, leaving every already-frozen smaller prefix unchanged. A repair is admissible only when hard support does not regress, no required-family coverage regresses beyond the numerical tolerance, and the exact lexicographic repair objective improves.

MVQUAL is independent membership qualification. It recomputes direct family coverage/extents and hard obligations from authenticated primitive evidence rather than trusting MVSEL2/REPAIR2 counters. This independence is scientifically important because internal optimization state is not its own adequacy proof.

## 5. Reconstructed D2 method

### 5.1 TargetCoverageReference

For a required family `m`, let `W_m` be its ordered reference witnesses. Each witness belongs to a P1 correlation unit. If `G_m` is the set of represented units and `n_{m,g}` is the number of participating witnesses/frames from unit `g`, then the final implementation assigns

```text
omega_m(w) = 1 / (|G_m| * n_{m,g(w)})
```

followed by exact FP64 normalization. Thus every represented correlation unit contributes equal family mass and every participating witness within a unit shares that unit's mass equally.

For each feature column, robust scale is:

1. weighted `q_0.75 - q_0.25` when greater than `1e-12`;
2. otherwise weighted `q_0.99 - q_0.01` when greater than `1e-12`;
3. otherwise `max(population_std, 1.0)`;
4. finally lower-bounded by `1e-12`.

Weighted quantiles use one stable ascending ordering and select the first value whose cumulative weight reaches the requested quantile mass.

For a `d_m`-dimensional family, distance is scaled RMS Euclidean distance:

```text
d_m(a,b) = sqrt( sum_j ((x_j(a)-x_j(b))/s_j)^2 / d_m ).
```

For each witness `w`, its local radius is the smallest leave-one-out neighbor distance at which normalized correlation-balanced cumulative mass reaches `beta = 1/128`. The local-radius cumulative comparison uses the recovered FP64 boundary `beta - 1e-15`.

The frozen exact NEIGHBOR1/MVIDX membership predicate is:

```text
d_m(w,c) <= r_m(w) + 1e-12 * max(1, r_m(w)).
```

This resolves a historical prose/code discrepancy: the retired chain specification wrote `d <= r`, while the final executable exact-neighborhood authority explicitly froze the `1e-12` metric tolerance and direct MVQUAL used the same tolerance.

### 5.2 Required family catalog

The final recovered baseline builds required families as follows.

**Universal structural families** from the accepted DATA6 universal local-structure contract, group/species resolved where provided:

`pair_distance`, `radial_environment`, `coordination`, `connectivity`, `chemical_environment`, `local_density`, `angular_environment`, `orientational_order`.

Extent obligations are attached to structural `pair_distance`, `coordination`, and `local_density` channels.

**Profile selection families**, when an accepted current profile provider exposes selection-stage scalar features: one required nonconstant valid scalar family per feature, with lower/upper extent obligations. Profile environment classes become required support strata.

**Raw pair-geometry families** for every applicable current pair rule:

- bond-length distribution: minimum pair distance and mean/maximum nearest-neighbor distance;
- coordination distribution: mean/maximum coordination.

These are required and extent-bearing.

**Target-development response families** from `P_train` labels/derived physical channels:

- one force-distribution family containing component RMS, force-norm mean/max and every canonical force-norm quantile channel present in the accepted raw feature evidence;
- nonconstant scalar families, when defined, for energy per atom, instantaneous temperature, hydrostatic strain, deviatoric-strain norm, pressure and deviatoric-stress norm.

These are required and extent-bearing.

**Foundation-residual families**, only when the target-size method uses a frozen authenticated foundation model:

- global absolute energy-error/atom and force-error summary vector;
- per-species force-error summary vectors.

These are required and extent-bearing. In the current one-`P_train` method they must be projected/fitted on exact `P_train`; the historical final-development/label-domain projection topology is not restored.

### 5.3 Coverage and extent predicates

For selected set `S`, witness `w` is covered when at least one selected candidate is adjacent under the exact neighborhood predicate. Family covered mass is

```text
C_m(S) = sum_{w in W_m} omega_m(w) * 1[w covered by S].
```

A required family passes mass coverage iff `C_m(S) + 1e-12 >= 0.95`.

For an extent-bearing raw channel `j`, let `L_j=q_0.01` and `U_j=q_0.99` under the same family weights. The selected representatives pass extent iff at least one selected value is `<= L_j + 1e-12` and at least one is `>= U_j - 1e-12`.

The final executable baseline has one uniform 0.95 required-family threshold. A retired prose allowance for unspecified family/profile threshold overrides had no corresponding final policy field and is therefore **not reconstructed as a current knob**. Any future family-specific threshold requires a separately accepted D1/D2 change.

### 5.4 Canonical hard-obligation set

The reconstructed automatic obligation set contains:

- every required condition stratum: minimum one;
- every required structural-event type observed in `P_train`: minimum one;
- every active profile-environment class: minimum one;
- every required extent lower/upper channel: minimum one support member per side;
- every P1 correlation interval/unit represented in `P_train`: minimum one.

Current explicit `ResolvedTargetSizePolicy.hard_support_obligations` are projected into the same canonical obligation owner using current P2 condition attributes and their declared minimum counts. All obligation IDs are canonical and unique. Contradictory reuse of an obligation ID fails closed. Distinct obligations may overlap in candidate incidence and remain distinct scientific requirements.

MVSEL2 hard gain is the **number of currently unsatisfied required obligations** to which a candidate belongs; it is not deficit magnitude.

### 5.5 FEAS1

FEAS1 verifies exact self-support/neighborhood consistency and hard-obligation capacity over the complete `P_train` candidate pool. Its fragility/support-degree reports are diagnostics. Its conservative cardinality lower bound may prove that no configured candidate can satisfy hard requirements.

The historical fixed maximum 16,384 is replaced by the current configured `N_max`. FEAS1 never creates a rescue size or relaxes a requirement.

### 5.6 MVSEL2 exact order

Let `n_m(w)` be current witness multiplicity, `C_m` family covered mass, `q_o` obligation counts, and `b_g` selected count for correlation unit `g`.

**Phase A** is active while at least one required obligation is unsatisfied or any required family has `C_m < 0.95 - epsilon`, with `epsilon = 1e-14` for contender comparisons. Available candidates are filtered lexicographically by:

1. maximum hard-obligation gain when any required obligation is pending;
2. choose the first canonical family minimizing `C_m/0.95`;
3. maximum newly covered mass in that bottleneck family;
4. maximum total newly covered mass across required families;
5. minimum current `b_g` of the candidate's correlation unit;
6. maximum representative gain
   `R(c)=sum_m sum_{w in A_m(c)} omega_m(w)/(n_m(w)+1)`;
7. maximum sparse diversity, the mean across nonempty family rows of the mean `1/(n_m(w)+1)`;
8. stable frame UID.

Every floating contender filter is inclusive: `value >= best - 1e-14`.

**Phase B**, after hard requirements are satisfied, filters by:

1. representative gain;
2. least-selected correlation unit;
3. sparse diversity;
4. stable UID.

The exact full-forward implementation is the numerical oracle. Certified lazy/native execution is admissible only when it yields the same ordered decisions.

The current master order is a complete permutation of `P_train`. After the last configured repair shell, state is reconstructed from the exact final repaired prefix and the same MVSEL2 phase logic continues to `P_train` exhaustion. No UID/scalar suffix or additional unconfigured repair shell is permitted.

### 5.7 REPAIR2

For configured candidate sizes in strictly increasing current ladder order, shell `i` is `[N_{i-1},N_i)` with `N_0=0`. Only active-shell members may be removed. A removable candidate must have unique covered mass `<= 1e-14` and be hard-safe.

Removal candidates are ordered by representative loss ascending, selected correlation-unit count descending, then removed UID, and truncated to 64. For each removal, replacement candidates use the same hard-gain / bottleneck-coverage / total-coverage frontier, then hypothetical correlation balance, pairwise representative gain, pairwise diversity and UID.

Repair objective is lexicographic:

```text
(hard_deficit minimized,
 minimum family coverage maximized,
 total family coverage maximized,
 harmonic representative utility maximized,
 -sum_g b_g^2 maximized).
```

Floating objective improvements use tolerance `1e-14`; correlation balance is exact integer final tie-break. Every accepted swap must strictly improve this objective and may not reduce any family coverage by more than tolerance. Policy limits are two passes per shell, at most 32 accepted swaps per shell, shortlist 64. Replacement inherits the removed rank; if it previously occurs in the future order, the removed member is displaced to that future rank. Lower configured prefixes remain immutable.

### 5.8 MVQUAL

For every configured materializable prefix, MVQUAL independently recomputes:

1. direct TargetCoverage family mass and extent predicates;
2. canonical hard-obligation counts;
3. label usability under current P2.

MVIDX-derived covered mass is a secondary exact cross-check and must agree with direct coverage within absolute `5e-12`; it is not the independent oracle itself.

A configured candidate is qualified iff the exact prefix exists, labels are usable, all required family mass/extent predicates pass and all canonical hard obligations pass. For nested prefixes these positive predicates are monotone; PASS->FAIL at a larger configured prefix is an invariant failure.

The current requirement of at least three qualified candidates for the target-size funnel remains unchanged. No rescue threshold or generated size is permitted.

## 6. Current-architecture reconciliation map

| Historical surface | Current R1 disposition | Reason |
| --- | --- | --- |
| per-label-domain/final+CV target-order domains | DROP | incompatible with current one-`P_train` P2 authority |
| exact P_train multi-view reference | RESTORE/REBIND | scientific capability still required |
| DATA7 fitted selector input owner | RESTORE/REBIND | evidence preparation, not membership owner |
| target-label coverage families | RESTORE | candidate-independent `P_train` training-design evidence |
| foundation residual families | RESTORE CONDITIONALLY | only when current target-size protocol uses authenticated foundation model |
| material/profile selection families | RESTORE CONDITIONALLY | only when accepted current provider supplies them |
| condition hard support | REBIND | current P2 `condition_id` is sole condition identity |
| correlation-unit coverage weighting/balance/support | RESTORE/REBIND | separate P1 protected/provenance concept, not a condition owner |
| historical fixed 128..16384 ladder | DROP | current ladder is configurable |
| 0.95 family coverage method | RESTORE | final mature membership-admissibility semantics |
| exact extent q01/q99 support | RESTORE | final mature hard support semantics |
| FEAS1 | RESTORE/REBIND | current `N_max`, no rescue sizes |
| MVIDX/NEIGHBOR exact relation | RESTORE/REBIND | numerical substrate for same method |
| MVSEL2 phases/ranking | RESTORE | latest mature order method |
| REPAIR2 active-shell repair | RESTORE/REBIND | shells are current configured sizes |
| MVQUAL independent qualification | RESTORE/REBIND | projects into current P2 qualification owner |
| historical fixed-universe target-size study/reducer | DROP | current P3 reducer/funnel remains owner |
| historical per-domain DATA7 prescribed prefixes | DROP | one current P2 `TargetTrainingOrder` owns membership |

## 7. Resolved historical contradictions

1. **Neighborhood boundary:** retired prose stated `d<=r`; final NEIGHBOR1/MVIDX/direct scorer freezes the `1e-12*max(1,r)` boundary tolerance. Proposed D2 adopts the final executable/qualified rule.
2. **Family threshold overrides:** retired prose permitted explicit named overrides; the final recovered `TargetCoveragePolicy` exposes only one threshold. Proposed method keeps uniform 0.95 and does not invent an override interface.
3. **DATA7 vs MVSEL2 ownership:** older DATA7 direct membership selection is not restored. Later DATA7 is fitted evidence input; MVSEL2/REPAIR2 owns membership.
4. **Fixed ladder:** historical fixed powers-of-two sizes are target-study topology, not intrinsic MVSEL2 science. Current configured sizes own repair shells and qualification rungs.
5. **Historical domain fan-out:** label-domain/fold selector domains are not scientifically retained because current authority has one exact `P_train` after upstream label reconciliation.
6. **Foundation residual source domain:** historical final-development residual projection could include evidence outside current `P_train`; current method refits/projects foundation weakness only on exact `P_train`.
7. **Full-order extent:** historical product work primarily qualified through 16,384. Current `TargetTrainingOrder` is a complete permutation; same MVSEL2 method therefore continues after the last configured repaired prefix to population exhaustion.

## 8. Leakage and metamorphic boundary

A valid restored method must satisfy:

- altering only `M3` labels or membership descendants cannot change `pi_train` when `P_train` and its selector inputs are unchanged;
- altering target-size candidate training outcomes, optimizer seeds, horizons, reducer evidence, CV, replay-monitor or downstream qualification cannot change `pi_train`;
- foundation-residual evidence may change `pi_train` only when the authenticated frozen foundation identity/predictions or authorized `P_train` labels change;
- profile families may change `pi_train` only through an accepted active profile provider identity/evidence change;
- execution worker count, native backend, chunking, queue completion order, cache state and restart path cannot change scientific order/repair/qualification outputs.

## 9. Evidence applicability and PEM/HAS

R1 uses the Revision-8 memory basis:

```yaml
pem_basis:
  accepted_project_state: e72090e21cec5311ce87745b03603f8783cd15a7
  accepted_pem: hjin98/mdstats@b5d101d8f73d3efd63ef4e70b3913e7d281406ce:PROJECT-ENGINEERING-MEMORY.md
  candidate_overlay_semantic_candidate: NONE
```

Relevant dispositions remain those frozen by Revision 8: SP-001..SP-004, FF-002 and FF-005 applicable; FF-001/FF-004 review-required only if model-derived selector evidence is active; FF-003 not applicable. PEM coverage is partial, so this R1 reconstruction uses direct historical intake as primary evidence for the August selector chain.

Historical tests/benchmarks support the reconstructed mechanisms but do not directly qualify current one-`P_train` rebinding. New current-domain falsification remains required after implementation.

## 10. R1 completion state

The reconstruction itself is complete enough to propose D1/D2 without an unresolved semantic placeholder. Remaining gates are governance/evidence gates, not hidden design choices:

1. independent D1/D2 falsification of the proposed overlays;
2. repair of any resulting Serious Challenge/blocker;
3. stakeholder human ratification of the exact proposed scientific/numerical method;
4. only then accepted-current D1/D2 promotion and R2 implementation dependency recovery.

Until those gates close, this artifact and its overlays remain **PROPOSED**.
