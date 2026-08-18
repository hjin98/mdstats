# mdstats 0.20.98a0 patch notes

## OPT-EVAL2: persistent prediction artifacts and foundation reuse

0.20.98a0 implements the second recorded MLFF post-campaign optimization stage.
Checkpoint evaluation now separates expensive model inference from reference-label
metric reduction and persists label-independent prediction artifacts for target and
replay monitors.

Prediction cache identity binds model SHA-256, head, ordered geometry identity,
evaluation dtype/device, acceleration policy, and a versioned numerical contract.
Prediction payloads are atomically published and SHA-256 authenticated. Corruption is
a cache miss and fails closed when neither a valid cache nor source checkpoint exists.

Candidate target/replay predictions can survive raw-checkpoint cleanup. If a metric
record becomes stale because true replay labels or metric weights changed, evaluation
can rebuild metrics directly from persisted predictions without reconstructing the
checkpoint or running MACE again.

Foundation work is also reused. Authenticated DATA6 predictions can satisfy the LTA
target foundation comparison, while frozen foundation-pseudolabel replay values can
supply the historical foundation prediction values for geometry-identical TRUE_DFT
replay evaluation. Parallel checkpoint workers use single-flight foundation miss
resolution so only one worker imports or computes each shared foundation prediction
set.

Checkpoint-evaluation records advance to schema v3 with optional prediction-artifact
digests while remaining compatible with v1/v2 records. The existing split between
TRUE_DFT evaluation replay provenance and DATA8 training replay lineage is unchanged.

Focused tests cover cache reuse after checkpoint deletion, metric-policy and true-label
changes without reinference, corruption recovery, DATA6/pseudolabel foundation reuse,
parallel single-flight behavior, legacy record migration, and the existing
restart/true-label/checkpoint/CuEq/evaluation-policy contracts.
