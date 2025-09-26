# SOP revolveSOP

## Overview

The Revolve SOP revolves faces to create a surface of revolution.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh Primitive Type. |
| `origin` | Origin | XYZ | Coordinates defining the origin of the revolution. |
| `dir` | Direction | XYZ | X, Y, and Z coordinates of the direction vector defining the direction of the revolve. |
| `polys` | Convert Mesh to Polygons | Toggle | Changes the output mesh to consist of individual polygons. |
| `imperfect` | Imperfect | Toggle | Applies to splines only. If selected, the results are approximated nonrational curves, otherwise they are perfect rational curves. |
| `type` | Revolve Type | Menu | Determines how the revolve should be generated. |
| `angle` | Start End Angles | Float | The start and end angles of the revolve. A revolve will start at the beginning angle, and proceed towards the ending angle. If Beginning = 0 and End = 360 it will be fully revolved. Values greater ... |
| `divs` | Divisions | Int | Density of the resulting mesh surface. |
| `order` | Order | Int | If a spline type is selected, it is built at this order. |
| `cap` | End Caps | Toggle | If selected, it adds faceted end caps. |

## Usage Examples

### Basic Usage

```python
# Access the SOP revolveSOP operator
revolvesop_op = op('revolvesop1')

# Get/set parameters
freq_value = revolvesop_op.par.active.eval()
revolvesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
revolvesop_op = op('revolvesop1')
output_op = op('output1')

revolvesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(revolvesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
