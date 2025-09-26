# SOP trimSOP

## Overview

The Trim SOP cuts out parts of a spline surface, or uncuts previously cut pieces.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | This field allows you to specify the group that you would like to trim. You can select the group from the pop-up menu, or specify a points and primitives range.     You can specify profile curves w... |
| `optype` |  | Menu | The types of trimming operations available. |
| `individual` | Process Profiles Individually | Toggle | When this option is off, the trim loops in the group (or all the loops on the surfaces if no group has been specified) will be considered together to form a region. It will report the first region ... |
| `bigloop` | Build outer Trim-Loop Explicitly | Toggle | This option allows you to specify that an outer trim loop be built. It is useful where you have more than one profile curve on the surface and are performing several successive trim operations invo... |
| `trimtol` | Trimming Tolerance | Float | How close two trim curves must be to each other or to the edge of the patch in order to be considered an intersection. |
| `altitude` | Altitude | Int | You can specify the altitude of the trim. The $ALTITUDE variable is the surface's current altitude. This marks the transition for the surface from trimmed in to trimmed out. |

## Usage Examples

### Basic Usage

```python
# Access the SOP trimSOP operator
trimsop_op = op('trimsop1')

# Get/set parameters
freq_value = trimsop_op.par.active.eval()
trimsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
trimsop_op = op('trimsop1')
output_op = op('output1')

trimsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(trimsop_op)
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
