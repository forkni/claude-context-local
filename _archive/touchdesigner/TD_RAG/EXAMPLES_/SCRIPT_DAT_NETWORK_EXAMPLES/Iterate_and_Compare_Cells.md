---
title: "Script DAT - Iterate and Compare All Cells"
category: EXAMPLES
document_type: example
difficulty: intermediate
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "data_artist", "generative_designer"]
operators: ["scriptDAT", "tableDAT"]
concepts: ["iteration", "data_transformation", "comparison", "cell_access"]
prerequisites: ["Python_fundamentals", "DAT_operations"]
workflows: ["data_analysis", "procedural_content_generation", "data_validation"]
keywords: ["scriptDAT", "table", "cell", "iterate", "compare", "transform"]
tags: ["python", "dat", "scripting", "iteration", "comparison", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "EX_DATS"]
example_count: 2
---

# Script DAT: Iterate and Compare All Cells

## Concept

This example is split into two parts, demonstrating how to process every cell in a table and how to compare two tables cell by cell.

1.  **Iterate and Transform**: The first script iterates over all cells in an input table and replaces each cell's string value with its length.
2.  **Iterate and Compare**: The second script takes two tables as input and creates a new table where each cell is `1` if the corresponding cells in the input tables are identical, and `0` otherwise.

## Network Setup

The network for this example includes:

-   **`table1`, `table2` (tableDATs)**: Two source tables with string data. `table2` is a slight variation of `table1` for the comparison part.
-   **`script1` (scriptDAT)**: Takes `table1` as input and calculates the length of each cell's string.
-   **`script2` (scriptDAT)**: Takes the output of `script1` and the original `table2` as inputs to perform a cell-by-cell comparison.

---

## Part 1: Iterate and Transform Cell Values

This script shows how to access and modify every cell in a table individually.

**`script1_callbacks.py`**
```python
# scriptOp is the OP which is cooking.

def cook(scriptOp):
	indat = scriptOp.inputs[0]

	scriptOp.copy(indat)

	# for each row
	for r in scriptOp.rows():
		for cell in r:
			cell.val = len(cell.val)
	return
```

### How It Works

1.  **`scriptOp.copy(indat)`**: The script copies the input table (`table1`) into itself, preserving the structure and original values.
2.  **`for r in scriptOp.rows():`**: It begins an outer loop to iterate through each row of the copied table.
3.  **`for cell in r:`**: It starts a nested inner loop to iterate through each `cell` object in the current `row`.
4.  **`cell.val = len(cell.val)`**: This is the core transformation. For each cell, it calculates the length of the cell's string value (`len(cell.val)`) and overwrites the cell's content with this new integer value.

### Output of `script1`

Given `table1`, the script produces a table where each color name is replaced by the number of characters in that name.

| 3 | 5 | 5 | 5 |
|---|---|---|---|
| 5 | 4 | 6 | 4 |
| 5 | 4 | 4 | 5 |
| 4 | 5 | 4 | 5 |
| 5 | 5 | 4 | 4 |
| 4 | 6 | 5 | 5 |

---

## Part 2: Iterate and Compare Two Tables

This script demonstrates how to compare two tables of the same size and generate a matrix indicating the differences.

**`script3_callbacks.py` (Note: file is named script3 in the project)**
```python
# scriptOp is the OP which is cooking.

def cook(scriptOp):
		
	tableA = scriptOp.inputs[0]	 # first input
	tableB = scriptOp.inputs[1]	 # second input

	scriptOp.copy(tableA)

	for r in scriptOp.rows():
		for cell in r:
			cell.val = int(tableA[cell.row, cell.col] == tableB[cell.row, cell.col])
	return
```

### How It Works

1.  **`tableA = scriptOp.inputs[0]`**: Gets the first input DAT.
2.  **`tableB = scriptOp.inputs[1]`**: Gets the second input DAT.
3.  **`scriptOp.copy(tableA)`**: Copies the structure of `tableA` to serve as the template for the output table.
4.  **`for r in scriptOp.rows():` and `for cell in r:`**: The script iterates through every cell of its own table, just like in the first part.
5.  **`cell.val = int(tableA[cell.row, cell.col] == tableB[cell.row, cell.col])`**: This is the comparison logic.
    -   `tableA[cell.row, cell.col]` accesses the cell in `tableA` at the current row and column.
    -   `tableB[cell.row, cell.col]` accesses the corresponding cell in `tableB`.
    -   `==` compares the values of these two cells. This comparison returns a boolean (`True` if they are the same, `False` otherwise).
    -   `int(...)` converts the boolean result into an integer: `True` becomes `1` and `False` becomes `0`.
    -   This `1` or `0` is then assigned as the new value for the current cell in the output table.

### Output of `script2`

This script produces a table of `1`s and `0`s, showing where `table1` and `table2` have identical or different values.

| 1 | 1 | 1 | 1 |
|---|---|---|---|
| 1 | 0 | 1 | 1 |
| 1 | 1 | 1 | 1 |
| 1 | 1 | 1 | 1 |
| 1 | 0 | 0 | 1 |
| 1 | 1 | 1 | 1 |
