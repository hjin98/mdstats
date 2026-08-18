# mdstats 0.20.164a0 - FOUNDATION-AUDIT1 target-side foundation baseline

This release implements the second gate of the post-0.20.162 target-accuracy and structural-stability roadmap. It freezes the untouched foundation model's target-side baseline before any target training is authorized. It does not yet implement TARGET-DATA2B reference-mass coverage or the target-size funnel.

## Frozen foundation target audit

A new immutable `FoundationTargetAudit` is derived from the already-completed DATA6 production model sweep and the TARGET-DATA2A role freeze. The audit binds:

- the exact training-eligible development frames for every label domain;
- source, frame, DATA5, DATA6, and TARGET-DATA2A digests;
- the exact foundation checkpoint identity and checkpoint SHA-256;
- the completed DATA6 model-sweep checkpoint and prediction manifest;
- the target-model audit policy; and
- any DATA6 universal structural-provider identities used for conditioned diagnostics.

The audit is persisted as `foundation_target_audit` and is part of the prepare restart receipt. `preflight` and `train` both authenticate the frozen authority and fail closed if it is missing or stale.

## No repeated foundation inference

FOUNDATION-AUDIT1 consumes the verified per-frame prediction sidecars already materialized by DATA6. It never invokes the foundation calculator again. This makes restart inexpensive and guarantees that the baseline is computed from the exact prediction evidence already used to construct DATA6 residual difficulty.

## Static target-side diagnostics

For each TARGET-DATA2A development domain, FOUNDATION-AUDIT1 persists:

- energy MAE per atom;
- force-component RMSE;
- stress-component RMSE when stress labels/predictions exist;
- species-macro and per-species force-component RMSE;
- exact P90/P95/P99 per-atom force-vector error tails;
- corresponding absolute force-component quantiles; and
- when DATA6 structural evidence is materialized, quantile-conditioned force-error summaries for generic pair-distance, angular-environment, and smooth-coordination channels.

The generic `TargetModelAuditPolicy` and metric records are public so later candidate evaluation can use the same semantics rather than inventing a second target-adequacy definition.

## Physical probe contract

Finite-displacement restoring-force and zero-K relaxation/topology probe identities are frozen at this gate, but their numerical protocols remain intentionally owned by PES-VERIFY1 and RELAX-VERIFY1. Their first-release status is `deferred_protocol`; no physical pass is fabricated. A future candidate cannot claim matched physical-probe evidence unless the corresponding foundation-side result is materialized under the same probe authority.

## Qualification

The focused qualification covers exact role/domain authority, cached-prediction metric arithmetic, force tails, per-species aggregation, structural-conditioned reductions, zero-reinference behavior, deterministic serialization/restart, stale-lineage rejection, deferred-probe semantics, prepare-receipt binding, and existing TARGET-DATA2A/DATA5/DATA6/campaign CLI regressions.

Result: **85 passed, 1 skipped**. The skip is the existing real-LTA-root campaign CLI integration test because an external training root is not supplied to the synthetic qualification environment. The separate historical DATA0 architecture specification still contains its pre-existing hard-coded `0.20.140a0` version assertion and is not part of the focused gate pass count.
