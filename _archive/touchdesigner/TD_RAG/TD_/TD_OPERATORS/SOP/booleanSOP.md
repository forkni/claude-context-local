# SOP booleanSOP

## Overview

The Boolean SOP takes two closed polygonal sets, A and B. Set these Sources to the SOPs with the 3D shapes that you wish to operate on.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `booleanop` | Operation | Menu | Some of the operations below produce guide geometry to give you visual feedback on the results of the operation being performed. The appearance of the geometry is context sensitive - if you are per... |
| `accattrib` | Accurate Attributes Interpolation | Toggle | If selected, all inputs are convexed to triangles, otherwise they are convexed to quadrilaterals. |
| `creategroup` | Create Groups | Toggle | If selected, a group is created containing all faces pertaining to the first input, and a second group containing all faces of the second input. |
| `groupa` | Group A | Str | When Create Groups = On, specify a name for Group A. |
| `groupb` | Group B | Str | When Create Groups = On, specify a name for Group B. |

## Usage Examples

### Basic Usage

```python
# Access the SOP booleanSOP operator
booleansop_op = op('booleansop1')

# Get/set parameters
freq_value = booleansop_op.par.active.eval()
booleansop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
booleansop_op = op('booleansop1')
output_op = op('output1')

booleansop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(booleansop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **5** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
