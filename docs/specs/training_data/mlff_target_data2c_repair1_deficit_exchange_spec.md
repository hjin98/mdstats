# TARGET-DATA2C-REPAIR1: Exact active-shell redundancy repair

**Release:** `mdstats 0.20.203a0`  
**Architecture:** revision 70 / dependency-graph schema 52  
**Status:** implemented diagnostic/pre-migration; TARGET-DATA2C v4 remains production authority.

## Purpose

REPAIR1 removes residual redundancy left by the deterministic MVSEL1 greedy construction without changing any already-frozen lower prefix. It consumes immutable TARGET-DATA2B, MVIDX1, and MVSEL1 identities and emits the campaign record `target_multi_view_repair`. It cannot alter DATA8 membership or generated policy before MVMIGRATE1.

## Exact removal authority

For every required witness, REPAIR1 maintains the exact number of currently selected candidates covering it. A selected frame has unique coverage only on witnesses with selected multiplicity exactly one. Its exact unique-coverage loss is the FP64 sum of those witness weights; literal K-times leave-one-out coverage rescoring is forbidden. Required extent, stratum, and correlation-interval multiplicities are tracked exactly. A frame is removal-eligible only inside the active shell, only when unique coverage is at or below the frozen numerical tolerance, and only when removing it cannot increase any required-obligation deficit. Clustering score is diagnostic only.

## Deficit-directed replacement

Because removal candidates have zero unique coverage, removing one cannot decrease a required-family coverage component. MVIDX1/MVSEL1 incremental gain state therefore remains the exact coverage frontier for candidate replacements. REPAIR1 prioritizes unsatisfied hard obligations, then current bottleneck-family uncovered mass, then total newly covered mass. Harmonic representative utility, correlation-unit balance, sparse diversity, and stable frame UID resolve later ties. If no hard deficit and no uncovered mass can be improved, repair stops rather than performing arbitrary diversity-only churn.

For witness weight `w` with current multiplicity `n`, removing a selected frame changes harmonic utility by `w / n`; adding a replacement after that removal contributes `w / (1 + n_after_removal)`. The pair-specific representative gain is evaluated exactly on shared sparse neighborhoods without globally recomputing the subset.

## Shell and rank invariants

At rung `N`, only ranks in `[previous_N, N)` may be removed. Every accepted replacement inherits the removed rank. If that replacement already occurs later in the unrepaired MVSEL1 order, the removed frame is moved to that future rank, preserving a unique master ordering. Lower frozen prefixes are immutable. Each accepted swap must strictly improve the frozen hard-deficit / minimum-coverage / total-coverage / harmonic-representation / provenance-balance objective and may not regress any coverage component.

The v1 bounded reference policy uses at most two passes, 32 accepted swaps per shell, and a deterministic 64-frame removal shortlist ordered by exact representative-removal loss, correlation over-representation, and stable frame UID. These bounds limit reference-gate cost; MVPERF1 may optimize execution only if selected identities and repair decisions remain exact-equivalent.

## Validation and migration boundary

Validation recomputes repaired-rung coverage and hard obligations directly from MVIDX1, requires same-N non-regression relative to MVSEL1, verifies frozen-prefix/rank invariants, and optionally rebuilds the entire repair authority for digest-identical replay. Campaign restart reuses the record only when TARGET-DATA2B, MVIDX1, MVSEL1, and repair-policy identities are unchanged.

**Next gate:** `TARGET-DATA2C-MVPERF1` - exact-equivalence sparse/incremental performance hardening.
