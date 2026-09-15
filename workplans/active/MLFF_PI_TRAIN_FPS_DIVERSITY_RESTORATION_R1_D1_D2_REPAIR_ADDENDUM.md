---
kind: proposed-R1-D1-D2-repair-addendum
workplan_id: MLFF-PI-TRAIN-FPS-DIVERSITY-RESTORATION-1
gate: R1
protocol_version: 6.3.0
lifecycle: PROPOSED_NOT_ACCEPTED
basis_commit: e72090e21cec5311ce87745b03603f8783cd15a7
recovery_snapshot: 3937881ef00222e80845aa81f5471d89a4a7736c
supersedes_conflicting_R1_text: true
---

# R1 D1/D2 repair addendum — independent-review blocker closure

## 1. Authority and scope

This addendum repairs the blocking findings from the first independent review of the proposed R1 D1/D2 reconstruction. It is part of the proposed R1 candidate and is **not accepted-current authority**. Where this addendum conflicts with the earlier R1 proposed D1 amendment, D2 amendment, reconstruction evidence, or handoff, this addendum controls the proposed candidate.

Accepted-current D1/D2 remains exactly the method papers at `e72090e21cec5311ce87745b03603f8783cd15a7`. R2/D3/D4 implementation remains unauthorized until independent re-review passes, the stakeholder ratifies the exact candidate, and the accepted method papers are explicitly promoted/reconciled.

The repair is intentionally narrow. It does not change current `U_size -> P_train + M3`, `pi_eval/M1/M2/M3`, P3 ranking/reducer semantics, post-selection CV, replay, production, or final GPU-qualification deferral.

## 2. D1 repair — one selector-specific fitted owner

For the restored target-order subchain, **`TargetCoverageReference` is the sole selector-specific fitted numerical owner**.

The historical DATA7 specification at recovery snapshot `3937881...` describes `TargetSubsetInputBundle` as a fitted selector-input product. However, the mature executable at the same coherent snapshot, `mdstats/training_data/target_coverage.py`, constructs `TargetCoverageReference` directly from upstream target-data products/role freeze/foundation audit and does not consume a DATA7 bundle. Restoring an independently materialized DATA7 fitted metric and also fitting the TargetCoverageReference would therefore create duplicate fitted authority not present in the mature executable path.

The restored interpretation is:

1. DATA7 retains **logical lineage/input semantics** relevant to selector construction: authorized-domain identity, condition/provenance/correlation identities, event/environment/profile applicability, representative/diversity inputs, training-domain difficulty inputs, and hard-obligation applicability;
2. those inputs are rebound to exact current `P_train` under the current one-population architecture;
3. `TargetCoverageReference` alone owns the fitted selector numerics: family witness rows, correlation-balanced weights, robust scales, weighted quantiles/extents, local radii, family applicability and the selector-facing fitted reference identities;
4. no second fitted metric/scaler/PCA/target-subset bundle is restored merely to preserve the historical DATA7 name;
5. historical DATA7 objects unrelated to the MVSEL2 membership chain (for example atomic-reference fitting, training-objective policy, checkpoint metric policy) remain outside this restoration unless separately required by accepted current owners.

This is a local contradiction resolution for the target-order subchain, not a repeal of DATA7 as a historical stage concept.

## 3. D1 repair — family threshold authority

At coherent recovery snapshot `3937881...`, the active executable and release evidence support one instantiated hard family threshold:

```text
coverage_threshold = 0.95
```

The integrated historical chain specification contains a generic hook permitting an explicitly identified material/profile policy to define another threshold for a named family. The reconstruction census found no instantiated selector policy, active material/profile policy record, policy map, or qualification identity at the coherent snapshot that supplies a different named-family threshold. In contrast:

- `TargetCoveragePolicy` exposes one scalar `coverage_threshold`, default/frozen at `0.95`;
- MVSEL2 receives one scalar coverage threshold;
- MVQUAL2 exposes one scalar coverage threshold; and
- historical selector qualification evidence records `coverage_threshold: 0.95` as the authority.

Therefore the restored baseline maps **every applicable required family to threshold 0.95 owned by the reconstructed `TargetCoveragePolicy` identity**. The historical named-family override clause is classified as **dormant/uninstantiated capability**, not as an active policy that may be silently varied at runtime.

A future named-family override requires newly accepted D1/D2 policy authority that identifies the family, threshold, applicability domain and policy identity. D3/D4 may not infer or invent such an override.

## 4. D1/D2 repair — canonical hard-obligation semantics

The canonical restored obligation set is defined before any obligation ID is assigned:

```text
O_canonical = semantic_dedup(
    O_automatic_restored
    union O_current_explicit
    minus O_retired_topology
)
```

where `O_retired_topology` includes obligations whose meaning exists only because of removed historical label-domain/fold target-size fan-out.

### 4.1 Semantic identity

For each obligation, define a normalized semantic key

```text
K(o) = (
  obligation_kind,
  applicability_scope,
  family_identity_or_none,
  target_identity,
  relation_or_side,
  normalized_required_minimum,
  applicability_domain
)
```

with the following interpretation:

