# MLFF architecture revision 30 - ADAPT-VERIFY1 implementation

This release implements `ADAPT-VERIFY1` on top of the binary model-precision, common-monitor,
adaptive-stop, run-local champion, and authoritative top-K full-evaluation evidence established by
ADAPT-PREC1 through ADAPT-EVAL1.

Implemented contract:

- verification consumes only the fully evaluated admissible candidates frozen by ADAPT-EVAL1 and
  attempts them strictly in authoritative full-score order;
- the lowest-score candidate receives the complete bounded NVE matrix first; hard verification
  failure advances deterministically to the next already fully evaluated admissible candidate when
  fallback is enabled;
- fallback purchases no new target/replay accuracy evaluation and stops at the first verification
  pass;
- an adaptive winner may be a fold-run champion, so adaptive production publishes one verified
  deployment identity rather than fabricating a historical final-development committee;
- candidate checkpoints/capsules are authenticated and reconstructed without dtype-template casts,
  then their exact target-head bytes are used for NVE;
- failed verification-only model materializations are never published; the first passing model is
  atomically copied into `models/`, and its published SHA-256 must match the bytes that passed NVE;
- `single` candidates remain FP32 learned-model inference/deployment and `double` candidates remain
  FP64, while mdstats-owned persistent MD state, reductions, drift fits, and reporting remain FP64;
- content-addressed NVE case evidence is restart-reused and candidate/aggregate verification,
  deployment, and adaptive protocol-freeze records are immutable;
- the compatibility `protocol_freeze` authority key is populated by the adaptive freeze so storage
  lifecycle gates remain sealed, while typed historical protocol-freeze handling remains confined
  to legacy verification paths;
- ADAPT-MIGRATE1 remains the final closure gate for schema/restart/storage migration and broad
  historical-campaign qualification.

The canonical contract is documented in
`docs/history/mlff/retired_specs/mlff_adaptive_verification_spec.{md,pdf}` and the MLFF architecture manual.
