# MLFF architecture revision 41 - target-PES accuracy, data-size convergence, and structural-stability roadmap

This architecture-only revision records the post-0.20.162 MLFF correction motivated by a campaign
that achieved strong held-out force metrics but produced an incorrect relaxed framework basin. It
does **not** change runtime behavior until its gates are implemented.

The revised authority is:

1. `TARGET-DATA2A` - freeze correlation/source lineage and independent evaluation/challenge roles
   before any evidence is allowed to choose the target training size;
2. `FOUNDATION-AUDIT1` - quantify zero-shot foundation adequacy. The target-size study may use only
   role-scoped foundation residuals from the authorized training-eligible development pool;
3. `TARGET-DATA2B` - hierarchical physics-stratified selection with generic bond-length, angle,
   coordination, local-distortion, worst-local-environment, tail, and structural coverage. Coverage is
   literal reference-side empirical-mass recall under one frozen local-neighborhood resolution, with
   separate robust extent guards and mandatory rare-stratum protection; Wasserstein/TV remain
   distribution-fidelity diagnostics rather than being renamed as coverage. Feature
   families/species/pairs/triplets are normalized without material-specific default bias;
4. `TARGET-DATA2C` - one deterministic nested seven-rung target ladder:
   `128/256/512/1024/2048/4096/8192` (`2^7` through `2^13`), with every rung a prefix of one frozen
   ranked target ordering;
5. `TARGET-DATA2D/E` - determine `N_target` through a bounded `7 -> <=4 -> 2 -> 1` funnel:
   - Stage A: no training; compare every rung with the full training-eligible reference. Every required
     family must cover at least 95% of frozen empirical reference mass at the common local-neighborhood
     resolution, while passing declared extent and mandatory-stratum guards. If more than four qualify,
     retain the four smallest; if three or four qualify, retain all; fewer than three is a hard coverage
     error.
   - Stage B: train the surviving three/four rungs for 10 epochs from one frozen foundation/seed and
     retain two. Target-force scores within `<= 1.0 meV/A` are practically equivalent and the smaller
     target set is preferred unless an applicable secondary hard gate distinguishes them.
   - Stage C: resume the two finalists to 30 total epochs under proven restart equivalence and select
     one using the same 1 meV/A rule plus PES, relaxation, topology, geometry, deployment, dynamics,
     and replay-admissibility evidence. If 8192 is still materially improving, report non-convergence
     within the bounded ladder instead of silently declaring it converged;
6. `TRAIN2A` - replay degradation has zero checkpoint/final-seed/target-size ranking credit and remains
   only an authenticated hard retention guardrail;
7. `TRAIN2B` - replace aggressive final-fit threshold stopping with substantial adaptation followed by
   an explicit low-learning-rate target-refinement stage;
8. `EVAL2` - add target global/species-macro/per-species/tail energy-force-stress evidence;
9. `DEPLOY-VERIFY1` - require target-head -> exported model -> deployment/ML-IAP numerical parity
   before physical verification;
10. `PES-VERIFY1` - add generic finite-displacement restoring-force probes;
11. `RELAX-VERIFY1` - require zero-K periodic graph/topology preservation plus quantitative geometry
    fidelity against the target reference;
12. `DYN-VERIFY2` - augment NVE/NVT numerical checks with structural integrity; and
13. `AL2` - add failure-onset/uncertainty-driven target enrichment with immutable generation lineage.

The generated protocol-development default is revised from three to **two optimizer seeds** with
three common CV folds and one final-development fit per seed:

```text
2 seeds x (3 CV folds + 1 final fit) = 8 training runs
```

The existing lightweight checkpoint monitors remain **256 target** and **512 TRUE_DFT replay**
configurations. They are not target-training-size defaults and are not changed by REV41.

A binding genericity rule is retained: observed failures may add generic descriptor classes or generic
qualification tests, but may not add element-, material-, or foundation-specific default weights.
Such weighting belongs only to explicit profiles/campaign overrides with provenance. Selection
weights, MACE training-loss weights, and qualification thresholds are separate namespaces.

Canonical details and gate acceptance criteria are in
`docs/arch_manuals/mlff_training_data_architecture.{md,pdf}`.

## Implementation progress through 0.20.167a0

TARGET-DATA2A, FOUNDATION-AUDIT1, TARGET-DATA2B, TARGET-DATA2C, and the TARGET-DATA2D bounded-funnel decision authority are implemented. TARGET-DATA2D executes Stage A and freezes the exact 10-of-30 / 30-of-30 evidence contracts; the historical adaptive-stop trainer is not accepted as Stage-B/C evidence. TRAIN2/EVAL2/physical-verification gates remain responsible for generating those later-stage records.
