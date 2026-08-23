---
title: "MLFF-DATA9A9b Production DATA6-DATA8 Materialization"
author: "mdstats project"
date: "2026-08-23"
version: "0.20.132a0"
geometry: margin=0.8in
fontsize: 10pt
header-includes:
  - |
    ```{=latex}
    \usepackage{microtype}
    \usepackage{booktabs}
    \usepackage{longtable}
    \usepackage{array}
    \usepackage{enumitem}
    \setlist{nosep}
    ```
---

# 1. Purpose

DATA9A9b closes the orchestration gap between a completed checkpoint-bound
DATA6 model sweep and executable final/fold DATA8 training jobs. DATA7 and DATA8
scientific semantics already exist. This stage makes their production
realization exact, restartable, tamper-evident, and bound to one replay corpus.

The stage owns neither feature definitions nor MACE training. It owns:

- freezing the complete DATA6 sweep identity;
- freezing every canonical final and cross-validation DATA7 domain;
- freezing all DATA7 fitting, objective, weighting, checkpoint, and selection policies;
- binding one exact replay-train/replay-monitor plan;
- checkpointing each realized DATA7 bundle independently;
- invalidating downstream DATA8 evidence when any DATA7 artifact changes;
- promoting a complete final/fold DATA8 tree only after all prerequisites pass;
- emitting one immutable materialization record that can update production qualification.

DATA9B remains closed until a complete production DATA9A9b record exists.

# 2. Ownership boundary

`mdstats.training_data.production_materialization` owns orchestration and
restart evidence only.

- DATA6 owns checkpoint-bound descriptors, predictions, residuals, and blinded summaries.
- DATA7 owns fold-local feature fitting, E0 fitting, objectives, weights, selection, and coverage.
- DATA8 owns extxyz export, MACE configuration, replay staging, loader dry runs, and sealed evaluation metadata.
- Replay owns replay-file inspection, disjointness, label provenance, and retention policy.
- DATA9B owns training execution, checkpoint comparison, committee construction, and freeze.

The production orchestrator calls these owners and records their native bundle
digests. It does not reproduce their algorithms.

# 3. Frozen production plan

`ProductionMaterializationPlan` binds:

- source, frame, DATA4, DATA5, and DATA6 identities;
- the complete DATA6 model-sweep checkpoint;
- exact descriptor and prediction manifests;
- every canonical `FeatureFitDomain` from DATA5;
- feature-metric, atomic-reference, objective, configuration-weight,
  checkpoint-metric, and selection-budget policies;
- the exact foundation checkpoint;
- optional foundation atomic reference energies;
- MACE compatibility policy and passing source probe;
- the exact replay train and monitor artifacts;
- optimizer, checkpoint-control, and extxyz policies;
- selected DATA7 ladder size and replay exposure settings.

The canonical domain set contains exactly one final-development domain and one
training domain for each declared cross-validation fold. The plan is rejected
when the replay plan is unresolved, when the completed DATA6 sweep differs from
the DATA6 bundle, or when the DATA8 foundation checkpoint differs from the
checkpoint used for DATA6 predictions.

# 4. Restart semantics

Each DATA7 domain is written independently to
`data7/<domain_digest>.data7.zip`. `ProductionData7ArtifactRecord` binds:

- domain digest;
- DATA7 bundle digest;
- safe relative path;
- file SHA-256.

`ProductionMaterializationCheckpoint` is atomically replaced after every newly
committed canonical domain. A bounded run may stop after
`max_new_data7_domains`; shared-cache hits count toward that limit because the
limit governs checkpoint advancement, not expensive-computation count. A later
run verifies and reuses all valid records. Parallel domain completion may be
out of order, but checkpoint mutation remains in canonical plan order.

The production implementation SHALL avoid hidden repeated whole-corpus work:

- build the frame-array index once and reuse it across DATA7 domains;
- use authenticated columnar/shard-batched raw descriptor sources where
  available while keeping every domain's fitted scaler/PCA/E0/weight state
  independent;
- admit independent final/fold domain fits through the runtime resource queue
  using the campaign CPU budget, a conservative peak incremental-memory
  estimate, inner native widths of one, and no GPU jobs;
- keep mutable extraction caches task-local under concurrent fitting;
- have workers publish immutable authenticated DATA7 cache generations and
  return compact receipts while the coordinator alone mutates production
  records/checkpoints;
- reuse lineage-identical DATA7 artifacts across seeds and modes through the
  shared recipe cache; current cache writes use atomic content-addressed
  generations while legacy flat generations remain read-compatible;
- verify and return each promoted DATA7 bundle in one load path rather than
  hashing/parsing it twice.

These rules make post-DATA6 orchestration linear in frame count for fixed fold
count, feature dimension, and largest selection ladder, apart from bounded
$O(K^2d)$ selected-neighbor reporting and fixed-dimension linear algebra.

If a DATA7 artifact is missing, malformed, modified, or bound to a foreign
DATA6 bundle, it is either rejected or recomputed according to the explicit
execution policy. Any invalid DATA7 artifact invalidates the DATA8 tree because
the training protocol depends on its fitted transforms, E0 values, selection,
and weights.

