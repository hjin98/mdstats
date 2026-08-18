# Node-display-mode source/specification consistency audit

## Release

- Package: `mdstats 0.13.1`
- Feature owner: `mdstats.plotting.graph_styles`
- Renderer consumers: `graph_2d.py`, `graph_3d.py`
- Framework convenience consumer: `framework_topology_graph.py`

## Public API audit

```text
NodeDisplayMode root export:          passed
GraphStyle fields in Markdown:        passed
GraphStyle fields in PDF:             passed
Node-display tokens in Markdown:      passed
Node-display tokens in PDF:           passed
framework_default signature aligned:  passed
```

GraphStyle runtime signature:

```text
(node_default: 'NodeStyle' = <factory>, edge_default: 'EdgeStyle' = <factory>, node_rules: 'tuple[NodeStyleRule, ...]' = (), edge_rules: 'tuple[EdgeStyleRule, ...]' = (), labels: 'GraphLabelOptions' = <factory>, palette: 'ChemicalColorPalette' = <factory>, background_color: 'ColorLike' = 'white', legend: "Literal['auto', 'none', 'all']" = 'auto', node_display_mode: 'NodeDisplayMode | str' = <NodeDisplayMode.MARKERS: 'markers'>, node_dot_size: 'float' = 16.0) -> None
```

`GraphStyle.framework_default()` runtime signature:

```text
(palette: 'ChemicalColorPalette | None' = None, *, diagnostic: 'bool' = False, node_display_mode: 'NodeDisplayMode | str' = <NodeDisplayMode.MARKERS: 'markers'>, node_dot_size: 'float' = 16.0) -> "'GraphStyle'"
```

## Behavioral ownership

- `GraphStyle` owns the global presentation choice and dot size.
- Node and edge style rules resolve before display-mode transformation.
- `DOTS` preserves resolved face color and alpha while forcing a small circular point without outline.
- `HIDDEN` suppresses node markers, periodic ghost markers, node labels, node legends, and 3-D node traces.
- Hidden nodes remain present in scientific keys, periodic display mappings, positions, and edge endpoint indices.
- Edge geometry and endpoint-derived edge colors are unchanged.

## Renderer audit

```text
2-D dot markers:                      passed
2-D hidden node artists:              passed
2-D hidden periodic ghosts:           passed
2-D hidden node labels/legend:        passed
3-D dot marker traces:                passed
3-D hidden node traces:               passed
Scientific node-key preservation:     passed
Na-LTA projected edge preservation:   passed
```

## Documentation artifacts

- `graph_styles_spec.md` / `.pdf`: 8 PDF pages; searchable and preflight-openable.
- `graph_2d_spec.md` / `.pdf`: 10 PDF pages; searchable and preflight-openable.
- `graph_3d_spec.md` / `.pdf`: 15 PDF pages; searchable and preflight-openable.
- `framework_topology_graph_spec.md` / `.pdf`: 13 PDF pages; searchable and preflight-openable.
- `graph_visualization_specification_index.md` / `.pdf`: 8 PDF pages; searchable and preflight-openable.

## Missing items

- Markdown fields missing: `[]`
- PDF fields missing: `[]`
- Markdown API tokens missing: `[]`
- PDF API tokens missing: `[]`

## Result

Source, exported API, focused tests, Markdown specifications, and regenerated PDF specifications are aligned for the 0.13.1 node-display feature.
