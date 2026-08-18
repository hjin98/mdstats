# mdstats 0.20.166a0 - TARGET-DATA2C deterministic nested target-size ladder

This release implements TARGET-DATA2C of the post-0.20.162 target-accuracy and structural-stability roadmap. It consumes the frozen TARGET-DATA2A role authority and TARGET-DATA2B reference-mass coverage authority to create one deterministic ranked target-development ordering and exact nested candidate subsets. TARGET-DATA2D Stage-A elimination and all later training/evaluation gates remain outside this release.

## Immutable seven-rung ladder authority

A new `TargetDataLadderPlan` is derived from the authenticated target-development domains and the TARGET-DATA2B reference. The default requested ladder is fixed at:

- 128;
- 256;
- 512;
- 1024;
- 2048;
- 4096; and
- 8192 target configurations.

Each materializable rung is exactly a prefix of one frozen master ordering, so membership is nested by construction. Requested rungs larger than the authorized pool are retained as explicit unavailable records rather than being silently truncated or fabricated. Construction fails closed when fewer than the configured minimum of three requested rungs are materializable.

Every materialized rung embeds its TARGET-DATA2B coverage report against the same immutable full reference. Nested coverage monotonicity is audited immediately. TARGET-DATA2C records this evidence only; it does not decide which rungs survive the later Stage-A coverage screen.

## Quota-first physical and lineage obligations

The master ordering first reserves the minimum representatives needed to satisfy mandatory support obligations. These comprise:

- every required TARGET-DATA2B condition/event/profile support stratum; and
- every TARGET-DATA2A correlation-aware development interval when interval reservation is enabled.

The quota reservation is deterministic. At each step it prefers the candidate satisfying the largest number of unmet obligations, then resolves ties by novelty in the frozen fused metric and finally by stable frame identity. Each materialized rung records a separate `mandatory_obligations_passed` flag and the exact unsatisfied obligation identities. This prevents a rung from appearing acceptable merely because its continuous reference-mass coverage is high while a long trajectory interval or rare mandatory regime is absent.

## Hierarchically normalized exact diversity ranking

After quota reservation, the remaining authorized pool is filled with deterministic exact maximin farthest-point sampling. The selector uses every required TARGET-DATA2B family in one fused metric while preventing high-dimensional or highly enumerated families from dominating by coordinate count:

1. each family is scaled by its frozen TARGET-DATA2B coordinate scales and robustly centered;
2. a presence coordinate distinguishes genuinely applicable family evidence from center-imputed non-applicability;
3. each family block is normalized by its dimensionality;
4. families receive equal budget within their semantic family; and
5. semantic families receive equal budget globally.

The ranking therefore remains one globally nested ordering rather than a merge of independently selected family-specific subsets. The exact FPS kernel reuses the optimized selector implementation and does not introduce an approximate or stochastic nearest-neighbor stage.

## Campaign integration and restart

`target_data_ladder` is part of the prepare restart receipt and the prepare contract is bound to `TARGET_DATA_LADDER_VERSION`. Preparation deterministically reuses an authenticated ladder when its policy and upstream identities match, and rebuilds it when those authorities are stale. Preflight and training authenticate TARGET-DATA2C after TARGET-DATA2B before proceeding.

The generated and example TOML configuration exposes the ladder exponents, minimum materializable-rung count, mandatory-stratum reservation, correlation-interval reservation, and FPS tie tolerance. The policy digest is part of the immutable authority.

## Gate boundary

This release does **not** implement TARGET-DATA2D. In particular, it does not eliminate rungs, apply the Stage-A `C >= 0.95` survivor rule, cap survivors at four, run the 10-epoch/30-epoch convergence funnel, or choose a final target size. It only materializes and authenticates the candidate ladder and the evidence required by those later decisions.

## Qualification

Focused and campaign-level tests cover exact prefix nesting, deterministic restart identity, quota front-loading, mandatory-obligation evidence, unavailable-rung representation, the minimum-three-rung fail-closed rule, policy/stale-lineage rejection, real TARGET-DATA2A/TARGET-DATA2B integration, campaign receipt persistence/reuse, and manual/public contract checks. The exact FPS kernel was also benchmarked on a 36,000-frame, 64-dimensional pool selecting 8,192 representatives to verify that the deterministic exact implementation is operationally reasonable for the intended target-size ceiling.
