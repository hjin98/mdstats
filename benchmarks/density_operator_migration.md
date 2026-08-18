# Density Operator Migration Benchmark

Comparison of `discrete_periodized_v1` against `legacy_spectral_v1` for one off-node CIC source on a $64^3$ grid. The legacy operator remains the default.

| Cell | $\sigma/h_{\max}$ | Relative $L^1$ | Relative $L^\infty$ | Canonical offsets | Image contributions |
|---|---:|---:|---:|---:|---:|
| orthogonal | 2.0 | 2.443023e-08 | 1.229097e-08 | 8409 | 8409 |
| orthogonal | 1.0 | 5.735037e-03 | 3.403506e-03 | 1045 | 1045 |
| orthogonal | 0.5 | 2.617198e-01 | 2.843563e-01 | 147 | 147 |
| lta_primitive | 2.0 | 2.067544e-08 | 1.042049e-08 | 12017 | 12017 |
| lta_primitive | 1.0 | 3.822507e-03 | 2.184177e-03 | 1505 | 1505 |
| lta_primitive | 0.5 | 2.450192e-01 | 2.695992e-01 | 201 | 201 |

At the default ratio $\sigma/h_{\max}=2$, the operators agree to approximately $2\times10^{-8}$ in relative $L^1$. The difference becomes material for under-resolved explicit bandwidths, which is why the operator identifier is scientific metadata and the default is not changed silently.
