---
title: "MLFF-DATA9A9c Production-Gate Integrity Closure"
author: "mdstats project"
date: "2026-07-30"
version: "0.20.55a0"
geometry: margin=0.7in
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

DATA9A9c closes integrity gaps discovered during the pause-and-review of the
DATA9A9a/b implementation. The earlier stages correctly implemented restartable
foundation-model sweeps and restartable DATA7/DATA8 materialization, but four
scientific identities were still too weak:

1. a caller could describe a small bounded fixture as the expected production corpus;
2. presence of DATA6/DATA7 objects was treated as proof of foundation features and residual-E0 fitting;
3. replay semantic comparison bound geometry and label-key names but not numerical labels; and
4. DATA8 was written directly into its visible final directory rather than promoted from a verified generation.

This stage makes the DATA9A gate fail closed. It does not train a model and does
not change DATA6, DATA7, DATA8, or MACE scientific algorithms.

# 2. Ownership boundary

`mdstats.training_data.production_qualification` owns the frozen production
corpus definition and the final DATA9A gate decision.

`mdstats.training_data.production_materialization` owns restart, artifact
verification, generation promotion, and self-verifying loads.

`mdstats.training_data.replay` owns replay geometry and numerical-label
identity. DATA8 may alter declared configuration weights, but it may not alter
reference energy, force, or stress labels.

`mdstats.training_data.protocol` owns the foundation-checkpoint scientific
identity. Local paths are location hints, not scientific identity.

# 3. Frozen production-corpus plan

`ProductionCorpusPlan` is mandatory for production qualification. It binds:

- a plan ID and dataset ID;
- exact source- and frame-catalog digests;
- exact normalization and electronic-reference manifests;
- every expected run ID, frame count, composition, ensemble, and target-temperature interval;
- the expected cross-validation fold count;
- generic optional-extension evidence requirements; and
- whether the gate requires foundation features, foundation-residual E0, DATA8 artifacts, and replay.

The qualification function recomputes all observed identities. Caller-supplied
counts or Boolean statements cannot replace the plan. A bounded fixture may
qualify only against its own explicitly different plan; it cannot satisfy a
foreign production plan.

# 4. Evidence-derived foundation status

Foundation features are materialized only when DATA6 contains all of:

- one model-sweep plan;
- one verified model-sweep checkpoint digest;
- a complete descriptor manifest for the descriptor frame set; and
- a complete prediction manifest for the prediction frame set.

A DATA6 bundle without these records is not foundation-feature evidence.

Foundation-residual E0 is materialized only when every required DATA7 domain
contains an `AtomicReferenceFitRecord` with:

- `fit_mode = foundation_residual`;
- foundation predictions for the full fit domain;
- a complete foundation elemental-reference mapping;
- the exact foundation-checkpoint digest used by DATA6/DATA8; and
- internally consistent element order and mapping.

From-scratch total-energy E0 fitting cannot pass a residual-E0 requirement.

# 5. Replay numerical-label identity

This section defines the numerical replay-label identity used by production materialization.

For replay configuration $i$, the label identity is

$$
L_i = H\!\left(H(E_i), H(\mathbf F_i), H(\boldsymbol\sigma_i)\right),
$$

where stress may be absent and each array hash binds dtype, shape, and numerical
bytes. The aggregate label-payload digest binds the ordered sequence
$(L_1,\ldots,L_N)$.

`ReplayFileArtifact` therefore records separate:

- file SHA-256;
- geometry identities;
- numerical label identities;
- aggregate label-payload digest; and
- a non-identity local path hint.

Source and staged replay files may differ bytewise when DATA8 realizes
configuration weights. Semantic equivalence still requires exact geometry,
energy, force, stress, provenance, count, and policy identity.

# 6. Relocatable scientific identities

`FoundationCheckpointIdentity.content_digest` excludes the local checkpoint
path. It binds checkpoint SHA-256, foundation head, and model family. Moving an
identical checkpoint does not create a new scientific model identity.

`ReplayFileArtifact.content_digest` likewise excludes its local path. Location
remains serialized for loading, but relocation does not alter identity.

# 7. Verified DATA8 generation promotion

DATA8 is built in a hidden sibling staging directory. The orchestrator:

1. builds the complete DATA8 tree in staging;
2. writes and reloads the native DATA8 bundle;
3. hashes every file and computes the tree digest;
4. moves the verified tree into `.data8-generations/<tree_digest>`;
5. performs the atomic `data8` symlink switch by replacing the visible link with a link to that generation; and
6. verifies the promoted tree again before recording completion.

A previously valid generation remains available until the pointer switch.
Corrupt generation contents are replaced from newly verified staging output.
Partial staging directories never become qualified DATA8 evidence.

# 8. Self-verifying materialization loads

`ProductionMaterializationRecord.load_data7_bundles()` and
`load_data8_bundle()` verify file hashes, bundle digests, domain lineage, tree
membership, and replay semantics immediately before deserialization. Loading a
record restored from JSON cannot bypass artifact verification.

# 9. Generic optional-extension requirements

The production plan declares zero or more
`ProfileExtensionEvidenceRequirement` records. Each extension can require:

- partition-critical feature evidence in DATA4;
- selection-grade feature evidence in DATA6; and
- represented extension environment classes in DATA7 coverage reports.

The gate evaluates all declared extensions generically. No core rule names LTA,
rings, sites, or cations. The LTA provider may satisfy an `extension_id = lta`
requirement through the same interface as any future extension.

# 10. Failure semantics

The gate emits explicit blockers including:

- `production_corpus_does_not_match_frozen_plan`;
- `foundation_features_not_materialized`;
- `foundation_residual_e0_not_materialized`;
- `profile_extension_coverage_not_materialized`;
- `data8_artifacts_not_materialized`;
- `production_replay_corpus_not_bound`; and
- `cross_validation_fold_count_mismatch`.

A `passed` status requires every requirement in the frozen plan. No caller
Boolean can suppress a blocker.

# 11. Test requirements

Focused tests must prove:

- a foreign production plan rejects a bounded fixture;
- from-scratch E0 does not pass residual-E0 qualification;
- numerical replay-label changes fail semantic matching even at fixed geometry;
- replay and foundation identities are path independent;
- DATA8 is exposed through a verified generation pointer;
- tampered DATA7/DATA8 files fail through direct record loaders;
- generic extension requirements fail closed when absent;
- source-tree and wheel exports agree; and
- the dependency graph remains acyclic.

# 12. Exit gate

DATA9A9c is complete when code, tests, manuals, graph, archive, and wheel agree
on these contracts. This does not imply production-corpus completion. DATA9B
remains blocked until DATA9A9a and DATA9A9b satisfy the frozen production plan.
