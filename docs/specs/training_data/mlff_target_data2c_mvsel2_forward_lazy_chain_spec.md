# TARGET-DATA2C MVSEL2/MVSTATE2/REPAIR2 forward-lazy chain specification

**Release:** `mdstats 0.20.242a0`  
**Architecture:** revision 104  
**Status:** implemented current production chain; v1 identities remain readable

## Scientific contract

MVSEL2 preserves target sizes `(128, 256, 512, 1024, 2048, 4096, 8192, 16384)`, coverage threshold `0.95`, default gain tolerance `1e-14`, FP64 scoring, canonical family/candidate/witness order, hard obligations, correlation units, and stable UID ties. Every floating contender filter is `value >= best - epsilon`. The hard-coverage criterion order is maximum hard gain, first canonical minimum-coverage family, bottleneck gain, total coverage gain, least-selected correlation unit, harmonic representative gain, sparse diversity, and UID. Representative fill uses representative gain, correlation balance, diversity, and UID.

## Execution contract

MVSEL2 and REPAIR2 consume only the MVIDX1 candidate-to-witness, candidate-to-obligation, and correlation-code projection. They do not map inverse witness arrays or maintain complete candidate marginal arrays. Phase A uses exact staged forward scans. Phase B begins with an exact all-candidate rebase; lazy scores are outward-rounded conservative upper bounds and are refreshed until the entire best-relative contender set is certified. Full-forward scoring remains the correctness oracle and bounded fallback.

MVSTATE2 persists exact selected-prefix continuation state: witness multiplicity, family coverage mass, obligation and correlation counts, and representative utility. It excludes candidate gain arrays and heap contents. Identity binds dataset/domain, UID/family order, DATA2B/MVIDX1 authority, witness weights, obligations, correlation units, selected prefix, selector policy, and v2 versions. Native publication is transactional and authenticated. Unsupported MVSTATE-REUSE1, stale lineage, tampering, truncation, and inconsistent continuation state are rejected and rebuilt.

REPAIR2 preserves REPAIR1 active-shell and immutable-prefix semantics, zero-unique/hard-safe removal, exact deficit-frontier replacement, strict no-coverage regression, objective/tolerance/tie hierarchy, rank inheritance, future displacement, bounded passes/swaps/shortlist, and deterministic trace. Hypothetical and accepted mutations use forward state only.

## Compatibility and qualification

New campaign records use `target_multi_view_selection_v2`, `target_multi_view_selection_state_v2:<domain>:<size>`, and `target_multi_view_repair_v2`. Legacy MVSEL1, MVSTATE-REUSE1, and REPAIR1 records retain their schemas and remain readable. V1 state is never interpreted as MVSTATE2.

Acceptance requires independent DATA2B and MVIDX1 validation of every materializable rung and repaired output; exact order equivalence across worker, batch, frontier rebuild, and restart settings; lazy/full-forward and independent-oracle equality; legacy repair-trace equality on accepted fixtures; no inverse propagation; bounded checkpoint/recovery behavior; fallback within one percent and three consecutive ranks; and at least tenfold projected or measured production selector improvement. GPU qualification is not implied.
