# SOP boxSOP

## Overview

The Box SOP creates cuboids.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `orientbounds` | Orient Bounds | Toggle | Available only when an input is connected to the Box SOP to set bounds for the box. When Orient Bounds = On it will rotate the geometry to match the orientation of the input SOP used for bounds. |
| `modifybounds` | Modify Bounds | Toggle | Available only when an input is connected to the Box SOP to set bounds for the box. When Modify Bounds = On to enable the transform parameters below to further modify the position and scale of the ... |
| `rord` | Rotate Order | Menu | Sets the order in which the rotations are applied. |
| `size` | Size | XYZ | Size of the Box or Cube along the X, Y, and Z axes. |
| `t` | Center | XYZ | These X,Y, and Z Values determine where the center of the Box is located. |
| `r` | Rotate | XYZ | These three fields rotate the Box along the X, Y, and Z axes. |
| `s` | Scale | Float | Adjusts the uniform scale of the box. |
| `reverseanchors` | Reverse Anchors | Toggle | Invert the direction of anchors. |
| `anchoru` | Anchor U | Float | Set the point in X about which the geometry is positioned, scaled and rotated. |
| `anchorv` | Anchor V | Float | Set the point in Y about which the geometry is positioned, scaled and rotated. |
| `anchorw` | Anchor W | Float | Set the point in Z about which the geometry is positioned, scaled and rotated. |
| `dodivs` | Use Divisions | Toggle | If checked, it divides the box into the number of Divisions specified below. Boxes divided in this way do not appear when rendered because the Divisions consist of open polygons. |
| `divs` | Divisions | Int | The number of divisions in X, Y, and Z to split this Box into. |
| `rebar` | Enforcement Bars | Toggle | Places four diagonal crossbars in each division of the Box. |
| `consolidatepts` | Consolidate Corner Points | Toggle | Merges the corner points together.  Instead of the box being composed of 6 separate faces (resulting in 4 points per corner and a total of 24 points), the corner points are merged together and the ... |
| `texture` | Texture Coordinates | Menu | Determines how the texture coordinates are applied to the box. |
| `normals` | Compute Normals | Toggle | Checking this option on will compute surface normals. |

## Usage Examples

### Basic Usage

```python
# Access the SOP boxSOP operator
boxsop_op = op('boxsop1')

# Get/set parameters
freq_value = boxsop_op.par.active.eval()
boxsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
boxsop_op = op('boxsop1')
output_op = op('output1')

boxsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(boxsop_op)
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
