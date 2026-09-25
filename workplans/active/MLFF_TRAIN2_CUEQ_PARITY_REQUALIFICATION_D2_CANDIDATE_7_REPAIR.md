---
kind: D2-candidate-repair-record
protocol_version: 6.4.0
status: AUTHOR_REPAIR_COMPLETE_PENDING_IMMUTABLE_FREEZE
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
review_basis: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_INDEPENDENT_REVIEW_R3.md
superseded_candidate: f3035317dcea1448c9d6d825c6f2d9f156aaec24
replacement_candidate_file: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_CANDIDATE_7.md
date: 2026-09-25
---

# Candidate-7 D2 repair record

Fresh independent Review R3 returned NO-PASS for immutable Candidate 6. Candidate 7 repairs the blocking findings by changing the authorizing relation rather than adding a D4 exception.

## B1 — finite functional witness did not identify the final portable state

Candidate 7 removes finite-W functional observation as the owner of complete-state equivalence.

The new authority observes the complete portable forward-affecting live state after initialization and every optimizer update, the complete EMA state at every EMA boundary, the final state after the last mutation, and the exact role-effective downstream continuous-consumer population E.

The portable inventory is explicitly broader than state_dict and includes forward-affecting ordinary module attributes such as avg_num_neighbors.

A final-step hidden coordinate that is inactive on TRAIN2 but active on EVAL2 is therefore directly observed as a portable-state discrepancy before publication authorization.

## B2 — sample maximum could authorize a systematic shift

The sample maximum is demoted to a catastrophic-tail guard.

The substantive stochastic relation now uses 101 prospective independent R1/R2/C triplets. For S_max and S_rms it measures whether the CuEq cross score is strictly worse than the paired reference-self score.

Candidate 7 requires a one-sided exact binomial upper confidence bound no larger than 0.60 for both score families at simultaneous confidence at least 0.95. With n=101 this means at most 50 strict-worse triplets per family.

The 0.60 ceiling is the exchangeability baseline 0.50 plus the entire predeclared 0.10 process-content shortfall implied by Gamma=0.90.

The explicit Review-R3 adversary reference 0/M with probabilities 0.90/0.10 versus candidate constant M/2 has worse probability approximately 0.90 and therefore fails even though M remains the reference tail maximum.

Reference adequacy is independent: e3nn self variability must remain strictly inside the actual accepted threshold/order decision margins. An unstable reference fails rather than widening candidate authority.

## B3 — ULP ambiguity around signed zero

Candidate 7 defines an exact finite IEEE rank:

- both signed zeros map to rank 0;
- positive finite values map to their sign-stripped magnitude-bit integer;
- negative finite values map to the negative of that magnitude-bit integer;
- ULP distance is absolute rank difference.

Thus -min-subnormal, zero, +min-subnormal have ranks -1, 0, +1.

NaN/infinity fail closed and cross-dtype comparison is undefined.

## B4 — projection oracle could share semantic owners with production

Candidate 7 strengthens independence from execution-level separation to semantic-owner separation.

The oracle independently derives source/destination inventories, correspondence, k ranges, permutations, basis transforms, and coefficient matrices.

For pinned MACE 0.3.16 it may not reuse get_kmax_pairs, symmetric_contraction_proj, production key enumeration/correspondence, production converter/inverse-converter logic, or production-generated projection/pseudoinverse matrices.

Exact inventory reconciliation precedes numeric comparison.

The floating bound now contains an explicit production-coefficient error term in addition to learned-dtype accumulation error.

## Candidate-6 finite-sample derivation correction

Candidate 7 removes the incorrect Candidate-6 candidate-side Bonferroni zero-exceedance argument entirely.

The new systematic-shift relation uses exact Bernoulli worse events and Clopper-Pearson bounds. The tail maximum has only its stated one-sided reference-content meaning and is not interpreted as the substantive equivalence theorem.

## Preserved Candidate-6 improvements

Candidate 7 preserves:

- exact-realization scope;
- complete accepted TRAIN2 horizon;
- no recurrence/window extrapolation;
- actual accepted loader semantics;
- no arbitrary future optimizer-state theorem;
- same-backend restart only;
- no mid-run backend switching;
- source/DATA6 e3nn narrowing;
- FP64 CuEq TRAIN2 fail closed;
- EVAL2 provider identity e3nn after projection; and
- routine doctor as currentness/reachability only.

No Candidate-6 Stage-C outcome was used in this repair.

Candidate 7 remains proposed until immutable freeze, fresh independent Review PASS, exact stakeholder ratification, and fresh Stage-C qualification.


## Pre-freeze author-side falsification refinements

Before immutable handoff, an additional author-side pass found and repaired two Candidate-7 draft defects:

1. the comparison key originally named K as if one backend/kernel realization were common to both sides. K is now explicitly the ordered pair (K_R,K_C), with the accepted e3nn realization and proposed CuEq realization separately bound while their upstream semantic inputs remain common;
2. one global RMS over the entire portable state could be diluted by an unrelated very large unchanged tensor. S_rms is now computed within fixed canonical semantic blocks and maximized over blocks/boundaries, while S_max remains the global rare-coordinate guard.

The same pass clarified that E-consumer comparison in the TRAIN2 relation evaluates reference and projected-candidate states through the same portable e3nn provider. Transient CuEq-versus-mapped-e3nn evaluator arithmetic remains a separate completed-state projection relation.

These are author-side semantic repairs made before immutable Candidate-7 Review freeze; no Candidate-7 Stage-C outcome exists.
