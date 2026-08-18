# DATA7 selection scaling benchmark — 2026-08-05

The former implementation recomputed every candidate-to-every-selected distance
at each FPS step and continued until all candidates had a rank. The new path
maintains one nearest-selected distance per candidate and stops at the largest
requested ladder size.

| Candidates | Target | Former prefix (s) | Incremental (s) | Speedup |
|---:|---:|---:|---:|---:|
| 250 | 64 | 0.878 | 0.0040 | 218× |
| 500 | 64 | 1.916 | 0.0029 | 661× |
| 1,000 | 64 | 3.947 | 0.0066 | 594× |
| 2,000 | 64 | 7.449 | 0.0061 | 1,223× |

With a fixed 512-frame target, the incremental implementation processed 36,759
synthetic 24-dimensional candidates in 0.504 s. The benchmark checks that the
new ordering exactly matches the former deterministic maximin prefix.

Complexity changes:

- complete former ordering: `O(N^3 d)`;
- former prefix-only equivalent: `O(N K^2 d)`;
- incremental bounded FPS: `O(N K d)`;
- vectorized coverage: `O(N K d + K^2 d)`.
