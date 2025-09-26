# SOP sprinkleSOP

## Overview

The Sprinkle SOP is used to add points to either the surface or the volume of a SOP. You can create points on a surface, or within a closed volume based on the Method menu.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `seed` | Seed | Float | Any number, integer or non-integer, which starts the random number generator. Each number gives completely different point positions. |
| `method` | Method | Menu | Describes where points are located. |
| `numpoints` | Number of Points | Int | The total number of points created. |
| `consolidate` | Consolidate | Toggle | Remove points until remaining are a minimum distance apart. |
| `neardist` | Distance to Nearest Point | Float | Minimum distance when using Consolidate option. |

## Usage Examples

### Basic Usage

```python
# Access the SOP sprinkleSOP operator
sprinklesop_op = op('sprinklesop1')

# Get/set parameters
freq_value = sprinklesop_op.par.active.eval()
sprinklesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sprinklesop_op = op('sprinklesop1')
output_op = op('output1')

sprinklesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sprinklesop_op)
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
