# Fixed-Cell Verlet Cache Benchmark

## Scope

This report records the stage S2 fixed-cell benchmark. Every cached frame was compared against a fresh exact S1 cell-list result before timing. Timings are machine-specific and are not an automatic backend policy.

```text
Python: 3.13.5
Platform: Linux-4.4.0-x86_64-with-glibc2.41
NumPy: 2.3.5
```

## Results

| Motion | Atoms | Frames | Rebuilds | Reuse | Fresh cell list (s) | Verlet (s) | Speedup | Acceptance ratio |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| solid | 64 | 12 | 1 | 11 | 0.8903 | 0.1417 | 6.28x | 0.545 |
| solid | 128 | 12 | 1 | 11 | 0.9985 | 0.1973 | 5.06x | 0.491 |
| solid | 256 | 12 | 1 | 11 | 1.2637 | 0.2943 | 4.29x | 0.495 |
| diffusive | 64 | 12 | 3 | 9 | 0.8879 | 0.3157 | 2.81x | 0.511 |
| diffusive | 128 | 12 | 3 | 9 | 0.9476 | 0.3610 | 2.63x | 0.573 |
| diffusive | 256 | 12 | 3 | 9 | 1.3032 | 0.5532 | 2.36x | 0.533 |

## Interpretation

- Solid-like trajectories rebuilt once and reused the cache for 11 of 12 evaluations.
- The more diffusive fixtures rebuilt three times and still retained nine reuse evaluations.
- Lower rebuild frequency gave the larger speedup.
- The candidate acceptance ratio measures accepted physical neighbors divided by all cached candidate evaluations across frames.
- No result mismatch was observed.

## Reproduction

```bash
python benchmarks/verlet_cache_benchmark.py
```

Raw data are stored in `benchmarks/verlet_cache_benchmark.json`.
