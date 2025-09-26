# SOP resampleSOP

## Overview

The Resample SOP will resample one or more primitives into even length segments.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Allows you to specify which primitives or group of primitives to resample. Accepts patterns, as described in Pattern Matching. |
| `lod` | Level of Detail | Float | If the geometry you are performing this operation on is made up of something other than polygons (e.g. a NURBS circle), this parameter determines how detailed the conversion to polygons will be. Th... |
| `edge` | Resample by Polygon Edge | Toggle | This toggle allows the resampling to be done on a per-edge basis of the polygon rather than on the polygon as a whole. This means that corners will be preserved in the resampling. When this paramet... |
| `method` | Method | Menu | Specifies how the geometry is segmented. |
| `measure` | Measure | Menu | Specifies how to measure along curved spline sections. |
| `dolength` | Maximum Segment Length | Toggle | When this option is enabled, it overrides the value of the Arc/Chord length and allows you to specify your own values for the length of the segments in the resampled geometry. Smaller values produc... |
| `length` | Length | Float | This parameter lets you specify the Arc/Chord length for the resampled geometry. |
| `dosegs` | Maximum Segments | Toggle | When enabled, allows you to override the maximum number of segments used in the resampled geometry. |
| `segs` | Segments | Int | Lets you specify the number of segments used when measuring along arc.     When both Maximum Segment Length and Maximum Segments are selected, the resultant polygon is constrained to a fixed length... |
| `last` | Maintain Last Vertex | Toggle | If selected, the primitive's final CV is included in the resampled polygon, even if the final resulting edge is shorter then the given segment length. |

## Usage Examples

### Basic Usage

```python
# Access the SOP resampleSOP operator
resamplesop_op = op('resamplesop1')

# Get/set parameters
freq_value = resamplesop_op.par.active.eval()
resamplesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
resamplesop_op = op('resamplesop1')
output_op = op('output1')

resamplesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(resamplesop_op)
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
