# SOP pointSOP

## Overview

The Point SOP allows you to get right down into the geometry and manipulate the position, color, texture coordinates, and normals of the points in the Source, and other attributes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `t` | Position | XYZ | Expressions to translate the XYZ coordinates of a given point can be entered here. The attributes to modify here are: me.inputPoint.x, me.inputPoint.y and me.inputPoint.z.      Simply entering me.i... |
| `doweight` | Weight | Menu | Select between keeping the weight or adding a new weight. |
| `weight` | Weight | Float | If you select 'New Weight' from the menu above, enter expressions here to control the values of the point weights here. The attribute to modify is: me.inputPoint.w. Values for the weight of the poi... |
| `doclr` | Color | Menu | Select between keeping the color, adding new color, or using no color. |
| `diff` | Color | RGB | If you select 'Add Color' from the menu above, Cd color attributes will be added/modified in the SOP. Enter expressions below to control the values of the point colors. The attributes to modify are... |
| `alpha` | Alpha | Float | Control the alpha attribute in the same manner as the rgb colors above. Alpha is Cd[3] and comes from input via me.inputColor[3] |
| `donml` | Normal | Menu | Select between keeping the normals, adding new normals, or using no normals. |
| `n` | Normals | XYZ | If you select 'Add Normal' from the menu above, N normal attributes will be added/modified in the SOP. Enter expressions to change a given point normal here. Point normals are directional vectors u... |
| `douvw` | Texture | Menu | Select between keeping the texture coordinates, adding new texture coordinates, or using no texture coordinates. |
| `map` | Texture | UVW | If you select 'Add Texture' from the menu above, uv texture coordinate attributes will be added/modified in the SOP. Enter expressions here to control the values of the texture coordinates here. Th... |
| `dowidth` | Width(Line MAT) | Menu | Select between keeping the width attribute or adding a new width. This Width (width) attribute is used exclusively with Line MAT to control line width when the material is rendered. |
| `width` | Width(Line MAT) | Float | If you select 'New Width' from the menu above, width attribute will be added/modified in the SOP. Enter expressions here to control the values of the point widths here. The attribute to modify is: ... |
| `dopscale` | Scale | Menu | Select between keeping the scale attribute, adding new scale, or using no scale. This scale (pscale) attribute is used with the Particle SOP and acts as a multiplier for the size of particles. The ... |
| `pscale` | Scale | Float | If you select 'Add Scale' from the menu above, pscale attribute will be added/modified in the SOP. Enter expressions here to control the values of the point particle scales here. The attribute to m... |
| `attr` | Custom Attribute | Sequence | Sequence of custom attributes to add |
| `domass` | Point Mass/Drag | Menu | Retains, adds, or removes mass and drag attributes for points. |
| `mass` | Mass | Float | If you select 'Add Mass/Drag' from the menu above, mass attribute will be added/modified in the SOP. If you select 'No Mass/Drag' from the menu above, the mass attribute will be removed from the SOP. |
| `drag` | Drag | Float | If you select 'Add Mass/Drag' from the menu above, drag attribute will be added/modified in the SOP. If you select 'No Mass/Drag' from the menu above, the drag attribute will be removed from the SOP. |
| `dotension` | Tension | Menu | Tension affects the elasticity of the edges the point is connected to. |
| `tension` | Tension | Float | If you select 'Add Tension' from the menu above, tension attribute will be added/modified in the SOP. Enter expressions here to control the values of the tension here. The attribute to modify is: m... |
| `dospringk` | Spring K | Menu | Retains, adds, or removes spring constant attributes for points. The Spring Constant is a well known physical property affecting each point. |
| `springk` | Spring K | Float | If you select 'Add Spring K' from the menu above, springk attribute will be added/modified in the SOP. Enter expressions here to control the values of the springk here. The attribute to modify is: ... |
| `dovel` | Velocity | Menu | Retains, adds, or removes the velocity of points. Defines the magnitude of the particle's velocity in the X, Y and Z directions. |
| `v` | Velocity | XYZ | If you select 'Add Velocity' from the menu above, v velocity attributes will be added/modified in the SOP. Enter expressions to change a given point velocity here. The attributes to modify here are... |
| `doup` | Up Vector | Menu | Creates/Removes the "up" attribute for points. This attribute defines an up vector which is used to fully define the space around a point (for particle instancing or copying geometry). The up vecto... |
| `up` | Up Vector | XYZ | If you select 'Add Up Vector' from the menu above, up attributes will be added/modified in the SOP. Enter expressions to change a given point up vector here. The attributes to modify here are: me.i... |
| `doradius` | Radius | Menu | Retains, adds, or removes radiusf attributes for points, used to modify the distance roll-off effect. The roll-off is: r /(r+d^2) Where r is radius, and d is distance from attractor point. If no ra... |
| `radiusf` | Radius | Float | If you select 'Add Radius' from the menu above, radiusf attribute will be added/modified in the SOP. Enter expressions here to control the values of the distance roll-off here. If you select 'No Ra... |
| `doscale` | F Scale | Menu | Retains, adds, or removes scalef attributes for points, a multiplier for total force associated with this attractor point.      Both Radius and Force Scale will default to 1 if not created as point... |
| `scalef` | F Scale | Float | If you select 'Add F Scale' from the menu above, scalef attribute will be added/modified in the SOP. Enter expressions here to control the values of the force multiplier here. If you select 'No F s... |
| `doradialf` | Radial F | Menu | Retains, adds, or removes radialf attributes for points, the force directed towards the attractor point. Positive multipliers are towards while negative are away. |
| `radialf` | Radial F | Float | If you select 'Add Radial F' from the menu above, radialf attribute will be added/modified in the SOP. Enter expressions here to control the values of the directed force here. If you select 'No Rad... |
| `donormalf` | Normal F | Menu | Retains, adds, or removes normalf attributes for points, the force directed along the point normal direction. |
| `normalf` | Normal F | Float | If you select 'Add Normal F' from the menu above, normalf attribute will be added/modified in the SOP. Enter expressions here to control the values of the force in the normal direction here. If you... |
| `doedgef` | Edge F | Menu | Retains, adds, or removes edgef attributes for points, which only works on primitive face types. The force is directed in the direction of the edge leading from that point. If multiple vertices ref... |
| `edgef` | Edge F | Float | If you select 'Add Edge F' from the menu above, edgef attribute will be added/modified in the SOP. Enter expressions here to control the values of the force in the normal direction here. If you sel... |
| `dodirf` | Dir. F | Menu | Retains, adds, or removes dirf attributes for points, an arbitrary directional force still affected by the distance roll-off function. |
| `dirf` | Dir. F | XYZ | If you select 'Add Dir. F' from the menu above, dirf attribute will be added/modified in the SOP. Enter expressions here to control the values of the force in the arbitrary direction here. If you s... |

## Usage Examples

### Basic Usage

```python
# Access the SOP pointSOP operator
pointsop_op = op('pointsop1')

# Get/set parameters
freq_value = pointsop_op.par.active.eval()
pointsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pointsop_op = op('pointsop1')
output_op = op('output1')

pointsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pointsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **39** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
