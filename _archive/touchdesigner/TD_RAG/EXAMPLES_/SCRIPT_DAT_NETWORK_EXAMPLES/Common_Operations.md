---
title: "Script DAT Common Operations"
category: EXAMPLES
document_type: example
difficulty: beginner
time_estimate: "20-30 minutes"
user_personas: ["script_developer", "beginner_programmer", "data_artist"]
operators: ["scriptDAT", "tableDAT", "textDAT"]
concepts: ["table_manipulation", "scripting", "data_generation", "row_operations", "column_operations"]
prerequisites: ["Python_fundamentals", "TouchDesigner_basics", "DAT_operations"]
workflows: ["data_processing", "procedural_table_generation", "automation"]
keywords: ["scriptDAT", "table", "cell", "row", "column", "append", "delete", "copy"]
tags: ["python", "dat", "scripting", "table", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "EX_DATS", "PY_Working_with_DATs_in_Python"]
example_count: 1
---

# Script DAT: Common Table Operations

## Concept

This example demonstrates fundamental table manipulation techniques using a `scriptDAT`. It covers creating tables from scratch, copying data from inputs, and performing row and column operations like appending, modifying, and deleting. These are foundational skills for any data-driven work in TouchDesigner.

## Network Setup

The network consists of a `scriptDAT` that performs various operations based on its Python script. It takes an input `tableDAT` and generates different outputs. The example is broken into five scripts, each showcasing a different operation.

-   **`table1` (tableDAT)**: A simple input table with sample data.
-   **`script1` to `script5` (scriptDATs)**: Each script performs a unique table operation.

### Input Table (`table1`)

| c1 | c2 | c3 |
|----|----|----|
| r1 | 1  | 2  |
| r2 | 23 | 62 |
| r3 | 17 | 9  |

---

## How It Works

### 1. Creating a Table from Scratch

This script demonstrates how to generate a new table with specific rows and columns.

**`script1_callbacks.py`**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):
	scriptOp.clear()
	scriptOp.appendRow( ['', 'c1', 'c2', 'c3'] )
	scriptOp.appendRow( ['r1', 'aa', 'bb', 'cc'] )
	scriptOp.appendRow( ['r2', 'dd', 'ee', 'ff'] )
	scriptOp.appendRow( ['r3', 'gg', 'hh', 'ii'] )
	return
```
-   `scriptOp.clear()`: Empties the DAT to ensure a clean slate on each cook.
-   `scriptOp.appendRow([...])`: Adds a new row to the table with the specified list of cell values.

### 2. Copying Input Data

This script shows the simplest way to duplicate an input table.

**`script2_callbacks.py`**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):
	scriptOp.copy(scriptOp.inputs[0])
	return
```
-   `scriptOp.copy(scriptOp.inputs[0])`: Copies the entire contents of the first input DAT (`table1`) into the `scriptDAT`.

### 3. Modifying a Table

This script performs several modifications: copying, adding a new column, calculating values for that column, and deleting other columns.

**`script3_callbacks.py`**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):
	so = scriptOp

	so.copy(so.inputs[0])
	
	so.appendCol( ['sum'], 'c2' )
	so[0,0] = 'row'
	
	for r in range(1,so.numRows):
		so[r,'sum'] = so[r,'c1'] + so[r,'c2'] 
		
	so.deleteCol('c1')		
	so.deleteCol('c2')
	
	# plural "appendCols" to append one, two or more
	so.appendCols( ['extra1', 'extra2', 'extra3'] )
	
	return
```
-   `so.appendCol(['sum'], 'c2')`: Appends a new column named "sum" after the column "c2".
-   `so[r,'sum'] = so[r,'c1'] + so[r,'c2']`: Iterates through rows to calculate the sum of 'c1' and 'c2' and places it in the 'sum' column. Note that since the cell values are strings, this performs string concatenation, not mathematical addition.
-   `so.deleteCol('c1')`: Deletes the specified column.
-   `so.appendCols([...])`: Appends multiple new, empty columns to the end of the table.

### 4. Generating Cells by Iterating

This script builds a table by iterating through its rows and cells and assigning a value based on their position.

**`script4_callbacks.py`**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):

	scriptOp.clear()
	scriptOp.setSize(4,3)
	
	# here "row" is a list of cells in a row
	for row in scriptOp.rows():
		for cell in row:
			cell.val = 'r' + str(cell.row) + 'c' + str(cell.col)

	return
```
-   `scriptOp.setSize(4,3)`: Sets the dimensions of the table to 4 rows and 3 columns.
-   `scriptOp.rows()`: Returns an iterator for all the rows in the table.
-   `cell.val = ...`: Assigns a new value to each cell based on its row and column index.

### 5. Clearing Data While Keeping Structure

This script demonstrates how to clear the contents of a table while preserving its dimensions and headers.

**`script5_callbacks.py`**
```python
# me is this DAT.
# scriptOp is the OP which is cooking.

def cook(scriptOp):
	so = scriptOp
	in0 = so.inputs[0]
	so.copy(so.inputs[0])
	so.clear(keepSize=True, keepFirstRow=True, keepFirstCol=True)
	
	return
```
-   `so.clear(keepSize=True, keepFirstRow=True, keepFirstCol=True)`: Clears the data but preserves the table's dimensions, the first row (header), and the first column (row labels).
