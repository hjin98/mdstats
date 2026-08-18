# mdstats 0.20.162a0 — GFX3D browser-budget hotfix

This release is intentionally narrow. It fixes the multi-density rendering failure reported after successful GFX3D preparation and does not include the deferred Phase-B/registration optimization gates.

## Root cause

The universal GFX3D density adapter rendered each HDR shell independently. A sparse shell was given a scene-controller face contract, but its visual target was still derived from the standalone per-shell allowance (normally up to 250,000 faces). With four density fields and the default three HDR mass fractions this can produce twelve individually acceptable meshes whose aggregate payload is several million faces.

Only after all layer primitives were built did `GraphicsBrowserBudget` apply the global `1,500,000`-face preflight. The reported `3,302,346 > 1,500,000` error is therefore a budgeting integration bug: the final scene budget was never apportioned across the density shells that consume it.

A second contract bug affected `--max-browser-faces`: the option changed `BrowserMeshProfile`, but the universal GFX3D payload validator still used its independent hard-coded face profile, so the error message's suggestion to increase the browser budget could fail to do so in practice.

## Fix 1 — one density scene budget

Before density primitives are rendered, GFX3D now constructs `DensitySceneShellRequest` records for every requested HDR shell and runs the existing deterministic `allocate_density_scene_budget()` controller. The budget is post-replication and shared across all density layers.

Each sparse shell receives its own allocated canonical-face target and the same topology/fidelity-preserving simplification policy used by the qualified legacy framework-density renderer. The scientific density field, HDR threshold, achieved mass fraction, grid, and Gaussian bandwidth do not change.

After primitive generation, GFX3D performs an exact aggregate density-usage check. If individual simplification could not meet its target, the existing closed-loop `fit_density_scene_to_browser_budget()` controller receives the full set of density shell geometries and reallocates/refits the scene before the generic Plotly preflight.

## Fix 2 — irreducible browser-safe fallback

If topology-preserving simplification/recontouring still cannot satisfy the hard density scene budget, GFX3D no longer throws the old terminal face-count error after the expensive density calculation. It converts the least-visible/highest-cost density shells to the package's deterministic HDR node-cloud representation until the mesh-face budget is met.

This fallback preserves the scientific HDR threshold and field identity; it changes only the browser representation of the affected shell. The fallback shell list and original fit failure are recorded in render metadata.

## Fix 3 — explicit face override now really overrides

`--max-browser-faces N` now:

1. sets the density scene face budget to `N`;
2. scales the companion density vertex and estimated-HTML allowances from the selected browser profile; and
3. raises the universal GFX3D face preflight to at least the requested density budget plus exact non-density mesh faces.

The option therefore no longer remains trapped behind the unrelated historical 1.5M generic cap.

## Audit metadata

The Plotly render result now includes:

- `density_scene_budget_plan`: per-shell canonical/serialized allocations;
- `density_scene_fit`: closed-loop fit report, or node-cloud fallback report when required;
- the final universal browser budget and measured payload as before.

## Qualification

Focused qualification: **97 tests passed**. New regressions verify that:

- four independent density layers share one scene face budget;
- sparse layer rendering consumes the allocated per-shell target;
- aggregate overspend invokes the scene fitter;
- a custom density face budget propagates through the universal GFX3D preflight; and
- the CLI face override scales companion density output budgets coherently.

The supplied Na-LTA four-density snapshot could not be re-run through rendering in the packaging container because its 4 GiB cgroup causes the 0.20.161a0 Phase-B density memory authority to reject the four-field plan before rendering. The reported rendering failure itself is covered at the scene-contract level and the integration uses the same allocator/fitter already qualified by the legacy multi-density renderer.
