# SOP tristripSOP

## Overview

The Tristrip SOP convert geometry into triangle strips.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Source Group | StrMenu | Specify a group of primitive to convert to tristrips. If no group is specified, then the entire geometry will be converted. |
| `constrainstriplength` | Constrain Strip Length | Toggle | When checked on, the length (number of triangles) of the tristrips can be constrained to a maximum using the Maximum Strip Length parameter below. |
| `maxstriplength` | Maximum Strip Length | Int | Set the maximum number of triangles in each tristrip. |

## Usage Examples

### Basic Usage

```python
# Access the SOP tristripSOP operator
tristripsop_op = op('tristripsop1')

# Get/set parameters
freq_value = tristripsop_op.par.active.eval()
tristripsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tristripsop_op = op('tristripsop1')
output_op = op('output1')

tristripsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tristripsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **3** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
