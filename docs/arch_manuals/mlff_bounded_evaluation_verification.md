# Bounded checkpoint evaluation and tiered verification

## Scope

This manual defines the DATA9B cost-control contract introduced in mdstats 0.20.82a0. It preserves authoritative model selection and deployment checks while preventing evaluation and verification from repeating training-scale work.

## Checkpoint screening versus authoritative evaluation

Training already writes validation summaries for every epoch. Those summaries are inexpensive evidence because no model reconstruction is required. mdstats uses them only to construct a deterministic shortlist containing the latest durable checkpoint and candidates representing strong target and, when present, replay validation metrics.

The shortlist is not the final selector. Every shortlisted checkpoint is reconstructed and evaluated against mdstats monitor sets, including target force/energy/stress and mobile-ion/condition strata. Genuine DFT-labeled replay can supply an additional retention gate; foundation-pseudolabel replay supplies only an absolute behavioral-drift diagnostic. Production checkpoint selection uses these authoritative results. A zero shortlist limit restores exhaustive behavior.

## Independent replay-label plane

DATA8 replay artifacts remain the immutable training plane. When `[paths].replay_true_labels` is configured, evaluation resolves an independent label plane with the exact same ordered replay geometries. The original source-to-split mapping is authenticated by `replay_source_index` and geometry identities. Candidate and foundation metrics are then computed against true labels while the campaign run remains bound to its pseudo-label DATA8 artifact. The evaluation cache includes both identities, so changing true labels refreshes metrics without rebuilding or relabelling training data.

Evaluation records store full per-dataset metrics for the foundation and candidate on the target and replay monitors. This makes improvement and forgetting directly inspectable rather than reducing the comparison to one replay ratio.

## Verification tiers

A final/deployment model receives all configured structures and temperatures for the full NVE length. Cross-validation fold models are comparison evidence rather than deployment candidates and receive a bounded stability smoke unless no final model exists, in which case the strongest available fold receives full coverage.

Every verification case is identified by model bytes, structure bytes, temperature, step count, timestep, sampling cadence, numerical mode and runtime identity. Completed cases are reusable after interruption. A single calculator is retained while sequential cases for the same model run.

## Diagnostic cadence

Velocity-Verlet integration still advances every MD step. Expensive energy, force and all-pairs minimum-distance diagnostics are evaluated at a configurable cadence and at the final step. Energy drift is fitted only for full-length cases. Short smoke cases enforce finite outputs, minimum-distance and maximum-force bounds but do not claim a long-time drift result.

## Cleanup contract

After full evaluation commits a selected checkpoint and complete shortlist evidence, checkpoints excluded during screening may be removed when configured. Interim evaluation never applies this pruning because unfinished training may still need restart checkpoints. Selected checkpoints, exported models, metric records, hashes and diagnostics remain protected.
