# mdstats 0.20.112a0 patch notes

This is a small MLFF runtime-output hotfix. It does not advance the architecture roadmap; STOR2 remains next.

## MACE/PyTorch warning condensation

Evaluation now captures repeated warnings originating from MACE and PyTorch across checkpoint materialization, inference, and target-head/deployment export. Repeated instances are grouped by origin, warning category, compact source path, and normalized message, then reported once as a compact `MaceRuntimeCompatibilityWarning`. The known TorchScript deprecation, tensor-copy, and TorchScript AST annotation warnings are shortened to concise labels.

The full campaign `evaluate` command is also an outer warning scope, so warnings emitted by setup/reconstruction code around the lower-level inference scopes are intercepted. Non-MACE/non-PyTorch warnings are still replayed with their original warning category/location.

The public historical TorchScript warning code remains unchanged; broader warning groups are additive fields on the compatibility record. Scientific DATA8/training/evaluation identities and existing campaign caches are unchanged.
