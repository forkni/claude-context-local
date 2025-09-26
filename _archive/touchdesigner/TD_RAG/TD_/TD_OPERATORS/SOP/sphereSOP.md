# SOP sphereSOP

## Overview

The Sphere SOP generates spherical objects of different geometry types.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type | Menu | Select from the following types. For information on the different types, see the Geometry category articles. Depending on the primitive type chosen, some SOP options may not apply. Using the 'Primi... |
| `surftype` | Connectivity | Menu | This option is used to select the type of surface, when using a Mesh Primitive Type. |
| `orientbounds` | Orient Bounds | Toggle | Available only when an input is connected to the Sphere SOP to set bounds for the sphere. When Orient Bounds = On it will rotate the geometry to match the orientation of the input SOP used for bounds. |
| `modifybounds` | Modify Bounds | Toggle | Available only when an input is connected to the Sphere SOP to set bounds for the sphere. When Modify Bounds = On the transform parameters below will further modify the rotation, position, and radi... |
| `rord` | Rotate Order | Menu | Sets the order in which the rotations are applied. |
| `rad` | Radius | XYZ | The radius of the sphere in X, Y and Z. |
| `t` | Center | XYZ | Offset of sphere center from object center. |
| `r` | Rotate | XYZ | These three fields rotate the Sphere along the X, Y, and Z axes. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `anchorw` | Anchor W | Float | Set the point in Z about which the geometry is positioned, scaled and rotated. |
| `orient` | Orientation | Menu | Determines axis for sphere. Poles of sphere align with orientation axis. |
| `freq` | Frequency | Int | This controls the level of polygons used to create the sphere, when using the Polygon Primitive Type. |
| `rows` | Rows | Int | Number of rows in a sphere when using the mesh, imperfect NURBS and imperfect Bzier. |
| `cols` | Columns | Int | Number of columns in a sphere when using the mesh, imperfect NURBS and imperfect Bzier. |
| `orderu` | U Order | Int | If a spline curve is selected, it is built at this order for U. |
| `orderv` | V Order | Int | If a spline curve is selected, it is built at this order for V. |
| `imperfect` | Imperfect | Toggle | This option applies only to Bzier and NURBS spheres. If selected, the spheres are approximated nonrational curves, otherwise they are perfect rational curves. |
| `upole` | Unique Points per Pole | Toggle | Applies to Mesh, NURBS and Bzier surfaces only. This option determines whether points at the poles are shared or are individual to the columns. |
| `accurate` | Accurate Bounds |  | If the SOP is being used to generate a bounding sphere for it's input geometry, this parameter tells the SOP to use a more accurate (but slower) bounding sphere calculation. |
| `texture` | Texture Coordinates | Menu | Adds UV texture coordinates to the sphere. |
| `normals` | Compute Normals | Toggle | Creates normals on the geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP sphereSOP operator
spheresop_op = op('spheresop1')

# Get/set parameters
freq_value = spheresop_op.par.active.eval()
spheresop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
spheresop_op = op('spheresop1')
output_op = op('output1')

spheresop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(spheresop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
