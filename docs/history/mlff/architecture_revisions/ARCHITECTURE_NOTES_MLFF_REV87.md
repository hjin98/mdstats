---
title: "MLFF Architecture Revision 87"
author: "mdstats development"
date: "2026-08-17"
geometry: margin=0.8in
fontsize: 10pt
---

# Revision 87

**Release:** `mdstats 0.20.220a0`  
**Gate:** `WARN-DOMAIN1`  
**Dependency-graph schema:** `69`

Revision 87 makes warning handling a campaign-level runtime property instead of a collection of local leak patches. One outer warning domain now spans every `mdstats-mlff-campaign` command. Existing MACE warning decorators nest into that owner, so setup, recovery, provider construction, evaluation, and worker-thread MACE operations contribute to one command record.

The same domain now intercepts two independent warning transports: Python `warnings` and Python `logging`. MACE/PyTorch `WARNING+` log records are classified from their emitting package pathname/logger and suppressed before any logger handler can print them; their signature/count is folded into the same compatibility record as TorchScript deprecations and MACE user warnings. This specifically closes the observed `WARNING:root:Default dtype ... converting models ...` leak.

The campaign owner is process-wide as well as context-local. A warning scope entered from a worker thread binds to the active campaign record even when the thread did not inherit the main-thread `ContextVar`. Operation merging is thread-safe.

A successful or failed command emits at most one normalized `[WARN]` compatibility summary. Raw TorchScript deprecation locations, raw MACE/PyTorch warning paths, and raw `WARNING:root:` messages are forbidden during campaign execution. Unrelated warning and logging behavior is preserved. Standalone mdstats API calls keep the prior local-scope warning behavior.

No scientific policy changes in this release. CUEQ-REPEAT1-PARITY1, DATA6, replay, TRAIN2, and FINAL-GPU1 numerical authorities remain revision-86-identical.
