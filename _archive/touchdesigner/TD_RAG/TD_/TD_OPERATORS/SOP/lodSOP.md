# SOP lodSOP

## Overview

The LOD SOP is unusual in so far as it does not actually alter any geometry.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `steppercent` | Step % | Float | Each successive level of detail will contain approximately this percentage on the number of polygons in the higher level of detail. |
| `distance` | Dist. Threshhold | Float | This is the distance from the camera at which full detail will be present. |
| `minpercent` | Minimum % | Float | The objects won't be drawn with fewer than this number of polygons. |
| `borderweight` | Stiffen Border | Float | The amount of weight to avoid erosion of boundary polygons. |
| `lengthweight` | Equalize Edges | Float | The amount of weight to favour even sized polygons. |
| `triangulate` | Pre-Triangulate | Toggle | Polygons can only be reduced if they are triangles. This option thus first converts them. |
| `tstrips` | Optimize Rendering | Toggle | When set, triangle strips will be generated and used for drawing. |
| `polysonly` | Only Affect Polygons | Toggle | If this is enabled, only the polygonal portion of the model will be displayed at lower levels of detail. Otherwise, all types of surfaces are affected by the distance to the camera. |

## Usage Examples

### Basic Usage

```python
# Access the SOP lodSOP operator
lodsop_op = op('lodsop1')

# Get/set parameters
freq_value = lodsop_op.par.active.eval()
lodsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lodsop_op = op('lodsop1')
output_op = op('output1')

lodsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lodsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **8** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
