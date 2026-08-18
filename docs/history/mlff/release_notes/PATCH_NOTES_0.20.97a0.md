# mdstats 0.20.97a0 patch notes

## OPT-EVAL1: fast checkpoint reconstruction and selected-model export

0.20.97a0 implements the first recorded post-first-campaign optimization stage.
Evaluation and post-selection publication no longer normally launch a fresh
`mdstats-mace-train` process to reconstruct every raw MACE epoch checkpoint.

The completed run `.model` is used as an architecture template.  Checkpoint storage is
memory-mapped when PyTorch supports it; direct restoration requires exact state keys,
shapes and dtypes; CuEq/OEq training-backend conversion is reproduced under the shared
FX lock; and only `checkpoint["model"]` is restored.  A selected final checkpoint whose
state already matches the completed training model reuses that model directly.
Unsupported configurations and strict mismatches fail closed to the previous sandboxed
restart-export implementation.  LoRA remains fallback-only.

Multi-head target extraction now uses MACE's own `remove_pt_head` implementation
in-process, with the existing qualified select-head wrapper retained as fallback.
Parent-level export prints separate model-materialization and target-head export timing.
Checkpoint-model cache schema v2 records the reconstruction method and elapsed time while
remaining backward compatible with v1 cache receipts.

Focused qualification verifies exact energy, force and stress equality on an actual
MACE 0.3.16 model fixture, direct final-model reuse, dtype fail-closed behavior, guarded
CuEq conversion, multi-head target extraction/reload, source-checkpoint immutability,
and the existing restart/true-label/CuEq campaign contracts.
