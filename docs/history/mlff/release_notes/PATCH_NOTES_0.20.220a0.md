# mdstats 0.20.220a0 - WARN-DOMAIN1

- Install one campaign-wide MACE/PyTorch warning capture domain around every `mdstats-mlff-campaign` command.
- Merge all existing operation-local warning scopes into that command owner instead of allowing gaps between decorators.
- Capture MACE/PyTorch `logging.WARNING+` records as well as Python warnings; suppress raw root-logger dtype conversion messages and include them in the normalized summary.
- Make the command owner visible to worker threads and merge worker-local MACE scopes thread-safely.
- Emit at most one `[WARN]` compatibility summary per campaign command while preserving unrelated warning/logging behavior.
- No DATA6, replay, TRAIN2, parity, convergence, or FINAL-GPU1 numerical policy changes.
