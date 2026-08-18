# MLFF-DATA2A Automatic Review-Manifest Inference Gate

**Implemented in mdstats 0.20.60a0**

## Purpose

The campaign manifest is the reviewed boundary between raw file discovery and
scientific data preparation. MLFF-DATA2A removes repetitive manual annotation
without weakening that review boundary. It separates three classes of evidence:

1. **Observed metadata** recovered from `vasprun.xml` controls and cells.
2. **Filename candidates** that describe intended strain semantics.
3. **Promoted operational assertions** allowed to influence reference-cell
   resolution, partitioning, condition coverage, and reporting only after
   geometry verification succeeds.

A filename is never sufficient proof of strain. Manual approval remains
mandatory after inference.

## Public records

- `ManifestInferencePolicy`
- `ManifestInferenceResult`
- `TrainingDataRunSpec.inference`
- `infer_training_manifest_metadata(...)`

The immutable policy records tolerances and filename interpretation. The result
records counts, warnings, the inferred manifest digest, and the policy digest.

## XML-derived metadata

One bounded-memory tolerant XML pass recovers completed records for:

- `TEBEG`, `TEEND`, target temperature;
- `POTIM`, `NSW`;
- `IBRION`, `MDALGO`, `SMASS`, `ISIF`, `LANGEVIN_GAMMA`;
- NVT/NVE ensemble and thermostat classification when controls are resolvable;
- initial and per-calculation cell matrices;
- ordered atom symbols;
- fixed-cell status and maximum relative cell deviation.

A truncated XML may populate the **review manifest** from completed records and
must carry an explicit parse warning. This tolerant pass does not replace the
later strict DATA2 source-quality, label, and trajectory qualification gate.

## Filename strain grammar

The LTA profile recognizes filenames containing:

```text
_strained.hydro+VALUE
_strained.ortho-VALUE
_strained.shear+VALUE
```

An explicit `%` is a percentage. By default, an unmarked absolute value at or
above one is also interpreted as a percentage:

```text
hydro+5    -> +0.05 relative volume change
ortho-2    -> -0.02 signed axial delta
shear+2    -> +0.02 engineering shear gamma
```

Values below one retain fractional meaning:

```text
hydro+0.05 -> +0.05 relative volume change
```

Temperature tokens may be present or absent in either the strained filename or
its reference filename. They are excluded from identity matching and used only
as a ranking hint after geometry passes.

## Fixed-cell prerequisite

Static strain inference is allowed only when both the strained trajectory and
candidate reference are verified fixed-cell MD. The maximum trajectory cell
deviation must satisfy

\[
\max_t \frac{\|H_t-H_0\|_F}{\|H_0\|_F}
\le \varepsilon_{\mathrm{fixed}}.
\]

Variable-cell runs remain ungrouped.

## Exact LTA strain definitions

The definitions are frozen to the supplied six-strain generator.

### Hydrostatic

A filename value \(\Delta V/V\) denotes a volume ratio

\[
\det F = 1+\Delta V/V,
\]

with equal axial stretch

\[
U_{\mathrm{expected}}=(1+\Delta V/V)^{1/3}I.
\]

### Orthorhombic

For signed \(d\), the deformation in LTA conventional axes is

\[
U_{\mathrm{aligned}}=
\operatorname{diag}\left(1+d,1-d,\frac{1}{1-d^2}\right),
\]

which preserves volume exactly.

### Shear

For signed engineering shear \(\gamma\), form the simple-shear matrix

\[
S=I+\gamma\,e_x\otimes e_y.
\]

The applied deformation is its exact symmetric right-polar stretch

\[
U_{\mathrm{aligned}}=(S^TS)^{1/2}.
\]

The LTA primitive-cell conventional axes are reconstructed from primitive rows
\(a,b,c\) as \(b+c-a\), \(a+c-b\), and \(a+b-c\), normalized and verified
orthogonal before transforming the expected stretch back to Cartesian space.

## Reference resolution

A candidate reference must be unstrained and satisfy:

- filename identity after removing the strain tag and temperature tokens;
- identical ordered atom identities;
- verified fixed-cell status;
- a cell deformation that passes the exact expected strain test.

Among geometry-passing candidates, target-temperature distance is a ranking hint.
A unique closest candidate is selected. Equally ranked equivalent cells may form
a consensus. Equally ranked non-equivalent cells are ambiguous and remain
unpromoted.

## Verification and fail-safe behavior

For reference cell \(H_0\) and strained cell \(H_s\), mdstats calculates

\[
F=H_sH_0^{-1}=RU
\]

and compares the observed right stretch \(U\), volume ratio, and rotation with
the expected profile deformation.

Only a passing relationship receives:

- `reference_group`;
- optional `reference_run_id`;
- `intended_strain_class` and magnitude/sign assertions;
- a verified reference-cell assertion on the selected baseline.

If verification fails or is ambiguous:

- no operational strain assertion is promoted;
- `reference_group` and `reference_run_id` remain null for that relationship;
- candidate matrices, residuals, references, and rejection reasons remain in
  `inference` for user inspection;
- `prepare` emits a warning and still requires manifest approval.

A failed sibling does not erase an independently verified relationship.

## CLI contract

The first `prepare` invocation discovers sources, runs inference, writes the
populated manifest, prints a compact resolution summary, and stops for review.

```bash
python tools/mdstats-mlff-campaign.py --config campaign.toml prepare
python tools/mdstats-mlff-campaign.py --config campaign.toml prepare --approve-manifest
```

Use `--refresh-inferences` before approval after source files or inference policy
settings change.

## Production acceptance

A production archive passes this inference gate when:

- every intended fixed-cell strain has one verified relationship;
- no intended strain is rejected or ambiguous;
- XML parse warnings are retained for later source-quality review;
- the user approves the exact populated manifest digest.
