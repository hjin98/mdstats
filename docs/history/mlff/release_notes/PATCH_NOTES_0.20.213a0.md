# mdstats 0.20.213a0

REPLAY-UNIFY1D integrates the single replay-source authority into the user-facing MLFF campaign workflow.

- new campaign configs expose one `[paths].replay_set` and default deterministic 5:1 train/monitor splitting;
- deprecated split-file init flags remain hidden/parser-compatible for historical automation, but mixed interfaces fail closed;
- `true_dft` campaigns lazily derive internal true-label train/monitor views from the single source;
- `foundation_pseudolabel` campaigns reuse the Gate-C batched prediction/audit cache, qualify the source, freeze one split, and derive pseudo train/monitor plus independent true monitor on identical geometry membership;
- `doctor` validates source/runtime prerequisites and defers the full expensive replay prediction pass to `prepare`;
- `prepare` persists the complete single-source replay authority into campaign restart state;
- internal MACE ExtXYZ files remain disposable transport adapters to existing TRAIN2/DATA8 contracts rather than external configuration authority;
- source-inspection and transport-artifact receipts eliminate repeated 12k replay scans on process restarts;
- storage accounting protects `replay_set` as the sole new-style external replay input;
- the supplied 12,000-frame LTA true-label campaign path produces exactly 10,000/2,000 and restarts in about 0.60 s on the development CPU host;
- real MACE/CUDA/CuEq qualification remains deferred to regenerated FINAL-GPU1 after REPLAY-UNIFY1E.
