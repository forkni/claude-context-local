# SOP curveclaySOP

## Overview

The Curveclay SOP is similar to the Clay SOP in that you deform a spline surface not by modifying the CVs but by directly manipulating the surface.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `facegroup` | Face Group | StrMenu | Subset of faces (NURBS, Bzier, Polygons) to project, or subset of proles to deform, depending on how many inputs are connected.   Examples include: 0.5 1.2-3.9 5.*        This group can even take s... |
| `surfgroup` | Surface Group | StrMenu | Subset of spline surfaces to be deformed when all three SOP inputs are connected. |
| `divs` | Divisions on Face | Int | The number of points to evaluate on the proles or the faces. This SOP works by using a straight line approximation of the given curve to deform the surface. Thus, more segments are slower, but the ... |
| `sharp` | Sharpness | Float | Species the area around the face to deform. The larger the sharpness is, the smaller the deformation area around them (thus having a sharper pull on the surface). |
| `refine` | Refinement | Float | Usually, CurveClay automatically renes the surface. However, you may specify some degree of renement control. In general, the more rened the surface is, the smoother the result. Better renement res... |
| `projop` | Projection Axis | Menu | Choice of several projection axes: |
| `projdir` |  | Float | Specify the direction vector of the projection. |
| `deformop` | Displacement Axis | Menu | Choice of several projection axes: |
| `deformdir` |  | Float | Specify the direction vector of the displacement. |
| `deformlen` | Distance | Float | Distance deformed along the vector. |
| `deforminside` | Deform Inside of Loop | Toggle | Check if the inside of closed loops should be deformed. |
| `individual` | Consider Profiles Individually | Toggle | Check if multiple curves form a closed loop. |

## Usage Examples

### Basic Usage

```python
# Access the SOP curveclaySOP operator
curveclaysop_op = op('curveclaysop1')

# Get/set parameters
freq_value = curveclaysop_op.par.active.eval()
curveclaysop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
curveclaysop_op = op('curveclaysop1')
output_op = op('output1')

curveclaysop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(curveclaysop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
