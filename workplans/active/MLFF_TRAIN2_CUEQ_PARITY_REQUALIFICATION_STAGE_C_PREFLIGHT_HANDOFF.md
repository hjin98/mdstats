---
kind: D2-stage-c-preflight-handoff
protocol_version: 6.4.0
status: TARGET_HOST_PREFLIGHT_REQUIRED
candidate: db2ed47e8c999cb61507803610c72c0fa7ffaaf7
law_binding: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_LAW_BINDING.md
risk_binding: workplans/active/MLFF_TRAIN2_CUEQ_PARITY_REQUALIFICATION_D2_C10_INSTANCE_RISK_BINDING.md
date: 2026-09-25
---

# Candidate-10 Stage-C target-host preflight handoff

Stage C must not launch Candidate-10 training yet.

The next target-host action is a **read-only/pre-output identity freeze**. It must capture the exact live values that Candidate 10 deliberately keys but that cannot be truthfully inferred from repository prose:

1. current branch/source identity used on the workstation;
2. exact campaign TOML/config digest;
3. exact CampaignStore selected-binding / \(T_{\rm selected}\) membership digest;
4. exact common-monitor membership/digest;
5. exact CV plan/fold/run identity if the CV role is being qualified;
6. exact final-production plan/run identity if the production role is being qualified;
7. exact replay geometry/train/true-monitor/label-mode/foundation/exposure lineage;
8. exact target/replay ExtXYZ or immutable transport artifact SHA-256 values;
9. exact optimizer seed, loader seed, batch size, shuffle/sampler and \`drop_last\`;
10. exact objective, optimizer, LR-schedule, scheduler, EMA and horizon identities;
11. MH-1 selected-head checkpoint path/SHA and qualification digest;
12. MPA-0 checkpoint path/SHA;
13. GPU name, UUID and compute capability;
14. NVIDIA driver version;
15. Torch/MACE/CUDA/CuEq package/build versions;
16. deterministic-algorithm/debug state, TF32/matmul state, cuDNN state, CUBLAS workspace configuration and relevant environment variables;
17. exact e3nn and pure-CuEq kernel/conversion source identities;
18. exact available free/total VRAM and confirmation that no other governed training child is active;
19. exact cache/scratch namespace policy that will be applied by \(\mathcal W_R/\mathcal W_C\);
20. exact accepted source relations resolved for the role.

The preflight must occur before any Candidate-10 \(R1/R2/C\) child output exists. It may inspect/authenticate immutable inputs and runtime state but may not execute a Candidate-10 qualification trajectory.

The resulting JSON must be content-addressed and committed/uploaded as the Stage-C preflight artifact. Only after its exact key is reviewed against the Candidate-10 risk/law binding may the 300-triplet Stage-C realization begin.

Because this environment has no access to the stakeholder RTX 3090 host or its live CampaignStore, target-host preflight is the first unavailable real-owner boundary.


## Executable preflight

The repository-owned observational collector is:

`tools/run_mlff_cueq_c10_stage_c_preflight.py`

It must be run from a clean checkout of this branch in the target `mace` environment, while the selected RTX 3090 has no other compute process. It validates the reviewed Candidate-10 blob, the ratified `0.09 / 0.09 / 300` risk binding, locked MH-1/selected-head/MPA-0 bytes, the Stage-A runtime family, current CampaignStore lineage, current selected membership/common monitor, and the exact accepted-parent `45 / 45 / 30 meV/Å` role thresholds plus `30 meV/Å` replay hard budget.

The branch currently carries an unratified assessment-policy renewal with generated `75 / 75 / 50 meV/Å` values. The collector records those D4 values as observations but does not treat them as Candidate-10 authority; their reconciliation remains Stage D.

Run:

```bash
conda run -n mace python tools/run_mlff_cueq_c10_stage_c_preflight.py \
  --config /ABSOLUTE/PATH/TO/campaign.toml \
  --mpa0-model /ABSOLUTE/PATH/TO/mace-mpa-0-medium.model \
  --output /ABSOLUTE/PATH/TO/mlff_cueq_c10_stage_c_preflight.json
```

The output JSON is the next required evidence input. Do not launch Candidate-10 triplets before it is reviewed and bound.
