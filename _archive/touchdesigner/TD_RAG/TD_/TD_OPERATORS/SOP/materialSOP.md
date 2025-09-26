# SOP materialSOP

## Overview

The Material SOP allows the assignment of materials (MATs) to geometry at the SOP level.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `mat` | Material | MAT | Select a material to apply. Drag and drop a MAT to this parameter or enter the path to that MAT in the parameter field. |

## Usage Examples

### Basic Usage

```python
# Access the SOP materialSOP operator
materialsop_op = op('materialsop1')

# Get/set parameters
freq_value = materialsop_op.par.active.eval()
materialsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
materialsop_op = op('materialsop1')
output_op = op('output1')

materialsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(materialsop_op)
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