# 5. Exact replay binding

Production multihead replay requires two disjoint files:

- replay training data;
- replay monitor data.

The plan binds their configuration counts, atomic-number sets, geometry
identities, numerical energy/force/stress label identities, label keys, label provenance, foundation-checkpoint identity for
pseudo-labels, selection provenance, head weight, target weight, and retention
policy.

DATA8 may stage and rescale the replay-train file to realize fixed-file MACE
weights. Therefore source and staged file byte hashes need not be equal. The
orchestrator verifies semantic equivalence: configuration identity, labels,
provenance, counts, species, and replay policy must remain unchanged.

# 6. DATA8 promotion

DATA8 construction begins only when every planned DATA7 domain is valid. Immutable fixed-file recipes are enumerated and deduplicated before production-tree mutation. Cache misses may be populated by balanced fresh CPU-only interpreter batches using compact recipe/path descriptors and mmap/file-backed read-only context. CPU, RAM, task count, and the configured free-disk reserve bound this execution-only concurrency. Workers publish only authenticated fixed-file cache generations; the parent then assembles the production tree canonically in hidden staging, verifies it, moves it into a content-addressed generation directory, and exposes it by an atomic `data8` symlink switch. The output tree contains:

- one final-development job;
- one job per cross-validation fold;
- selected target-train and target-monitor extxyz files;
- fold evaluation files that are never referenced by training configs;
- staged foundation and replay resources;
- MACE configs, commands, job manifests, and loader dry-run evidence;
- sealed locked-test metadata without materialized locked-test labels.

A DATA8 artifact record binds the native DATA8 bundle digest and a deterministic
relative-path/file-SHA tree manifest. Fixed-file cache population is
reconstructible execution state and never replaces this promoted authority.
Foundation/selected-head sources are authenticated and staged by atomic
hardlink-or-copy; repeated weighted-replay byte realizations may be reused from
an exact recipe-bound execution cache. Completion is promoted only after the
whole staged tree is hashed and its bundle is valid. Restored records perform
independent tree verification. Failed construction removes an unpromoted
partial DATA8 directory and records failure evidence.

# 7. Atomic-reference modes

For foundation-model fine-tuning, production normally uses
`FOUNDATION_RESIDUAL`. In that mode every fit-domain frame requires a persisted
foundation energy prediction, the exact foundation checkpoint digest, and a
complete foundation E0 mapping for all target elements.

From-scratch total-energy E0 fitting remains available for explicit tests and
non-transfer workflows. Foundation predictions or E0s must not be supplied to a
from-scratch fit.

# 8. Materialization record

`ProductionMaterializationRecord` exposes:

- plan and checkpoint identity;
- ordered DATA7 bundle digests;
- DATA8 bundle digest;
- completion state;
- verified loading of native DATA7 and DATA8 bundles.

The filesystem root is a relocatable location hint and is excluded from the
scientific content digest. The record supplies the exact DATA7/DATA8 digests and
replay binding needed by `ProductionCorpusQualificationRecord`. The production
qualification builder accepts the complete record directly, verifies DATA6
lineage, loads the native bundles, and derives replay/materialization status
without caller-supplied duplicate digests.

# 9. Failure rules

The stage fails closed for:

- incomplete or foreign DATA6 model-sweep evidence;
- changed source, frame, DATA4, DATA5, or DATA6 identity;
- a foundation checkpoint mismatch;
- unresolved or absent replay when replay is required;
- foreign or noncanonical DATA7 domains;
- modified DATA7 files;
- modified DATA8 files or tree membership;
- missing MACE compatibility support;
- selection sizes absent from a DATA7 ladder;
- replay/target exact geometry overlap;
- incomplete residual-E0 evidence;
- any attempt to materialize DATA8 before all DATA7 domains pass.

# 10. Focused acceptance tests

The release gate must cover:

1. bounded one-domain execution followed by deterministic resume;
2. one final and all fold-local DATA7 bundles;
3. exact replay binding in every DATA8 protocol;
4. no evaluation or locked-test file in a MACE training configuration;
5. DATA7 tamper detection and downstream DATA8 invalidation;
6. DATA8 tree tamper detection;
7. plan mismatch rejection;
8. historical DATA6 compatibility remaining unchanged;
9. source/wheel export and registry parity;
10. immutable record serialization and relocation-safe identity;
11. exact bounded-FPS prefix equivalence to the former deterministic algorithm;
12. descriptor-summary reuse across overlapping DATA7 domains;
13. shared DATA7 reuse across training variants and process restarts;
14. no duplicate parse/hash pass when verified DATA7 immediately feeds DATA8.

# 11. Scope of the current implementation

Version 0.20.55a0 retains and hardens the complete restartable control layer and
qualifies it on a bounded four-domain target/replay workflow. It does not claim
that the full 2,734-frame production sweep has completed in this execution
environment. The production corpus must run DATA9A9a to completion, then execute
this DATA9A9b plan before DATA9B training begins.
