# E1 - real MACE/CUDA replay provider-retirement evidence

`e1_replay_provider_retirement_proof.py` drives the production replay
prediction owner - `build_replay_foundation_prediction_cache` with
`provider=None`, so the owner constructs the provider, transfers ownership once
to the operation-scoped executor, and must retire it itself - against the real
MH-1 checkpoint and the real selected replay corpus, in a Python process that
stays alive after the owner returns.

It captures NVML aggregate/process occupancy and PyTorch
allocated/reserved/max around provider acquisition, the inference high-water,
the final prediction consumer, the explicit close, and post-close.

It runs **two** disjoint cold builds on purpose. One cycle can only show that
occupancy fell; two cycles distinguish retirement from a smaller leak, because a
second full build with its own provider and its own inference must add nothing
durable.

Host at capture time: NVIDIA GeForce RTX 3090 (24 GiB), PyTorch 2.13.0+cu126,
mace-torch 0.3.16.

`E1_REPLAY_PROVIDER_RETIREMENT_EVIDENCE.txt` is the captured run. Reproduce with:

```bash
python qualification/replay-provider-lifetime/e1_replay_provider_retirement_proof.py <scratch-dir> 128
```

The script asserts its own claims and exits non-zero if they do not hold:
exactly one provider construction, one executor construction, and one explicit
close per cold build; no live provider/executor/model reference in the returned
cache record; post-close occupancy a small fraction of the inference
high-water; and post-close occupancy that does not grow across the second
cycle.

The residual left after close is a bounded one-time MACE/e3nn first-forward
runtime residency that is independent of this owner: closing a provider that
never ran inference returns allocated/reserved to exactly the pre-provider
baseline, and the second cold build adds zero further residency.
