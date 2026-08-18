# mdstats 0.20.229a0 patch notes

- Implement COVREF-PAR1 / architecture revision 96 as an exact-equivalence optimization of TARGET-DATA2B reference-radius construction.
- Replace the serial Python block driver around multi-threaded cKDTree with one stage-wide PARCORE1 outer block queue; every native tree query uses one worker.
- Add execution-only adaptive row-block sizing to keep query temporaries cache-sized and expose several tasks per assigned CPU lane on 30k-40k-frame domains.
- Preserve the historical direct API native-tree path when no execution scope is supplied, providing a stable serial/native oracle and backward-compatible execution control.
- Harden PARCORE1 direct FEAS1/NEIGHBOR1/MVIDX fallback semantics: implicit direct-API execution no longer derives hard RAM ceilings from transient host/cgroup free memory; explicit campaign `StageResourceScope` RAM limits remain strictly enforced.
- Replace repeated pair-rule and foundation-species linear scans with O(1) lookup maps.
- Move the exact historical target-label scalar constant-family rejection before statistics/tree construction so rejected families consume no radius work.
- Preserve frozen PERFBASE1 radius digest `823a2c0c2f8a012c84bee0fe27085535862b71ff48a75f31b6d96e52cd642e2d` across qualified worker schedules.
- Keep active qualification on supplied MACE-MPA-0 medium while preserving the same execution contract for MACE-MH-1.
- Next optimization gate is MVKERNEL1.
