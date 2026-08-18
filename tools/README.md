# User-facing tools

`mdstats-3d.py` is the supported source-checkout launcher for the universal GFX3D
scene composer. It delegates to `mdstats.graphics3d.cli.main`, so TOML, presets,
layer shorthand, manifests, and rendering all use the packaged command authority.

```bash
python tools/mdstats-3d.py dump.lammpstrj --layer framework --layer trajectory:Na
python tools/mdstats-3d.py dump.lammpstrj --config examples/gfx3d_na_lta.toml
```

The installed package exposes the equivalent `mdstats-3d` entry point.

`mdstats-mlff-campaign.py` is the supported source-checkout interface for the
complete MLFF preparation, fine-tuning, checkpoint-selection, committee, and
bounded deployment-verification workflow.

```bash
python tools/mdstats-mlff-campaign.py guide
python tools/mdstats-mlff-campaign.py --config campaign.toml init
```

The wrapper deliberately delegates all campaign behavior to
`mdstats.training_data.campaign_cli.main`; the OPT-EVAL1--OPT-CTRL1 optimized
backend is therefore used without duplicating scheduler, evaluation,
verification, cache, or control-plane logic in the tool.

The command stores orchestration state in one SQLite database below the chosen
workspace. Scientific DATA2-DATA9B records remain owned by the package modules.

Additional maintenance/qualification tools:

- `qualify_mace_runtime.py` creates and qualifies an offline MACE 0.3.16 runtime.
- `finalize_lta_data9a3_qualification.py` reconstructs the historical DATA9A3
  DATA2--DATA5 target-corpus qualification using the current immutable
  `ProductionCorpusPlan` API. Full modern DATA9A9c qualification belongs to the
  campaign `prepare` path and is not bypassed by this utility.
- `performance/scan_interpreter_hotpaths.py` performs static Python-loop triage.
