# mdstats 0.20.231a0 patch notes

- Implement REPAIR-PAR1 / architecture revision 98 as exact deterministic repair-proposal performance hardening.
- Preserve sequential repair mutation/winner authority while vectorizing immutable replacement-frontier scoring.
- Add thread-private epoch/stamp membership, fused sparse removal scans, and O(1) inverse candidate-rank lookup.
- Dispatch only sufficiently large proposal batches through the PARCORE1 queue; small batches stay serial to avoid executor overhead.
- Reduce parallel results in historical removal-shortlist order and recompute the winning representative contribution with historical scalar arithmetic before persistence.
- Preserve the frozen complete repair-plan digest across scalar reference and optimized 1/2/4-worker schedules.
- Keep MACE-MPA-0 as the active qualification checkpoint while retaining model-generic MACE-MH-1 compatibility.
- Next optimization gate is MVQUAL-PAR1.
