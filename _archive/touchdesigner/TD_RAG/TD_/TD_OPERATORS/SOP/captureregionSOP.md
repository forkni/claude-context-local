# SOP captureregionSOP

## Overview

The Capture Region SOP defines capture region (cregion), which is a type of primitive which can be thought of as a modified tube primitive (a tube with half a sphere on either end).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `orient` | Orientation | Menu | Defines the direction axis of the region. Use Z axis when the region is inside a bone object.      Image:TouchGeometry46.gif |
| `t` | Center | XYZ | Position of the center of the region. |
| `theight` | Top Height | Float | Height of the region from the centre to the top cap. |
| `tcap` | Top Cap | XYZ | The X, Y, Z radii of the top/bottom hemisphere. |
| `bheight` | Bottom Height | Float | Height of the region from the centre to the top cap. |
| `bcap` | Bottom Cap | XYZ | The X, Y, Z radii of the top/bottom hemisphere. |
| `weight` | Max/Min Weight | Float | Defines the weight of a point exactly on the centre line and edge of the region respectively. Point weights in-between are blended. |
| `color` | Display Color | RGB | The Capture Region SOP<uses region colors for helpful feedback.      By default the region inherits the color of its containing object (via an expression). |

## Usage Examples

### Basic Usage

```python
# Access the SOP captureregionSOP operator
captureregionsop_op = op('captureregionsop1')

# Get/set parameters
freq_value = captureregionsop_op.par.active.eval()
captureregionsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
captureregionsop_op = op('captureregionsop1')
output_op = op('output1')

captureregionsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(captureregionsop_op)
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
