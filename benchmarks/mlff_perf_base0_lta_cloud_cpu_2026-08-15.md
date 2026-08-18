# mdstats MLFF PERF-BASE0 baseline

- Baseline ID: `lta-perf-base0-cloud-cpu-run1-2026-08-15`
- Source version: `0.20.178a0`
- Authority status: **bounded**
- Scientific digest: `44a5aa8b492cece8d303f83a163ddbeee6d3a340932d4716c53b4ddf28a81e3c`
- Execution digest: `2c7614fea8dc60594e176e7c4fa17413922c56d67982e881a8fab0eebbc5b18c`
- Record digest: `a8573580a906da95ff4e5af3154814bcba8b702174fe81437a1c22f1375da198`

## Corpora

| Corpus | Role | Frames | Atoms | Source units | Bytes |
|---|---|---:|---:|---:|---:|
| `perf_base0_compact_adversarial` | compact deterministic and adversarial numerical regression corpus | 26 | 0 | 1 | 2,345 |
| `lta_target_complete` | realistic complete target-development source corpus | 37,633 | 6,322,344 | 27 | 966,777,484 |
| `lta_replay_authoritative_splits` | replay train/monitor/outlier materialization with complete supplied provenance package | 12,000 | 364,370 | 3 | 168,633,407 |

## Scientific references

| Stage | Subset rule | Arrays | JSON references | Digest |
|---|---|---:|---:|---|
| `input_identity` | complete supplied source, target, replay, dependency artifact inventory | 0 | 3 | `9df51f27dc571708876e87939ab76a1c1fc86113f4226e81877103a5965d6030` |
| `training_ingest` | complete 27-file LTA target corpus | 4 | 4 | `99af923bbc936849cfa5a9502ae8cdb7bfda97d453a30f40d764f2dc3c60922a` |
| `replay_ingest` | complete authoritative replay train/monitor/outlier split materialization | 2 | 3 | `b90d495a7772421e8adcc41c123adf54008edc47f9d6918a59a5a16b20e76957` |
| `compact_regression` | complete six-point deterministic synthetic corpus | 5 | 3 | `e148b85be98790d9add9d55bec8ba94b3b08942b1f6da3d3d460588174dbe2e1` |
| `adversarial_geometry_statistics` | complete frozen adversarial duplicate/tie/weight/mask/triclinic-MIC corpus | 8 | 3 | `241e98d886c113ad9bc6393949669cd6d25125d1acdb40ebbd66e2c61ab733e5` |
| `target_data2b_exact_radii` | complete target corpus for target/stress/cell/mobile/framework-force families; complete valid-frame subsets for Li/Na/K species-force families; no reference subsampling | 48 | 2 | `3b756227165356fcfea794ef8e594006181612a1a41c1ab2e626129bf9df0b58` |
| `target_data2c_exact_fps` | complete 37633-frame fused target-label/cell matrix; exact deterministic FPS prefix K=1024; nested rungs=[128, 256, 512, 1024] | 3 | 3 | `70fa902520592aa6739a4a211a5fd2595b26deaa61257b3742e776ad971876c5` |

## CPU execution telemetry

| Stage | Wall (s) | Process CPU (s) | Effective cores | Peak RSS (MiB) | Throughput |
|---|---:|---:|---:|---:|---:|
| `input_identity` | 1.284392 | 1.296955 | 1.010 | 259.10 | 30.365 artifacts/s |
| `training_ingest` | 131.846106 | 134.663969 | 1.021 | 527.31 | 285.431 frames/s |
| `replay_ingest` | 7.300726 | 7.361805 | 1.008 | 527.34 | 1643.672 frames/s |
| `compact_regression` | 0.002670 | 0.002727 | 1.021 | 542.07 | 2246.896 reference_elements/s |
| `adversarial_geometry_statistics` | 0.002331 | 0.002403 | 1.031 | 542.07 | 8580.171 adversarial_elements/s |
| `target_data2b_exact_radii` | 5.518176 | 24.194879 | 4.385 | 559.38 | 47732.798 family-elements/s |
| `target_data2c_exact_fps` | 6.018641 | 40.434348 | 6.718 | 561.04 | 170.138 selections/s |

## Unavailable stages

- `TARGET-DATA2B production DATA6 structural/foundation-residual families`
- `TARGET-DATA2C mandatory-quota and exhaustive ladder authority`
- `DATA6 foundation descriptors, predictions, difficulty, recovery, and GPU telemetry`
- `DATA7 complete production selection authority`
- `DATA8 campaign bundle materialization authority`
- `TRAIN2 checkpoint/continuation timing and identities`
- `EVAL2 checkpoint inference, metric, and decision timing`

## Limitations

- No MACE-MH-1 checkpoint was supplied, so foundation-model scientific outputs are not inferred or fabricated.
- The cloud host is CPU-only and cgroup-limited; no GPU memory, OOM, DATA6 inference, training, or evaluation telemetry is available.
- The realistic FPS authority is a deterministic exact K-bounded prefix over label/cell/composition summaries, because the campaign DATA6 fused descriptor table is not present.
- Source XML and replay bytes are fully authenticated; all target and authoritative replay split frames are ingested without frame subsampling.
- Operating-system page-cache state is observed rather than forcibly controlled; process CPU time and exact byte identities accompany wall time.
