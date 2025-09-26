---
title: "Script DAT - Copy and Iterate"
category: EXAMPLES
document_type: example
difficulty: beginner
time_estimate: "15-20 minutes"
user_personas: ["script_developer", "beginner_programmer"]
operators: ["scriptDAT", "tableDAT", "textDAT"]
concepts: ["iteration", "table_copy", "cell_access", "scripting"]
prerequisites: ["Python_fundamentals", "DAT_operations"]
workflows: ["data_processing", "automation", "text_manipulation"]
keywords: ["scriptDAT", "table", "iterate", "rows", "copy", "cell"]
tags: ["python", "dat", "scripting", "iteration", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "EX_DATS"]
example_count: 1
---

# Script DAT: Copy Inputs and Iterate Rows

## Concept

This example demonstrates a common workflow in TouchDesigner: copying an input table into a `scriptDAT` and then iterating over its rows to perform an operation. This pattern is fundamental for processing and transforming data from any table-based source.

## Network Setup

The network consists of:

-   **`table10` (tableDAT)**: The source table containing the data to be processed.
-   **`script11` (scriptDAT)**: The script that copies the input and iterates through it.
-   **`dump` (textDAT)**: A DAT used to store the output of the script for visualization.

### Input Table (`table10`)

|    |    |   |
|----|----|---|
| aa | 1  | 2 |
| dd | 3  | 4 |
| gg | 5  | 6 |
| kk | 7  | 8 |

---

## How It Works

The `script11_callbacks.py` script executes the logic. It copies the input, clears a target DAT, and then loops through each row of the copied table to build a new string.

**`script11_callbacks.py`**
```python
# me - this DAT
# scriptOp - the OP which is cooking

def onCook(scriptOp):

	scriptOp.copy(scriptOp.inputs[0])

	op('dump').text = ''
	
	# here "row" is a list of cell objects in a row
	# this joins together the first cell of each row
	for row in scriptOp.rows():
		cell = row[0]
		op('dump').text = op('dump').text + cell.val

	return
```

1.  **`scriptOp.copy(scriptOp.inputs[0])`**: The script first copies the entire contents of its first input (`table10`) into itself. This is a crucial step as it creates a local, editable copy of the data for the current cook frame.

2.  **`op('dump').text = ''`**: It finds an operator named `dump` and clears its text content. This ensures the output is fresh for each cook.

3.  **`for row in scriptOp.rows():`**: This loop iterates through each row of the `scriptDAT`'s own table. The `rows()` method returns a list of row objects.

4.  **`cell = row[0]`**: Inside the loop, it accesses the first cell (`index 0`) of the current `row`.

5.  **`op('dump').text = op('dump').text + cell.val`**: It retrieves the value of the cell (`cell.val`) and appends it to the text content of the `dump` DAT. The result is a single string concatenating the values from the first column of the input table.

### Output in `dump` DAT

```
aaddggkk
```
