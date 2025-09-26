---
title: "Script DAT - Iterate Input Rows"
category: EXAMPLES
document_type: example
difficulty: beginner
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "beginner_programmer", "data_artist"]
operators: ["scriptDAT", "tableDAT"]
concepts: ["iteration", "data_processing", "cell_access", "summation"]
prerequisites: ["Python_fundamentals", "DAT_operations"]
workflows: ["data_transformation", "aggregation", "procedural_text_generation"]
keywords: ["scriptDAT", "table", "iterate", "rows", "sum", "cell"]
tags: ["python", "dat", "scripting", "iteration", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "EX_DATS"]
example_count: 2
---

# Script DAT: Iterate Input Rows

## Concept

This example demonstrates two different methods for iterating through the rows of an input table to perform calculations and transformations. 

1.  **Method 1: Using `table.rows()`**: This method iterates through a list of `row` objects, which is useful for accessing cells by their index within the row.
2.  **Method 2: Using `range(table.numRows)`**: This method iterates using a numerical index, which provides more flexibility for accessing cells by column name and for processing specific ranges of rows.

## Network Setup

The network contains two distinct examples:

-   **Example A**: A `scriptDAT` (`script4`) takes `table9` as input and uses the `table.rows()` method to append an 'x' to the first cell of each row.
-   **Example B**: A `scriptDAT` (`script12`) takes `table11` as input and uses the `range()` method to sum the values in a specific column.

### Input Tables

**`table9` and `table11` (Identical)**

|      | col1 | col2 |
|------|------|------|
| a    | 1    | 2    |
| b    | 3    | 4    |
| c    | 5    | 6    |
| d    | 7    | 8    |

---

## Method 1: Iterating with `table.rows()`

This approach is straightforward and ideal when you need to process every row sequentially and can access cells by their numerical index.

**`script2_callbacks1.py` (for `script4`)**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):

	scriptOp.clear()

	table = scriptOp.inputs[0]	 # first input

	for row in table.rows():

		# grab first cell
		cell = row[0]
		newcell = cell + 'x'

		# add it to our table
		scriptOp.appendRow(newcell)

	return
```

### How It Works

1.  **`table = scriptOp.inputs[0]`**: Gets the input DAT object.
2.  **`for row in table.rows():`**: This loop iterates over each row of the input table. Each `row` is a list-like object containing the `Cell` objects for that row.
3.  **`cell = row[0]`**: It accesses the first cell (index 0) of the current `row`.
4.  **`newcell = cell + 'x'`**: It concatenates the string value of the cell with the character 'x'.
5.  **`scriptOp.appendRow(newcell)`**: It appends the resulting new string as a new row in the `scriptDAT`.

### Output of `script4`

|    |
|----|
| ax |
| bx |
| cx |
| dx |

---

## Method 2: Iterating with `range(table.numRows)`

This method provides more control and is better when you need to access cells by column name or work with specific row ranges (e.g., skipping a header).

**`script2_callbacks2.py` (for `script12`)**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):

	scriptOp.clear()

	# this will get values from the input table
	table = scriptOp.inputs[0]	 # first input	
	sum = 0

	for r in range(1, table.numRows):
		sum = sum + table[r, 'col1']

	scriptOp.appendRow(sum)
	
	return
```

### How It Works

1.  **`sum = 0`**: Initializes a variable to hold the sum.
2.  **`for r in range(1, table.numRows):`**: This loop iterates from row `1` up to (but not including) the total number of rows. It starts at `1` to intentionally skip the header row (row `0`). `r` is an integer representing the row index.
3.  **`sum = sum + table[r, 'col1']`**: This is the core of the logic.
    -   `table[r, 'col1']`: It accesses the cell at the current row index `r` and in the column named `'col1'`. This ability to access by column name is a key advantage of this iteration method.
    -   TouchDesigner automatically attempts to convert the cell's value to a number for the addition operation.
    -   The result is added to the `sum`.
4.  **`scriptOp.appendRow(sum)`**: After the loop finishes, the final calculated `sum` is appended as a new row in the `scriptDAT`.

### Output of `script12`

The script sums the values in `col1` (1 + 3 + 5 + 7).

|    |
|----|
| 16 |
