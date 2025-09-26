# SOP isosurfaceSOP

## Overview

The Iso Surface SOP uses implicit functions to create 3D visualizations of isometric surfaces found in Grade 12 Functions and Relations textbooks.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `func` | Implicit Function | Float | Enter the function for implicit surface building here.     Example 1: (me.curPos.x**2) / (4*4) - (me.curPos.y**2) / (3*3) + me.curPos.z     This formula creates a hyperbolic paraboloid, or saddle s... |
| `min` | Minimum Bound | XYZ | Determines the minimum clipping plane boundary for display of iso surface. |
| `max` | Maximum Bound | XYZ | Determines maximum clipping plane boundary for display of iso surfaces. |
| `divs` | Divisions | Int | The density, or resolution of the iso surface polygons in X, Y and Z. |
| `normals` | Compute Normals | Toggle | Adds normals to the surface. |

## Usage Examples

### Basic Usage

```python
# Access the SOP isosurfaceSOP operator
isosurfacesop_op = op('isosurfacesop1')

# Get/set parameters
freq_value = isosurfacesop_op.par.active.eval()
isosurfacesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
isosurfacesop_op = op('isosurfacesop1')
output_op = op('output1')

isosurfacesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(isosurfacesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **5** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
