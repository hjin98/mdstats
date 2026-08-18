# MLFF architecture revision 65 - multi-view target-data coverage optimization roadmap

**Release:** `mdstats 0.20.198a0`  
**Gate:** `TARGET-DATA2-MVPLAN1`  
**Dependency-graph schema:** `47`

Revision 65 freezes the implementation roadmap for replacing random/semi-random target-data ordering with deterministic multi-view coverage optimization. It is a plan-only revision: revision-64 TARGET-DATA2C v4 remains executable until the final migration gate is qualified.

The planned generated size ceiling is 16,384, producing exactly eight power-of-two candidate sizes from 128 through 16,384. Full-development-pool feasibility is checked before subset optimization; the selector then builds exact nested prefixes using worst-view coverage deficit as the primary objective, followed by protected-stratum deficit, new weighted reference mass, representative gain, and diversity tie-breaking. Redundancy is defined by leave-one-out unique coverage, and repair uses deficit-directed shell-local swaps rather than random regeneration.

The downstream `8 -> 4 -> 2 -> 1` rule is explicitly candidate-count halving across the 3 -> 10 -> 30 epoch successive-fidelity stages. All eight sizes may receive 3-epoch evidence, but hard-coverage-failing candidates are ineligible to survive; at least four hard qualifiers are therefore required before the 10-epoch stage. The 0.95 hard coverage threshold is unchanged.

Implementation is frozen into nine ordered gates: FEAS1, MVIDX1, MVSEL1, REPAIR1, MVPERF1, MVQUAL1, SIZE-HALVE2, SIZE-FIDELITY2, and MVMIGRATE1. Dynamic upper-ladder rescue is retired only by the final migration gate after scientific and survivor-fidelity qualification.
