# mdstats 0.20.127a0 patch notes

## ADAPT-VERIFY1 — score-ordered final verification and verified deployment

This release implements the sixth gate of the post-0.20.120 adaptive MLFF revision and closes the
new production selection loop from ADAPT-EVAL1 full-score ordering to one verified deployed model.

### Sequential authoritative verification

Adaptive verification consumes only ADAPT-EVAL1's fully evaluated admissible candidates. It tests
the lowest-full-score candidate first with the complete configured bounded-NVE matrix. A hard
verification failure advances to the next already fully evaluated candidate when
`fallback_to_next_full_evaluation_candidate = true`; verification stops at the first pass. Fallback
never purchases additional target/replay evaluation.

### Exact-byte publication instead of synthetic committee reconstruction

An adaptive winner may originate from a cross-validation fold, so the historical final-development
committee exporter cannot represent the new selection rule faithfully. mdstats authenticates each
candidate checkpoint/capsule, reconstructs it without dtype-template promotion, materializes its
exact target head internally, and verifies those bytes. Failed internal artifacts are deleted. The
first passing target-head artifact is atomically promoted into `models/`, and the deployment record
requires its SHA-256 to match the bytes that passed NVE. No synthetic adaptive committee is created.

### Precision and restart evidence

`single` remains FP32 learned-model inference/deployment and `double` remains FP64. mdstats-owned
persistent MD state, energy/observable accumulation, drift regression, scoring, and reporting remain
hard-coded FP64. Each NVE case is content-addressed and can be reused after interruption. Immutable
candidate, aggregate verification, deployment-model, and adaptive protocol-freeze records bind the
selected model back to EVAL1, checkpoint, full target/replay domains, model dtype, and exact bytes.

### Gate boundary

ADAPT-VERIFY1 publishes the first fully evaluated candidate that passes final deployment
verification. ADAPT-MIGRATE1 remains the final gate for schema/restart/storage migration closure and
broad historical-readability qualification. Historical committee/EVAL-MF workflows remain readable
for compatible old campaigns and do not determine adaptive winners.
