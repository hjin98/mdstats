# mdstats 0.20.66a0 MACE multi-head E0 correction

## Observed failure

The production preflight reached the real one-epoch MACE child and failed with:

```text
KeyError: Atomic number 1 not found in atomic_energies_dict for head target_head
```

The TorchScript deprecation warnings in the same log are unrelated and remain
consolidated compatibility warnings.

## Root cause

DATA8 correctly set the top-level MACE `atomic_numbers` value to the union of
target and replay elements, but it did not set a head-local element table on
`target_head`. MACE 0.3.16 therefore assigned the global union to the target
head. The replay corpus contains hydrogen and other foundation elements absent
from LTA target configurations, while DATA7 target E0 fitting intentionally
produces reference energies only for elements that occur in the target data.
MACE then rejected the first replay-only element, hydrogen (`Z=1`).

## Correction

- Keep top-level `atomic_numbers` as the target/replay union required to build
  the shared multi-head model.
- Emit `heads.target_head.atomic_numbers` as the target-only element set.
- Keep `target_head.E0s` restricted to fitted target elements; no fabricated
  hydrogen or replay-only target E0 values are introduced.
- Let MACE's native multi-head array construction zero-pad elements absent from
  a particular head, which is the behavior implemented by MACE 0.3.16.
- Check every explicit E0 mapping against its head-local element table before
  launching the one-epoch smoke.
- Print the final child exception directly in preflight output.

## Restart behavior

Install the patched wheel and run plain `prepare` once. Do not use
`--rebuild-catalog`. The DATA8 parser identity is advanced to `0.20.66a0`, so
pre-0.20.66 DATA8 generations are invalidated and reconstructed. Existing DATA7
archives, DATA6 descriptors/predictions, normalized frame cache, manifest, and
source catalog are reused and checksum-verified. No foundation inference sweep
should repeat.

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml prepare
python tools/mdstats-mlff-campaign.py --config campaign.toml preflight
```

## Validation

The regression reproduces a target corpus containing Li/O and a replay corpus
containing H. The generated MACE configuration parses to a global element table
`[1, 3, 8]`, a target-head table `[3, 8]`, and target E0 keys `[3, 8]`; the exact
MACE 0.3.16 lookup that previously raised `KeyError: 1` is therefore satisfied.
