# MLFF publication closeout GitHub Actions execution evidence

- workflow evidence commit: 57d902910f6ad5a633ad1e2a68ccf5bfa3dc093c
- immutable product/test evidence base: 14c191f2a97c22c4ea27b27015e780fba051a9d5
- source identity proof: git diff --exit-code $EVIDENCE_BASE -- mdstats tests passed before execution
- compileall exit: 0
- corrected-surface pytest exit: 1
- focused-suite pytest exit: 0

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
- failures: 6
- errors: 0
- skipped: 2
- junit time: 2316.033

### Non-pass details

#### skipped: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_real_mace_product_execution_is_unavailable_or_passes

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_p7_r11_repair_acceptance.py:273: UNAVAILABLE/BLOCKING: the supported LAMMPS/ML-IAP runtime is absent (LAMMPS python module unavailable: No module named 'lammps'); deferred to final target-machine qualification.
~~~

#### failure: tests.test_mlff_p7_r12_repair_acceptance::test_r12b7_disk_exhaustion_aborts_without_touching_science

~~~text
tests/test_mlff_p7_r12_repair_acceptance.py:538: in test_r12b7_disk_exhaustion_aborts_without_touching_science
    cfg, paths = cli._load_config(config)
                 ^^^^^^^^^^^^^^^^^^^^^^^^
mdstats/training_data/_campaign_cli_core.py:1173: in _load_config
    cfg = tomllib.load(handle)
          ^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/tomllib/_parser.py:74: in load
    return loads(s, parse_float=parse_float)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/tomllib/_parser.py:121: in loads
    pos, header = create_dict_rule(src, pos, out)
                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
/opt/hostedtoolcache/Python/3.11.16/x64/lib/python3.11/tomllib/_parser.py:298: in create_dict_rule
    raise suffixed_err(src, pos, f"Cannot declare {key} twice")
E   tomllib.TOMLDecodeError: Cannot declare ('execution',) twice (at line 88, column 11)
~~~

#### skipped: tests.test_mlff_p7_r12_repair_acceptance::test_r12b11_real_publication_execution_is_blocking_until_a_capable_runtime

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_p7_r12_repair_acceptance.py:768: UNAVAILABLE/BLOCKING: actual frozen-publication MACE execution could not run on this host (The LAMMPS qualification worker exited abnormally; no successful product evidence is publishable (exit 1): ModuleNotFoundError: No module named 'lammps'); deferred to target-machine qualification.
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_foreign_sibling_continuation_with_equal_runtime_shape_fails_before_eval2

~~~text
tests/test_mlff_downstream_integration_closure.py:907: in test_foreign_sibling_continuation_with_equal_runtime_shape_fails_before_eval2
    assert first.plan.to_dict() == sibling.plan.to_dict()
E   AssertionError: assert {'schema': 'm...se, ...}, ...} == {'schema': 'm...se, ...}, ...}
E     
E     Omitting 10 identical items, use -vv to show
E     Differing items:
E     {'structures_per_epoch': 3} != {'structures_per_epoch': 5}
E     {'content_digest': '3018f37f624708e5bfa7faa1d7d1533c168adecb77f7b7407cfa2f617f577f61'} != {'content_digest': '75cd713bc8b9ced2640f9cf8fdc2ebbe2491cba3306e3c86bedee0fe828049c6'}
E     
E     Full diff:
E       {
E           'schema': 'mdstats.train2-runtime-plan.v1',
E           'training_protocol_digest': '4c1ef6690be624f126f39c9aaa4e47c57e1458edbf8ec5db99e8d14e6586c8d9',
E           'optimizer_policy_digest': 'a779456f706e030acd7ceb8417045c448ca55851ade53191b4a22339d3ff7d8e',
E           'budget_policy': {
E               'schema': 'mdstats.train2-training-budget-policy.v1',
E               'planned_epochs': 2,
E               'checkpoint_interval_epochs': 1,
E               'allow_performance_driven_termination': False,
E               'genuine_failure_reasons': [
E                   'nonfinite_objective',
E                   'nonfinite_model_state',
E                   'nonfinite_optimizer_state',
E                   'corrupt_restart_state',
E                   'unrecoverable_runtime_failure',
E               ],
E               'policy_digest': '1f2db1cd065d891c4ef50484e8c10df6ccd710d9dbe047d71b01744e297aa8f1',
E           },
E           'learning_rate_policy': {
E               'schema': 'mdstats.train2-learning-rate-schedule-policy.v1',
E               'base_learning_rate': 0.0001,
E               'warmup_end_fraction': 0.05,
E               'adaptation_end_fraction': 0.8,
E               'initial_multiplier': 0.1,
E               'adaptation_end_multiplier': 0.1,
E               'final_multiplier': 0.01,
E               'update_driven': True,
E               'validation_can_mutate_schedule': False,
E               'native_adaptive_scheduler_enabled': False,
E               'policy_digest': 'c48a0d9a2a7143b4bcada812c65652417d53d4eeac840df5d4f6dd8765ed858d',
E           },
E     -     'structures_per_epoch': 5,
E     ?                             ^
E     +     'structures_per_epoch': 3,
E     ?                             ^
E           'replay_monitor_enabled': False,
E           'target_head_name': 'target_head',
E           'replay_head_name': 'pt_head',
E           'true_replay_monitor_sha256': None,
E           'execution_epoch_limit': 2,
E     -     'content_digest': '75cd713bc8b9ced2640f9cf8fdc2ebbe2491cba3306e3c86bedee0fe828049c6',
E     +     'content_digest': '3018f37f624708e5bfa7faa1d7d1533c168adecb77f7b7407cfa2f617f577f61',
E       }
~~~

#### failure: tests.test_mlff_downstream_integration_closure::test_every_frozen_size_is_cross_validated_before_the_campaign_rejects[0-0.02]

~~~text
tests/test_mlff_downstream_integration_closure.py:1117: in test_every_frozen_size_is_cross_validated_before_the_campaign_rejects
    fx.run_cross_validate(config, harness)
tests/_mlff_post_selection_fixture.py:683: in run_cross_validate
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
tests/_mlff_post_selection_fixture.py:683: in run_cross_validate
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
tests/_mlff_post_selection_fixture.py:683: in run_cross_validate
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
tests/_mlff_post_selection_fixture.py:683: in run_cross_validate
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
- errors: 0
- skipped: 2
- junit time: 204.542

### Non-pass details

#### skipped: tests.test_mlff_mh1_publication_integration::test_real_mh1_resolves_family_and_explicit_omat_pbe_head

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_mh1_publication_integration.py:597: the locked real MACE-MH-1 checkpoint is not readily available in this environment; real MH-1 campaign qualification is deferred by the workplan
~~~

#### skipped: tests.test_mlff_mh1_publication_integration::test_real_mh1_publishes_and_reloads_through_the_publication_owner

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_mh1_publication_integration.py:615: the locked real MACE-MH-1 checkpoint is not readily available in this environment; real MH-1 campaign qualification is deferred by the workplan
~~~

