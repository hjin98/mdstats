# Atomic mean vertex periodic-gauge audit

## Finding

The Plot-D5 implementation in 0.19.35a0-0.19.36a0 computed atomic vertex
positions by averaging coordinates lifted through each frame's atomic
connectivity graph. This is not invariant when the connectivity component or
the spanning tree changes. An atom can move to an equivalent periodic image in
the lifted graph even when its physical position does not change. Averaging
those image representatives and folding only at the end can place the displayed
vertex far from its density cloud.

## Corrected definition

Version 0.19.37a0 computes each atomic vertex from the same registered atomic
coordinates used for density deposition. The vertex is the weighted periodic
Frechet/Karcher mean under the Cartesian minimum-image metric of the display
cell. The atomic connectivity graph is used only for edge occupancy.

Retained edge occupancy is accumulated by unordered atom pair. The displayed
edge image shift is then recomputed from the corrected mean endpoints by the
Euclidean minimum-image convention.

## Synthetic regression

A three-atom periodic triangle changes to a chain while the third atom remains
at fractional coordinate 0.8. The former connectivity-gauge average placed that
atom at 0.3. The corrected mean remains at 0.8.

## Na-LTA validation

For the 300 K Na-LTA trajectory sampled every ten archived frames:

- atoms: 168;
- maximum distance between corrected atomic vertex and the periodic registered
  trajectory mean: 0.00101134 A;
- mean distance: 0.00007856 A;
- number farther than 0.01 A: 0;
- retained atomic bonds: 266;
- bond-length range: 1.59391-2.58272 A;
- bonds longer than 3.2 A: 0.

The previously displaced vertices included O, Si, Al, and one Na atom, with the
largest old mismatch about 9.00 A.

## References

- M. Frechet, "Les elements aleatoires de nature quelconque dans un espace
  distancie," Annales de l'Institut Henri Poincare 10 (1948), 215-310.
- H. Karcher, "Riemannian center of mass and mollifier smoothing,"
  Communications on Pure and Applied Mathematics 30 (1977), 509-541.
  DOI: 10.1002/cpa.3160300502.