- `obligation_kind` distinguishes condition support, structural-event support, profile-environment support, extent support, P1 correlation-unit support, and an accepted explicit support kind;
- `applicability_scope` is the current exact `P_train` scope plus any accepted narrower provider-defined applicability;
- `family_identity_or_none` is present for family/extent obligations and absent otherwise;
- `target_identity` is the canonical current condition/event/profile class/extent channel/correlation-unit/explicit target identity;
- `relation_or_side` distinguishes semantics such as lower versus upper extent support;
- `normalized_required_minimum` is the positive integer minimum selected count after current policy normalization;
- `applicability_domain` binds the current policy/provider identity needed to interpret the target.

Source display names, source-local obligation IDs and source file/stage names are **not** part of semantic identity.

### 4.2 Canonicalization algorithm

1. Project every retained automatic obligation and every current explicit `ResolvedTargetSizePolicy.hard_support_obligations` entry into current `P_train` semantics.
2. Drop any obligation whose only meaning is retired target-size topology.
3. Normalize each remaining obligation into `K(o)` plus exact candidate-incidence semantics.
4. Group by `K(o)` **before** assigning canonical obligation IDs.
5. Exact semantic aliases — same normalized key and same incidence semantics — collapse to one canonical obligation. Preserve all contributing source aliases only as provenance.
6. If two source records reuse the same supplied source ID but normalize to different semantics, preparation fails closed.
7. If records refer to the same semantic locus but disagree on minimum count, incidence, applicability, family, side, or other requirement semantics, they are not silently merged. Preparation fails closed until the owning policy is adjudicated.
8. Assign one deterministic canonical ID per surviving semantic record after deduplication.
9. Build MVIDX obligation incidence and all selector/repair/qualification counts from this canonical set only.

### 4.3 Numerical consequence

MVSEL2 hard gain remains

$$
H(c)=\#\{o\in O_{canonical}: o\text{ required, unsatisfied, and }c\text{ helps }o\}.
$$

Thus source aliases cannot change `H(c)`, candidate rank, repair behavior, or qualification.

### 4.4 Mandatory metamorphic falsification

Adding, removing, renaming, or reordering an **exact semantic alias** must leave all of the following bit-for-bit/identity-equivalent under unchanged canonical inputs:

- canonical obligation set;
- `pi_train` selection history;
- configured REPAIR2 trace/result;
- MVQUAL pass/fail and unsatisfied canonical-obligation set.

Failure is a D2 method violation.

## 5. D2 repair — certified-lazy MVSEL2 numerical contract

The full-forward MVSEL2 comparator defined in the proposed R1 D2 amendment is the exact scientific/numerical oracle. An optimized lazy implementation is conforming only if it satisfies the following certification invariant; equality of final cardinality alone is insufficient.

### 5.1 Phase transition rebase

At the Phase-A -> Phase-B transition, and after any authoritative state reconstruction that invalidates representative marginals, score **every currently available candidate exactly** under the current Phase-B state. This all-candidate rebase establishes generation `g` and one exact representative score `R_g(c)` for every available candidate.

The initial lazy bound for candidate `c` is an outward-rounded upper bound

```text
B_g(c) = nextafter(R_g(c), +infinity)
```

or a numerically stronger bound proven to be at least as conservative under the same binary64 semantics.

### 5.2 Stale-bound invariant

After subsequent selections, a cached score from an earlier generation may not be treated as the candidate's current exact score. It may be retained only as a conservative upper bound while the representative-gain functional is monotone non-increasing under the selected-state update.

When a stale candidate `c` is refreshed at current generation `h`, compute exact `R_h(c)`. If the implementation uses the recovered monotonicity guard, an increase beyond the accepted numerical guard (`5e-13` in the recovery executable) is an invariant failure, not a reason to widen scientific tolerance. The refreshed bound is outward-rounded with `nextafter(R_h(c), +infinity)`.

### 5.3 Exact incumbent and certification

Maintain an exact incumbent score `R_best` from candidates refreshed/evaluated in the current generation. Consider candidates in descending conservative-bound order. A stale candidate whose bound can still reach the inclusive contender region must be refreshed exactly.

The representative contender set is certified only when the greatest remaining stale bound satisfies

```text
B_max < R_best - epsilon
```

with exact selector contender tolerance

```text
epsilon = 1e-14.
```

At that point, every candidate capable of satisfying

```text
R(c) >= R_best - epsilon
```

has an exact current score and is present in the certified contender set.

Apply the remaining Phase-B comparator only to this certified exact contender set:

1. least-selected correlation-unit count;
2. maximum sparse diversity within `1e-14`;
3. minimum stable UID.

### 5.4 Fallback and oracle equivalence

If a bound cannot be proven conservative, certification cannot terminate, a cache generation is inconsistent, or a numerical invariant is violated, discard/rebuild the lazy frontier or fall back to the exact full-forward oracle. Optimized execution may cost more work; it may not choose a different UID.

For every selected rank, the chosen UID must equal the full-forward oracle under the same canonical state. Qualification must include oracle-equivalence fixtures that exercise epsilon ties, stale-bound refresh, rebase, restart/rebuild, and fallback.

