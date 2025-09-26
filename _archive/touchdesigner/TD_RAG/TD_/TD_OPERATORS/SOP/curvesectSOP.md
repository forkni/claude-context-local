# SOP curvesectSOP

## Overview

The Curvesect SOP finds the intersections or the points of minimum distance between two or more faces (polygons, Bziers, and NURBS curves) or between faces and a polygonal or spline surface.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `leftgroup` | Face Group | StrMenu | A subset of faces (NURBS, Bzier, polygons) to act upon. Accepts patterns, as described in Pattern Matching. |
| `rightgroup` | Cutter Group | StrMenu | A subset of faces or spline surfaces to intersect with. Accepts patterns, as described in Pattern Matching. |
| `xsect` | Find All Intersections | Toggle | Compute intersection points if the faces touch the cutter primitive. If the button is unchecked, only the point of minimum distance will be found. Currently, finding the minimum distance between a ... |
| `tolerance` | Tolerance | Float | Determines the precision of the intersection. |
| `method` | Method | Menu | Choose between 'Cut' or 'Extract' operations. |
| `left` | Left Face Pieces | Menu | Choose what parts of the left faces to keep: |
| `right` | Right Face Pieces | Menu | Choose what parts of the right faces to keep: |
| `affect` | Affect | Menu | Choose which input to operate on: |
| `extractpt` | Extract Point | Toggle | If the right input is a surface, choose between point and isoparm extraction; only points are extracted if the right input is a face. |
| `keeporiginal` | Keep Original | Toggle | When using Extract method, turning this on will keep the original geometry connected to the first input (input0). |

## Usage Examples

### Basic Usage

```python
# Access the SOP curvesectSOP operator
curvesectsop_op = op('curvesectsop1')

# Get/set parameters
freq_value = curvesectsop_op.par.active.eval()
curvesectsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
curvesectsop_op = op('curvesectsop1')
output_op = op('output1')

curvesectsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(curvesectsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
