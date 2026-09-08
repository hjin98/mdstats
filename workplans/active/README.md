# Active workplans

Active workplans are temporary engineering coordination and do not define current mdstats behavior by themselves.

The current MLFF implementation authority is:

- `workplans/active/MLFF_TARGET_SIZE_INTEGRATION_CLOSURE_REPAIR_WORKPLAN.md`

Independent Software Design review round 4 of candidate `eef79ed3a0829d4d385c881456ce40c30c58e5bb` / executable `bb4befc4158049873f186acb28de83ba26da08c8` is **NO-PASS**.

Round 4 accepts the Part-VI documentation repair and preserves all previously accepted current-v3/multi-size runtime behavior. The recovered exact P5A6 workspace is also the correct historical evidence artifact.

The remaining blockers are now concentrated in the compatibility realization:

1. Round 4 added a large generic prerework reconstruction path in `campaign_post_selection.py` that synthesizes selected/P2-like authority from P5 CV/final descendants (`_LegacyEvaluationOrder`, `_LegacyExperimentDefinition`, `_LegacyTargetSizeAggregate`, `_load_legacy_prerework_training_contexts`). This reverses the frozen parent->child dependency direction and is the unplanned compatibility bridge the P6 authority explicitly required Design to avoid.
2. The new compatibility oracle is not independent: selected membership is reconstructed from a CV plan, and the expected M3 lineage used to validate the final plan is reconstructed from that final plan/materialization. Current target-size policy is also inserted into the synthetic historical definition without first authenticating it as the historical P2 policy. Remove the synthetic bridge and restore the minimum native P5A6 historical decoder/currentness path from the recovered source/workspace.
3. Because Round 4 changed central P5 runtime owners by roughly 400 lines, the recorded 200-test target-size/result-view suite is not the complete affected regression. Final closure must include the direct P5 R6-R9, production/restart/publication/assembled consumers and downstream P7/qualification paths that call the changed post-selection owners.

Repair policy is subtraction plus native historical schema/currentness restoration: no fake experiment definitions/orders/aggregates, no descendant-to-ancestor reconstruction, no blanket prerework-v1 current path, no preload migration, no synthetic fixture, and no new compatibility database/sidecar.

Full long-running real-data/GPU/CuEq/LAMMPS production qualification remains separate and deferred to the established final-release/user-machine qualification stage.
