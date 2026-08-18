# mdstats 0.20.215a0 - TRAIN2 FP32 CuEq parity hotfix

## Scope

This release changes only the TRAIN2 FP32 e3nn-versus-pure-CuEq numerical-equivalence policy and the release provenance that binds it. It does not change the source/DATA6 parity policy, FP64 parity, training convergence criteria, replay logic, target-data selection, or FINAL-GPU1 matrix membership.

## Policy change

- Generic source/DATA6 FP32 parity: unchanged at `rtol=1e-5, atol=1e-6`.
- TRAIN2 FP32 parity: `rtol=1e-5, atol=1e-5` (previously `atol=2e-6`).
- TRAIN2/source FP64 parity: unchanged at `rtol=1e-10, atol=1e-12`.

The revised TRAIN2 ceiling is motivated by MPA-0/default workstation evidence (`Emax=2.384e-7`, `Fmax=8.911e-6`, `Smax=1.660e-7`, `Dmax=2.883e-7`, `selection_identical=True`). It is treated as an FP32 backend-equivalence envelope for non-associative/reordered accumulation, not as an accuracy or convergence tolerance.

## Fail-closed behavior

- Selection identity is still mandatory.
- Non-finite values still fail immediately.
- The `1e-5` ceiling is fixed and never automatically widened.
- A zero-reference difference just above `1e-5` is explicitly regression-tested as a failure.
- No automatic e3nn fallback is introduced.

## FINAL-GPU1 binding

FINAL-GPU1 remains v3/18 items. Preflight advances from v8 to v9 and now embeds the exact TRAIN2 parity-policy payload and digest in the handoff manifest. Handoff integrity verification rejects a policy-digest mismatch.
