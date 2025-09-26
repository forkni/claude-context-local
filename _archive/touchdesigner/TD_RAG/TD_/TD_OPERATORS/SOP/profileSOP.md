# SOP profileSOP

## Overview

The Profile SOP enables the extraction and manipulation of profiles.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | This field allows you to specify the particular group of curves on the surface. Other primitives are ignored. You can specify profile curves within the group by providing a profile pattern (e.g. *.... |
| `method` | Method | Menu | This menu allows you to extract a stand-alone 3D curve as the world or parametric image of the profile. The non-parametric option will yield a curve whose shape and position in space are identical ... |
| `parametric` | Parametrically to X Y | Toggle | If Fitted (this option not checked), the profile will be a spatial NURBS curve whose position and shape in space will be identical to the curve on surface. It may very well be non-planar. If Extrac... |
| `smooth` | Smooth Curve | Toggle | If enabled, it will fit a spline through the extracted points. This parameter is disabled when extracting the profile parametrically. Disable this parameter in order to bypass the fitting process w... |
| `sdivs` | Divisions per Span | Int | The number of points per span to be computed on the profile. A span is the line connecting two consecutive CVs on a polygon, or the arc between two breakpoints on a spline curve. The profile tends ... |
| `tolerance` | Tolerance | Float | This parameter specifies the precision of the fitting process for the extracted 3D data, and is typically less than 0.01. |
| `order` | Order | Int | The spline order of the resulting 3D curve. The type of curve (Bzier or NURBS) is inherited from the spatial curve. The order, however, is not inherited because the spline order provides useful con... |
| `csharp` | Preserve Sharp Corners | Toggle | Controls the precision with which sharp corners in the profile curve are interpolated. It should be on when the profile has areas of high changes in curvature. |
| `keepsurf` | Keep Surface | Toggle | Specifies whether the parent surface should be removed after the extraction or not. |
| `delprof` | Delete Original Profile | Toggle | When Keep Surface parameter is On, select whether to leave or delete the original profile. |
| `maptype` | Mapping Type | Menu | Select how to reposition and scale an existing profile to fit within the specified domain range. It is a good means of bringing an invisible profile into view by setting the mapping range between 0... |
| `urange` | U Range | Float | Indicates in percentages what part of the U surface domain is the mapping area. A full range of 0-1 will cause the profiles to be mapped to the entire domain in the U parametric direction. The rang... |
| `vrange` | V Range | Float | Indicates in percentages what part of the V surface domain is the mapping area. A full range of 0-1 will cause the profiles to be mapped to the entire domain in the V parametric direction. The rang... |

## Usage Examples

### Basic Usage

```python
# Access the SOP profileSOP operator
profilesop_op = op('profilesop1')

# Get/set parameters
freq_value = profilesop_op.par.active.eval()
profilesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
profilesop_op = op('profilesop1')
output_op = op('output1')

profilesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(profilesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
