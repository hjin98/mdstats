# mdstats 0.20.235a0 - CAMPAIGN-PERF-QUAL1

- Close the integration/measurement CAMPAIGN-PERF-QUAL1 gate without changing runtime scientific algorithms.
- Run a common end-to-end target-data chain against an untouched PERFBASE1-era 0.20.225a0 control; preserve exact FEAS/MVIDX/MVSEL/REPAIR/MVQUAL outputs while reducing wall time from about 27.26 s to about 11.95 s at four lanes (~2.28x).
- Recheck authenticated replay restart, EVAL2/bootstrap, Foundation Audit, worker scaling, and representative memory behavior.
- Identify the shifted dominant CPU cost: exact MVSEL sparse state mutation and REPAIR replay of that already-computed selector state.
- Keep the CPU optimization program open for one targeted exact-equivalence follow-up, MVSTATE-REUSE1, instead of falsely declaring closure.
- Preserve active MACE-MPA-0 medium qualification and the same model-generic execution contracts for MACE-MH-1.
- Final GPU qualification remains deferred.
