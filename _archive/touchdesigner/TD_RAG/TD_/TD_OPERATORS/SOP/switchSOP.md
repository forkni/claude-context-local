# SOP switchSOP

## Overview

The Switch SOP switches between up to 9999 possible inputs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `input` | Select Input | Int | The index of the source to use, where the first source is 0, the second 1, and so on. |

## Usage Examples

### Basic Usage

```python
# Access the SOP switchSOP operator
switchsop_op = op('switchsop1')

# Get/set parameters
freq_value = switchsop_op.par.active.eval()
switchsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
switchsop_op = op('switchsop1')
output_op = op('output1')

switchsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(switchsop_op)
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
