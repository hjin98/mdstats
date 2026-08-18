# Stage 8A Periodic-Net Embedding Audit

Version: `0.19.20a0`  
Architecture: revision 27

## Scope

This audit covers the first authoritative Euclidean reference realization:

- exact source ownership;
- complete-symmetry certification;
- lattice-metric derivation;
- Cartesian cell convention;
- projected straight-edge geometry;
- collision and degeneracy rejection; and
- explicit separation from later global periodic crossing certification.

## Scientific representation

The authoritative exact data are:

```text
PeriodicBarycentricPlacement.coordinates
+
PeriodicNetEmbedding.primitive_gram_matrix
```

For projected quotient-edge vectors

$$
\mathbf d_e=\mathbf x_j+\boldsymbol\delta_e-\mathbf x_i,
$$

the implementation constructs

$$
C=\sum_e\mathbf d_e\mathbf d_e^{\mathsf T},
\qquad
G_{\mathbb Q}=C^{-1},
$$

then clears denominators and removes the common integer divisor. The result is a
primitive positive-definite integral Gram matrix.

## Exact invariants

Every discovered operation is verified against:

$$
A_g^{\mathsf T}GA_g=G,
$$

and every quotient vertex is verified against

$$
A_g\mathbf x_i+\mathbf x_{\pi_g(i_0)}
=
\mathbf x_{\pi_g(i)}+\boldsymbol\tau_i^g.
$$

Explicit edge permutation and orientation are used to verify the transformed
straight-edge displacement exactly.

## Basis covariance

A nontrivial unimodular shear fixture verifies

$$
G'=P^{\mathsf T}GP.
$$

The metric therefore follows the periodic lattice basis correctly rather than
being tied to an arbitrary Cartesian identity form in the source indexing basis.

## Cartesian convention

The numerical Cartesian cell uses row lattice vectors. It is the lower-triangular
Cholesky factor of

$$
\bar G=G/(\det G)^{1/3},
$$

so the reference cell has positive unit volume. Numerical Cartesian values are
derived; the rational coordinates and exact Gram matrix remain authoritative.

## First edge model

The active model is

```text
ProjectedEdgeCurveModel.STRAIGHT_SEGMENT
```

`EmbeddedStraightEdgeSegment` is transient and source-bound. Distinct multiedges
are never merged. If two distinct quotient edges coincide geometrically modulo a
lattice translation and reversal, the first backend rejects the view and requires
a future distinct-curve model.

## Scope limit

Stage 8A certifies:

- distinct quotient vertices modulo translations;
- positive-definite metric;
- nonzero projected-edge lengths;
- no coincident distinct straight projected edges; and
- exact complete-group equivariance.

It does not certify the absence of crossings between arbitrary nonincident edge
images. That requires Stage 8B's periodic extended-object broad phase and exact
segment predicates.

## Ground fixtures

- Diamond net: primitive Gram matrix

  $$
  \begin{pmatrix}
  2&1&1\\
  1&2&1\\
  1&1&2
  \end{pmatrix},
  $$

  equal projected-edge squared lengths, and a unit-volume Cartesian cell.
- Sheared diamond basis: exact $P^{\mathsf T}GP$ covariance.
- Na-LTA: successful construction under the complete 96-operation unlabeled
  $T$-net symmetry group.

## Conclusion

Stage 8A is accepted. The codebase now has an exact, reproducible, symmetry-bound
Euclidean reference without conflating that reference with a trajectory frame or
with the future global spatial partition certificate.
