# REPAIR-PAR1 cloud CPU benchmark — MPA-0 active qualification

Release: `mdstats 0.20.231a0`  
Architecture revision: 98  
Date: 2026-08-17

REPAIR-PAR1 preserves sequential repair mutation/winner authority and accelerates only immutable proposal construction. The medium fixture remains below the adaptive parallel threshold and demonstrates the vectorized CSR/stamp kernel; the large fixture crosses the threshold and demonstrates additional deterministic proposal-task scaling.

| Workload | Untouched 0.20.230a0 | 1 lane | 2 lanes | 4 lanes |
|---|---:|---:|---:|---:|
| 2,048-candidate proposal | 3.175791 s | 0.119369 s | — | adaptive serial |
| 8,192-candidate proposal | 3.129870 s | 0.830133 s | 0.610776 s | 0.460878 s |

The medium proposal kernel is 26.60x faster from vectorized sparse scoring alone. The large fixture is 3.77x faster at one lane and 6.79x faster end-to-end at four lanes, with 1.80x additional 1→4 lane scaling.

Scientific identities are exact: the frozen complete repair-plan digest is `5dcb048b02ae2670d48d15f3f610b5814b611b2339df4ec4b265a52615b9545b`; medium proposal result digest `1a09e7745aa534bed757334ad9d365099e28635050ec63f1244421e4b859a9b1`; large proposal result digest `9fda146806fc12f7c4d8030877e3a09cd206cef01eb6f821be0010c468b41994`. Arbitrary task completion is reduced in historical removal-shortlist order and does not change the persisted repair trace.

The active checkpoint is MACE-MPA-0 medium (`75428afe...638`); the repair kernel is foundation-model independent and the same contract applies to MACE-MH-1.
