# mdstats 0.20.236a0 - MVSTATE-REUSE1

- Complete MVSTATE-REUSE1 / architecture revision 103 and close the exact-equivalence CPU optimization program.
- Add authenticated exact MVSEL rung-state checkpoints and bundled native persistence for selector-to-repair execution-state reuse.
- Allow REPAIR checkpoint jumps only before its first accepted swap; reject post-divergence pure-checkpoint reconciliation because it changes FP64 arithmetic history.
- Keep historical exact replay as fallback/oracle for missing, stale, corrupt, or incompatible cache state.
- Batch only deterministic CSR gather preparation for predetermined replay additions; preserve candidate-major FP64 state mutation order.
- Reduce integrated 8,192-candidate target-chain time from about 12.00 s in untouched 0.20.235a0 to about 11.19 s including the one-time cache write; reduce REPAIR from about 5.37 s to 4.27 s with exact scientific digests.
- Preserve active MACE-MPA-0 qualification and model-generic MACE-MH-1 compatibility; next gate is FINAL-GPU1.
