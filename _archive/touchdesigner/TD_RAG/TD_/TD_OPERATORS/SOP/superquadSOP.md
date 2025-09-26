# SOP superquadSOP

## Overview

The Superquad SOP generates an isoquadric surface.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type | Menu | Select from the following types. For information on the different types, see the Primitive article. Depending on the primitive type chosen, some SOP options may not apply. |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh primitive type. |
| `modifybounds` | Modify Bounds | Toggle | Available only when an input is connected to the Superquad SOP to set bounds for the superquad. When Modify Bounds = On the transform parameters below will further modify the position and radius of... |
| `rad` | Radius | XYZ | Determines overall radius. |
| `t` | Center | XYZ | Offset of superquad center from object center. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `anchorw` | Anchor W | Float | Set the point in Z about which the geometry is positioned, scaled and rotated. |
| `orient` | Orientation | Menu | Determines pole axis for the iso surface. |
| `rows` | Rows | Int | Number of rows used in the superquad. |
| `cols` | Columns | Int | Number of columns used in the superquad. |
| `expxy` | XY Exponent | Float | The XY Exponent determines inflation / contraction in the X and Y axes. |
| `expz` | Z Exponent | Float | The Z Exponent determines inflation / contraction in the Z axis. See the Metaball SOP for a description of exponents. |
| `upole` | Multiple Points per Pole | Toggle | Determines whether points at the poles are shared or are unique to the columns. |
| `cusp` | Cusp Polygons | Toggle | Makes points unique, causing the superquad to be faceted. |
| `angle` | Cusp Angle | Float | Input angle in degrees to determine when vertices are shared or not, creating cusping. |
| `texture` | Texture Coordinates | Menu | Adds UV texture coordinates to the sphere. |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP superquadSOP operator
superquadsop_op = op('superquadsop1')

# Get/set parameters
freq_value = superquadsop_op.par.active.eval()
superquadsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
superquadsop_op = op('superquadsop1')
output_op = op('output1')

superquadsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(superquadsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
