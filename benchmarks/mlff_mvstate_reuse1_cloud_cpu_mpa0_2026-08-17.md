# MVSTATE-REUSE1 CPU qualification

Release: mdstats 0.20.236a0  
Architecture revision: 103  
Status: **PASS - CPU optimization program closed; FINAL-GPU1 next**

MVSTATE-REUSE1 persists authenticated MVSEL sparse-state checkpoints and allows REPAIR to start from the exact cached rung state until the first accepted repair swap. After repair diverges, the historical mutable state is carried forward; pure checkpoint reconciliation was rejected because it perturbed FP64 representative-gain arrays at the 1e-17--1e-16 level. Batched CSR gather preparation is permitted only while candidate-major arithmetic remains in the historical exact order.

## Integrated result

The untouched 0.20.235a0 chain median is 11.998 s. MVSTATE-REUSE1 is 11.017 s excluding persistence and 11.193 s including the one-time authenticated cache write, a fresh-chain speedup of 1.072x. REPAIR improves from 5.365 s to 4.272 s (1.256x). Cache write/read medians are 0.176/0.125 s for ~7.02 MiB. Peak RSS changes from 339.5 MiB to 358.5 MiB.

All FEAS/NEIGHBOR/MVIDX/MVSEL/REPAIR/MVQUAL digests are identical between control and current runs. The repair digest is `ab7dc752555114bcd756913187e1d0eb7069c2e9a093f2a8a41130f485cdc33f` and state-cache digest is `9904a0c96c83f4fdfe47558dc115d59664ab1a5a5456e687b9d7d3c75c1912db`.

Cumulative fresh-chain speedup versus the PERFBASE1-era 0.20.225a0 target-chain authority is 2.435x. The remaining target-chain cost is dominated by exact sequential sparse-state mutation; no additional material duplicated reconstructible state remains that justifies another CPU-only gate.

Active qualification uses MACE-MPA-0 medium checkpoint SHA-256 `75428afe3a1d7d8062e19bcaabd5c433623cabf308242ec9fb493e38604fb638`; the state-cache architecture is foundation-model independent and remains compatible with MACE-MH-1.

Evidence content digest: `6574082019480b5ea3cbe82e9cee2295db477bb74685123dfd569ab08aa320ac`.
