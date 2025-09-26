# SOP projectSOP

## Overview

The Project SOP creates curves on surface (also known as trim or profile curves) by projecting a 3D face onto a spline surface, much like a light casts a 2D shadow onto a 3D surface.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `facegroup` | Face Group | StrMenu | The group of faces to be projected onto the spline surfaces. Accepts patterns, as described in Pattern Matching. |
| `surfgroup` | Surface Group | StrMenu | The group of surfaces to project faces onto. Accepts patterns, as described in Pattern Matching. |
| `cycle` | Cycle Type | Menu | Select the method use to project the 3D faces onto the 3D spline surfaces. |
| `method` | Method | Menu | Select between projecting along a vector or parametrically using the parameters below. |
| `axis` | Axis | Menu | The axis along which the four corners of the feature are projected onto the base. When adding the feature from the outside as a Vector paste. |
| `vector` | Vector | Float | The X, Y, and Z components of the projection vector if none of the main axes is chosen in the Axis parameter above. |
| `projside` | Side | Menu | Select which sides of the geometry to project on, closest or farthest. |
| `sdivs` | Divisions per Span | Int | The number of points to be computed on the spatial face between successive spans. A span is the line connecting two consecutive CVs on a polygon, or the arc between two breakpoints on a spline curv... |
| `rtolerance` | Ray Tolerance | Float | Controls the precision of the ray intersection with the surface. The ray is cast along the projection vector from every point of the 3-D curve. |
| `ftolerance` | Fit Tolerance | Float | Controls the 2-D fitting precision and is typically less than 0.01. |
| `uvgap` | Max UV Gap (%) | Float | This specifies what percentage of the size of the surface domain is acceptable for two separate profiles to be joined into a single curve. |
| `order` | Order | Int | The spline order of the resulting profile curve. The type of curve (Bzier or NURBS) is inherited from the spatial curve. The order, however, is not inherited because the spline order provides usefu... |
| `csharp` | Preserve Sharp Corners | Toggle | Controls the precision with which sharp corners in the projection curve are interpolated. It should be on when the projection has areas of high changes in curvature. |
| `accurate` | Super Accurate Projection | Toggle | Use a very accurate yet expensive algebraic pruning algorithm to determine the intersection of the vector with the surface. |
| `ufrom` | U from | Menu | Specifies which of the spatial coordinates - X, Y, or Z - must be mapped to the U parametric direction of the surface. |
| `vfrom` | V from | Menu | Specifies which of the spatial coordinates - X, Y, or Z - must be mapped to the V parametric direction of the surface. |
| `userange` | Map Profile to Range: | Toggle | This option is on by default. It causes the profile to be scaled and translated to fit within the surface's domain ranges described below. If this option is off, the profile's coordinates are mappe... |
| `urange` | U Range | Float | Indicates in percentages what part of the U surface domain is the mapping area. A full range of 0-1 will cause the profiles to be mapped to the entire domain in the U parametric direction. The rang... |
| `vrange` | V Range | Float | Indicates in percentages what part of the V surface domain is the mapping area. A full range of 0-1 will cause the profiles to be mapped to the entire domain in the V parametric direction. The rang... |
| `maptype` | Mapping Type | Menu | Select how to reposition and scale an existing profile to fit within the specified domain range. |

## Usage Examples

### Basic Usage

```python
# Access the SOP projectSOP operator
projectsop_op = op('projectsop1')

# Get/set parameters
freq_value = projectsop_op.par.active.eval()
projectsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
projectsop_op = op('projectsop1')
output_op = op('output1')

projectsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(projectsop_op)
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
