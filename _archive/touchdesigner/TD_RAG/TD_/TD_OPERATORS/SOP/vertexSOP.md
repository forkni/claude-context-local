# SOP vertexSOP

## Overview

The Vertex SOP allows you to edit/create attributes on a per-vertex (rather than per-point) basis.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `doclr` | Color | Menu | Select between keeping the color, adding new color, or using no color for vertex color attributes from incoming geometry. |
| `diff` | Color | RGB | If you select 'Add Color' from the menu above, Cd color vertex attributes will be added/modified in the SOP. Enter expressions below to control the values of the point colors. The attributes to mod... |
| `alpha` | Alpha | Float | Control the alpha attribute in the same manner as the rgb colors above. Alpha is Cd[3] and comes from input via me.inputColor[3] |
| `douvw` | Texture | Menu | Select between keeping the texture coordinates, adding new texture coordinates, or using no texture coordinates for the vertex texture attributes from incoming geometry. |
| `map` | Texture | UVW | If you select 'Add Texture' from the menu above, uv texture coordinate vertex attributes will be added/modified in the SOP. Enter expressions here to control the values of the vertex texture coordi... |
| `docrease` | Crease | Menu | Select between keeping the crease, adding new crease, or using no crease for creaseweight attribute from incoming geometry.     The Crease Weight attribute can be used to set individual edge crease... |
| `crease` | Crease | Float | If you select 'Add Crease' from the menu above, enter expressions here to control the values of the creaseweights here. The attribute to modify is: me.inputVertex.creaseWeight[0]. Values for the we... |
| `attr` | Custom Attribute | Sequence | Sequence of custom attributes to be added to the geometry created. |

## Usage Examples

### Basic Usage

```python
# Access the SOP vertexSOP operator
vertexsop_op = op('vertexsop1')

# Get/set parameters
freq_value = vertexsop_op.par.active.eval()
vertexsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
vertexsop_op = op('vertexsop1')
output_op = op('output1')

vertexsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(vertexsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
