# SOP inSOP

## Overview

The In SOP creates a SOP input in a Component. Component inputs are positioned alphanumerically on the left side of the node.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `label` | Label | Str | Creates a pop-up label when the cursor rolls over this Component input. |

## Usage Examples

### Basic Usage

```python
# Access the SOP inSOP operator
insop_op = op('insop1')

# Get/set parameters
freq_value = insop_op.par.active.eval()
insop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
insop_op = op('insop1')
output_op = op('output1')

insop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(insop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **1** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
