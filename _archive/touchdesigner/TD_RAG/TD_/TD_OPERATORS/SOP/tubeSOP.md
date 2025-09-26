# SOP tubeSOP

## Overview

The Tube SOP generates open or closed tubes, cones, or pyramids along the X, Y or Z axes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type | Menu | Select from the following types. For information on the different types, see the Geometry category articles. Using the 'Primitive' primitive type is not recommended when using instancing. |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh Primitive Type. |
| `orient` | Orientation | Menu | Primary axis of tube (long axis). |
| `orientbounds` | Orient Bounds | Toggle | Available only when an input is connected to the Tube SOP to set bounds for the tube. When Orient Bounds = On it will rotate the geometry to match the orientation of the input SOP used for bounds. |
| `modifybounds` | Modify Bounds | Toggle | Enabled only when an input is connected to the Tube SOP to set bounds for the tube. Turn Modify Bounds = On to enable the transform parameters below to further modify the position, scale, radius an... |
| `rord` | Rotate Order | Menu | Sets the order in which the rotations are applied. |
| `t` | Center | XYZ | Location of the tube center from the object origin. |
| `r` | Rotate | XYZ | These three fields rotate the Tube along the X, Y, and Z axes. |
| `rad` | Radius | Float | The first field is the radius of the top of the tube and the second field represents the radius of the bottom of the tube. |
| `height` | Height | Float | The height of the tube. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `anchorw` | Anchor W | Float | Set the point in Z about which the geometry is positioned, scaled and rotated. |
| `imperfect` | Imperfect | Toggle | This option applies only to Bezier and NURBS types. If selected, the tube is an approximated nonrational curve, otherwise it is a perfect rational curve. |
| `rows` | Rows | Int | Number of rows in tube. |
| `cols` | Columns | Int | Number of columns in tube. |
| `orderu` | U Order | Int | If a spline surface is selected, it is built at this order for U. |
| `orderv` | V Order | Int | If a spline surface is selected, it is built at this order for V. |
| `cap` | End Caps | Toggle | If selected, it adds faceted end caps to the ends of the tube. |
| `texture` | Texture Coordinates | Menu | Adds UV texture coordinates to the sphere. |
| `normals` | Compute Normals | Toggle | Checking this option On will compute surface normals. |

## Usage Examples

### Basic Usage

```python
# Access the SOP tubeSOP operator
tubesop_op = op('tubesop1')

# Get/set parameters
freq_value = tubesop_op.par.active.eval()
tubesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tubesop_op = op('tubesop1')
output_op = op('output1')

tubesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tubesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
