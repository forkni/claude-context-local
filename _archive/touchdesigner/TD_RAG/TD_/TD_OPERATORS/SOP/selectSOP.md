# SOP selectSOP

## Overview

The Select SOP allows you to reference a SOP from any other location in TouchDesigner.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sop` | SOP | SOP | The path of the SOP being referenced. |

## Usage Examples

### Basic Usage

```python
# Access the SOP selectSOP operator
selectsop_op = op('selectsop1')

# Get/set parameters
freq_value = selectsop_op.par.active.eval()
selectsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
selectsop_op = op('selectsop1')
output_op = op('output1')

selectsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(selectsop_op)
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
