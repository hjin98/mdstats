# Bounded checkpoint evaluation and tiered deployment verification

## Scope

This note explains the current cost-control boundary for checkpoint evaluation and deployment verification. It preserves authoritative model selection and mandatory deployment checks while avoiding repeated training-scale inference when a bounded exact-equivalent evaluation plan is available.

Exact shortlist, metric, resource, and verification policies are owned by the current specifications indexed in `docs/specs/training_data/README.md`.

## Checkpoint screening versus authoritative evaluation

Training may emit inexpensive per-epoch validation summaries. Those summaries may construct a deterministic evaluation shortlist under the current checkpoint-control policy, but they are not themselves final checkpoint authority.

Every shortlisted checkpoint is reconstructed and evaluated on the current authenticated target/replay monitor evidence. The resulting authoritative metrics and mandatory constraints decide checkpoint admissibility.

A bounded shortlist is an evaluation budget, not an exhaustive scientific claim. A completed run with no admissible checkpoint records that result explicitly; it does not silently promote an unevaluated or constraint-violating checkpoint. When the current policy permits exhaustive evaluation, its explicit configuration changes the evaluation workload without changing metric semantics.

## Replay-label plane

Replay training and replay evaluation remain separate evidence roles. When true-label replay evaluation is configured, the evaluation layer binds exact replay geometry/source identities to the independent true-label plane and computes candidate/foundation retention metrics against that evidence.

Pseudo-label replay may diagnose behavioral drift but does not masquerade as an absolute DFT-label validation metric.

Changing replay-label evidence refreshes evaluation identity; it does not rewrite the immutable replay-training artifact under the same identity.

## Verification tiers

Production/deployment candidates receive the complete mandatory verification suite defined by the current deployment policy. Cross-validation fold models are protocol-validation evidence and are not deployment candidates.

A verification case binds model bytes, structure/evidence bytes, physical condition, integration/analysis settings, numerical mode, and runtime identity. Authenticated completed cases may be reused after interruption.

Short stability smokes may establish finite-output and gross physical-safety predicates but cannot claim long-time drift/transport evidence that requires a longer trajectory.

## Diagnostic cadence

The numerical integrator advances according to the current simulation contract. Expensive diagnostic evaluation may occur at a qualified cadence when that cadence preserves the owning verification predicate.

Long-time metrics such as energy-drift fits are reported only when the required trajectory length/evidence conditions are satisfied. A short smoke cannot substitute for them.

## Cleanup contract

Reconstructible excluded-checkpoint caches may be pruned after authoritative selection evidence is committed and restart requirements are satisfied. Selected checkpoints, exported models, current metric/admissibility records, hashes, and mandatory verification evidence remain protected under the storage policy.

Cleanup cannot alter scientific selection or erase evidence needed to reproduce why a candidate passed or failed.

## Single-generation boundary

This note defines current behavior only. Historical release/gate implementations remain in Git/history and do not create alternate shortlist, reconstruction, or verification semantics for new campaigns.
