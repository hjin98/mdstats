# Na-LTA corrected primitive-ring acceptance result

- Framework topology digest: `11d0b594ba1564d14ede796e86b5a73901f91d5c2e31ab031b5b202ce96a4af4`
- Framework vertices: 48
- Framework edges: 96
- Default method: `shortest_path_pairs`
- Default family: `primitive_no_shortcut`
- Primitive rings through size 8: 82
- Edge-shortest subset rings through size 8: 52
- Resource truncation: False
- Primitive catalog digest: `32965d01ad6f6cb16855e4cebe9efaa73f0b6f0959aa8d6eecbb5daae221ed87`

| Framework cycle size | Primitive/no-shortcut | Edge-shortest subset |
|---:|---:|---:|
| 4 | 36 | 36 |
| 6 | 40 | 16 |
| 8 | 6 | 0 |

The corrected default returns 36 four-rings, 40 six-rings, and 6 eight-rings.
The removed-edge compatibility method returns the earlier 36 four-rings and 16
six-rings. These are topological cycle counts, not conventional geometrically
classified ring-site counts. Ring geometry, cages, portals, and site labels
remain downstream responsibilities.
