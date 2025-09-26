---
title: "Script DAT - Exclude Rows by Parameter"
category: EXAMPLES
document_type: example
difficulty: intermediate
time_estimate: "20-25 minutes"
user_personas: ["script_developer", "interactive_designer", "data_artist"]
operators: ["scriptDAT", "tableDAT"]
concepts: ["filtering", "custom_parameters", "string_manipulation", "conditional_logic"]
prerequisites: ["Python_fundamentals", "DAT_operations", "custom_parameters"]
workflows: ["data_filtering", "interactive_dashboards", "procedural_content_generation"]
keywords: ["scriptDAT", "table", "exclude", "filter", "parameter", "string"]
tags: ["python", "dat", "scripting", "filtering", "parameters", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "CLASS_Par_Class", "EX_DATS"]
example_count: 1
---

# Script DAT: Exclude Rows by Parameter

## Concept

This example demonstrates how to filter a table by excluding rows that contain specific keywords. The keywords are provided via a custom parameter on the `scriptDAT`, making the filtering process interactive and dynamic.

## Network Setup

The network includes:

-   **`table5` (tableDAT)**: The source table containing a list of colors.
-   **`script3` (scriptDAT)**: The script that performs the filtering. It has a custom string parameter named `Exclude` on a page called `My Parameters`.

### Input Table (`table5`)

|       |        |        |       |
|-------|--------|--------|-------|
| red   | brown  | black  | green |
| green | pink   | orange | blue  |
| white | blue   | gold   | brown |
| blue  | black  | pink   | green |
| black | green  | blue   | pink  |
| gold  | yellow | white  | brown |

### Custom Parameter

The `script3` operator has a custom parameter `Exclude` (string type). The user can type a comma-separated list of words into this parameter (e.g., "red,orange,yellow") to exclude rows containing those words.

---

## How It Works

The `script3_callbacks.py` script is responsible for setting up the custom parameter and performing the filtering logic during each cook.

**`script3_callbacks.py`**
```python
# me is this DAT.
# 
# scriptOp is the OP which is cooking.

# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def setupParameters(scriptOp):
	scriptOp.appendParStr('Exclude',label='Exclude List (comma separated)', page='My Parameters')
	return

# called whenever custom pulse parameter is pushed
def onPulse(par):
	return

def cook(scriptOp):
	# make single list of strings to exlude
	excludeList = []
	for c in scriptOp.par.Exclude.val.split(','):
		excludeList.append(c)

	# clear table
	scriptOp.clear()
	
	# get input DAT
	indat = scriptOp.inputs[0]

	# test each row
	for r in indat.rows():

		# see if any of the cell strings are in our list
		found = False
		for cell in r:
			if (cell.val in excludeList):
				found = True

		# add row if none found
		if not found:
			scriptOp.appendRow(r)

	return
```

1.  **`setupParameters(scriptOp)`**: This function is called to create the custom parameters on the `scriptDAT`. `scriptOp.appendParStr(...)` adds a string parameter named `Exclude`.

2.  **`cook(scriptOp)`**: This is the main cooking function.

3.  **Parsing the Exclude List**: 
    -   `scriptOp.par.Exclude.val` retrieves the current string from the custom parameter.
    -   `.split(',')` splits this string into a list of words using the comma as a delimiter.
    -   The code iterates through this list to build `excludeList`, which holds all the words to be filtered out.

4.  **Filtering Logic**:
    -   `scriptOp.clear()`: Empties the script's own table to prepare for the new, filtered output.
    -   `for r in indat.rows():`: The script iterates through each row of the input DAT (`table5`).
    -   `found = False`: A flag is initialized for each row to track if an excluded word is found.
    -   `for cell in r:`: It then iterates through each cell within the current row.
    -   `if (cell.val in excludeList):`: It checks if the cell's value exists in the `excludeList`.
    -   If a match is found, the `found` flag is set to `True`.

5.  **Appending Rows**: 
    -   `if not found:`: After checking all cells in a row, if the `found` flag is still `False`, it means no excluded words were present in that row.
    -   `scriptOp.appendRow(r)`: The entire original row (`r`) is appended to the `scriptDAT`'s table.

### Example Output

If the `Exclude` parameter is set to `red,orange,yellow`, the output in `script3` would be:

|       |       |      |       |
|-------|-------|------|-------|
| white | blue  | gold | brown |
| blue  | black | pink | green |
| black | green | blue | pink  |
