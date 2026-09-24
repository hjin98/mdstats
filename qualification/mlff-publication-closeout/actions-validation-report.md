# MLFF publication closeout GitHub Actions execution evidence

- workflow evidence commit: a2045f727a4acaf6aeb9150cc19058ae689cf20e
- immutable product/test evidence base: a382c118a62dc32f52536efe7b8aa08dc38f18f5
- source identity proof: git diff --exit-code $EVIDENCE_BASE -- mdstats tests passed before execution
- compileall exit: 0
- corrected-surface pytest exit: 1
- focused-suite pytest exit: 1

## Environment

~~~text
python=3.11.16
mdstats=0.20.242a0
mace-torch=0.3.16
ase=3.29.0
torch=2.14.0+cpu
torch-ema=0.3
e3nn=0.4.4
numpy=2.4.6
scipy=1.17.1
pytest=9.1.1
hypothesis=6.168.1
~~~

## Corrected closeout evidence surfaces

- tests: 104
- failures: 71
- errors: 0
- skipped: 1
- junit time: 1291.969

### Non-pass details

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b1_qualification_consumes_the_p5_decision_and_ranks_nothing

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:100: in test_r11b1_qualification_consumes_the_p5_decision_and_ranks_nothing
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b1_single_best_publication_is_qualified_end_to_end

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:139: in test_r11b1_single_best_publication_is_qualified_end_to_end
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_canonical_target_head_reaches_export_and_mliap_builder

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:168: in test_r11b2_canonical_target_head_reaches_export_and_mliap_builder
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_wrong_head_is_a_different_product

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:188: in test_r11b2_wrong_head_is_a_different_product
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### skipped: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_real_mace_product_execution_is_unavailable_or_passes

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_p7_r11_repair_acceptance.py:273: UNAVAILABLE/BLOCKING: the supported LAMMPS/ML-IAP runtime is absent (LAMMPS python module unavailable: No module named 'lammps'); deferred to final target-machine qualification.
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_real_runtime_gate_blocks_rather_than_passing

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:360: in test_r11b2_real_runtime_gate_blocks_rather_than_passing
    config, _workspace, harness = _campaign(
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b3_terminal_record_is_not_current_after_a_binding_change

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:422: in test_r11b3_terminal_record_is_not_current_after_a_binding_change
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b3_status_never_reports_a_stale_release_verdict

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:463: in test_r11b3_status_never_reports_a_stale_release_verdict
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b3_documentation_only_change_does_not_stale_the_verdict

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:477: in test_r11b3_documentation_only_change_does_not_stale_the_verdict
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b3_release_index_enforces_the_same_current_binding

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:491: in test_r11b3_release_index_enforces_the_same_current_binding
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b4_new_bundle_stales_only_reference_dependent_components

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:522: in test_r11b4_new_bundle_stales_only_reference_dependent_components
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b4_component_input_identity_separates_dependent_components

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:567: in test_r11b4_component_input_identity_separates_dependent_components
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_dynamics_starts_from_authenticated_relaxed_coordinates

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:597: in test_r11b5_dynamics_starts_from_authenticated_relaxed_coordinates
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_missing_relaxed_reference_cannot_pass_dynamics

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:623: in test_r11b5_missing_relaxed_reference_cannot_pass_dynamics
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_each_frozen_diagnostic_rejects_independently[overrides0-nonfinite_or_incomplete_nve_temperature]

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:690: in test_r11b5_each_frozen_diagnostic_rejects_independently
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_each_frozen_diagnostic_rejects_independently[overrides1-nve_temperature_out_of_tolerance]

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:690: in test_r11b5_each_frozen_diagnostic_rejects_independently
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_each_frozen_diagnostic_rejects_independently[overrides2-protected_displacement_above_maximum]

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:690: in test_r11b5_each_frozen_diagnostic_rejects_independently
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_each_frozen_diagnostic_rejects_independently[overrides3-minimum_pair_distance_below_safety_bound]

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:690: in test_r11b5_each_frozen_diagnostic_rejects_independently
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_each_frozen_diagnostic_rejects_independently[overrides4-maximum_force_above_safety_bound]

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:690: in test_r11b5_each_frozen_diagnostic_rejects_independently
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b5_each_frozen_diagnostic_rejects_independently[overrides5-nve_energy_drift_above_maximum]

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:690: in test_r11b5_each_frozen_diagnostic_rejects_independently
    config, _workspace, harness = _campaign(tmp_path, config_text=_dynamics_config())
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b6_resume_after_crash_at_activation_completes_one_test

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:803: in test_r11b6_resume_after_crash_at_activation_completes_one_test
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b6_resume_after_locked_evidence_does_not_reopen_the_cohort

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:856: in test_r11b6_resume_after_locked_evidence_does_not_reopen_the_cohort
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b6_reveal_history_before_activation_pointer_is_repaired_without_reopen

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:894: in test_r11b6_reveal_history_before_activation_pointer_is_repaired_without_reopen
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b6_revealed_cohort_stays_revealed_after_a_currentness_change

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:974: in test_r11b6_revealed_cohort_stays_revealed_after_a_currentness_change
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b6_activation_holds_the_retention_reference_until_terminal

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:995: in test_r11b6_activation_holds_the_retention_reference_until_terminal
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b7_case_workers_come_from_the_accepted_resource_owner

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1035: in test_r11b7_case_workers_come_from_the_accepted_resource_owner
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b7_resource_scope_is_bound_but_capacity_is_not_numerical_identity

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1052: in test_r11b7_resource_scope_is_bound_but_capacity_is_not_numerical_identity
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b7_deployed_artifact_is_create_once_and_reauthenticated

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1072: in test_r11b7_deployed_artifact_is_create_once_and_reauthenticated
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b7_concurrent_same_member_artifact_creation_converges

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1104: in test_r11b7_concurrent_same_member_artifact_creation_converges
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b8_placeholder_protocol_fails_closed

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1127: in test_r11b8_placeholder_protocol_fails_closed
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b8_missing_protocol_fails_closed

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1136: in test_r11b8_missing_protocol_fails_closed
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b9_stress_unavailability_is_explicit_not_silent

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1189: in test_r11b9_stress_unavailability_is_explicit_not_silent
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11_assembled_integration_including_the_publication_decision

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1254: in test_r11_assembled_integration_including_the_publication_decision
    config, _workspace, harness = _campaign(tmp_path, config_text=text)
                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_wrong_head_or_dtype_receipt_is_refused

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1276: in test_r11b2_wrong_head_or_dtype_receipt_is_refused
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r11_repair_acceptance::test_r11b7_nested_thread_budget_is_applied_around_case_execution

~~~text
tests/test_mlff_p7_r11_repair_acceptance.py:1319: in test_r11b7_nested_thread_budget_is_applied_around_case_execution
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r11_repair_acceptance.py:71: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b9_capability_resolves_applicable_and_stress_is_compared

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:189: in test_r12b9_capability_resolves_applicable_and_stress_is_compared
    config, _workspace, harness = _campaign(
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b9_deployed_stress_divergence_rejects

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:214: in test_r12b9_deployed_stress_divergence_rejects
    config, _workspace, harness = _campaign(
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b9_operator_cannot_suppress_an_available_stress_channel

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:242: in test_r12b9_operator_cannot_suppress_an_available_stress_channel
    config, _workspace, harness = _campaign(
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b9_capability_reasons_are_auditable_when_inapplicable

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:268: in test_r12b9_capability_reasons_are_auditable_when_inapplicable
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b13_deployed_dynamics_preserves_periodicity_end_to_end

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:429: in test_r12b13_deployed_dynamics_preserves_periodicity_end_to_end
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b7_release_evidence_carries_a_measured_resource_observation

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:461: in test_r12b7_release_evidence_carries_a_measured_resource_observation
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b7_disk_exhaustion_aborts_without_touching_science

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:520: in test_r12b7_disk_exhaustion_aborts_without_touching_science
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b7_resource_observation_does_not_stale_scientific_evidence

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:569: in test_r12b7_resource_observation_does_not_stale_scientific_evidence
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b7_restart_extends_one_attempt_without_rewriting_samples

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:589: in test_r12b7_restart_extends_one_attempt_without_rewriting_samples
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b11_frozen_publication_member_drives_the_current_p7_deployment_owner

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:653: in test_r12b11_frozen_publication_member_drives_the_current_p7_deployment_owner
    config, _workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b11_real_publication_execution_is_blocking_until_a_capable_runtime

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:710: in test_r12b11_real_publication_execution_is_blocking_until_a_capable_runtime
    config, _workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b7_concurrency_changes_cost_but_not_scientific_evidence

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:818: in test_r12b7_concurrency_changes_cost_but_not_scientific_evidence
    config, _workspace, harness = _campaign(tmp_path)
                                  ^^^^^^^^^^^^^^^^^^^
tests/test_mlff_p7_r12_repair_acceptance.py:43: in _campaign
    config, workspace = fx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_foundation_path_forms_execute_and_survive_relocation[absolute]

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_downstream_integration_closure.py:196: in test_foundation_path_forms_execute_and_survive_relocation
    assert fx.run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
/home/runner/work/mdstats/mdstats/tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_foundation_path_forms_execute_and_survive_relocation[tilde]

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_downstream_integration_closure.py:196: in test_foundation_path_forms_execute_and_survive_relocation
    assert fx.run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
/home/runner/work/mdstats/mdstats/tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_foundation_path_forms_execute_and_survive_relocation[config_relative]

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_downstream_integration_closure.py:196: in test_foundation_path_forms_execute_and_survive_relocation
    assert fx.run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
/home/runner/work/mdstats/mdstats/tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/home/runner/work/mdstats/mdstats/mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_current_unaccepted_materialization_is_idempotent_without_reclamation

~~~text
tests/test_mlff_downstream_integration_closure.py:461: in test_current_unaccepted_materialization_is_idempotent_without_reclamation
    config, foundation, run_root = _failed_foundation_workspace(tmp_path)
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:443: in _failed_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_incomplete_materialization_publication_is_rebuilt_by_the_real_owner

~~~text
tests/test_mlff_downstream_integration_closure.py:487: in test_incomplete_materialization_publication_is_rebuilt_by_the_real_owner
    config, foundation, run_root = _failed_foundation_workspace(tmp_path)
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:443: in _failed_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_corrupt_materialization_config_is_typed_and_preserved

~~~text
tests/test_mlff_downstream_integration_closure.py:503: in test_corrupt_materialization_config_is_typed_and_preserved
    config, foundation, run_root = _failed_foundation_workspace(tmp_path)
                                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:443: in _failed_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_corrupt_final_materialization_record_is_typed_and_preserved

~~~text
tests/test_mlff_downstream_integration_closure.py:523: in test_corrupt_final_materialization_record_is_typed_and_preserved
    config, _foundation, run_root = _failed_foundation_workspace(tmp_path)
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:443: in _failed_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_foreign_internally_valid_materialization_is_typed_and_preserved

~~~text
tests/test_mlff_downstream_integration_closure.py:538: in test_foreign_internally_valid_materialization_is_typed_and_preserved
    config, _foundation, run_root = _failed_foundation_workspace(tmp_path)
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:443: in _failed_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_partial_checkpoint_is_not_resumable_by_file_presence

~~~text
tests/test_mlff_downstream_integration_closure.py:563: in test_partial_checkpoint_is_not_resumable_by_file_presence
    config, _foundation, run_root = _failed_foundation_workspace(tmp_path)
                                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:443: in _failed_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_authenticated_train2_continuation_is_resumed_by_the_real_p5_owner

~~~text
tests/test_mlff_downstream_integration_closure.py:740: in test_authenticated_train2_continuation_is_resumed_by_the_real_p5_owner
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_durable_continuation_without_materialization_fails_closed_and_preserves_state

~~~text
tests/test_mlff_downstream_integration_closure.py:760: in test_durable_continuation_without_materialization_fails_closed_and_preserves_state
    config, _foundation, run_root, _pauser = _paused_foundation_workspace(tmp_path)
                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:608: in _paused_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_durable_continuation_with_incomplete_materialization_fails_closed_without_rebuild

~~~text
tests/test_mlff_downstream_integration_closure.py:783: in test_durable_continuation_with_incomplete_materialization_fails_closed_without_rebuild
    config, _foundation, run_root, _pauser = _paused_foundation_workspace(tmp_path)
                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:608: in _paused_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_full_horizon_continuation_recloses_only_after_joint_authentication

~~~text
tests/test_mlff_downstream_integration_closure.py:863: in test_full_horizon_continuation_recloses_only_after_joint_authentication
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_foreign_sibling_continuation_with_equal_runtime_shape_fails_before_eval2

~~~text
tests/test_mlff_downstream_integration_closure.py:892: in test_foreign_sibling_continuation_with_equal_runtime_shape_fails_before_eval2
    config, _foundation, paused_root, _pauser = _paused_foundation_workspace(
tests/test_mlff_downstream_integration_closure.py:608: in _paused_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_persisted_mace_execution_evidence_mismatch_is_typed_and_preserved[authority_config_digest-ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff]

~~~text
tests/test_mlff_downstream_integration_closure.py:944: in test_persisted_mace_execution_evidence_mismatch_is_typed_and_preserved
    config, _foundation, run_root, _pauser = _paused_foundation_workspace(tmp_path)
                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:608: in _paused_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_persisted_mace_execution_evidence_mismatch_is_typed_and_preserved[target_frame_uid_set_digest-eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee]

~~~text
tests/test_mlff_downstream_integration_closure.py:944: in test_persisted_mace_execution_evidence_mismatch_is_typed_and_preserved
    config, _foundation, run_root, _pauser = _paused_foundation_workspace(tmp_path)
                                             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:608: in _paused_foundation_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_persisted_mace_replay_uid_evidence_mismatch_is_typed_and_preserved

~~~text
tests/test_mlff_downstream_integration_closure.py:969: in test_persisted_mace_replay_uid_evidence_mismatch_is_typed_and_preserved
    config, run_root, _pauser = _paused_multihead_workspace(tmp_path)
                                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_mlff_downstream_integration_closure.py:674: in _paused_multihead_workspace
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_corrupt_train2_continuation_is_typed_and_preserved

~~~text
tests/test_mlff_downstream_integration_closure.py:1000: in test_corrupt_train2_continuation_is_typed_and_preserved
    p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_every_frozen_size_is_cross_validated_before_the_campaign_rejects[0-0.02]

~~~text
tests/test_mlff_downstream_integration_closure.py:1117: in test_every_frozen_size_is_cross_validated_before_the_campaign_rejects
    fx.run_cross_validate(config, harness)
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_every_frozen_size_is_cross_validated_before_the_campaign_rejects[0-0.05]

~~~text
tests/test_mlff_downstream_integration_closure.py:1117: in test_every_frozen_size_is_cross_validated_before_the_campaign_rejects
    fx.run_cross_validate(config, harness)
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_every_frozen_size_is_cross_validated_before_the_campaign_rejects[1-0.02]

~~~text
tests/test_mlff_downstream_integration_closure.py:1117: in test_every_frozen_size_is_cross_validated_before_the_campaign_rejects
    fx.run_cross_validate(config, harness)
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_every_frozen_size_is_cross_validated_before_the_campaign_rejects[1-0.05]

~~~text
tests/test_mlff_downstream_integration_closure.py:1117: in test_every_frozen_size_is_cross_validated_before_the_campaign_rejects
    fx.run_cross_validate(config, harness)
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_p7_explicit_reference_root_is_canonical_and_cwd_independent[absolute]

~~~text
tests/test_mlff_downstream_integration_closure.py:1200: in test_p7_explicit_reference_root_is_canonical_and_cwd_independent
    config, _workspace = qfx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_p7_explicit_reference_root_is_canonical_and_cwd_independent[tilde]

~~~text
tests/test_mlff_downstream_integration_closure.py:1200: in test_p7_explicit_reference_root_is_canonical_and_cwd_independent
    config, _workspace = qfx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_p7_explicit_reference_root_is_canonical_and_cwd_independent[config_relative]

~~~text
tests/test_mlff_downstream_integration_closure.py:1200: in test_p7_explicit_reference_root_is_canonical_and_cwd_independent
    config, _workspace = qfx.build_qualified_campaign(
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

## Mandatory focused publication and P7 suites

- tests: 91
- failures: 0
- errors: 51
- skipped: 2
- junit time: 125.315

### Non-pass details

#### error: tests.test_mlff_p5_model_publication_acceptance::test_published_model_follows_the_selected_representative_not_the_terminal_epoch

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_published_file_is_a_complete_reloadable_mace_model

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_published_model_state_equals_the_authenticated_provider_realization

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_published_model_performs_bounded_finite_inference

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_train_production_prints_the_canonical_product_locator

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_operator_projection_is_written_and_is_not_authority

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_status_authenticates_product_bytes_and_is_side_effect_free

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_missing_model_publication_is_reclosure_not_completion

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_corrupt_leaf_recovers_at_a_fresh_locator_without_overwrite

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_same_run_evidence_at_a_different_position_is_not_currentness

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_storage_owner_certifies_the_exact_published_models

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_product_pointer_set_is_all_old_or_all_new[1]

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_product_pointer_set_is_all_old_or_all_new[2]

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_p5_parent_advance_after_materialization_blocks_pointer_commit[final_plan]

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_p5_parent_advance_after_materialization_blocks_pointer_commit[cv_plan]

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_p5_parent_advance_after_materialization_blocks_pointer_commit[cv_acceptance]

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_p5_parent_advance_after_materialization_blocks_pointer_commit[final_seed_assessment]

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_disk_reserve_refuses_publication_before_any_pointer_moves

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_loader_runtime_drift_reuses_identical_bytes_after_an_equivalence_proof

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_unloadable_representation_rebuilds_only_the_representation

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_provider_state_drift_fails_closed_instead_of_laundering_it

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_workspace_relocation_with_identical_bytes_preserves_deployment_identity

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_projection_replacement_refuses_a_planted_symlink

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_a_stale_classification_cannot_commit_after_currentness_moves

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p5_model_publication_acceptance::test_a_parameter_shell_checkpoint_cannot_source_a_published_model

~~~text
tests/test_mlff_p5_model_publication_acceptance.py:70: in published
    assert run_cross_validate(config, harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_deployment_identity_binds_the_p5_source_model_and_uses_a_full_root

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_deployment_source_is_the_published_model_not_the_checkpoint

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_realization_digest_composes_identity_and_deployed_bytes

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_identical_byte_rebuild_preserves_the_realization_set

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_frozen_r1_refuses_receipt_advance_to_r2[delete]

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_frozen_r1_refuses_receipt_advance_to_r2[corrupt]

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_changed_deployed_bytes_change_the_realization_set

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_receipt_and_artifact_are_authenticated_no_follow

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_receipt_replace_before_directory_fsync_requires_retry_fence

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_replaced_execution_scratch_does_not_delete_foreign_sentinel

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_replaced_build_scratch_does_not_delete_foreign_sentinel

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_reclaimed_scratch_rebuilds_without_treating_absence_as_corruption

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_checkpoint_only_components_do_not_acquire_representation_identity

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_mixed_realization_sets_are_not_terminally_admissible

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_a_receipt_advance_cannot_switch_a_frozen_invocation

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_deployment_realization::test_waiting_evidence_deploys_nothing

~~~text
tests/test_mlff_p7_deployment_realization.py:30: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_admission_captures_one_coherent_p5_parent_graph

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_terminal_publication_refuses_a_moved_p5_parent

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_terminal_publication_refuses_a_moved_assessment_parent

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_binding_drift_before_publication_is_refused

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_current_binding_reload_rejects_campaign_toml_drift_without_false_stale[specification]

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_current_binding_reload_rejects_campaign_toml_drift_without_false_stale[dtype]

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_current_binding_reload_rejects_campaign_toml_drift_without_false_stale[device]

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_release_claim_requires_its_matching_index

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_status_survives_released_scratch_cleanup_without_recreating_it

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### error: tests.test_mlff_p7_product_currentness_fences::test_checkpoint_only_components_do_not_reserve_model_staging

~~~text
tests/test_mlff_p7_product_currentness_fences.py:29: in session_bundle
    config, _workspace = qual.build_qualified_campaign(tmp_path, harness=harness)
                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_qualification_fixture.py:647: in build_qualified_campaign
    assert p5.run_cross_validate(config, p5_harness) == 0
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/_mlff_post_selection_fixture.py:669: in run_cross_validate
    return p4d._run(
tests/test_mlff_target_size_p4d_runtime_cutover.py:173: in _run
    return args.func(args)
           ^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:6317: in command_cross_validate
    return execute_current_cross_validate(args)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:6151: in execute_current_cross_validate
    plan, acceptance = execute_post_selection_cross_validation(context)
                       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5283: in execute_post_selection_cross_validation
    results = _run_post_selection_positions(pending)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:5066: in _run_post_selection_positions
    trained = _train_post_selection_pending_runs(training)
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/campaign_post_selection_runtime.py:4883: in _train_post_selection_pending_runs
    raise TrainingAdmissionBlockedError(
E   mdstats.training_data.training_parallel.TrainingAdmissionBlockedError: 2 pending TRAIN2 job(s) remain but no job is currently resource-admissible: initial=0; ceiling=0; native CPU threads/job=3; zero safe admission; zero currently admissible training jobs: host RAM budget holds no 16.0 GiB training process
~~~

#### skipped: tests.test_mlff_mh1_publication_integration::test_real_mh1_resolves_family_and_explicit_omat_pbe_head

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_mh1_publication_integration.py:597: the locked real MACE-MH-1 checkpoint is not readily available in this environment; real MH-1 campaign qualification is deferred by the workplan
~~~

#### skipped: tests.test_mlff_mh1_publication_integration::test_real_mh1_publishes_and_reloads_through_the_publication_owner

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_mh1_publication_integration.py:615: the locked real MACE-MH-1 checkpoint is not readily available in this environment; real MH-1 campaign qualification is deferred by the workplan
~~~

