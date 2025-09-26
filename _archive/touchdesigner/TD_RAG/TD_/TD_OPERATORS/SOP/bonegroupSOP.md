# SOP bonegroupSOP

## Overview

The Bone Group SOP groups primitives by common bones (shared bones).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `bonesperpoint` | Max Bones per Point | Int | Trims the number of bones per point by ignoring the bones with the lowest weight until this maximum number is met. |
| `bonespergroup` | Max Bones per Group | Int | The maximum number of bones allowed per group of primitives. If there are more bones than this number, a new group is created. |

## Usage Examples

### Basic Usage

```python
# Access the SOP bonegroupSOP operator
bonegroupsop_op = op('bonegroupsop1')

# Get/set parameters
freq_value = bonegroupsop_op.par.active.eval()
bonegroupsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
bonegroupsop_op = op('bonegroupsop1')
output_op = op('output1')

bonegroupsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(bonegroupsop_op)
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
