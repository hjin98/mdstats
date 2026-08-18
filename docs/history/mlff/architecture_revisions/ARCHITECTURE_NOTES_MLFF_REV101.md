# MLFF architecture revision 101 - REPLAY-PERF1

Release: mdstats 0.20.234a0  
Date: 2026-08-17

REPLAY-PERF1 completes the exact-equivalence replay parsing/materialization optimization gate.

The unified selected replay ExtXYZ remains the only external replay authority. A new reconstructible `ReplaySourceIndex` binds exact source bytes and source-artifact/order identities to byte offsets, frame lengths, and atom counts. The campaign persists this cache beneath the internal replay tree and rebuilds it on source mutation or cache corruption.

True-label views, pseudo-label views, and foundation-prediction source iteration can consume the index. Sparse requests seek only requested source frames; full requests parse bounded contiguous chunks. Authenticated source-order geometry identities are reused instead of re-hashing every parsed frame. ASE parser threading was rejected after qualification showed it regressed wall time.

On the supplied 12,000-frame corpus, monitor-only true-label reconstruction improves about 3.03x with byte-identical output; complete source parsing/identity bookkeeping improves about 1.19x; complete train+monitor materialization improves about 1.09x. REPLAY-UNIFY1 source, split, true-label, pseudo-label, prediction-cache, and retention scientific authority is unchanged.

The active qualification model remains MACE-MPA-0 medium. The replay execution contract is model-family independent and remains valid for MACE-MH-1.

Next gate: CAMPAIGN-PERF-QUAL1.
