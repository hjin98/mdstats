# MLFF Architecture Revision 92

**Gate:** `PERFBASE1`  
**Release:** `mdstats 0.20.225a0`  
**Authority:** reproducible performance measurement; no scientific/runtime optimization authority change

Revision 92 implements the first gate of the frozen campaign optimization sequence. `PERFBASE1` introduces versioned trial, workload, and top-level baseline records that bind exact scientific-output digests independently from execution telemetry. Timing, CPU occupancy, RSS, worker settings, throughput, and queue observations may vary between exact-equivalent implementations without entering scientific authority.

The benchmark contract is foundation-model generic. The current LTA qualification run binds the supplied MACE-MPA-0 medium checkpoint by SHA-256 `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`, while the same schemas and harness remain valid for MACE-MH-1 by changing only the foundation identity/input.

The frozen CPU suite covers a supplied TARGET-DATA2B reference-radius workload, deterministic synthetic FEAS1/MVIDX1/MVSEL1 workloads, and the supplied unified 12,000-frame replay source across serial, dual, bounded-intermediate, and automatic CPU schedules. Current serial stages record requested schedule size separately from actual allocated lanes. Foundation Audit/EVAL2 model-inference timings are explicitly unavailable on the cloud host because the authoritative measurement environment lacks the MACE runtime; no synthetic timing is substituted.

All repeated schedules preserve their exact scientific-output digests. The cloud evidence shows useful FEAS1 scaling but no MVIDX1 gain from increasing its current native cKDTree query workers, supporting the frozen ordering in which `PARCORE1` is next, followed by shared neighborhood production/reuse.

Canonical evidence:

- `benchmarks/mlff_perfbase1_lta_cloud_cpu_mpa0_2026-08-17.json`
- `benchmarks/mlff_perfbase1_lta_cloud_cpu_mpa0_2026-08-17.md`
- `release/qualification_logs/MLFF_PERFBASE1_QUALIFICATION_0.20.225a0.json`

`TARGET-DATA2B-FEAS1-PERF3` remains the most recent runtime optimization authority. Revision 92 is measurement-only.
