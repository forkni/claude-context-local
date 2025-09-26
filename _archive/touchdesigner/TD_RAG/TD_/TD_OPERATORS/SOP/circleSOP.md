# SOP circleSOP

## Overview

The Circle SOP creates open or closed arcs, circles and ellipses.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type | Menu | For information on the different types, see the Primitive and Spline articles. Depending on the primitive type chosen, some SOP options may not apply. Using the 'Primitive' primitive type is not re... |
| `orient` | Orientation | Menu | The plane on which the circle lies. |
| `modifybounds` | Modify Bounds | Toggle | Available only when an input is connected to the Curcle SOP to set bounds for the sphere. When Modify Bounds = On the transform parameters below will further modify the radius and position of the b... |
| `rad` | Radius | XY | The Radius of the Circle in the X and Y directions. |
| `t` | Center | XYZ | The Center of the Circle in X, Y and Z. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `order` | Order | Int | If a spline curve is selected, it is built at this order. |
| `divs` | Divisions | Int | The number of edges (points +1) used to describe the circle. This option applies to polygons and imperfect splines. The more Divisions a circle has, the smoother it looks. Using three divisions mak... |
| `arc` | Arc Type | Menu | Determines how the circle should be drawn. Applies to polygons and imperfect splines only. |
| `angle` | Arc Angles | Float | The beginning and ending angles of the arc. An arc will start at the beginning angle, and proceed towards the ending angle. If beginning=0 and end=360 it will be a full circle. As a reference:     ... |
| `imperfect` | Imperfect | Toggle | This option applies only to Bezier and NURBS circles. If selected, the circles are approximated non-rational curves, otherwise they are perfect rational closed curves. |
| `texture` | Texture Coordinates | Menu | Option to include texture cooordinates or not. |
| `normals` | Compute Normals | Toggle | When On, normals are created for the surface. |

## Usage Examples

### Basic Usage

```python
# Access the SOP circleSOP operator
circlesop_op = op('circlesop1')

# Get/set parameters
freq_value = circlesop_op.par.active.eval()
circlesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
circlesop_op = op('circlesop1')
output_op = op('output1')

circlesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(circlesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
