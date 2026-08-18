# mdstats 0.20.145a0 patch notes

## PAR-DENS6 — end-to-end qualification and auto-tuning

This revision closes the PAR-DENS0→PAR-DENS6 atomic/framework density optimization program. The new auto-tuning authority is deliberately execution-only: scientific grid resolution, Gaussian bandwidth, density operator, support semantics, normalization, HDR definition, and scalar-field content identity are immutable.

### Scientific/execution identity correction

During the 10,001-frame Na-LTA qualification, the O field exposed a one-ulp worker-count difference. The cause was lease-local re-planning of the hybrid direct/FFT tile partition: a field starting with one CPU token selected a different direct/FFT mix than an isolated field with three tokens. PAR-DENS6 now freezes the exact direct/FFT tile partition during scene-level Phase-B, before field admission. Worker leases may change worker counts used to execute approved tiles, but may not change each tile's executor. The corrected 10,001-frame auto and one-worker paths are bit-identical for Na, Si, and O.

### Resource-model closure

The sparse Phase-B contract now includes optimized CIC transient workspace. Dead geometry arrays are released before the stable reduction. The provisional basin prepass processes bounded item blocks through triclinic MIC rather than all items at once, preventing trajectory-wide image-candidate workspace. Scheduler admission prioritizes the largest-peak independent field so retained smaller outputs cannot strand a later high-workspace field.

### Auto-tuning policy

PAR-DENS6 calibrates/caches a hardware-local execution profile. It may bound field concurrency, work-group depth and FFT workers, while PAR-DENS1 remains the direct/FFT cost-model owner and PAR-DENS5 remains the CPU/GPU/VRAM owner. The PAR-DENS3-qualified group multiplier of four is retained as a fail-safe because the isolated chunk microbenchmark does not model cooperative lease redistribution reliably enough to override it.

### Na-LTA qualification

Input: `dump.prod.Na_lta_300K.old(1).lammpstrj`, SHA-256 `81c86cc40f5a11031f80817213eb558c02348494d1c6cad9b4775a5bc3c9f9cd`, 10,001 frames × 168 atoms. Fixed science: Na/Si/O, `64^3`, local sparse, 8^3 storage blocks, 0.5 Å Gaussian, canonical discrete-periodized smoothing.

- three auto scales: 101, 1,001, 10,001 frames;
- two independent 10,001-frame auto repeats: 17.7906 s, 18.0370 s;
- two one-worker references: 19.3897 s, 20.5076 s;
- median total-wall speedup: **1.1136×**;
- median scheduled-realization speedup: **1.1203×**;
- maximum long-run measured density-stage RSS growth: about **640.3 MB**, below each dynamic ~1.33–1.34 GB 80%-RAM budget;
- max pointwise difference: **0.0** for Na, Si and O;
- content identities, integrals, 50/80/95% HDR thresholds, executor partitions and deterministic repeats all match exactly.

The authoritative record is `release/par_dens6_na_lta_qualification.json`. This host has no CUDA runtime, so the CPU production path is authorized while GPU performance remains conditional on a CUDA-capable qualification host.
