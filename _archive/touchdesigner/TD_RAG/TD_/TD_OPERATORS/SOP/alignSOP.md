# SOP alignSOP

## Overview

The Align SOP aligns a group of primitives to each other or to an auxiliary input, by translating or rotating each primitive along any pivot point.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | A subset of primitives to align (accepts patterns, as described in Pattern Matching in the Scripting Guide). If blank, it aligns the entire input. |
| `align` | Align | Menu | Can optionally align subgroups of n primitives or every nth primitive in a cyclical manner. |
| `inc` | N | Int | Determines the number of primitives to be either grouped or skipped. Example: Assume there are six primitives numbered for 0 - 5, and N = 2. Then:   a)b) |
| `bias` | Bias | Float | Determines which primitive remains unaffected: 0 Left, 1 Right. |
| `leftuv` | Left UV | Float | Pivot Location for each "left" primitive. |
| `rightuv` | Right UV | Float | Pivot location for each "right" primitive. |
| `rightuvend` | Right UV End | Float | If an auxiliary input is used, this location specifies an end point for the alignment. Left primitives are then distributed uniformly between the Right UV and the Right UV End. |
| `individual` | Individual Alignment | Toggle | Causes each primitive of the input to be aligned. If unchecked, only the first primitive is aligned and all others are placed relative to it, preserving the spatial layout of the left primitives. |
| `dotrans` | Translate | Toggle | When enabled, translates primitives during alignment by translating the left UV position to the right UV position. |
| `dorotate` | Rotate | Toggle | When enabled, rotates primitives during alignment by aligning the left UV tangents (at the left UV position) to the right UV tangents (at the right UV position). |
| `xord` | Transform Order | Menu | Sets the overall transform and rotation order for the transformations. The transform and rotation order determines the order in which transformations take place. Depending on the order, you can ach... |
| `rord` | Rotate Order | Menu | Sets the overall transform and rotation order for the transformations. The transform and rotation order determines the order in which transformations take place. Depending on the order, you can ach... |
| `t` | Translate | XYZ | Allows you to perform a post-alignment transformation. Specify the amount of translation about the local xyz axes. |
| `r` | Rotate | XYZ | Allows you to perform a post-alignment transformation. Specify the amount of rotation about the local xyz axes. |
| `s` | Scale | XYZ | Allows you to perform a post-alignment transformation. Specify the amount of scaling about the local xyz axes. |
| `p` | Pivot | XYZ | Allows you to perform a post-alignment transformation. Specify the amount of translation / rotation / scaling about the local xyz axes |

## Usage Examples

### Basic Usage

```python
# Access the SOP alignSOP operator
alignsop_op = op('alignsop1')

# Get/set parameters
freq_value = alignsop_op.par.active.eval()
alignsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
alignsop_op = op('alignsop1')
output_op = op('output1')

alignsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(alignsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **16** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
