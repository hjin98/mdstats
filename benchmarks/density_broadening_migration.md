# Density Broadening Migration Benchmark

This benchmark compares the legacy Gaussian-width diagnostic with the
effective CIC-plus-canonical-stencil RMS width. The density operator itself
is not changed by this benchmark.

| Cell | Phase | sigma/h_max | CIC RMS (A) | Stencil RMS (A) | Effective RMS (A) | Effective/sigma |
|---|---|---:|---:|---:|---:|---:|
| orthogonal | on_node | 0.0 | 0 | 0 | 0 | n/a |
| orthogonal | half_node | 0.0 | 0.079159813 | 0 | 0.079159813 | n/a |
| orthogonal | mixed | 0.0 | 0.063700962 | 0 | 0.063700962 | n/a |
| orthogonal | on_node | 1.0 | 0 | 0.18749998 | 0.18749998 | 0.99999990 |
| orthogonal | half_node | 1.0 | 0.079159813 | 0.18749998 | 0.20352523 | 1.08546789 |
| orthogonal | mixed | 1.0 | 0.063700962 | 0.18749998 | 0.19802539 | 1.05613542 |
| orthogonal | on_node | 2.0 | 0 | 0.37499998 | 0.37499998 | 0.99999993 |
| orthogonal | half_node | 2.0 | 0.079159813 | 0.37499998 | 0.38326395 | 1.02203721 |
| orthogonal | mixed | 2.0 | 0.063700962 | 0.37499998 | 0.38037192 | 1.01432511 |
| lta_primitive | on_node | 0.0 | 0 | 0 | 0 | n/a |
| lta_primitive | half_node | 0.0 | 0.1356484 | 0 | 0.1356484 | n/a |
| lta_primitive | mixed | 0.0 | 0.10539919 | 0 | 0.10539919 | n/a |
| lta_primitive | on_node | 1.0 | 0 | 0.27129687 | 0.27129687 | 0.99999994 |
| lta_primitive | half_node | 1.0 | 0.1356484 | 0.27129687 | 0.30331911 | 1.11803387 |
| lta_primitive | mixed | 1.0 | 0.10539919 | 0.27129687 | 0.29105151 | 1.07281552 |
| lta_primitive | on_node | 2.0 | 0 | 0.54259374 | 0.54259374 | 0.99999993 |
| lta_primitive | half_node | 2.0 | 0.1356484 | 0.54259374 | 0.55929282 | 1.03077632 |
| lta_primitive | mixed | 2.0 | 0.10539919 | 0.54259374 | 0.55273588 | 1.01869190 |

At sigma/h_max = 2, the effective width equals sigma for on-node
samples and is modestly larger for off-node CIC phases. At sigma = 0,
the artificial width is the CIC contribution alone.
