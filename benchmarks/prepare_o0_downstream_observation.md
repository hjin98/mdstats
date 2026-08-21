# O0 downstream `prepare` observation

Date: 2026-08-20
Branch: `codex/repair2-perf1`
Evidence: `prepare-o0.json`

## Scope

O0 wrapped the unchanged production `prepare` command with an external 30-minute observation harness. The wrapper wrote no campaign scientific authority and sampled only coarse stage boundaries plus Linux process-tree CPU/RSS/I/O evidence.

## Product observation

The run used the LTA product campaign and reached the historical TARGET-DATA2C ladder after 00:30:03, where the external observation timeout terminated the process.

| observed interval | wall | sampled user CPU | sampled read bytes | sampled peak RSS |
|---|---:|---:|---:|---:|
| startup | 00:00:51 | 47.53 s | 0.73 GiB | 2.16 GiB |
| DATA6 first interval | 00:00:23 | 22.56 s | 0.13 GiB | 2.89 GiB |
| DATA4 restore | 00:00:31 | 29.41 s | 0.91 GiB | 4.07 GiB |
| DATA6 restore | 00:01:20 | 72.00 s | 0.32 GiB | 4.88 GiB |
| TARGET-DATA2C-MVIDX1 restore | **00:08:42** | 326.57 s | **77.71 GiB** | **85.38 GiB** |
| TARGET-DATA2C-REPAIR2 integrated interval | **00:18:16** | **1213.04 s** | 2.53 GiB | **86.45 GiB** |

Whole-command evidence at the external bound was 297,220 major faults, 14,711,153 minor faults, 90,868,748 KiB child peak RSS, and 172,659,856 filesystem input blocks.

The MVIDX1 restore explicitly reported `validation=receipt-hit`; therefore the 00:08:42 interval is not a cold compound-validation pass.

## Source attribution

The standalone R5 REPAIR2 builder is stable at approximately 00:08:28. The integrated O0 REPAIR2 interval is approximately 00:18:16. Inspection of the production seam shows that `_ensure_target_multi_view_repair_v2` opens a forward-only MVIDX1 view before starting the optimized scalar repair builder.

The canonical forward-only native reader currently reconstructs each `TargetCoverageSparseForwardFamilyView` through its ordinary constructor. That constructor performs O(E) witness range and per-row sorted/duplicate validation over `candidate_witnesses`, even when the exact compound MVIDX1 validation receipt has already authenticated the identical sidecars. In the LTA product this repeats work over 9,505,021,522 forward edges. O0's integrated REPAIR2 interval is CPU-heavy but incurs only about 2.53 GiB of physical reads, consistent with a redundant scan over file-backed pages that were already populated by the immediately preceding full MVIDX1 restore.

The full native MVIDX1 reader already has the required trust model: on an exact compound receipt hit it uses metadata validation plus a trusted-native constructor and performs a final restore-identity check. The forward-only reader did not reuse that mechanism.

## O1 decision

O1 targets only the authenticated forward-view reopen:

1. receipt miss delegates unchanged to the canonical forward reader;
2. exact receipt hit uses the same pointer/manifest and compound restore identity as the full reader;
3. product-scale `candidate_offsets` and `candidate_witnesses` use metadata validation rather than repeated value hashing;
4. compact CSR offsets remain structurally validated;
5. the already-receipted O(E) range/sortedness scan is not repeated;
6. per-file checksum handling remains unchanged;
7. a final restore-identity comparison fails closed if a sidecar changes during open;
8. no scientific schema, policy, digest, selector, repair, or persistence authority changes.

Implementation is isolated in `mdstats/training_data/mvidx1_forward_receipt_runtime.py` and installed into the shared MVSEL2/REPAIR2 forward-view seam by `campaign_cli.py`. Focused regression lives in `tests/test_mlff_mvidx1_forward_receipt_runtime.py`; product timing is measured by `benchmarks/benchmark_mvidx1_forward_receipt_o1.py`.

The separate 00:08:42 full MVIDX1 restore remains an O0 bottleneck but is not modified in O1. Its 77.71 GiB physical-read signature needs narrower attribution after the duplicate forward scan is removed; no integrity weakening is authorized merely to reduce that interval.
