# SOP textureSOP

## Overview

The Texture SOP assigns texture UV and W coordinates to the Source geometry for use in texture and bump mapping.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Primitive Group | StrMenu | If there are input primitive groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Does not work with point or vertex groups. Accepts patterns, as ... |
| `texlayer` | Texture Layer | Int | If the geometry has multiple textures layers applied to it, this parameter determines which layer of UV coordinates this Texture SOP will effect. |
| `type` | Texture Type | Menu | The Face, Uniform Spline, and Arc-Length Spline texturing methods accept spline curves as well as polygons.      When using one of the spline-based methods, specifying a paste hierarchy in the Grou... |
| `axis` | Projection Axis | Menu | Axis to project along, or projection method from splines. X, Y, or Z axes. |
| `camera` | Camera Name | Object | This is used when the Perspective From Camera Texture Type is selected. The menu is used to select which light or camera to project the perspective coordinates from. |
| `coord` | Apply to | Menu | Select to apply texture coordinates to their Natural Location, Point textures, or Vertex textures.      When Natural location is selected, the UV's will be applied to the verticies when using Polar... |
| `s` | Scale | UVW | Scales the texture coordinates a specific amount. |
| `offset` | Offset | UVW | Offsets the texture coordinates a specific amount. |
| `angle` | Rotate | Float | Rotates the texture coordinates the specified value.      Tip: Before applying a spline-based texture projection with the Texture SOP, remap the U and/or V bases of the spline surface (using a Basi... |
| `fixseams` | Fix Face Seams | Toggle | Attempts to correct texture continuity at face seams. |
| `xord` | Transform Order | Menu | Sets the overall transform order for the transformations. The transform order determines the order in which transformations take place. Depending on the order, you can achieve different results usi... |
| `rord` | Rotate Order | Menu | Sets the order of the rotations within the overall transform order. |
| `t` | Translate | XYZ | These three fields move the texture coordinates in the three axes. |
| `r` | Rotate | XYZ | These three fields rotate the texture coordinates in the three axes. |
| `scaletwo` | Scale | XYZ | These three fields scale the texture coordinates in the three axes. |
| `p` | Pivot | XYZ | The pivot point for the transformations (not the same as the pivot point in the pivot channels). The pivot point parameters allow you to define the point about which the texture coordinates scale a... |

## Usage Examples

### Basic Usage

```python
# Access the SOP textureSOP operator
texturesop_op = op('texturesop1')

# Get/set parameters
freq_value = texturesop_op.par.active.eval()
texturesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
texturesop_op = op('texturesop1')
output_op = op('output1')

texturesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(texturesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
