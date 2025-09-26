---
title: "Script DAT - Shuffle Cell Contents"
category: EXAMPLES
document_type: example
difficulty: intermediate
time_estimate: "15-20 minutes"
user_personas: ["script_developer", "generative_artist", "data_artist"]
operators: ["scriptDAT", "tableDAT"]
concepts: ["string_manipulation", "randomization", "custom_parameters", "procedural_effects"]
prerequisites: ["Python_fundamentals", "DAT_operations", "custom_parameters"]
workflows: ["text_processing", "generative_typography", "data_randomization"]
keywords: ["scriptDAT", "table", "shuffle", "random", "string", "cell", "parameter"]
tags: ["python", "dat", "scripting", "shuffle", "random", "procedural", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "CLASS_Par_Class", "EX_DATS"]
example_count: 1
---

# Script DAT: Shuffle Cell Contents

## Concept

This example demonstrates how to procedurally shuffle the characters within each cell of a table. The randomization is controlled by a `Seed` custom parameter, allowing for repeatable random results. This technique is useful for creating generative text effects or for randomizing data in a controlled way.

## Network Setup

The network consists of:

-   **`table7` (tableDAT)**: The source table containing strings to be shuffled.
-   **`script1` (scriptDAT)**: The script that performs the shuffling. It has a custom integer parameter named `Seed`.

### Input Table (`table7`)

|      |       |       |
|------|-------|-------|
| red  | black | green |
| green| orange| blue  |
| gold | white | brown |

### Custom Parameter

The `script1` operator has a custom integer parameter `Seed` on a page named `Custom1`. Changing the value of this seed will produce a different shuffled result, but the same seed will always produce the same result.

---

## How It Works

The `script1_callbacks.py` script is responsible for setting up the parameter and executing the shuffling logic.

**`script1_callbacks.py`**
```python
# me is this DAT.
# 
# scriptOp is the OP which is cooking.

# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def setupParameters(scriptOp):
	scriptOp.appendParInt('Seed', page='Custom')
	return

# called whenever custom pulse parameter is pushed
def onPulse(par):
	return

def cook(scriptOp):
	import random

	# copy input DAT
	indat = scriptOp.inputs[0]
	scriptOp.copy(indat)

	# seed based on custom parameter
	v = scriptOp.par.Seed.eval()
	random.seed(v)
		
	for cell in scriptOp.cells('*', '*'):
		s = cell.val
		cell.val = ''.join(random.sample(s,len(s)))
	
	return
```

1.  **`setupParameters(scriptOp)`**: This function creates the custom integer parameter named `Seed`.

2.  **`cook(scriptOp)`**: This is the main function that executes on each cook.

3.  **`import random`**: Imports Python's `random` module, which contains the necessary functions for shuffling.

4.  **`scriptOp.copy(indat)`**: The script copies the input table (`table7`) into itself to have a base to work from.

5.  **Seeding the Random Generator**:
    -   `v = scriptOp.par.Seed.eval()`: It gets the current integer value from the `Seed` custom parameter.
    -   `random.seed(v)`: This crucial step initializes the random number generator with the provided seed. This ensures that the sequence of "random" operations will be identical every time the script is run with the same seed value.

6.  **Iterating and Shuffling Cells**:
    -   `for cell in scriptOp.cells('*', '*'):`: This loop iterates through every single cell in the table. `cells('*', '*')` is a convenient way to get all cells.
    -   `s = cell.val`: It stores the original string value of the cell in a variable `s`.
    -   `random.sample(s, len(s))`: This is the core shuffling logic. `random.sample()` takes a sequence (the string `s`) and returns a new list containing all the elements from the original sequence in a random order. For example, `random.sample('red', 3)` might return `['e', 'd', 'r']`.
    -   `''.join(...)`: The `join()` method is used to combine the list of shuffled characters back into a single string (e.g., `'edr'`).
    -   `cell.val = ...`: The cell's original value is overwritten with the new, shuffled string.

### Example Output

With a specific seed, the output might look like this:

|     |       |       |
|-----|-------|-------|
| der | kblca | rgnee |
| egenr| erngoa| lbue  |
| ogld | hewit | ornbw |
