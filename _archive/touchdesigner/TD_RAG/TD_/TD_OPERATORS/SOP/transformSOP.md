# SOP transformSOP

## Overview

The Transform SOP translates, rotates and scales the input geometry in "object space" or local to the SOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `xord` | Transform Order | Menu | Sets the overall transform order for the transformations. The transform order determines the order in which transformations take place. Depending on the order, you can achieve different results usi... |
| `rord` | Rotate Order | Menu | Sets the order of the rotations within the overall transform order. |
| `t` | Translate | XYZ | These three fields move the Source geometry in the three axes. |
| `r` | Rotate | XYZ | These three fields rotate the Source geometry in the three axes. |
| `s` | Scale | XYZ | These three fields scale the Source geometry in the three axes. |
| `p` | Pivot | XYZ | The pivot point for the transformations (not the same as the pivot point in the pivot channels). The pivot point parameters allow you to define the point about which geometry scales and rotates. Al... |
| `scale` | Uniform Scale | Float | Uniform Scale allows you to shrink or enlarge geometry along all three axes simultaneously. |
| `vlength` | Normals Maintain Length | Toggle | When selected, vector type attributes (i.e. normals, velocity) maintain the same length under transforms. i.e. When geometry is scaled, the normals remain constant in length. |
| `lookat` | Look At | Object | Allows you to orient your object by naming the object you would like it to Look At, or point to. Once you have designated this object to look at, it will continue to face that object, even if you m... |
| `upvector` | Up Vector | XYZ | When orienting an object, the Up Vector is used to determine where the positive Y axis points. |
| `forwarddir` | Forward Direction | Menu |  |
| `postxord` | Post Transform Order | Menu | Set the order in which scale and transform is applied in the post transform. |
| `posttx` | Post Translate X | Menu | Sets the center of the geometry after the Transform page has been applied. |
| `fromx` | From Input | Menu | Determines which part of the input geometry to align to the Origin or Reference Input as selected in Post Translate parameter above. |
| `tox` | To Reference | Menu | When using Reference Input this determines which part of the Reference Input to align the geometry to. |
| `postty` | Post Translate Y | Menu | Sets the center of the geometry after the Transform page has been applied. |
| `fromy` | From Input | Menu | Determines which part of the input geometry to align to the Origin or Reference Input as selected in Post Translate parameter above. |
| `toy` | To Reference | Menu | When using Reference Input this determines which part of the Reference Input to align the geometry to. |
| `posttz` | Post Translate Z | Menu | Sets the center of the geometry after the Transform page has been applied. |
| `fromz` | From Input | Menu | Determines which part of the input geometry to align to the Origin or Reference Input as selected in Post Translate parameter above. |
| `toz` | To Reference | Menu | When using Reference Input this determines which part of the Reference Input to align the geometry to. |
| `postscale` | Post Scale | Menu | Sets the scale of the geometry after the Transform page has been applied. |
| `postscalex` | Post Scale X | Menu | Sets the scale of the geometry after the Transform page has been applied to scale. |
| `postscaley` | Post Scale Y | Menu | Sets the scale of the geometry after the Transform page has been applied to scale. |
| `postscalez` | Post Scale Z | Menu | Sets the scale of the geometry after the Transform page has been applied to scale. |

## Usage Examples

### Basic Usage

```python
# Access the SOP transformSOP operator
transformsop_op = op('transformsop1')

# Get/set parameters
freq_value = transformsop_op.par.active.eval()
transformsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
transformsop_op = op('transformsop1')
output_op = op('output1')

transformsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(transformsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
