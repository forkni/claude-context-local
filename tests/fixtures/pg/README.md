# Procedural graph fixtures

`network_layout_seed.json` is the **canonical dump** of the producer repo's
`tools/pg_seed_network_layout.json` (`TD_Glossary_tox`, ADR-0011) at commit
`3880f617ca85262b9281ec924a8126a57606e97c` (`fix(pg-seed): drop Set_Position
self-loop the consumer validator rejects`), run through
`ProceduralGraph.from_document(...).to_document("network_layout")` for
`graph.procedural_graph` (ADR-0074): 12 nodes, 4 relations, 24 transitions,
cyclic via `Verify_Layout -TRIGGERS-> Set_Position` and
`Update_Annotation -LEADS_TO-> Identify_Group`. The producer's top-level
`notes` string is preserved. All `condition`/`guidance`/`pitfalls` text is
owned by the producer repo; drift between the two in node ids, relations, or
edge keys is a contract break, not a local bug.

The file is pure ASCII and already in the canonical form `ProceduralGraph`
writes (`schema_version, name, notes, nodes, edges` top-level;
`src, dst, relation, condition, guidance, pitfalls` per edge; edges sorted
`(src, relation, dst)`) -- see the byte-stability note in
`graph/procedural_graph.py`'s module docstring before hand-editing it.

Regenerate with `ProceduralGraph.from_document(...).to_document('network_layout')`,
then `json.dumps(indent=2)`, plus a trailing newline; never hand-edit.
