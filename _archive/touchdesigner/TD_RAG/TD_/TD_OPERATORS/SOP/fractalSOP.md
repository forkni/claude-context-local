# SOP fractalSOP

## Overview

The Fractal SOP allows you created jagged mountain-like divisions of the input geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `divs` | Divisions | Int | The number of subdivisions of the input geometry. Values in the range of 1 - 3 are reasonable to start with. Higher values cause excessive geometry and should be used with caution. |
| `smooth` | Smoothness | Float | The smoothness value scales the deviations. The range is usually between 0 and 1, and small numbers create larger deviations than large numbers. Smoothness and Scale have a similar effect, but ther... |
| `scale` | Scale | Float | Global setting of the fractal divisions. See the above discussion about Smoothness vs. Scale. |
| `seed` | Seed | Int | The random seed used for fractalising. Specifying a different integer value gives a different shape. |
| `fixed` | Fixed Boundary | Toggle | When enabled, this option prevents Fractal from applying any deviations to the edges (boundaries) so that you could, for example, fractalise a plane and still be able to connect the edges of the pl... |
| `vtxnms` | Use Vertex Normals | Toggle | Instead of using the Direction fields below, this sets the direction of the fractalisation at any given point to be the direction of the vertex normals of the input. This may be preferable when usi... |
| `dir` | Direction | XYZ | The direction of the Fractalisation. The default values of 0, 0, 1 make the fractal deviations point in the Z direction. Can be overridden by: Use Vertex Normals. |

## Usage Examples

### Basic Usage

```python
# Access the SOP fractalSOP operator
fractalsop_op = op('fractalsop1')

# Get/set parameters
freq_value = fractalsop_op.par.active.eval()
fractalsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fractalsop_op = op('fractalsop1')
output_op = op('output1')

fractalsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fractalsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **8** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
