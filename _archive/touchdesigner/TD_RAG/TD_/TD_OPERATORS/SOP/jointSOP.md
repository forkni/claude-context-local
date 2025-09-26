# SOP jointSOP

## Overview

The Joint SOP will aid in the creation of circle-based skeletons by creating a series of circles between each pair of input circles.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | If there are input groups, specifying a group name in this field causes the SOP to act only upon the group specified. Accepts patterns, as described in Pattern Matching. |
| `divs` | Divisions | Int | Allows you to specify the number of circles between each pair of input circles. |
| `preserve1` | Preserve First Input | Toggle | Preserves the first input circle being fed into the SOP. |
| `preserve2` | Preserve Last Input | Toggle | Preserves the last input circle. |
| `orient` | Orient Circles | Toggle | This helps to create a joint that blends between the input circles without flattening or curving outwards. In order to do this, there may be a reversal of the normal of each input circle. For examp... |
| `smoothpath` | Smooth Path | Toggle | If not on, the joint circles are blended linearly. Otherwise, they are placed along a cubic piece-wise Bzier curve between the circle centres. This is useful when the input contains more than two c... |
| `smoothtwist` | Smooth Twist | Toggle | Each joint circle is rotated slightly such that its X and Y axis align as it approaches an input circle. This toggle causes the adjustments to be an incremental, or piece-wise, Bzier function. Agai... |
| `majoraxes` | Align Major Axes | Toggle | If enabled, this option aligns the first circle's largest axis to the last circle's largest axis. If disabled, the first and last circles' x axes are aligned. This option can help minimize the twis... |
| `mintwist` | Minimum Twist | Toggle | If on, the rotations of the added circles are calculated such that they never rotate further than one half turn in either direction. This leads to a visually continuous layout suitable for creating... |
| `lrscale` | LR Scale | Float | These parameters control the shape of the smooth path, varying the shape of the implied curve from the left or right. If the Orient Circles option is on, the sign of the scale has no effect. For a ... |
| `lroffset` | LR Offset | Float | These parameters allow you to override the distance between circles, thereby affecting the shape of the joint. |

## Usage Examples

### Basic Usage

```python
# Access the SOP jointSOP operator
jointsop_op = op('jointsop1')

# Get/set parameters
freq_value = jointsop_op.par.active.eval()
jointsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
jointsop_op = op('jointsop1')
output_op = op('output1')

jointsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(jointsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
