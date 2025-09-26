# SOP copySOP

## Overview

The Copy SOP lets you make copies of the geometry of other SOPs and apply a transformation to each copy.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sourcegrp` | Source Group | StrMenu | Specifies a subset of input primitives to copy from. Accepts patterns, as described in Pattern Matching. |
| `templategrp` | Template Group | StrMenu | Specifies a subset of template primitives from which to copy onto. Accepts patterns, as described in Pattern Matching. |
| `ncy` | Number of Copies | Int | Sets number of Copies to be made of the source. For a template input, it specifies the number of copies to be placed at each point of the template. |
| `nprims` | Primitives per Point | Int | Defines how many primitives to copy from each point. |
| `nml` | Rotate to Normal | Toggle | Only used when a template input is specified. If the template is a sphere, and the first input is a circle, a circle is placed at each point of the sphere. With this option on, all the circles will... |
| `cum` | Transform Cumulative | Toggle | Each transformation "builds" on the location left by the one before it. Transformations are cumulative as the Copy SOP produces new copies. |
| `xord` | Transform Order | Menu | Sets the overall transform order for the transformations. The Transform Order determines the order in which transformations take place. Depending on the order, you can achieve different results usi... |
| `rord` | Rotate Order | Menu | Sets the order of the rotations within the overall transform order. |
| `t` | Translate | XYZ | These allow you to specify the Translation (how much it moves over in a given direction), Rotation, and the Scale between each copy. Three columns are given for X, Y, and Z coordinates. Guide geome... |
| `r` | Rotate | XYZ | These allow you to specify the Translation (how much it moves over in a given direction), Rotation, and the Scale between each copy. Three columns are given for X, Y, and Z coordinates. Guide geome... |
| `s` | Scale | XYZ | These allow you to specify the Translation (how much it moves over in a given direction), Rotation, and the Scale between each copy. Three columns are given for X, Y, and Z coordinates. Guide geome... |
| `p` | Pivot | XYZ | These allow you to specify the Translation (how much it moves over in a given direction), Rotation, and the Scale between each copy. Three columns are given for X, Y, and Z coordinates. Guide geome... |
| `scale` | Uniform Scale | Float | Uniform Scale allows you to shrink or enlarge geometry along all three axes simultaneously. |
| `vlength` | Normals Maintain Length | Toggle | Vector type attributes (i.e. normals, velocity) maintain the same length under transforms. i.e. When geometry is scaled, the normals remain constant in length. |
| `newg` | Create Output Groups | Toggle | If selected, this creates a group for each copy number, and places each primitive created at that stage into it. |
| `copyg` | Copy Groups | Str | Defines the base name of the groups created. |
| `lookat` | Look At | OBJ | Orients the copied geometry to lookat, or point to, the object component specified in the parameter. |
| `upvector` | Up Vector | XYZ | When specifying a Look At, it is possible to specify an up vector for the lookat. Without using an up vector, it is possible to get poor animation when the lookat object passes through the Y axis o... |
| `stamp` | Stamp Inputs | Toggle | When enabled, it will Stamp proceeding variables for each input copied. |
| `copy` | Copy | Sequence | Sequence of stamp variables |
| `doattr` | Use Template Point Attribs | Toggle | Enables the parameters below to allow template point attributes to be applied to the copied source geometry. |
| `setpt` | Copy to Point | StrMenu | Copy the attributes to the source geometry's points. |
| `setprim` | Copy to Primitive | StrMenu | Copy the attributes to the source geometry's primitives. |
| `setvtx` | Copy to Vertex | StrMenu | Copy the attributes to the source geometry's vertices. |
| `mulpt` | Multiply Point | StrMenu | Multiply the attributes with the source geometry's point attributes. |
| `mulprim` | Multiply Primitive | StrMenu | Multiply the attributes with the source geometry's primitive attributes. |
| `mulvtx` | Multiply Vertex | StrMenu | Multiply the attributes with the source geometry's vertex attributes. |
| `addpt` | Add Point | StrMenu | Add the attributes to the source geometry's point attributes. |
| `addprim` | Add Primitive | StrMenu | Add the attributes to the source geometry's primitive attributes. |
| `addvtx` | Add Vertex | StrMenu | Add the attributes to the source geometry's vertex attributes. |
| `subpt` | Subtract Point | StrMenu | Subtract the attributes from the source geometry's point attributes. |
| `subprim` | Subtract Primitive | StrMenu | Subtract the attributes from the source geometry's primitive attributes. |
| `subvtx` | Subtract Vertex | StrMenu | Subtract the attributes from the source geometry's vertex attributes. |

## Usage Examples

### Basic Usage

```python
# Access the SOP copySOP operator
copysop_op = op('copysop1')

# Get/set parameters
freq_value = copysop_op.par.active.eval()
copysop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
copysop_op = op('copysop1')
output_op = op('output1')

copysop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(copysop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
