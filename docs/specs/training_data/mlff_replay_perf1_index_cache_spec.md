# REPLAY-PERF1 replay source-index/cache specification

## Status

Implemented in mdstats 0.20.234a0 / MLFF architecture revision 101.

## Scientific invariants

REPLAY-PERF1 is an exact-equivalence execution gate. It MUST NOT change:

- the single selected replay ExtXYZ as external replay authority;
- `ReplaySourceArtifact`, canonical replay geometry identity, or source true-label identity semantics;
- deterministic 5:1 train/monitor split membership or split seed/rank authority;
- independently retained source true labels;
- foundation-prediction policy, checkpoint/head identity, prediction values, shard identity, or qualification thresholds;
- pseudo-label train/monitor view labels or true-label monitor authority;
- replay-retention/admissibility semantics;
- MACE-MPA-0 versus MACE-MH-1 model-family behavior.

The index is reconstructible execution state and is never a replacement scientific authority.

## Source index

`ReplaySourceIndex` uses schema `mdstats.replay-source-index.v1`. Its receipt uses `mdstats.replay-source-index-receipt.v1`.

The index is bound to:

- exact source SHA-256;
- `ReplaySourceArtifact.content_digest`;
- ordered `ReplaySourceArtifact.source_index_digest`;
- exact source byte size;
- ordered frame byte offsets and lengths;
- per-frame atom counts.

The source locator is not scientific identity. An identical source relocated to another path MAY rebind the locator without changing index content identity. A source-byte mutation, stale/corrupt receipt, count mismatch, or index-authentication failure MUST rebuild or fail closed rather than silently reuse stale offsets.

Parser chunk size, buffer size, worker count, and cache directory MUST NOT enter replay scientific identity.

## Indexed frame access

Requested source indices MUST be strictly increasing and unique. Sparse selections seek directly to their indexed frame payloads. Contiguous selected frames MAY be coalesced into bounded parse chunks. Yield order remains increasing source index and is invariant to parse chunk size.

For authenticated indexed reads, source-order geometry identity is taken from the already-authenticated `ReplaySourceArtifact.geometry_identities[source_index]`. Recomputing the canonical geometry hash after each ASE parse is unnecessary execution work and MUST NOT be required for scientific equivalence once the source SHA and index authority have been validated.

## Materialization and prediction integration

The canonical single-source campaign builds/reuses the source index beneath `.mdstats/replay-unified/source-index` and supplies it to:

- true-label train/monitor view materialization;
- pseudo-label train/monitor view materialization;
- foundation-prediction cache source iteration.

Monitor-only reconstruction MUST NOT scan unrelated train frames. Full train+monitor materialization still parses every required frame and therefore is expected to gain less than sparse reconstruction.

Existing authenticated materialized-view and prediction-cache hits remain earlier exits and MUST NOT reopen the source.

## Parser concurrency decision

Python-threaded ASE ExtXYZ chunk parsing was directly benchmarked during the gate and was slower than one parser lane on the qualification host. REPLAY-PERF1 therefore keeps ExtXYZ parsing serial. This is a measured implementation decision, not a prohibition on future exact-equivalent parser work if a later profile identifies a faster backend.

## Acceptance authority

The supplied 12,000-frame replay source has SHA-256 `187eed42fb2d6cf5e7e745ffed0ce34541e92c6a35ec9e654520cd3c7198403c` and source-artifact digest `9f43677d6100cea85f6de287fe1dd739322609fd82cbeb320e46f9434ce90688`.

The qualified index content digest is `ce6c678ad556cff63be8ee75754d87cba2b3d08e80f544c5983fe4498dc0c5e1`.

Same-host paired evidence against untouched 0.20.233a0 records:

- monitor-only true-label materialization: approximately 9.139 s -> 3.012 s median (~3.03x), exact logical digest `633aae8a6deb1a3d857880f3eecd9bb40dbaedba8357a13944184c1bafbf1114`, and exact output SHA-256 `cc0f9b308becd5c027a2adc64fc251808323e19c217412d82ea3d50b3deab2cf`;
- complete source parse plus geometry-identity bookkeeping: approximately 7.642 s -> 6.423 s (~1.19x), exact ordered-identity digest `89d5b7a678ed846557c1f15f6592058e9ee3b78d81eb3516a320d2eabca7659f`;
- complete train+monitor materialization: approximately 15.676 s -> 14.348 s (~1.09x), exact train logical digest `8d7a29c35443cd8a8e7b2142157dce7c9804c8137d4a42e824edef9e42240901`, exact train SHA-256 `e6977082593a5b5610292e13ae49df7afbdbb7744ea9fe496952952474636f8c`, and the same exact monitor artifacts above.

The one-time byte-index build is approximately 0.451 s and an authenticated persisted hit approximately 0.071 s on the qualification host.

Timing is execution evidence. Replay source/split/label/prediction/view identities remain scientific authority.

The next optimization gate is `CAMPAIGN-PERF-QUAL1`.
