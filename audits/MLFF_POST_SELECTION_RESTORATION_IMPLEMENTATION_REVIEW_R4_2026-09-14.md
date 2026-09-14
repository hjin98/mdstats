# MLFF post-selection restoration implementation/integration Review R4 — 2026-09-14

## Disposition

**PASS for implementation and integration; overall workplan remains NO-PASS only because G13 scientific qualification is still open.**

Review subject:

- executable/spec/test candidate: `8df2dd798c3390071b89d54fbd9e5d88c8b8e4cb` (`fix-3`);
- assembled branch head: `bf98b47ad39831364abef0a53957f421df8b4d4b`, whose only delta from the executable candidate is regenerated documentation PDFs;
- governing accepted D1/D2 method papers, canonical D3 architecture, current P5/P7/DATA8/DATA9B3 D4 specifications, replay/currentness/restart owners, and affected real-owner evidence.

There is **no Serious Challenge** to D1, D2, or D3. The accepted method and architecture remain coherent and realizable.

## G1B ancestry re-review — PASS / CLOSED

The current P5 D4 specification and implementation preserve the accepted acyclic dependency direction:

```text
role plan
  -> PostSelectionFittedPreparation
  -> PostSelectionMaterialization
  -> run/checkpoint/evaluation evidence
```

Current CV and final-production plans do not bind fitted-preparation ancestry. Fitted preparation binds its owning plan/run ancestry, and downstream materialization/evidence bind the preparation. No reverse edge, placeholder plan, parallel schema, or runtime compensation was introduced.

## G12A replay-transport/integration re-review — PASS / CLOSED

### Replay transport

The repair is reductive and uses the existing replay owners. `replay.py::_replay_transport_frame` is the common label/transport writer for current TRUE_DFT, pseudolabel, and legacy true-label rematerialization. It removes inherited source labels and `config_weight` / `config_*_weight` metadata, then emits:

```text
config_weight         = 1.0
config_energy_weight  = 1.0 iff a current energy label is rendered, else 0.0
config_forces_weight  = 1.0 iff current force labels are rendered, else 0.0
config_stress_weight  = 1.0 iff a current stress label is rendered, else 0.0
```

Direct legacy split files remain immutable and are admitted only when the existing replay inspection boundary establishes the same effective MACE semantics. No new P5-only parser, wrapper, loss, weighting layer, replay registry, or cache was added.

The direct-file stress rule was independently checked against pinned MACE `v0.3.16` (`4d2da09413ac1407f37cdbb6b81fa28e4c15655e`): `mace.data.utils.config_from_atoms` first reads `config_<property>_weight` and then forces the property weight to zero when the actual property is absent. The mdstats guard therefore matches the dependency's effective loader behavior rather than inventing different mask semantics.

### Currentness and expensive-parent reuse

TRUE_DFT and pseudolabel derived-view/receipt generations were advanced and now bind the canonical neutral/binary transport policy. Pre-repair self-authenticating views cannot remain current. The changed representation is limited to derived ExtXYZ transport; replay source identity, split authority, true-label cache, foundation-prediction cache, pseudo qualification, and source index remain reusable when unchanged. The real-owner currentness test demonstrates rematerialization with a prediction-cache hit and zero new foundation-inference calls.

### Numerical/real-MACE falsification

The real MACE parser/loader/native `UniversalLoss` test compares otherwise identical neutral and deliberately contaminated replay sources. Current rendered views produce identical exact binary masks and identical native loss, including both stress-present and stress-absent cases. The sensitivity control shows that feeding the same contamination directly into MACE changes the loss, proving that the oracle can detect the original defect.

### Legacy and restart boundaries

The legacy direct-file and rematerialization cases are covered, including PRESELECTED, TRUE_DFT, pseudolabel, paired `true_labels/` candidates, and stale pre-repair provenance.

The P5-F structural oracle no longer forbids the generic `restart_latest` token. It now traces actual P3 screening-continuation ownership and separately proves that P5's own `--restart_latest` is reachable only through authenticated P5 continuation/currentness. Product restart behavior was not removed or renamed to satisfy the test.

### Cross-surface integration

Current guide/config/spec surfaces now agree that `[objective]` governs P3 and separately accepted P5 scratch, while foundation P5 uses fixed native `UniversalLoss` 1:10:1. DATA9B3 exposes the actual command surface and current CV defaults. P7 consumes the frozen P5 publication through `common_monitor_record_digest`; target-size M3 is not a P5 publication/currentness parent. DATA8 atomic-number prose is scoped away from restored-P5 foundation-checkpoint reconstruction.

A broader side-effect check found no regression of current P3/DATA8 weighted ownership: current DATA8 no longer routes through `inspect_replay_extxyz`, and current P3/P5-scratch weighting remains on its separately accepted owners.

## Evidence assessment

Focused changed-owner evidence recorded by the implementer is admissible for the repaired candidate:

- replay transport owner suite: `10 passed`; the same new oracle gives `9 failed, 1 passed` against the pre-repair product, establishing discrimination;
- real pinned-MACE replay-mask/UniversalLoss oracle: `1 passed`;
- replay-view currentness/no-reinference oracle: `1 passed`;
- P5-F structural restart/absence suite: `15 passed`, with existing real P5 continuation/currentness tests also passing;
- public/config/spec agreement check: passed;
- Semgrep structural scan found no replay `REF_*` writer outside the common replay transport owner.

The 119-file affected sweep produced `2083 passed, 47 failed, 4 skipped`. This is **not** treated as a green full-suite result. Its admissible use here is differential only: the 47 failing node IDs are exactly the same node set on the stashed pre-repair baseline, and the skips are pre-existing environment/unavailable checks. No new affected failure was introduced. The focused real-owner and numerical oracles, not this broad sweep, close G12A.

The docs-build workflow succeeded for executable candidate `8df2dd...` and generated branch head `bf98b47...`; that establishes derived-document regeneration only and is not used as functional acceptance evidence.

## Remaining blocker — G13 only

G13 remains required before the overall restoration workplan can pass:

1. run a bounded current-candidate real-LTA pilot;
2. record the true pre-update foundation baseline and restored checkpoint observations;
3. record common-monitor target RMSE, TRUE_DFT replay RMSE/degradation, resolved loss/dimensional-threshold/exposure identity, selected-head residual-E0 identity, composition-transfer result, corpus counts/order, and exact common-monitor identity;
4. if the pilot passes, run the required three-fold affected qualification;
5. if correctly restored TRUE_DFT replay still shows material forgetting comparable to the prior failure regime, reopen D1/D2 rather than adding another D4 compensation.

Production-scale GPU/CuEq/LAMMPS/MLIAP qualification remains deferred to the final complete release package and the user's final machine-side qualification pass.

## Review state

```text
D1/D2                         PASS
D3                            PASS
G1B D4 ancestry               PASS / CLOSED
D4 implementation             PASS
G11/G12 unchanged claims      PASS / applicable
G12A replay/integration       PASS / CLOSED
G13 scientific qualification OPEN / BLOCKING
Overall workplan              NO-PASS until G13
```

No product-runtime change is authorized by this review.