# SOP torusSOP

## Overview

The Torus SOP generates complete or specific sections of torus shapes (like a doughnut).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type | Menu | Select from the following types. For information on the different types, see the Geometry category articles. |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh primitive type. |
| `orient` | Orientation | Menu | The axis along which the torus is constructed. |
| `modifybounds` | Modify Bounds | Toggle | Enabled only when an input is connected to the Torus SOP to set bounds for the torus. Turn Modify Bounds = On to enable the transform parameters below to further modify the position and radius of t... |
| `rad` | Radius | XY | The first value (radx) defines the radius of the torus, the second value (rady) determines the radius of the inner ring.      Image:TouchGeometry256.gif |
| `t` | Center | XYZ | Offset of torus center from object origin. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `anchorw` | Anchor W | Float | Set the point in Z about which the geometry is positioned, scaled and rotated. |
| `rows` | Rows | Int | The rows define the number of divisions along the torus. |
| `cols` | Columns | Int | The columns determine the number of divisions along the torus' cross-section. |
| `angleoffset` | Angle Offset | Float | Rotates the torus along the minor radius.  For example, if using 4 rows set this value to 45 to create flat top + bottom surfaces. |
| `imperfect` | Imperfect | Toggle | This option applies only to Bezier and NURBS types. If selected, the tube is an approximated nonrational curve, otherwise it is a perfect rational curve. |
| `orderu` | U Order | Int | If a spline curve is selected, it is built at this order for U and V. |
| `orderv` | V Order | Int | If a spline curve is selected, it is built at this order for U and V. |
| `angleu` | U Angle | Float | The start and end sweep angles of the torus, if U Wrap is not enabled. |
| `anglev` | V Angle | Float | These are the start and end angles of the cross-section circle that is swept to make the torus, if V Wrap is not enabled. |
| `closeu` | U Wrap | Toggle | If U Wrap is checked, it creates a 360 cross-section. |
| `closev` | V Wrap | Toggle | Checking V Wrap creates a torus along V by closing the primitive. |
| `capu` | U End Caps | Toggle | If U End Caps is checked, it puts faceted end-caps on the ends of the torus if it is less than 360.      For more capping options, turn this parameter off, and append a Cap SOP. |
| `capv` | V End Caps | Toggle | If V End Caps is checked, it applies a face between the top and bottom of the torus - if the torus is open.      For more capping options, turn this parameter off, and append a Cap SOP. |
| `texture` | Texture Coordinates | Menu | This adds uv coordinates to the geometry created by the Torus SOP. |
| `normals` | Compute Normals | Toggle | Checking this option On will compute surface normals. |

## Usage Examples

### Basic Usage

```python
# Access the SOP torusSOP operator
torussop_op = op('torussop1')

# Get/set parameters
freq_value = torussop_op.par.active.eval()
torussop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
torussop_op = op('torussop1')
output_op = op('output1')

torussop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(torussop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
