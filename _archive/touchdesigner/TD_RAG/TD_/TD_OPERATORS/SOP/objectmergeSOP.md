# SOP objectmergeSOP

## Overview

The Object Merge SOP allows you to merge the geometry of several SOPs spanning different components.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `xform` | Transform Object | OBJ | Specify a geometry component to which all the merged geometry should be transformed relative to. |
| `merge` | Merge | Sequence | Sequence of SOPs to merge |

## Usage Examples

### Basic Usage

```python
# Access the SOP objectmergeSOP operator
objectmergesop_op = op('objectmergesop1')

# Get/set parameters
freq_value = objectmergesop_op.par.active.eval()
objectmergesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
objectmergesop_op = op('objectmergesop1')
output_op = op('output1')

objectmergesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(objectmergesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **2** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
