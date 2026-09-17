# Procedural graph fixtures

`network_layout_seed.json` is a structural fixture for `graph.procedural_graph`
(ADR-0074): 12 nodes, 4 relations, 17 transitions, cyclic
(`Verify_Layout -> Set_Position`). It exercises the contract shape only --
the real `condition`/`guidance`/`pitfalls` text for this procedure is owned
by the producer repo, `TD_Glossary_tox`
(`tools/pg_seed_network_layout.json`). Drift between the two in node ids,
relations, or edge keys is a contract break, not a local bug.

The file is pure ASCII and already in the canonical form `ProceduralGraph`
writes (`schema_version, name, nodes, edges` top-level;
`src, dst, relation, condition, guidance, pitfalls` per edge; edges sorted
`(src, relation, dst)`) -- see the byte-stability note in
`graph/procedural_graph.py`'s module docstring before hand-editing it.
