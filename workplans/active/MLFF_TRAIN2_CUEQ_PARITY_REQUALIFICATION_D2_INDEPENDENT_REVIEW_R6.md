---
kind: D2-independent-review
protocol_version: 6.4.0
status: NO_PASS
workplan: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_WORKPLAN.md
reviewed_candidate: d288d0f931b36e0304a91312915b9785e07dbe3c
reviewed_candidate_blob: 7fbe754c60fab953453586619c8ecb21d8a2b9cc
lifecycle_head_basis: 1645529b5320342842bf4997d4d9e853a2b36631
accepted_parent_d2_kernel: a759e81aa1b4c70c8fb513c569ddce57e99cbdb2
accepted_parent_d2_source: a4824d28775164aa942fd29fa97ee0957eb87e6f
serious_challenge: false
highest_blocking_owner: D2
stage_C_state: BLOCKED
D3_D4_state: BLOCKED
date: 2026-09-25
---

# Candidate-9 fresh independent Protocol-6.4 D2 Review R6

## 1. Immutable binding and disposition

This Review targets immutable Candidate 9 exactly at:

\`d288d0f931b36e0304a91312915b9785e07dbe3c\`

with Candidate-9 Git blob:

\`7fbe754c60fab953453586619c8ecb21d8a2b9cc\`.

The lifecycle descendant

\`1645529b5320342842bf4997d4d9e853a2b36631\`

is one direct child of Candidate 9. The C9-to-descendant diff changes only the Candidate-9 repair record, the Candidate-9 independent-review handoff, and the active workplan. It does not modify the Candidate-9 semantic file and was not substituted for C9 as the Review target.

The prefreeze author states

- \`2a5317558cf3d32455617e5f07efa97c31ef0afe\`; and
- \`4fc493d53b225a36682937e0c8d6659619adc5db\`

are historical authoring states. Their commit ancestry confirms they precede the immutable C9 freeze and are not Review targets.

The accepted parent was independently reconstructed from:

- accepted D1/D2 kernel \`a759e81aa1b4c70c8fb513c569ddce57e99cbdb2\`;
- exact accepted D1/D2 source \`a4824d28775164aa942fd29fa97ee0957eb87e6f\`.

Newer proposed canonical-path files were not treated as accepted parents.

Candidate-4 Review R1, Candidate-5 Review R2, Candidate-6 Review R3, Candidate-7 Review R4, Candidate-8 Review R5, the Candidate-9 repair record, Stage-A MH-1/order-process/MPA-0 analyses, the active workplan, materially applicable PEM FF-001/FF-002/SP-002/SP-003/SP-004, and pinned MACE 0.3.16 conversion sources were used as falsification/evidence context only.

No Candidate-9 Stage-C result exists in the reviewed lifecycle state and none was used.

**Overall disposition: NO-PASS**

**SERIOUS CHALLENGE to accepted parent D1/D2 authority: NO**

Candidate 9 correctly repairs the Candidate-8/R5 conditional-exchangeability defect. One different blocking D2 defect remains: the candidate materiality-risk proposition is defined over the qualification-only uniform launch-slot mixture, while the production CuEq TRAIN2 launch authorized by that record is not proved to have the same launch/start-state distribution. A true low-risk qualification mixture can therefore authorize a higher-risk ordinary production start.

The earliest defective owner is the proposed Candidate-9 D2 overlay. Accepted parent D1/D2 does not assert this transport.

Candidate 9 must remain immutable historical state. It must not proceed to Stage C and must not be handed to D3/D4. Any semantic repair is Candidate 10 or later.

## 2. Accepted-parent reconstruction and authority boundary

The accepted parent numerical-equivalence registry is source-closed. In particular, accepted D2.DEF.060A permits only exact identity/equality, explicitly accepted local numerical predicates, exact imported source-owned relations, and exact canonical binary64 comparison when no nonzero tolerance exists. Backend-observed discrepancy, performance evidence, or an unlisted convenience tolerance cannot create a D2 equivalence relation.

Candidate 9 remains a bounded proposed D2 overlay over that parent. It does not turn Rev86 tolerances, Stage-A observations, current implementation behavior, or PEM into authority.

The active workplan's existing "SERIOUS CHALLENGE" concerns the current executable TRAIN2 FP32 rule and the missing historical accepted-D2 source closure for CuEq. That is not a newly discovered defect in the accepted parent D1/D2 kernel itself. This Review therefore raises no SERIOUS CHALLENGE to accepted parent D1/D2 authority.

## 3. Candidate-9 pre-assignment exchangeability theorem is mathematically repaired

Let the six assignments be the permutations of labels \((R1,R2,C)\) over launch slots \(1,2,3\). Let \(\tau\) swap labels \(R2\) and \(C\) while leaving \(R1\) fixed.

For fixed pre-assignment nuisance state \(\Lambda=\lambda\), Candidate 9 requires the protected-response law under assignment \(a\) to map under \(\tau\) to the same law under assignment \(\tau a\), with \(R2/C\) responses exchanged and the \(R1\) response unchanged.

Because

\[
P(A=a)=P(A=\tau a)=1/6,
\]

pairing \(a\) with \(\tau a\) and marginalizing over assignment gives

\[
(S^{RR},S^{RC})\mid\Lambda=\lambda
\overset d=
(S^{RC},S^{RR})\mid\Lambda=\lambda.
\]

Therefore

\[
P(S^{RC}>S^{RR}\mid\Lambda=\lambda)
=
P(S^{RR}>S^{RC}\mid\Lambda=\lambda)
\le 1/2,
\]

with strict inequality possible when ties have positive probability. No independence of \(R2\) or \(C\) from the shared \(R1\) anchor is required.

This theorem remains valid under arbitrary asymmetric fixed launch-slot effects as long as the stated pre-assignment label-exchange null holds. The proof uses assignment-pair symmetry, not conditional exchangeability after the assignment is realized.

### 3.1 R5 order-only adversary

For deterministic launch-position values \(h=(0,1,2)\) and pair score equal to absolute launch-position difference:

- assignment \((R1,R2,C)\): \((S^{RR},S^{RC})=(1,2)\), strict worse \(=1\);
- \((R1,C,R2)\): \((2,1)\), strict worse \(=0\);
- \((R2,R1,C)\): \((1,1)\), strict worse \(=0\);
- \((C,R1,R2)\): \((1,1)\), strict worse \(=0\);
- \((R2,C,R1)\): \((2,1)\), strict worse \(=0\);
- \((C,R2,R1)\): \((1,2)\), strict worse \(=1\).

Thus the indicators are \((1,0,0,0,0,1)\) up to ordering and the marginal strict-worse probability is \(1/3\). Candidate 9 correctly rejects the false fixed-stratum theorem and handles this exact-same-backend counterexample.

## 4. Renewal/common-law and Binomial theorem are coherent for the qualification population

Candidate 9 does not equate "fresh OS process" with independence. Its exact prospective \(\mathcal W\) contract requires an owner-based census of material cross-triplet mutable state and requires each known owner to be reset/fixed by \(\mathcal W\), immutable in \(\rho\), or independently randomized under the declared model.

The explicit owner class includes CUDA/driver/compiler state, allocator/residency, autotuning/cache state, process-supervisor residue, filesystem/page cache, clock/power/thermal state, and analogous persistent runtime state. Post-assignment stochastic state that can correlate triplets is also covered. Stationarity and autocorrelation diagnostics are only falsification aids and cannot establish independence.

A hidden persistent state can trivially pass superficial stationarity/autocorrelation checks while making adjacent triplets dependent. Candidate 9 does not authorize from those diagnostics alone; failure of the structural common-law justification makes the Binomial model unavailable.

Under the exact stated assumptions,

\[
\Lambda_p\stackrel{iid}{\sim}P_\Lambda,
\]

independent uniform assignments and independently regenerated post-assignment child randomness make each

\[
B_{p,j}=\mathbf 1[S^{RC}_{p,j}>S^{RR}_{p,j}]
\]

an independent Bernoulli draw with one common marginal

\[
p_j=E_{\Lambda}\{P(B_{p,j}=1\mid\Lambda)\}.
\]

The common \(R1\) anchor creates within-triplet dependence between \(S^{RR}\) and \(S^{RC}\), not cross-triplet dependence, and does not invalidate this result.

For \(X_j=\sum_pB_{p,j}\), the exact one-sided Clopper-Pearson upper bound is the Binomial upper confidence limit with per-statement error \(\alpha=0.0125\). For \(0\le x<n\), this is equivalently the \(1-\alpha\) beta quantile with parameters \((x+1,n-x)\); for \(x=n\), the upper limit is 1.

For zero joint materiality events,

\[
Q=1-\alpha^{1/n}.
\]

The finite executable requirement

\[
n\ge
\left\lceil
\frac{\log\alpha}{\log(1-q_{\rm cat})}
\right\rceil
\]

is correct for \(0<q_{\rm cat}<1\). No finite \(n\) realizes \(q_{\rm cat}=0\).

The four-way Bonferroni allocation

\[
\kappa=0.95,\qquad
\alpha=(1-\kappa)/4=0.0125
\]

does not require independence among the four simultaneous statements.

These conclusions apply to the **qualification population actually defined by \(\mathcal W\) plus the uniform assignment law**. Section 5 shows why that is not yet enough for production authorization.

## 5. Blocking finding B1 — qualification launch-slot mixture is not proved transportable to the authorized production CuEq start regime

Candidate 9 deliberately defines a qualification-only randomization:

\[
\text{renew/start}
\rightarrow
\Lambda_p\ \text{frozen}
\rightarrow
A_p\sim\mathrm{Uniform}(S_3)
\rightarrow
\text{children execute}.
\]

This is exactly what repairs R5's nuisance problem for the systematic score comparison.

However, Candidate 9 also uses the same randomized triplets to define the candidate joint materiality population:

\[
C^C_p=1
\]

when any governed \(R1\)-versus-\(C\) consumer relation fails. Its population risk \(q_{\rm cat}\) is therefore the materiality probability of a **candidate whose launch slot is itself uniformly randomized among the three qualification slots**.

An ordinary production TRAIN2 run is a single CuEq launch. Candidate 9 says the production realization must satisfy production-start predicates in \(\rho\) that make it a member of the fresh-process population generated by \(\mathcal W\), but this binds the pre-assignment renewal envelope; it does not prove that the actual single production launch has the same post-renewal launch-slot mixture used by \(C^C_p\).

This distinction matters precisely because Candidate 9 admits launch/order nuisance large enough to require randomization.

### 5.1 Exact false-authorization construction

Take a valid Candidate-9 instance with

\[
q_{\rm cat}=0.08,\qquad \alpha=0.0125.
\]

The minimum zero-event sample size is \(n=53\), for which

\[
Q=1-\alpha^{1/53}\approx0.079354\le0.08.
\]

Let \(\mathcal W\) produce one common i.i.d. cold/fresh pre-assignment triplet state. Let reference behavior be source-materiality-safe in all slots. Let the candidate CuEq materiality-event probability depend only on its qualification launch slot because preceding children modify an ambient cache/residency/thermal state after the triplet renewal boundary:

\[
P(C^C=1\mid C\text{ in slot }1)=0.20,
\]

\[
P(C^C=1\mid C\text{ in slot }2)=0,
\qquad
P(C^C=1\mid C\text{ in slot }3)=0.
\]

This construction does not violate the Candidate-9 cross-triplet common-law assumption. The pre-assignment \(\Lambda_p\) values can be perfectly i.i.d.; the slot effect arises after assignment inside each triplet.

Under uniform assignment,

\[
P_{\rm qual}(C^C=1)
=
\frac{0.20+0+0}{3}
=
0.066\overline6
<
0.08.
\]

Thus the Candidate-9 candidate-tail population proposition is genuinely true for the qualification mixture. With \(n=53\), zero observed events occurs with probability about \(0.02582\); on such a realization the exact Clopper-Pearson upper bound is \(0.079354\), so the tail criterion legitimately passes for the **qualification mixture**. The systematic strict-worse tests can simultaneously pass because even assigning every material event as a strict-worse score gives marginal \(p_j=0.066\overline6<1/2\).

Now let ordinary production execute one CuEq TRAIN2 child immediately after the same cold/fresh production renewal boundary. It therefore corresponds to the first-launch regime:

\[
P_{\rm prod}(C^C=1)=0.20>q_{\rm cat}.
\]

The qualification statement was not statistically wrong. The transport was wrong: a true \(6.67\%\) randomized-mixture risk authorized a \(20\%\) production-start risk.

### 5.2 Why the current production-start sentence does not close the counterexample

Saying that production belongs to the "fresh-process population generated by \(\mathcal W\)" is insufficient because \(\mathcal W\) occurs before the triplet assignment and before slot-dependent child execution.

Either:

1. all three candidate launch slots must have the exact same production-start law, in which case that equality must be established prospectively and authenticated at the actual child start boundary; or
2. production must itself draw from the same declared slot-mixture law; or
3. the production-risk proposition must be valid separately for the production-relevant stratum or under a proved conservative transport/dominance relation.

Candidate 9 states none of these.

Binding "production-internal construction/evaluation order" in \(K,\rho\) does not repair this gap. The counterexample uses **qualification-harness launch position and ambient host state before the production child begins**, not a changed internal CuEq operator order.

### 5.3 Relation to \(\eta_{\rm NI}\)

Candidate 9 correctly states that \(\eta_{\rm NI}\) is a qualification-comparison probability, not a production catastrophic-risk probability. The R5 marginal randomization theorem is therefore acceptable for that comparison role.

The blocker is \(q_{\rm cat}\), because Candidate 9 uses the randomized triplet materiality population as the catastrophic-tail protection for the TRAIN2 realization that a passing record authorizes. That population must transport to the actual production start regime.

### 5.4 Projection evaluator inherits the same transport obligation

The completed-state projection evaluator has its own \(\mathcal Q_{\rm eval}\), renewal policy and randomized assignment theorem. Structural inventory/correspondence/coefficient failure remains correctly dominant.

But any evaluator \(q_{\rm cat}\) statement used to authorize a fixed real projection/evaluation start regime needs the same population-transport proof. Randomized evaluator launch slots cannot silently stand in for a materially different fixed production evaluator start condition.

## 6. Risk-family and confidence semantics apart from B1

The family

\[
0\le\eta_{\rm NI}\le q_{\rm cat}<0.10,\qquad q_{\rm cat}>0
\]

is otherwise coherent as a parameterized reviewed family.

\(\eta_{\rm NI}\) and \(q_{\rm cat}\) govern different event families. Their ordering is a conservative stakeholder admissibility restriction, not a theorem. Candidate 9 says so explicitly.

The \(0.10\) ceiling is only a known-counterexample exclusion. It does not imply that a value near \(0.10\) is scientifically preferred.

The R3 reference adversary

- score 0 with probability 0.90;
- source-material \(M\) with probability 0.10;

is outside every admissible reference population when \(M\) violates \(\mathcal R_e\), because the joint reference materiality probability is 0.10 while every admissible \(q_{\rm cat}<0.10\). Finite sampling can still miss the event with the stated confidence error; Candidate 9 does not claim otherwise.

Rare candidate materiality probabilities below, equal to, or above \(q_{\rm cat}\) are correctly distinct population propositions for the qualification law. B1 concerns whether that law is the production law.

## 7. Preserved Candidate-8/R5 surfaces

Fresh reinspection found no new blocker in the C8 surfaces that Candidate 9 preserves.

### 7.1 Exact consumer closure and final completed-state consequence

Exact \(E\) remains part of the key. The qualified role observes every actual role-effective downstream continuous consumer in

\[
TRAIN2
\rightarrow
checkpoint/monitor
\rightarrow
completed-state\ projection
\rightarrow
EVAL2
\]

and always evaluates the completed state after the final optimizer/EMA mutation.

The R3 final-hidden-coordinate counterexample therefore cannot escape inside exact \(E\). A future consumer outside \(E\) is explicitly outside authority.

Held-out labels/metrics are observation-only and cannot feed training, target membership, checkpoint selection, early stopping, optimizer control, or another upstream scientific decision.

### 7.2 Source-owned materiality relations

Every governed continuous consumer requires accepted source relation \(\mathcal R_e\). Candidate 9 correctly resolves current checkpoint/monitor, replay-retention, CV outer-threshold, practical-equivalence/ranking, exact-tie, lexicographic, inclusivity and accepted guard semantics back to accepted parent owners.

A consumed continuous quantity with no accepted relation makes the role unqualifiable. No D4 tolerance can mint \(\mathcal R_e\).

### 7.3 IEEE ULP primitive

For each exact dtype,

\[
r_d(x)=0\text{ for }\pm0,\quad
r_d(x)=+m_d(x)\text{ for }x>0,\quad
r_d(x)=-m_d(x)\text{ for }x<0
\]

is monotone over finite IEEE values and gives

\[
r(-\mathrm{minsub})=-1,\quad r(\pm0)=0,\quad r(+\mathrm{minsub})=1.
\]

Negative/positive normals, subnormal boundaries, exponent transitions and largest finite values are unambiguous. NaN/infinity fail closed. Cross-dtype ULP comparison is undefined absent an accepted conversion relation; binary64 controls cannot be silently coerced to binary32.

### 7.4 \(S_{\max}\) and exact \(S_\Sigma\)

\[
S_{\max}=\max_i z_i,\qquad
S_\Sigma=\sum_i z_i
\]

with exact integer accumulation are invariant to adding unchanged coordinates, storage block repartition, tensor split/merge and reduction ordering.

\(S_{\max}\) catches rare large displacement; exact unnormalized \(S_\Sigma\) prevents broad small displacement from being diluted by zeros.

Different displacement geometries can share the same pair \((S_{\max},S_\Sigma)\). Candidate 9 does not claim those scores are complete scientific materiality metrics; \(\mathcal R_e\) owns material distinctions.

### 7.5 Exact scientific decisions

Checkpoint identity, admissibility/retention, stop/continue, representative/final ordering, ties, selected survivor identity, outer acceptance, publication/deployment decisions and any other governed discrete consequence remain exact. A stochastic score cannot rescue a discrete mismatch.

## 8. Pinned MACE 0.3.16 projection reconstruction

Pinned tag \`v0.3.16\` resolves to commit \`4d2da09413ac1407f37cdbb6b81fa28e4c15655e\`.

Direct source inspection confirms:

- \`mace/cli/convert_e3nn_cueq.py\` owns \`get_kmax_pairs\`;
- reduced-CG e3nn-to-CuEq conversion obtains \`symmetric_contraction_proj\` and applies it through tensor contraction;
- \`mace/tools/cg_cueq_tools.py\` constructs the projection from two polynomial representations using a pseudoinverse internally and rounds the resulting representation;
- the reverse CuEq-to-e3nn conversion uses the same semantic conversion family and a pseudoinverse for reduced-CG reconstruction;
- conversion explicitly copies \`interactions[i].avg_num_neighbors\` outside ordinary \`state_dict\` transfer.

Candidate 9 therefore correctly forbids an independent structural oracle from reusing the production converter/inverse, \`get_kmax_pairs\`, \`symmetric_contraction_proj\`, production key enumeration/correspondence, generated mapping tables, or production projection/pseudoinverse matrices as semantic owners.

Exact independently derived inventory/cardinality/correspondence must detect omission, duplicates, wrong permutation, wrong k range, wrong contraction membership, extra fallback and quiescent forward-capable state, including non-\`state_dict\` state such as \`avg_num_neighbors\`.

Structural failure remains terminal and evaluator agreement cannot rescue it.

## 9. Reduced-CG inverse, \(A^\ast\), and floating transfer bound

Candidate 9 does not treat production pseudoinverse choice as semantic authority.

For every nontrivial transform it requires an independently defined exact semantic \(A^\ast\), proof of existence/uniqueness on the active authenticated subspace, certified higher-precision enclosure, and exact bitwise production coefficient equality

\[
\widehat A=\operatorname{RN}_d(A^\ast).
\]

A non-unique/rank-deficient required inverse or an unaccepted canonical representative fails closed. This is appropriate for the rectangular/reduced-CG situation.

The R4 scalar adversary

\[
A^\ast=1,\quad \widehat A=100,\quad x=1
\]

fails at coefficient qualification before output comparison.

The accumulation bound

\[
\gamma_{n_r}=\frac{n_ru}{1-n_ru}
\]

is authorized only after the realized operation graph supports its hypotheses. Candidate 9 binds actual reduction structure, accumulation/coefficient dtype, FMA/fused order, operation count, rounding mode, coefficient provenance and kernel identity and fails closed on unsupported subnormal/flush-to-zero behavior, underflow/overflow, conditioning ambiguity, or inability to prove correct rounding.

The coefficient-rounding term is derived from

\[
\operatorname{RN}_d(A^\ast)-A^\ast
\]

rather than observed production disagreement. No self-authorizing production error remains.

## 10. Loader, restart, dtype, provider, and authority scope

Candidate 9 preserves:

- replay/\`pt_head\` first and target second before native shuffle;
- native sampler/shuffle;
- no balancing sampler;
- no intentional target duplication;
- \`drop_last=true\`;
- target-only foundation adaptation where that accepted role applies;
- the complete accepted optimizer horizon;
- same-backend restart only;
- no cross-backend TRAIN2 restart;
- source/DATA6 CuEq outside authority;
- FP64 CuEq TRAIN2 unsupported/fail closed;
- post-projection EVAL2 numerical provider identity e3nn;
- routine doctor as currentness/reachability only; and
- no D3/D4 ownership creep.

PEM FF-001/FF-002 and SP-002/SP-003/SP-004 remain relevant evidence guidance: exact realized-model identity, authenticated restart boundaries, fail-closed durable identity, immutable reuse and real-owner/target-host qualification are all preserved. They do not become D2 authority.

## 11. Failure, prewarm, evidence identity, and no-retry semantics

\(\mathcal Q\) is correctly prospective semantic method identity. Realized entropy commitment, randomization seed when used, permutation sequence and triplet assignments are evidence-realization identity.

A different realized assignment sequence is not a new semantic key and cannot reset a failed same-key qualification.

The assignment entropy is committed before governed output and cannot feed scientific RNG, loader order, model initialization, optimizer state or training arithmetic.

Any prewarm must be fixed, label-blind, identical for all triplets, inside \(\mathcal W\), and unable to inspect protected outputs. Adaptive warm-up is forbidden.

Startup failure, OOM, timeout, crash, unsupported runtime, nonfinite output, partial completion, infrastructure failure and failed renewal boundaries are prospectively terminal failure/inconclusive states. They cannot become a discarded Bernoulli zero, favorable redraw, reassignment or retry-until-pass path. Because Candidate 9 explicitly defines no same-key retry path, an "inconclusive" classification cannot lawfully be used to remove unfavorable evidence and rerun the same semantic key.

## 12. Historical regression against Reviews R1-R5

No regression was found in the prior closed defect families:

- no forward-inference tolerance reused as TRAIN2 bias budget;
- no heuristic Huber/\(\delta\sqrt u\) tolerance;
- no finite optimizer-probe injectivity claim;
- no finite EMA witness claimed complete;
- no recurrence/secant/finite-window extrapolation;
- no metadata-only difficult-regime sampling;
- no sample maximum minting candidate tolerance;
- final completed-state consumer closure remains;
- no raw cross-basis optimizer equality;
- no signed-zero ULP ambiguity;
- no block/RMS dimensional dilution;
- no correlated projection semantic owner;
- no production coefficient self-authorization;
- no generic publication beyond exact \(E\);
- no source/DATA6 or FP64 scope drift;
- no cross-backend restart;
- no adaptive retry; and
- the R5 fixed-stratum conditional-exchangeability defect is genuinely closed.

B1 is a new transport defect adjacent to the repaired stochastic design: the randomized qualification population is coherent, but its candidate materiality risk is not yet tied to the fixed production-start population it authorizes.

## 13. Review matrix against the required falsification program

| Required area | Review result |
|---|---|
| 1. Immutable identity/lifecycle | C9 commit/blob exact; descendant does not mutate C9; prefreeze commits historical; no C9 Stage C. |
| 2. Accepted parent reconstruction | Bounded overlay confirmed; no accepted-parent challenge. |
| 3. Pre-assignment exchangeability theorem | Correct after assignment marginalization; shared anchor is not a defect. |
| 4. R5 counterexample | Correctly reproduced; marginal worse probability \(1/3\). |
| 5. Renewal/common-law authority | Coherent fail-closed applicability contract; owner census required; diagnostics cannot prove independence. |
| 6. Production-population transport | **BLOCKING B1**: randomized candidate slot-mixture risk does not imply fixed production-start risk. |
| 7. Randomization policy vs realized evidence | Correctly separated; favorable rerun/seed escape prohibited. |
| 8. Prewarm/failure semantics | Prospective and fail-closed; no outcome-selected discard/retry path. |
| 9. Binomial inference | Correct for the qualification population under exact C9 assumptions. |
| 10. Risk-family semantics | Parameterized family coherent; \(\eta_{\rm NI}\le q_{\rm cat}\) conservative only; transport of \(q_{\rm cat}\) blocked by B1. |
| 11. Simultaneous confidence | Bonferroni and zero-event algebra correct; \(q_{\rm cat}=0\) non-executable finitely. |
| 12. Materiality/consumer closure | Exact \(E\), final completed-state evaluation and held-out leakage prohibition preserved. |
| 13. Source-owned \(\mathcal R_e\) | Parent relations resolved; missing relation fails closed; D4 cannot mint one. |
| 14. ULP primitive | Signed-zero/dtype/nonfinite/cross-dtype semantics correct. |
| 15. \(S_{\max}\), \(S_\Sigma\) | Non-dilutable/invariant as claimed; scientific geometry remains owned by \(\mathcal R_e\). |
| 16. R3 adversary/rare tails | Qualification-population semantics correct; production-tail authorization still blocked by B1. |
| 17. Exact scientific decisions | Exact preservation remains mandatory. |
| 18. Projection structural oracle | Pinned MACE owners independently reconstructed; C9 independence exclusions sufficient in form. |
| 19. Reduced-CG inverse/\(A^\ast\) | Non-unique inverse fails closed; exact correctly-rounded coefficient gate closes R4 adversary. |
| 20. Projection error budget | Acceptable only under realized operation proof; C9 fails closed otherwise. |
| 21. Projection evaluator | Structural hierarchy correct; evaluator risk transport inherits B1. |
| 22. TRAIN2/restart/scope | Loader, horizon, restart, source/DATA6, FP64, EVAL2 provider and doctor boundaries preserved. |
| 23. Historical regression | R1-R5 blockers remain closed; B1 is newly identified at production-population transport. |

## 14. Required Candidate-10-or-later repair

Preserve immutable Candidate 9 and every C9 surface this Review found adequate. Repair only the production/evaluator population-transport owner unless a new independent defect is found.

A replacement must, before any Stage-C outcome:

1. define the exact **production start-state probability law** \(P_{\rm prod}\) for the CuEq TRAIN2 launch that a passing qualification record is intended to authorize;
2. define the exact candidate-start law induced by qualification \(\mathcal W\), the three launch slots and the assignment policy;
3. prove prospectively that the candidate materiality event law used for \(q_{\rm cat}\) is the same as, or a conservative upper bound for, the actual \(P_{\rm prod}\) event law;
4. forbid using mere membership in the pre-assignment \(\mathcal W\) envelope as a substitute for equality/dominance of the **actual child-start** law;
5. authenticate the relevant production-start predicate at the boundary immediately before CuEq TRAIN2 arithmetic begins;
6. if launch slot can materially alter that start law, either:
   - make each qualification child start from an independently renewed/authenticated production-equivalent state before label-dependent arithmetic, so the candidate marginal is exactly \(P_{\rm prod}\); or
   - bind production itself to the exact same prospective slot-mixture law; or
   - use a prospectively specified per-stratum/worst-case materiality inference whose simultaneous confidence and sample allocation are valid for the production-relevant stratum;
7. do not average a high-risk production-relevant stratum with lower-risk qualification-only strata to satisfy \(q_{\rm cat}\);
8. keep the R5 pre-assignment marginal theorem for \(\eta_{\rm NI}\) if desired, but state explicitly that this comparison theorem does not by itself transport catastrophic-tail risk to production;
9. apply the same actual-start population transport requirement to the projection evaluator wherever its \(q_{\rm cat}\) statement authorizes a fixed real evaluator/projection regime;
10. add a Stage-C falsification fixture matching Section 5.1: one launch stratum has candidate materiality probability above \(q_{\rm cat}\), the uniform mixture lies below it, and production uses the high-risk stratum; the replacement method must reject authorization;
11. prohibit Candidate-9 Stage C and do not use Candidate-9 outcomes to choose the transport rule, risk coordinates, sample allocation or repair form; and
12. freeze the semantic repair as Candidate 10 or later and submit it to fresh independent D2 Review before stakeholder instance ratification.

The reduction-preferred repair is to move/redefine the renewal owner so each qualification child is authenticated at the same production-equivalent start boundary before its arithmetic begins, eliminating qualification-only slot-state transport rather than adding a second post-hoc correction layer. If that is not realizable on the target host, the method must fail closed or adopt a separately reviewed stratified design; it may not preserve the mixture and simply assert transport.

## 15. Workplan/lifecycle action

The active workplan is reopened/continued with this R6 NO-PASS and the Candidate-10 repair obligations above.

Required lifecycle state:

1. preserve Candidate 9 and blob \`7fbe754c60fab953453586619c8ecb21d8a2b9cc\` unchanged;
2. preserve the C9 lifecycle/handoff descendant as historical lifecycle evidence;
3. do not run Candidate-9 Stage C;
4. do not use any Candidate-9 outcome to tune its replacement;
5. keep D3/D4 blocked;
6. implement any semantic repair only as Candidate 10 or later;
7. perform fresh independent Review on that immutable replacement; and
8. only after independent D2 PASS may the stakeholder bind an exact reviewed instance before fresh Stage-C qualification.

## 16. Final disposition

**NO-PASS**

**SERIOUS CHALLENGE to accepted parent D1/D2 authority: NO**

Candidate 9 repairs Review R5's stochastic-conditioning defect, but its \(q_{\rm cat}\) materiality proposition remains attached to a qualification-only randomized launch-slot mixture that is not proved transportable to the ordinary single production CuEq start regime. The resulting false-authorization construction is exact at the D2 population level and is not cured by larger \(n\), Clopper-Pearson confidence, or the owner-based cross-triplet renewal proof.