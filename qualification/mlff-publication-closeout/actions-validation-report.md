# MLFF publication closeout GitHub Actions execution evidence

- workflow evidence commit: e048aeebcde62301f4ccf6109fd89a238030cf83
- immutable product/test evidence base: 5a6719d9fbabf04ddad7407b2729be0d0d1f76bf
- source identity proof: git diff --exit-code $EVIDENCE_BASE -- mdstats tests passed before execution
- compileall exit: 0
- corrected-surface pytest exit: 0
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
- failures: 0
- errors: 0
- skipped: 2
- junit time: 2145.090

### Non-pass details

#### skipped: tests.test_mlff_p7_r11_repair_acceptance::test_r11b2_real_mace_product_execution_is_unavailable_or_passes

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_p7_r11_repair_acceptance.py:273: UNAVAILABLE/BLOCKING: the supported LAMMPS/ML-IAP runtime is absent (LAMMPS python module unavailable: No module named 'lammps'); deferred to final target-machine qualification.
~~~

#### skipped: tests.test_mlff_p7_r12_repair_acceptance::test_r12b11_real_publication_execution_is_blocking_until_a_capable_runtime

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_p7_r12_repair_acceptance.py:773: UNAVAILABLE/BLOCKING: actual frozen-publication MACE execution could not run on this host (The LAMMPS qualification worker exited abnormally; no successful product evidence is publishable (exit 1): ModuleNotFoundError: No module named 'lammps'); deferred to target-machine qualification.
~~~

## Mandatory focused publication and P7 suites

- tests: 91
- failures: 0
- errors: 0
- skipped: 2
- junit time: 191.553

### Non-pass details

#### skipped: tests.test_mlff_mh1_publication_integration::test_real_mh1_resolves_family_and_explicit_omat_pbe_head

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_mh1_publication_integration.py:597: the locked real MACE-MH-1 checkpoint is not readily available in this environment; real MH-1 campaign qualification is deferred by the workplan
~~~

#### skipped: tests.test_mlff_mh1_publication_integration::test_real_mh1_publishes_and_reloads_through_the_publication_owner

~~~text
/home/runner/work/mdstats/mdstats/tests/test_mlff_mh1_publication_integration.py:615: the locked real MACE-MH-1 checkpoint is not readily available in this environment; real MH-1 campaign qualification is deferred by the workplan
~~~

