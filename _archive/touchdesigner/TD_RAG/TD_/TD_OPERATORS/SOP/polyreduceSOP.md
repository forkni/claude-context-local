# SOP polyreduceSOP

## Overview

The Polyreduce SOP reduces a high detail polygonal model into one consisting of fewer polygons.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `reduce` | Polygons | StrMenu | The polygons which will be candidates for simplification. Other polygons which share points with these might also be affected. |
| `creases` | Features | StrMenu | Which polygons are feature edges. |
| `method` | Method | Menu | Select how to reduce the number of polygons from the following methods. |
| `percentage` | Keep % | Float | Specify the percentage of polygons to keep when Method set to 'Percentage'. |
| `numpolys` | Keep # | Int | Specify the number of polygons to keep when Method set to 'Number'. |
| `obj` | Object | Object | The object to use as a reference. |
| `distance` | Dist. Threshhold | Float | The world distance at which the polygons should be left at full detail. |
| `minpercent` | Minimum % | Float | A lower bound to the level of reduction. |
| `borderweight` | Stiffen Border | Float | Without any constraints, the edges of planar surfaces can erode. This controls a bias which penalizes such erosion. |
| `creaseweight` | Stiffen Features | Float | The amount of penalty to add to the feature edges being eroded. |
| `lengthweight` | Equalize Edges | Float | This bias penalizes the removal of long edges. It tends to reduce high aspect ratio triangles at the expense of more uniform reduction. |
| `meshinvert` | Prevent Mesh Inversion | Toggle | When enabled, each reduction is tested to see if it would flip a triangle normal. While encurring a slight cost, the results are almost always worth it. |
| `triangulate` | Pre-Triangulate | Toggle | As only triangular polygons will be reduced, this option will automatically triangulate the input polygons. |
| `keepedges` | Prevent Cracking | Toggle | This prohibits the removal of any edge that occurs at the boundary of the polygons. This ensures no cracks develop with unreduced areas. |
| `originalpoints` | Use Original Points | Toggle | When it collapses edges, it will use one of the two original points instead of finding the optimal interior point. |

## Usage Examples

### Basic Usage

```python
# Access the SOP polyreduceSOP operator
polyreducesop_op = op('polyreducesop1')

# Get/set parameters
freq_value = polyreducesop_op.par.active.eval()
polyreducesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
polyreducesop_op = op('polyreducesop1')
output_op = op('output1')

polyreducesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(polyreducesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
