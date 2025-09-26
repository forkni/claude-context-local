---
title: "Script DAT - Replace Rows from Another Table"
category: EXAMPLES
document_type: example
difficulty: intermediate
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "data_artist", "interactive_designer"]
operators: ["scriptDAT", "tableDAT"]
concepts: ["data_merging", "conditional_logic", "table_lookup", "data_replacement"]
prerequisites: ["Python_fundamentals", "DAT_operations"]
workflows: ["data_management", "content_versioning", "interactive_data_updating"]
keywords: ["scriptDAT", "table", "replace", "merge", "lookup", "conditional"]
tags: ["python", "dat", "scripting", "replace", "merge", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "EX_DATS"]
example_count: 1
---

# Script DAT: Replace Rows from Another Table

## Concept

This example demonstrates a powerful data manipulation technique: taking a primary table and replacing some of its rows with corresponding rows from a secondary (or "override") table. The script matches rows based on the value in the first column, providing a way to update or override data in one table with data from another.

## Network Setup

The network for this example consists of:

-   **`table6` (tableDAT)**: The primary or original data table.
-   **`table8` (tableDAT)**: The secondary table containing the rows that will replace rows in the primary table.
-   **`script2` (scriptDAT)**: The script that performs the replacement logic, taking `table6` as its first input and `table8` as its second.

### Input Table A (`table6`)

|   |   |   |
|---|---|---|
| a | 1 | 2 |
| b | 3 | 4 |
| c | 5 | 6 |
| d | 7 | 8 |

### Input Table B (`table8` - The Override Table)

|   |        |        |
|---|--------|--------|
| b | new 9  | new 10 |
| c | new 11 | new 12 |

---

## How It Works

The `script2_callbacks.py` script contains the logic to iterate through the primary table and decide whether to keep the original row or substitute it with a row from the override table.

**`script2_callbacks.py`**
```python
# me is this DAT.
# 
# scriptOp is the OP which is cooking.

def cook(scriptOp):

	scriptOp.clear()

	tableA = scriptOp.inputs[0]	 # first input
	tableB = scriptOp.inputs[1]	 # second input

	for row in tableA.rows():

		# grab first cell
		cell = row[0]

		# look for this row in tableB
		newrow = tableB.row(cell.val)

		# if it doesn't exist, use table A:
		if newrow is None:
			newrow = row

		# add it to our table
		scriptOp.appendRow(newrow)

	return
```

1.  **`tableA = scriptOp.inputs[0]`**: Gets the primary table (`table6`).
2.  **`tableB = scriptOp.inputs[1]`**: Gets the override table (`table8`).
3.  **`for row in tableA.rows():`**: The script iterates through each `row` of the primary table (`tableA`).
4.  **`cell = row[0]`**: It grabs the first cell of the current row from `tableA`. The value of this cell will be used as the lookup key.
5.  **`newrow = tableB.row(cell.val)`**: This is the core lookup operation.
    -   `tableB.row(...)` is a powerful DAT method that searches for a row in `tableB` where the first column matches the provided value (`cell.val`).
    -   If a matching row is found in `tableB`, `newrow` becomes that row object.
    -   If no match is found, `newrow` will be `None`.
6.  **`if newrow is None:`**: The script checks if the lookup was successful.
    -   If `newrow` is `None` (no matching row was found in `tableB`), it means the original row from `tableA` should be kept.
    -   **`newrow = row`**: In this case, `newrow` is reassigned to be the original `row` from `tableA`.
7.  **`scriptOp.appendRow(newrow)`**: The script appends the final `newrow` to its own table. This will either be the override row from `tableB` or the original row from `tableA`.

### Final Output (`script2`)

The output table reflects the merged data. Rows 'b' and 'c' from `table6` have been replaced by the corresponding rows from `table8`.

|   |        |        |
|---|--------|--------|
| a | 1      | 2      |
| b | new 9  | new 10 |
| c | new 11 | new 12 |
| d | 7      | 8      |
