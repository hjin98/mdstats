# mdstats 0.20.114a0 patch notes

- Implement MLFF STOR3 lifecycle-safe automatic reclamation under the STOR1 ownership boundary, without deleting external inputs, selected production artifacts, active restart state, scientific prediction caches, or authoritative diagnostic/protocol records.
- Add authenticated append-only `results/cleanup-manifest.jsonl` events containing pre-deletion filesystem identities, reasons, reclaimed bytes, preserved capabilities, and an explicit zero-capability-loss contract.
- Reclaim the reconstructable OPT-EVAL3 graph/view cache only after authoritative evaluation is complete; retain evaluation-prediction shards, DATA6/model-sweep predictions, and true-label replay artifacts for later metric-only/reanalysis workflows.
- Change low-disk training behavior so STOR3 safe reclamation runs before active MACE jobs are interrupted; disk pressure never broadens cleanup authority, and active run roots remain excluded.
- Advance the MLFF architecture dependency graph to revision 32. STOR4 manual tiered reclamation is the next gate.
