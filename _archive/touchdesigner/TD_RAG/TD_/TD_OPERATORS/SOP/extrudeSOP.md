# SOP extrudeSOP

## Overview

The Extrude SOP can be used for extruding and bevelling Text and other geometry, cusping the bevelled edges to get sharp edges, and making primitives thicker or thinner.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `sourcegrp` | Source Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified for the source. Accepts patterns, as described in Pattern Matching. |
| `xsectiongrp` | X-Section Group | StrMenu | If there are input groups, specifying a group name in this field will cause this SOP to act only upon the group specified for the cross-section. Accepts patterns, as described in Pattern Matching. |
| `dofuse` | Fuse Points | Menu | This should almost always be turned on when cross-sections are used. It consolidates points of polygons that would otherwise cross or overlap when the bevel takes place. |
| `fronttype` | Front Face | Menu | Control how the front face of the extrusion should be built. You may wish to have a "No Output" because some faces are never actually seen when doing animation and, therefore, would only take up ad... |
| `backtype` | Back Face | Menu | This value controls whether or not the back of the extruded object will have a face or not. The options are the same as the Front Face options above. |
| `sidetype` | Side Mesh | Menu | Controls how the cross-section(s) will be extruded. If the input cross-section is a Bzier or NURBS curve, the surface will be constructed with a patch of the same geometry type. |
| `initextrude` | Initialize Extrusion | Pulse | If the cross-section face that you created doesn't match up nicely to the size of the geometry you are extruding, this command will scale and translate it so that it fits nicely.      The reason it... |
| `thickxlate` | Thickness Translate | Float | Shifts the cross-section profile perpendicularly to the normals of the input geometry. This relates to the X axis of the cross-section profile. When used with text, this typically has the effect of... |
| `thickscale` | Thickness Scale | Float | Scales the cross-section profile perpendicularly to the normals of the input geometry. This is equivalent to scaling the cross-section in its X axis. This parameter has no effect on the default pro... |
| `depthxlate` | Depth Translate | Float | Moves the cross-section in the direction of the normal. Positive values will move backwards to the direction of the normal. Depth movement relates to the Y axis of the input cross-section. Using th... |
| `depthscale` | Depth Scale | Float | Scales the cross-section in the direction of the source geometry's normals. This is equivalent to scaling the input cross-section in its Y axis and will determine how deep (thick) the resulting ext... |
| `vertex` | Vertex | Int | Translates the cross-section such that the vertex specified is at the cross-section origin. |
| `docusp` | Cusp Polygonal Sides | Toggle | Determines whether or not sides are to be smooth-shaded or faceted using the angle value in Side Cusp Angle field.      Cusping lets you specify at which angle between adjacent polygons, a sharp ed... |
| `cuspangle` | Side Cusp Angle | Float | When checked, this value will control the angle at which faceting of the sides will occur. A value of 20 is default. |
| `sharefaces` | Consolidate Faces to Mesh | Toggle | If selected the extrusion will share points between the front face and the first row of the side mesh and between the last face and the last row of the side mesh. |
| `removesharedsides` | Remove Shared Sides | Toggle | Prevents the creation of duplicate sides. |
| `newg` | Create Output Groups | Toggle | When this option is checked, it causes the Extrude SOP to generate three new groups representing the primitives belonging to the front faces, back faces, and the side bevel/extrusion. The name of t... |
| `frontgrp` | Front Group | Str | Output group name to create for front face geometry. |
| `backgrp` | Back Group | Str | Output group name to create for back face geometry. |
| `sidegrp` | Side Group | Str | Output group name to create for side bevel/extrude geometry. |

## Usage Examples

### Basic Usage

```python
# Access the SOP extrudeSOP operator
extrudesop_op = op('extrudesop1')

# Get/set parameters
freq_value = extrudesop_op.par.active.eval()
extrudesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
extrudesop_op = op('extrudesop1')
output_op = op('output1')

extrudesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(extrudesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
