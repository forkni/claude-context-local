# SOP limitSOP

## Overview

The Limit SOP creates geometry from samples fed to it by CHOPs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `chop` | CHOP | CHOP | Specifies which CHOP Network / CHOP contains the sample data to fetch. |
| `rord` | Rotate Order | Menu | Specifies the order in which the Rotate Channel X / Y / Z channels are applied. |
| `chanx` | X Channel | StrMenu | Channels used to specify the point's positions, tx. |
| `chany` | Y Channel | StrMenu | Channels used to specify the point's positions, ty. |
| `chanz` | Z Channel | StrMenu | Channels used to specify the point's positions, tz. |
| `chanrx` | Rotate Channel X | StrMenu | Channels used to specify the rotational data of the geomtery created at each point. Only used when Output Type is "Polygon at Each Point" or "Primitive Circle at Each Point". |
| `chanry` | Rotate Channel Y | StrMenu | Channels used to specify the rotational data of the geomtery created at each point. Only used when Output Type is "Polygon at Each Point" or "Primitive Circle at Each Point". |
| `chanrz` | Rotate Channel Z | StrMenu | Channels used to specify the rotational data of the geomtery created at each point. Only used when Output Type is "Polygon at Each Point" or "Primitive Circle at Each Point". |
| `chanrad` | Radius Channel | StrMenu | Uniformly controls the radius of the geometry created at each point. The Radius channels are multiplied with the Radius parameter on the Output Page. |
| `chanradx` | Radius Channel X | StrMenu | Channels that control the radius on the respective axis. The Radius channels are multiplied with the Radius parameter on the Output Page. |
| `chanrady` | Radius Channel Y | StrMenu | Channels that control the radius on the respective axis. The Radius channels are multiplied with the Radius parameter on the Output Page. |
| `chanradz` | Radius Channel Z | StrMenu | Channels that control the radius on the respective axis. The Radius channels are multiplied with the Radius parameter on the Output Page. |
| `chanalpha` | Alpha Channel | StrMenu | Controls the point alpha, giving you alpha control of any geometry created at those points.      Note: If using a Copy SOP, turn on the Use Template Point Attributes option in the Copy SOP's Attrib... |
| `chanr` | Red Channel | StrMenu | These channels control the point color, or the color of any geometry created at those points. |
| `chang` | Green Channel | StrMenu | These channels control the point color, or the color of any geometry created at those points. |
| `chanb` | Blue Channel | StrMenu | These channels control the point color, or the color of any geometry created at those points. |
| `texturew` | Texture W | StrMenu | Controls the w texture-offset for the point(s) This is most often used as a frame-offset or time-offset, expressed in # of frames from the current frame or frame 1 of an image sequence. |
| `customattr` | Custom Attribute | Sequence | Sequence of custom attributes to be added to the geometry created. |
| `output` | Output Type | Menu | The type of geometry the Limit SOP produces from its sample data. |
| `divisions` | Divisions | Int | Only works on the following Output Types.      Polygon at Each Point - Number of points per polygon.   Poly Sphere at Each Point - Frequency of each Polygonal Sphere.    Tubes - Number of points in... |
| `rad` | Radius | Float | Radius of geometry created. Disabled for "Polygonal Line". |
| `flipsmooth` | Smooth Flip | Float | Dynamically controls the twist of each instance of geometry on a series of points to avoid frame-by-frame flipping, which can sometimes occur when geometry is oriented along a path. |
| `dolimit` | Limit | Menu | Creates a bounding box for the position of the output geometry. Drop down menu determines behavior when outside bounded region. |
| `xlimit` | X Limit | Float | Parameters to set edges of bounding region when Limit is active. |
| `ylimit` | Y Limit | Float | Parameters to set edges of bounding region when Limit is active. |
| `zlimit` | Z Limit | Float | Parameters to set edges of bounding region when Limit is active. |
| `texture` | Apply Texture | Toggle | Applys u, v, and w texture coordinates to the created geometry. |
| `texscale` | Scale | Float | Scales the texture coordinates a specific amount. |
| `texoffset` | Offset | Float | Offsets the texture coordinates a specific amount. |
| `orient` | Orient to Path | Toggle | If this option is selected, the object will be oriented along the path. To see what the path looks like, change the Output Type to "Polygonal Line". When the Output Type is "Polygon/Primitive Circl... |
| `lookat` | Lookat Object | OBJ | Orient to Path must be checked for Lookat Object to have any effect. This allows you to orient your geometry by naming the object you would like it to Look At, or point to. Once you have designated... |
| `dorotate` | Rotate Polys | Menu | Rotate the geometry at each point using the Rotate parameter (below). Only works for Output Type is "Polygon/Primitive Circle at Each Point". |
| `rotate` | Rotate | XYZ | Rotation channels rx, ry, and rz for Rotate Polys parameter. |
| `normals` | Compute Normals | Toggle | Computes normals for the geometry created. |

## Usage Examples

### Basic Usage

```python
# Access the SOP limitSOP operator
limitsop_op = op('limitsop1')

# Get/set parameters
freq_value = limitsop_op.par.active.eval()
limitsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
limitsop_op = op('limitsop1')
output_op = op('output1')

limitsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(limitsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **34** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
