# SOP divideSOP

## Overview

The Divide SOP divides incoming polygonal geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `convex` | Convex Polygons | Toggle | When checked, this option will convex all incoming polygons to the maximum number of sides as specified in the field below. This is useful for reducing the number of sides of polygons that are conc... |
| `numsides` | Maximum Edges | Int | Input value determines the maximum number of edges that all of the input polygons will be reduced to if they exceed this number. Sets the maximum number of sides for convexed polygons. There must b... |
| `planar` | Triangulate Non-Planar | Toggle | Triangulates any non-planar polygons. |
| `smooth` | Smooth Polygons | Toggle | If checked, this feature will divide the polygons which are adjacent to each other and are not flat, as in the corners of a box. The threshold of the smoothing and the amount of polygon divisions t... |
| `weight` | Weight | Float | Determines the localization effect of the added polygons. You can isolate the divisions to where there are edges in the geometry with values greater than 1 enhancing the edges by smoothing out the ... |
| `divs` | Divisions | Int | Determine the level of sub-divisions for the Smooth Polygons option. A value of 1 doubles the number of polygons at the corners, a value of 2 will add twice as much sub-division. Values of 3 and gr... |
| `brick` | Bricker Polygons | Toggle | Selecting this option divides the input polygon geometry into grid-like squares, though the output is not a mesh. Brickering creates new polygons. It can be used to divide a surface so that it defo... |
| `size` | Size | XYZ | Sets the size of the bricker grid divisions in each of the three axes. |
| `offset` | Offset | XYZ | Sets the XYZ offset of the grid divisions to the Source geometry (the Brickering Grid is moved). |
| `angle` | Angle | XYZ | Determines the angle relative to XYZ axes, at which Bricker Polygons are created. |
| `removesh` | Remove Shared Edges | Toggle | Eliminates any common edges. |
| `dual` | Compute Dual | Toggle | Convert the polyhedron into its point/face dual.Convert the polyhedron into its point/face dual. |

## Usage Examples

### Basic Usage

```python
# Access the SOP divideSOP operator
dividesop_op = op('dividesop1')

# Get/set parameters
freq_value = dividesop_op.par.active.eval()
dividesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
dividesop_op = op('dividesop1')
output_op = op('output1')

dividesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(dividesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
