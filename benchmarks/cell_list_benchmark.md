# Stage S1 Cell-List Benchmark

Every timed cell-list record was first compared with the dense oracle for
exact atom-pair and image-shift equality and tolerance-bounded vector and
distance equality. Timings are machine-specific and are not portable
performance guarantees.

## Environment

- **python:** `3.13.5`
- **platform:** `Linux-4.4.0-x86_64-with-glibc2.41`
- **cpu:** `unknown`
- **numpy:** `2.3.5`
- **scipy:** `1.17.0`
- **ase:** `3.26.0`
- **networkx:** `3.6.1`
- **dense_backend:** `dense`
- **cell_list_backend:** `cell_list`

## Measurements

| Geometry | Selection | N | Dense evals | Cell evals | Candidate fraction | Accepted | Bins | Stencil | Reduced | Dense median (s) | Cell median (s) | Speedup |
|---|---|---:|---:|---:|---:|---:|---|---:|---|---:|---:|---:|
| orthogonal | all_unordered | 64 | 4096 | 838 | 0.2046 | 125 | 4x4x4 | 27 | False | 0.140402 | 0.082584 | 1.70x |
| orthogonal | all_unordered | 128 | 16384 | 1728 | 0.1055 | 238 | 5x5x5 | 27 | False | 0.307110 | 0.088883 | 3.46x |
| orthogonal | all_unordered | 256 | 65536 | 4145 | 0.0632 | 514 | 6x6x6 | 27 | False | 0.387649 | 0.110040 | 3.52x |
| orthogonal | oxygen_silicon_directed | 64 | 1024 | 238 | 0.2324 | 48 | 5x5x5 | 27 | False | 0.002959 | 0.069455 | 0.04x |
| orthogonal | oxygen_silicon_directed | 128 | 4096 | 506 | 0.1235 | 67 | 6x6x6 | 27 | False | 0.139772 | 0.074434 | 1.88x |
| orthogonal | oxygen_silicon_directed | 256 | 16384 | 880 | 0.0537 | 143 | 8x8x8 | 27 | False | 0.337299 | 0.084827 | 3.98x |
| triclinic | all_unordered | 64 | 4096 | 1504 | 0.3672 | 112 | 3x4x3 | 27 | True | 0.134846 | 0.090775 | 1.49x |
| triclinic | all_unordered | 128 | 16384 | 2175 | 0.1328 | 242 | 4x5x5 | 27 | True | 0.419018 | 0.120104 | 3.49x |
| triclinic | all_unordered | 256 | 65536 | 4052 | 0.0618 | 560 | 6x6x6 | 27 | True | 0.492720 | 0.118711 | 4.15x |
| triclinic | oxygen_silicon_directed | 64 | 1024 | 335 | 0.3271 | 35 | 4x5x4 | 27 | True | 0.002873 | 0.068328 | 0.04x |
| triclinic | oxygen_silicon_directed | 128 | 4096 | 515 | 0.1257 | 72 | 6x6x6 | 27 | True | 0.144201 | 0.072944 | 1.98x |
| triclinic | oxygen_silicon_directed | 256 | 16384 | 1118 | 0.0682 | 124 | 7x8x7 | 27 | True | 0.351096 | 0.085880 | 4.09x |
| highly_skewed | all_unordered | 64 | 4096 | 708 | 0.1729 | 102 | 2x5x5 | 27 | True | 0.229083 | 0.090850 | 2.52x |
| highly_skewed | all_unordered | 128 | 16384 | 2951 | 0.1801 | 393 | 2x5x5 | 27 | True | 0.280304 | 0.152744 | 1.84x |
| highly_skewed | all_unordered | 256 | 65536 | 11759 | 0.1794 | 1551 | 2x5x5 | 27 | True | 0.571715 | 0.254210 | 2.25x |
| highly_skewed | oxygen_silicon_directed | 64 | 1024 | 378 | 0.3691 | 53 | 2x5x5 | 27 | True | 0.002882 | 0.079421 | 0.04x |
| highly_skewed | oxygen_silicon_directed | 128 | 4096 | 1463 | 0.3572 | 185 | 2x5x5 | 27 | True | 0.137388 | 0.107343 | 1.28x |
| highly_skewed | oxygen_silicon_directed | 256 | 16384 | 2994 | 0.1827 | 364 | 3x7x7 | 27 | True | 0.279631 | 0.143800 | 1.94x |

## Interpretation

The dense backend evaluates the full center-candidate product. The
cell-list backend evaluates only atom pairs found through the exact
metric-aware bin stencil, then applies the same original-cell MIC and
strict physical cutoff. Candidate fraction measures geometric pruning,
not the accepted-neighbor fraction. S1 remains single-frame and does not
reuse candidates across trajectory frames.
