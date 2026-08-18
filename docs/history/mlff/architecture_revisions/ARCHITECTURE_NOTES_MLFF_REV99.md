# MLFF architecture revision 99 - MVQUAL-PAR1

Revision 99 completes the exact-equivalence `MVQUAL-PAR1` performance gate.

- Schedules immutable `(domain, selector, target size)` same-N scoring jobs globally through PARCORE1.
- Preserves TARGET-DATA2B independent coverage reports, MVIDX covered-mass cross-checks, hard obligations, MVKERNEL1 telemetry, comparison order, and the complete persisted MVQUAL plan.
- Constrains campaign cKDTree/BLAS work to one native lane per outer job and reduces completed work in historical domain/size order.
- Keeps direct API calls without an explicit resource scope in their historical native-thread environment after qualification exposed a ~1e-16 Wasserstein change caused solely by BLAS thread limiting.
- Adds execution-only task-memory admission and a conservative four-lane automatic ceiling for memory-bandwidth-heavy same-N jobs.
- Preserves the production-contract benchmark plan digest `2ebd7f5dc2b560e3150fe4849e7098be2eff56469779f15b2befda74059fc90b` while reducing the paired 16k/12-job median from about 0.866 s to about 0.409 s at four lanes.
- Advances the optimization program to `AUDIT-EVAL-PERF1`.
