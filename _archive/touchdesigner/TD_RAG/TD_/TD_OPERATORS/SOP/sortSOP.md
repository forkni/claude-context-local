# SOP sortSOP

## Overview

The Sort SOP allows you to sort points and primitives in different ways.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `ptsort` | Point Sort | Menu | Sort the points in the input geometry, according to the following criteria: |
| `pointseed` | Seed | Int | The random seed when Point Sort is set to Random. |
| `pointoffset` | Offset | Int | Shift point order by the amount specified on the offset line. |
| `pointprox` | Point | XYZ | The X, Y and Z coordinates to reference when sorting by Proximity to Point. |
| `pointobj` | Vector Object | Object | Sort points along a vector defined by the object's transformation values. |
| `pointdir` | Vector | XYZ | Allows you to specify a unique vector along which points can be sorted. |
| `primsort` | Primitive Sort | Menu | Sort the primitives according to the following criteria: |
| `primseed` | Seed | Int | Random seed when sorting by Random. |
| `primoffset` | Offset | Int | Shift primitive order by the amount specified on the offset line. |
| `primprox` | Point | XYZ | The X, Y and Z coordinates to reference when sorting by Proximity to Point. |
| `primobj` | Vector Object | Object | Sort primitives along a vector defined by the object's translation. |
| `primdir` | Vector | XYZ | Allows you to specify a unique vector along which primitives can be sorted. |
| `partsort` | Particle Sort | Menu | Sort the primitives according to the following criteria: |
| `partreverse` | Reverse Results | Toggle | Reverses the result from the Particle Sort as defined above. |
| `partoffset` | Offset | Int | Shift particle order by the amount specified on the offset line. |
| `partprox` | Point | XYZ | The X, Y and Z coordinates to reference when sorting by Proximity to Point. |
| `partobj` | Vector Object | Object | Sort particles along a vector defined by the object's translation. |
| `partdir` | Vector | XYZ | Allows you to specify a unique vector along which particles can be sorted. |

## Usage Examples

### Basic Usage

```python
# Access the SOP sortSOP operator
sortsop_op = op('sortsop1')

# Get/set parameters
freq_value = sortsop_op.par.active.eval()
sortsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
sortsop_op = op('sortsop1')
output_op = op('output1')

sortsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(sortsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **18** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