### 5.5 REPAIR2 invalidation boundary

Any accepted REPAIR2 swap changes authoritative selected-prefix state. All lazy/frontier entries, score generations, cached candidate marginals, reconstructible representative summaries, and selection-history state whose validity depends on the pre-swap state are invalid after that divergence.

Before suffix continuation, reconstruct exact forward state from the repaired prefix and perform the required exact Phase-B rebase if continuation begins in Phase B (or reconstruct the exact Phase-A state until the transition occurs). A pre-repair lazy frontier may never be continued across the swap boundary.

Heap layout, queue implementation, mmap strategy, worker scheduling, OpenMP/native execution and cache placement remain D3/D4 choices so long as this D2 invariant and exact full-forward rank history are preserved.

## 6. D2 repair — exact restored policy dispositions

The following recovered policy fields are explicitly classified for the proposed current reconstruction. Detailed immutable evidence is in `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_R1_EXACT_RECONSTRUCTION_LEDGER.md`.

### 6.1 TargetCoveragePolicy

RESTORE/REBIND to exact current `P_train`:

- `coverage_metric = reference_mass_local_knn`;
- `coverage_threshold = 0.95`;
- `coverage_resolution_mass = 1/128`;
- `coverage_leave_one_out = true`;
- `extent_quantile_alpha = 0.01`;
- `metric_minimum_scale = 1e-12`;
- required/extent structural family catalogs;
- condition/event/profile-support booleans;
- `minimum_family_elements = 2`.

The policy version/schema is historical evidence, not a requirement to preserve obsolete serialization naming.

### 6.2 FEAS1

- `support_degree_bins = (2,4,8,16,32)`: RESTORE as diagnostic evidence only; it does not rank candidates.
- `exclude_own_correlation_unit = true`: RESTORE as the recovered cross-support fragility diagnostic semantics.
- `fragile_zero_mass_tolerance = 1e-12`: RESTORE as FEAS1 diagnostic numerical policy.
- historical `maximum_candidate_size = 16384`: DROP as obsolete fixed-universe topology; current capacity is derived from current `P_train`/configured ladder policy and must not resurrect the old fixed-eight ceiling.
- authority/schema versions: REBIND to current artifacts; do not make historical serialization identifiers scientific constants.

### 6.3 NEIGHBOR1/MVIDX1

RESTORE exact neighborhood identity:

```text
d <= r + 1e-12 * max(1,r)
```

and required-family sparse indexing. MVIDX recovered dtypes/layout are implementation/persistence constraints only where current architecture requires exact artifact compatibility; scientific identity is adjacency/content/canonical ordering, not an obsolete file layout.

### 6.4 MVSEL2

RESTORE the two-phase comparator, `1e-14` inclusive best-relative tolerance, binary64 decision arithmetic, stable UID final tie, hard gain over canonical obligations, exact full-forward oracle and certified-lazy invariant in Section 5. Old per-label-domain/fixed-ceiling topology is DROP/REBIND to one exact current `P_train` and current configured ladder.

### 6.5 REPAIR2

RESTORE:

- unique-coverage tolerance `1e-14`;
- gain-tie tolerance `1e-14`;
- maximum 2 passes per shell;
- maximum 32 swaps per shell;
- removal shortlist 64;
- active-shell-only;
- replacement-rank inheritance;
- strict no-coverage regression;
- `clustering_score_authority = diagnostic_only`.

Clustering is not promoted to selection authority.

### 6.6 MVQUAL

RESTORE independent direct coverage/obligation qualification and FAIL* -> PASS* monotonicity. REBIND the candidate-size universe from historical fixed powers of two to current strictly increasing configured `ResolvedTargetSizePolicy.candidate_sizes`. Direct TargetCoverage scoring is the qualification oracle; MVIDX recomputation is a secondary exactness cross-check with absolute tolerance `5e-12`, not an alternate selector.

## 7. Required independent re-review questions added by this repair

The next independent reviewer must explicitly falsify:

1. whether semantic obligation dedup occurs before IDs and hard-gain scoring and is alias-invariant;
2. whether conflicting same-locus obligations fail closed rather than silently merge;
3. whether exactly one fitted selector numeric owner remains (`TargetCoverageReference`);
4. whether any required historical DATA7 semantic input was lost when duplicate numeric ownership was rejected;
5. whether the threshold census justifies uniform 0.95 and correctly classifies the override hook as dormant rather than active;
6. whether the lazy certification invariant is sufficient to derive the same UID at every rank as full-forward MVSEL2;
7. whether REPAIR2 invalidates/reconstructs all stale post-swap lazy state before suffix continuation;
8. whether the field-by-field reconstruction ledger accounts for every policy field relevant to scientific/numerical behavior.

## 8. Gate disposition

This repair closes the authoring defects identified by the first independent review, but the repair author does **not** self-approve the candidate. The repaired R1 state is:

```text
PROPOSED_D1_D2_REPAIRED_AWAITING_INDEPENDENT_REREVIEW
```

Independent re-review and stakeholder ratification remain mandatory before promotion or R2 implementation.