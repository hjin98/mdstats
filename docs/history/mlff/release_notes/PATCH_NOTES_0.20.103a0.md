# mdstats 0.20.103a0 patch notes

This release implements the final staged MLFF optimization roadmap item,
**OPT-CTRL1**.

- CampaignStore now keeps one SQLite connection per calling thread and avoids the
  former duplicate SQL fetch/JSON decode in ordinary record restoration.
- Optional record accessors remove common `has_record` + `get_record` double queries;
  naturally grouped parent-side records can be committed in one transaction.
- `<workspace>/.mdstats/hash-receipts.sqlite3` stores reconstructable SHA-256 receipts
  keyed by strong file-stat identity for restart-time artifact authentication.
- GPU telemetry prefers persistent direct NVML/libnvidia-ml calls and falls back to
  `nvidia-smi`; evaluation/verification poll less frequently after CUDA calibration.
- Replay configuration-weight staging is streamed frame-by-frame rather than loading
  the complete ExtXYZ corpus into memory.
- Campaign cleanup reuses one run-directory snapshot across related cleanup passes.
- Runtime advances to 0.20.103a0 while MLFF scientific compatibility remains
  0.20.99a0 and verification-case compatibility remains 0.20.85a0.

No model, dataset, prediction, metric, checkpoint-selection, or verification acceptance
identity changes.
