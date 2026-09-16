# Revision 2 workplan review — `pi_train` diversity restoration

Date: 2026-09-15
Reviewed: `MLFF_PI_TRAIN_FPS_DIVERSITY_RESTORATION_WORKPLAN_REVISION_2.md` at `be86b4214a09ca646b25335d3493e51edb4d981e`
Basis: mdstats `e72090e21cec5311ce87745b03603f8783cd15a7`
Disposition: **NO PASS — plan-level blockers remain; repair in Revision 3 before implementation.**

## Strengths confirmed

Revision 2 corrects the principal error in Revision 1: reuse is now decided by current semantic fit rather than age. The current DATA7 lineage is correctly recognized as the leading reuse path because DATA5, model-free DATA6 builders, the fitted metric framework, exact FPS state/kernels, structural/environment queues and coverage scorer still exist. MVSEL2/REPAIR2 remain eligible but are correctly classified as deleted historical components requiring explicit dependency resurrection.

The plan also correctly preserves one P2/current prepared-generation owner, exact nested prefixes, current P_train/M3 split and evaluation semantics, and explicitly blocks label-derived membership in the baseline.

## Blocking gaps

### B1 — DATA6 acquisition/currentness is not closed

Current public `prepare` only invokes `_prepare_catalog` when DATA5 is missing/rebuilt or live preparation inputs changed, and passes only DATA4 into `build_prepared_target_size_substrate`. A reusable `data6` record is permitted by the cutover, but it is not guaranteed to exist and the current P1/P2 builder does not consume it.

Revision 2 says to reuse/build DATA6 but does not define the fail-closed acquisition rule. It could therefore accidentally force a whole lower-catalog rebuild, load a model-dependent DATA6 path, overwrite a richer existing DATA6 record with a model-free bundle, or create a second DATA6 lifecycle.

**Required repair:** current `prepare` must first revalidate an existing compatible DATA6 structural record through its owner. If no compatible structural evidence exists, build only the required model-free structural evidence through the existing DATA6/structural providers inside `prepare`, without MACE inference/difficulty and without destructively replacing unrelated richer DATA6 evidence. Persist only what the target-order prepared generation needs under its own immutable generation, or publish through an existing safe reusable record boundary if identity-equivalent. Downstream commands never rebuild it.

### B2 — prepared-generation persistence shape is under-specified

`campaign_prepared_generation.py` has a fixed `PREPARED_COMPONENT_NAMES` tuple and exact type map under schema v1. Revision 2 requires a fitted metric and coverage evidence to be reloadable but does not state whether they are embedded in the aggregate or become explicit prepared components. An implementation could therefore invent parallel storage or leave `selection_evidence_digest` unauthenticated on reload.

**Required repair:** make target-order evidence a first-class child of the one prepared generation. Prefer reuse of `FittedFeatureMetric` and existing coverage-report records rather than a second database. If separate components are used, version the prepared manifest/type map coherently and keep old generations historical; if embedded, prove the aggregate remains bounded and independently validates all lineage. On reload, aggregate/order authentication must verify the exact target-order evidence identity rather than trusting a digest with no bound object.

### B3 — condition authority can accidentally split between P2 and historical DATA5

Current `TargetSizePopulation`/P2 `condition_id` is the target-size condition authority. Historical selector code also derives condition buckets from DATA5 units. Revision 2 permits DATA5 context but does not explicitly forbid it from becoming a second condition owner.

**Required repair:** P2 condition IDs remain authoritative for target-order support/scheduling. DATA5 condition/unit metadata may be used only when D2 explicitly requires an additional structural/correlation fact and its relation to P2 is defined. No selector may silently substitute historical DATA5 condition grouping for current P2 condition identity.

### B4 — resurrected MVSEL2 policy constants/inputs are not sufficiently quarantined

Historical MVSEL2 binds a 0.95 hard family-coverage threshold, 1e-14 contender tolerance, sparse witness radii, correlation balancing and training-domain difficulty inputs as scientific policy. Revision 2 says MVSEL2 may be restored if needed but does not explicitly prohibit those constants/inputs from acquiring current authority merely through reuse.

**Required repair:** R0 must separate **engine reuse** from **historical policy reuse**. Every MVSEL2/REPAIR2 scientific input/predicate must map to accepted current D1/D2 or be removed/reclassified before resurrection. In particular, historical hard thresholds, witness radii, difficulty inputs and tie tolerances are not inherited automatically.

### B5 — target-order preparation identity is incomplete

The current prepared configuration identity binds neutral partition, target-size policy and common-training policy. A restored metric/provider/selector policy can change `pi_train` while those existing digests remain unchanged unless the new method is explicitly included in a preparation-owned identity.

**Required repair:** add the accepted target-order feature/metric/selector policy identity to the current preparation configuration and P2/aggregate ancestry, either through an expanded `ResolvedTargetSizePolicy` digest or a separately named target-order policy digest. A change must force a new prepared generation before any downstream exposure.

### B6 — reuse path needs a concrete absence test for deleted MVSEL2 dependencies

The old MVSEL2/REPAIR2 modules named by the historical contract are absent from current main. R0 must not treat historical benchmarks/specs as proof that current code can simply import them.

**Required repair:** R0 must record code-availability/dependency closure. Restoring MVSEL2 means restoring the coherent implementation dependency set (sparse forward/index types, selector, repair, state and any required independent qualifier), with current package/build/test integration. If that closure is larger than the accepted requirement, the still-current DATA7 route wins unless the extra semantics are materially required.

### B7 — structural-feature materialization must not become a model prerequisite

The current DATA6 API can be model-free, but its default policy may enable model work when a model provider is supplied. A careless current-prepare integration could turn target-order preparation into a foundation-model inference requirement.

**Required repair:** the baseline target-order structural acquisition path must explicitly pass/resolve a model-free policy/provider set and have a negative integration test proving no MACE/model provider/checkpoint/inference is accessed.

## Nonblocking clarifications to incorporate

- Historical `build_training_selection_plan` only materializes through `max(target_sizes)` and has UID fallback; Revision 2 already catches this, but acceptance should explicitly test the suffix/full-continuation behavior.
- Historical `raw_physical` is label-contaminated for this purpose; Revision 2 correctly rejects the default block policy.
- Raw partition-independent structural descriptors may be generated over a broader authorized domain, but any dataset-fitted transform declared P_train-fitted must be invariant to M3-only changes.
- Existing cutover code explicitly classifies `data6` as reusable lower-level content, supporting reuse after owner revalidation; it does not make old DATA6 target-size authority current.

## Review decision

Revision 2 is directionally correct but not implementation-ready because B1-B7 allow materially different or architecturally unsafe implementations while claiming plan conformance. Produce Revision 3 closing these points, then re-review the assembled plan.