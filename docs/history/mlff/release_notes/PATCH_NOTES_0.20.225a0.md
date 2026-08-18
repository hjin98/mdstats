# mdstats 0.20.225a0 patch notes

## PERFBASE1 reproducible optimization baseline

This release implements `PERFBASE1`, the first gate of the frozen campaign optimization program. It adds foundation-generic, content-addressed performance baseline records and a deterministic benchmark harness without changing scientific datasets, neighborhood definitions, coverage thresholds, target selection, training/evaluation semantics, or GPU authority.

The baseline records exact scientific-output digests separately from wall/CPU time, assigned-lane occupancy, RSS, throughput, worker settings, and queue telemetry. The current qualification uses the supplied MACE-MPA-0 medium checkpoint, but the record contract does not hard-code MPA-0 and is directly reusable for MACE-MH-1 campaigns.

The canonical cloud CPU suite authenticates the supplied 27-file LTA target archive, a fixed 4,100-frame/eight-family representative TARGET-DATA2B cache, the unified 12,000-frame replay source, the dependency bundle, the active foundation checkpoint, and a benchmark implementation manifest. It measures TARGET-DATA2B reference radii, FEAS1, MVIDX1, MVSEL1 sparse selection, and replay ingest at serial, dual, bounded-intermediate, and automatic CPU schedules. Serial implementations report one actually allocated lane even when a larger schedule is requested.

Qualification shows FEAS1 scaling from about 1.78 s to 0.85 s median wall time from one to three lanes on the cloud host, while current MVIDX1 is essentially non-scaling/slightly slower (about 2.17 s to 2.40 s) and drops to about one-third assigned-lane occupancy. This is baseline evidence only; no runtime algorithm is changed in this release. Foundation Audit/EVAL2 model-inference timing is explicitly marked unavailable on the host rather than inferred.

`PARCORE1` is the next optimization gate.
