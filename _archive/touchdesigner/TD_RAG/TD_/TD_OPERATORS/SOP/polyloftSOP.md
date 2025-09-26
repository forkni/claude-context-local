# SOP polyloftSOP

## Overview

The Polyloft SOP generates meshes of triangles by connecting (i.e. lofting/stitching) the points of open or closed faces without adding any new points.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `proximity` | Connect Closest Ends | Toggle | Start stitching at the two closest points, and handle arbitrary face orientation and start vertices. |
| `consolidate` | Consolidate Points | Toggle | Fuse neighbouring points before stitching. |
| `dist` | Distance | Float | Threshold distance for consolidation. |
| `minimize` | Minimize | Menu | Distance minimization goal: |
| `closeu` | U Wrap | Menu | Close the stitch in U (close each cross-section). |
| `closev` | V Wrap | Menu | Connect first and last cross-sections. |
| `creategroup` | Create Polygon Group | Toggle | Place the generated triangles into a group. |
| `polygroup` | Name | Str | Specify the name of the group here when the above parameter Create Polygon Group = On. |
| `method` | Method | Menu | Selects how to perform the lofting/stitching. |
| `group` | Group | StrMenu | Subset of faces to loft. |
| `prim` | Keep Primitives | Toggle | Preserve the cross-sections after stitching. |
| `point` | Point Group | Sequence | Sequence of point sets to be stitched. |

## Usage Examples

### Basic Usage

```python
# Access the SOP polyloftSOP operator
polyloftsop_op = op('polyloftsop1')

# Get/set parameters
freq_value = polyloftsop_op.par.active.eval()
polyloftsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
polyloftsop_op = op('polyloftsop1')
output_op = op('output1')

polyloftsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(polyloftsop_op)
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
