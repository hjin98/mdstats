# mdstats 0.20.84a0 — true-label checkpoint acceptance and pseudolabel diagnostics

## Scientific correction

Foundation-generated replay labels are predictions from the frozen foundation model, not independent ground truth. Comparing that model with its own labels produces a near-zero self-error by construction. Dividing a fine-tuned model's replay disagreement by that numerical self-error creates an ill-conditioned relative percentage and must not determine checkpoint accuracy or admissibility.

## Behavior

- DFT-labeled target energy, force, mobile-ion force, stress, and worst-condition metrics remain the mandatory accuracy gates and the primary checkpoint-ranking evidence.
- Foundation-pseudolabel replay is retained as an absolute candidate-versus-foundation disagreement diagnostic only. It does not reject or rank checkpoints.
- The exact foundation must still reproduce its own pseudolabel monitor to within 1 meV/Å force RMSE. A larger mismatch is treated as replay-provenance or model-identity corruption, not as candidate-model failure.
- Genuine `true_dft` replay remains eligible for the configured relative retention gate because both foundation and candidate errors are measured against independent reference labels.
- Legacy cached checkpoint evaluations are rebound to their immutable replay-label provenance without rerunning MACE inference. Historical million-percent pseudolabel ratios are removed, while the absolute replay disagreement is preserved.
- Selection diagnostics now state the replay label mode, absolute baseline/candidate values, and whether replay is a diagnostic or a mandatory true-label gate.

## Interpretation of the reported example

The target DFT metrics (approximately 25 meV/Å force RMSE, 0.25–0.83 meV/atom energy MAE, and 0.0003–0.0004 eV/Å³ stress RMSE) satisfy the configured target gates. The 23–43 meV/Å pseudolabel disagreement measures behavioral drift from MPA-0 on the replay geometries; it is not a million-percent accuracy failure. Under the corrected policy, epoch 29 is preferred by the primary DFT target-force metric among the four evaluated candidates.

## Restart

Install this release and rerun `evaluate`. Existing checkpoint inference records are migrated in place and reused. No `prepare`, preflight, training, or exhaustive 30-epoch reevaluation is required.
