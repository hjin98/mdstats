# MLFF Architecture Notes - Revision 89

Release: `mdstats 0.20.222a0`
Gate: `TARGET-DATA2B-FEAS1-PERF2`

Revision 89 replaces PERF1 family-level scheduling with exact shared-tree witness-block concurrency for FEAS1. The scientific neighborhood relation and all FEAS1/TARGET-DATA2C digests remain unchanged.

Automatic FEAS1 execution now factors the `StageResourceScope` CPU budget across bounded block workers and native cKDTree workers. Blocks share one read-only scaled descriptor matrix/tree, avoiding the copy/IPC overhead measured for a rejected process-pool prototype. Completed blocks are reduced in canonical witness order so historical FP64 candidate-gain addition order is preserved exactly.

FEAS1 now provides interval heartbeats and block/witness elapsed-rate-ETA progress. MVIDX1 now provides block/witness elapsed-rate-ETA-edge progress within each family. These are execution-only observability changes.

No GPU exact-neighborhood authority is introduced. FINAL-GPU1 remains deferred as previously frozen.
