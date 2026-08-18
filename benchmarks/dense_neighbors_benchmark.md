# Dense Neighbor Benchmark

This report is a machine-specific stage-S0 baseline. It is not a portable
performance guarantee. Scientific outputs are checked for deterministic pair
counts before timing and memory results are accepted.

## Environment

- **python:** `3.13.5`
- **platform:** `Linux-4.4.0-x86_64-with-glibc2.41`
- **cpu:** `x86_64`
- **numpy:** `2.3.5`
- **scipy:** `1.17.0`
- **ase:** `3.26.0`
- **networkx:** `3.6.1`
- **backend:** `dense`

## Measurements

| Geometry | Selection | N | Species | Cutoff registry (A) | Centers | Candidates | Dense evaluations | Accepted | Median (s) | Min (s) | Max (s) | Peak tracemalloc (MiB) |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| orthogonal | all_unordered | 64 | O:32, Si:32 | all-all:3 | 64 | 64 | 4096 | 125 | 0.121365 | 0.118278 | 0.218562 | 7.326 |
| orthogonal | all_unordered | 128 | O:64, Si:64 | all-all:3 | 128 | 128 | 16384 | 238 | 0.307445 | 0.214372 | 0.321469 | 29.268 |
| orthogonal | all_unordered | 256 | O:128, Si:128 | all-all:3 | 256 | 256 | 65536 | 514 | 0.514762 | 0.391823 | 0.532261 | 117.027 |
| orthogonal | oxygen_silicon_directed | 64 | O:32, Si:32 | Si-O:2.4 | 32 | 32 | 1024 | 48 | 0.002462 | 0.002440 | 0.002509 | 1.840 |
| orthogonal | oxygen_silicon_directed | 128 | O:64, Si:64 | Si-O:2.4 | 64 | 64 | 4096 | 67 | 0.139337 | 0.124005 | 0.241787 | 7.328 |
| orthogonal | oxygen_silicon_directed | 256 | O:128, Si:128 | Si-O:2.4 | 128 | 128 | 16384 | 143 | 0.324624 | 0.304240 | 0.327484 | 29.271 |
| triclinic | all_unordered | 64 | O:32, Si:32 | all-all:3 | 64 | 64 | 4096 | 110 | 0.136364 | 0.120976 | 0.207252 | 7.328 |
| triclinic | all_unordered | 128 | O:64, Si:64 | all-all:3 | 128 | 128 | 16384 | 241 | 0.227450 | 0.223913 | 0.315080 | 29.269 |
| triclinic | all_unordered | 256 | O:128, Si:128 | all-all:3 | 256 | 256 | 65536 | 554 | 0.485514 | 0.433556 | 0.496757 | 117.028 |
| triclinic | oxygen_silicon_directed | 64 | O:32, Si:32 | Si-O:2.4 | 32 | 32 | 1024 | 33 | 0.002701 | 0.002601 | 0.002786 | 1.842 |
| triclinic | oxygen_silicon_directed | 128 | O:64, Si:64 | Si-O:2.4 | 64 | 64 | 4096 | 68 | 0.119828 | 0.024418 | 0.128282 | 7.329 |
| triclinic | oxygen_silicon_directed | 256 | O:128, Si:128 | Si-O:2.4 | 128 | 128 | 16384 | 125 | 0.420769 | 0.218741 | 0.424821 | 29.272 |

## Interpretation

The dense backend performs `n_centers * n_candidates` minimum-image pair
evaluations before cutoff filtering. `UNORDERED_IDENTICAL` removes duplicate
output pairs but does not reduce the current dense displacement calculation.
These records establish the correctness/performance reference for stage S1.
