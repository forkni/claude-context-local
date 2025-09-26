# SOP polystitchSOP

## Overview

The Polystitch SOP attempts to stitch polygonal surfaces together, thereby eliminating cracks that result from evaluating the surfaces at differing levels of detail.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `stitch` | Polygons to Stitch | StrMenu | The polygons to consider for stitching. |
| `corners` | Corner Points | StrMenu | A list of point numbers that are to be considered breaks in the boundary edges. |
| `tol3d` | Max Dist to Stitch | Float | The maximum distance two edges can be from each other and still be stitched. |
| `consolidate` | Consolidate Points | Toggle | When several points along one edge are snapped to the same position, consolidate them into a single point. This only consolidates along the boundary, not across the boundary. |
| `findcorner` | Automatically Find Corners | Toggle | Whenever an edge changes direction at a point more than the specified angle, it will mark that point as a corner. |
| `angle` | Corner Angle | Float | The maximum angle a boundary point can change before it is considered a corner. |

## Usage Examples

### Basic Usage

```python
# Access the SOP polystitchSOP operator
polystitchsop_op = op('polystitchsop1')

# Get/set parameters
freq_value = polystitchsop_op.par.active.eval()
polystitchsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
polystitchsop_op = op('polystitchsop1')
output_op = op('output1')

polystitchsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(polystitchsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **6** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
