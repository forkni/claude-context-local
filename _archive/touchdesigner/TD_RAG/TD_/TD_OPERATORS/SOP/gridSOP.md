# SOP gridSOP

## Overview

The Grid SOP allows you to create grids and rectangles using polygons, a mesh, Bzier and NURBS surfaces, or multiple lines using open polygons.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type | Menu | Select from the following types. For information on the different types, see the Geometry Types section. Depending on the primitive type chosen, some SOP options may not apply. |
| `surftype` | Connectivity | Menu | (Results only viewable for polygons and meshes). |
| `orient` | Orientation | Menu | Specifies on which plane the Grid is built. |
| `modifybounds` | Modify Bounds | Toggle | Enabled only when an input is connected to the Grid SOP to set bounds for the grid. Turn Modify Bounds = On to enable the transform parameters below to further modify the position and scale of the ... |
| `size` | Size | XY | The X and Y scale of the grid. |
| `t` | Center | XYZ | Center of grid in X, Y, and Z. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `rows` | Rows | Int | The number of rows and columns. Rows are horizontal lines; Columns are vertical lines. Two rows by two columns makes a square or rectangle. For example, one row and two columns makes a single line ... |
| `cols` | Columns | Int | The number of rows and columns. Rows are horizontal lines; Columns are vertical lines. Two rows by two columns makes a square or rectangle. For example, one row and two columns makes a single line ... |
| `orderu` | U Order | Int | U Order Degree of spline basis +1 in the U parametric direction. |
| `orderv` | V Order | Int | V Order Degree of spline basis +1 in the V parametric direction. |
| `interpu` | End Point Interpolate in U | Toggle | End-point interpolate in U Extends the surface to touch the end point in the U direction. |
| `interpv` | End Point Interpolate in V | Toggle | End-point interpolate in V Extends the surface to touch the end point in the V direction. |
| `texture` | Texture Coordinates | Menu | This adds uv coordinates to the geometry created by the Grid SOP. |
| `normals` | Compute Normals | Toggle | Checking this option On will compute surface normals. |

## Usage Examples

### Basic Usage

```python
# Access the SOP gridSOP operator
gridsop_op = op('gridsop1')

# Get/set parameters
freq_value = gridsop_op.par.active.eval()
gridsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
gridsop_op = op('gridsop1')
output_op = op('output1')

gridsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(gridsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
