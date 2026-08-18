# MLFF Architecture Revision 90

**Gate:** `TARGET-DATA2B-FEAS1-PERF3`  
**Release:** `mdstats 0.20.223a0`

Revision 90 replaces PERF2's profile-local nested block/tree execution with a campaign-wide, single-level FEAS1 executor. Automatic mode consumes the full CPU thread budget (default 90% of available logical threads) as independent work-queue lanes; parallel cKDTree blocks use one native worker each. All domain/profile preparations and witness blocks share the queue, while exact candidate-gain reduction remains deterministic within each profile.

The progress authority is upgraded from profile-local block counters to campaign totals: completed/total profiles, prepared and active profiles, global block and witness progress, sampled busy executor lanes, queue depth, elapsed time, throughput, and ETA. Scientific FEAS1, MVIDX1, TARGET-DATA2C, and deferred GPU authority are unchanged.
