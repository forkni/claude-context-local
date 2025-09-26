---
title: "Script DAT - Generate Random Numbers"
category: EXAMPLES
document_type: example
difficulty: beginner
time_estimate: "15-20 minutes"
user_personas: ["script_developer", "generative_artist", "beginner_programmer"]
operators: ["scriptDAT"]
concepts: ["random_numbers", "custom_parameters", "procedural_generation"]
prerequisites: ["Python_fundamentals", "custom_parameters"]
workflows: ["generative_art", "data_simulation", "interactive_control"]
keywords: ["scriptDAT", "random", "generate", "parameter", "procedural"]
tags: ["python", "dat", "scripting", "random", "procedural", "examples"]
related_docs: ["CLASS_ScriptDAT_Class", "CLASS_Par_Class", "EX_DATS"]
example_count: 1
---

# Script DAT: Generate Random Numbers

## Concept

This example demonstrates how to use a `scriptDAT` to generate a column of random numbers. The quantity of numbers generated is controlled interactively by a custom integer parameter on the `scriptDAT` itself. This is a common pattern for creating procedurally generated content that can be easily controlled by the user.

## Network Setup

The network is very simple:

-   **`script8` (scriptDAT)**: This is the only operator. It contains the Python script to generate the random numbers and has a custom parameter to control the number of rows.

### Custom Parameter

The `script8` operator has a custom integer parameter named `Rows` on a page called `Custom`. This parameter is set up as a slider ranging from 1 to 20, allowing the user to easily define how many random numbers to generate.

---

## How It Works

The `script8_callbacks.py` script handles both the creation of the custom parameter and the logic for generating the random numbers.

**`script8_callbacks.py`**
```python
# me is this DAT.
# 
# scriptOp is the OP which is cooking.

# press 'Setup Parameters' in the OP to call this function to re-create the parameters.
def setupParameters(scriptOp):
	scriptOp.appendParInt('Rows', page='Custom')

	scriptOp.par.Rows.normMin = 1
	scriptOp.par.Rows.normMax = 20
	return

# called whenever custom pulse parameter is pushed
def onPulse(par):
	return

def cook(scriptOp):
	import random
	# you can also use tdu.rand()
	
	scriptOp.clear()

	# get custom parameter value
	numRows = scriptOp.par.Rows
	scriptOp.appendRow('random numbers')
	
	for i in range(numRows):
		scriptOp.appendRow(random.randint(1,10))
	
	return
```

1.  **`setupParameters(scriptOp)`**: This function defines the custom `Rows` parameter.
    -   `scriptOp.appendParInt('Rows', page='Custom')`: Creates an integer parameter named `Rows`.
    -   `scriptOp.par.Rows.normMin = 1` and `scriptOp.par.Rows.normMax = 20`: These lines set the slider range for the parameter, making it user-friendly.

2.  **`cook(scriptOp)`**: This function runs every time the DAT cooks.
    -   `import random`: Imports Python's standard `random` module.
    -   `scriptOp.clear()`: Clears the DAT to ensure the list of numbers is regenerated on each cook.
    -   `numRows = scriptOp.par.Rows`: Retrieves the current value of the `Rows` custom parameter.
    -   `scriptOp.appendRow('random numbers')`: Appends a header row to the table.
    -   `for i in range(numRows):`: This loop runs for the number of times specified by the `Rows` parameter.
    -   `scriptOp.appendRow(random.randint(1,10))`: Inside the loop, it generates a random integer between 1 and 10 (inclusive) and appends it as a new row in the table.

### Interactivity

-   To generate a new set of random numbers, you can right-click on the `scriptDAT` and select "Force Cook".
-   To change the quantity of numbers, simply adjust the `Rows` slider on the `scriptDAT`'s parameter window. The script will automatically re-cook and generate the new amount.
