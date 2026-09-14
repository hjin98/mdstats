# Gate A bounded falsification record — FPS/coverage target-order candidate

Date: 2026-09-13
Workplan: `MLFF-FPS-COVERAGE-METHOD-RECONCILIATION-1`
Candidate: `GATE_A_D1_D2_FPS_COVERAGE_METHOD_CANDIDATE.md`
Status: same-session author-side falsification; **not** the independent Gate A review.

## Fixture

A deterministic two-dimensional bounded fixture was constructed with:

- 60 frames in dense common condition A near the origin;
- 5 geometrically distant A-tail frames;
- 30 frames in common condition B near `(0,5)`;
- 5 frames in rare condition C near `(5,5)`;
- deliberately high synthetic difficulty assigned to the A tail and C;
- a science-derived hash key independent of the displayed UID.

Five order families were compared at prefixes 8, 16, and 32:

1. lexical UID baseline;
2. pure global medoid-seeded FPS;
3. representative-only centroid-nearest queues;
4. difficulty-only descending order; and
5. the proposed condition-medoid + within-condition FPS + empirical-condition proportional interleaving.

Metrics were full-population nearest-selected mean distance, Q95, maximum covering radius, condition-proportion L1 discrepancy, represented-condition count, and number of selected A-tail frames.

## Results

```text
K=8
method               mean    q95    max    prop-L1  conds  A-tail  counts(A,B,C)
UID                   3.421   5.521  5.578  1.300    2      0       (0,3,5)
pure FPS              0.330   0.560  0.894  0.150    3      1       (5,2,1)
representative only   0.557   0.985  4.809  0.150    3      0       (5,2,1)
difficulty only       4.215   5.350  5.373  0.650    2      5       (5,0,3)
proposed              0.296   0.538  0.547  0.150    3      2       (5,2,1)

K=16
UID                   3.110   5.101  5.162  1.300    2      0       (0,11,5)
pure FPS              0.190   0.360  0.374  0.175    3      3       (9,5,2)
representative only   0.501   0.944  4.809  0.050    3      0       (10,5,1)
difficulty only       2.753   4.773  4.956  0.675    3      5       (5,6,5)
proposed              0.173   0.300  0.374  0.050    3      3       (10,5,1)

K=32
UID                   3.037   5.101  5.107  1.300    2      0       (0,27,5)
pure FPS              0.104   0.206  0.224  0.300    3      4       (16,13,3)
representative only   0.399   0.789  4.704  0.037    3      0       (21,9,2)
difficulty only       2.657   4.773  4.956  0.988    3      5       (5,22,5)
proposed              0.100   0.224  0.283  0.037    3      5       (21,9,2)
```

## Interpretation

The fixture falsifies UID order, representative-only order, and difficulty-only order for the intended claim. Pure global FPS covers geometry well, but at larger prefixes materially departs from the empirical condition mass (`prop-L1=0.300` at K=32 versus `0.037` for the proposed method). The proposed method preserves the empirical condition count schedule while eliminating the representative-only blind spot to the distant A tail. At K=8 it also gives a smaller maximum covering radius than pure FPS on this fixture because the explicit condition anchors prevent a rare condition from being delayed.

This does **not** establish universal optimality. It establishes that the resolved combined construction survives the workplan's required obvious-pathology counterexamples on an interpretable bounded fixture and is materially distinguishable from all four comparison baselines.

## Metamorphic check performed

The proposed fixture implementation does not read the displayed UID for metric, medoid, FPS, or condition scheduling. Replacing UIDs one-to-one therefore preserved the mapped order exactly:

```text
uid_renaming_invariance=PASS
```

## Remaining independent Gate A checks

The independent reviewer must still reproduce or replace this evidence and cover:

- input-enumeration invariance;
- feature-coordinate canonicalization invariance;
- direct simple-reference FPS/medoid equivalence under the exact proposed FP64 tolerance;
- evaluation-prefix/M3-estimand reference checks;
- old-generation rejection;
- current producer-lineage authentication; and
- resource/scaling evidence.

No D3/D4 behavioral implementation is authorized by this author-side record alone.