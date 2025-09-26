# SOP primitiveSOP

## Overview

The Primitive SOP is like the Point SOP but manipulates a primitive's position, size, orientation, color, alpha, in addition to primitive-specific attributes, such as reversing primitive normals.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Source Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. You can specify profile curves within the group by providing a profile pat... |
| `templategrp` | Template Group | StrMenu | A subset of template points to transform to. |
| `doxform` | Do Transformation | Toggle | When checked, allows transformations to occur. |
| `dorot` | Rotate to Template | Menu | A template can be specified using the second input of the Primitive SOP. When set to On, this template can be used to transform each primitive to the location and orientation of the template point.... |
| `xord` | Transform Order | Menu | Sets the overall transform order for the transformations. The transform order determines the order in which transformations take place. Depending on the order, you can achieve different results usi... |
| `rord` | Rotate Order | Menu | Sets the order of the rotations within the overall transform order. |
| `t` | Translate | XYZ | These three fields move the input geometry in the three axes. Profiles use tx and ty only. |
| `r` | Rotate | XYZ | These three fields rotate the Source geometry in the three axes. Profiles use rz only. |
| `s` | Scale | XYZ | These three fields scale the Source geometry in the three axes. Profiles use sx and sy only. |
| `p` | Pivot | XYZ | The pivot point for the transformations. Profiles use px and py only. |
| `lookat` | Lookat Object | OBJ | Selects the object the primitive should point towards. This performs the lookat in object space; if you need to a lookat in world space, use the lookat in the object's Transform page instead.      ... |
| `upvector` | Up-Vector | XYZ | Defines the orientation of the primitive along the X, Y, or Z axes.      The Up Vector determines how a primitive orients itself with respect to the target object (specified in Lookat Object). The ... |
| `doclr` | Color | Menu | If Keep is selected, the color attribute is left unchanged. If Add is selected, this parameter changes the color of input primitives according to diffuse color field. If No is selected, the color a... |
| `diff` | Color | RGB | The color to add. |
| `alpha` | Alpha | Float | The alpha value to add. |
| `docrease` | Crease | Menu | If Keep is selected, the crease attribute is left unchanged. If Add is selected, this parameter generates a crease attribute for the primitive. If No is selected, the crease attribute is removed. |
| `crease` | Crease | Float | Attribute is used to set edge crease weights for subdivision surfaces (see Subdivide SOP). The Crease Weight attribute for a primitive sets all edges of the polygon to the value specified. On share... |
| `attr` | Custom Attrib | Sequence | Sequence of custom attributes to be added to the geometry created. |
| `pshapeu` | Preserve Shape U | Toggle | These options only become available once a type of clamping or closure has been selected.      Closure - Change the closure and clamping of a face or hull. |
| `pshapev` | Preserve Shape V | Toggle | These options only become available once a type of clamping or closure has been selected.      Closure - Change the closure and clamping of a face or hull. The options are: |
| `closeu` | Close U | Menu | Close the primitive in U / V. Select from: Open, Closed Straight, Close Rounded, and Unroll. When you unroll a closed curve you duplicate the wrapped points (you make them unique) and turn the curv... |
| `closev` | Close V | Menu | Close the primitive in U / V. Select from: Open, Closed Straight, Close Rounded, and Unroll. When you unroll a closed curve you duplicate the wrapped points (you make them unique) and turn the curv... |
| `clampu` | Clamp U | Menu | Clamp the primitive in U / V. Select from: Clamp, Unclamp. |
| `clampv` | Clamp V | Menu | Clamp the primitive in U / V. Select from: Clamp, Unclamp. |
| `vtxsort` | Vertex | Menu | Reorder the vertices in a number of ways. |
| `vtxuoff` | U Offset | Int | Cycles face or hull columns / rows when the Shift operation is selected. |
| `vtxvoff` | V Offset | Int | Cycles face or hull columns / rows when the Shift operation is selected. |
| `metaweight` | Meta-Surface Weight | Toggle | When selected, allows meta-surface weighting. |
| `doweight` | Weight | Float | Enter weight of meta-surface here when Meta-surface Weight is selected. |
| `doprender` | Particle Render Type | Toggle | When On the Particle Type menu below allows section of particle render type. |
| `prtype` | Particle Type | Menu | Selects how the particles are rendered. |

## Usage Examples

### Basic Usage

```python
# Access the SOP primitiveSOP operator
primitivesop_op = op('primitivesop1')

# Get/set parameters
freq_value = primitivesop_op.par.active.eval()
primitivesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
primitivesop_op = op('primitivesop1')
output_op = op('output1')

primitivesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(primitivesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
