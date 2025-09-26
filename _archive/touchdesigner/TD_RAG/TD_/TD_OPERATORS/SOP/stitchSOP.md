# SOP stitchSOP

## Overview

The Stitch SOP is used to stretch two curves or surfaces to cover a smooth area.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `group` | Group | StrMenu | Which primitives to stitch. If blank, it stitches the entire input. Accepts patterns, as described in Pattern Matching. |
| `stitchop` | Stitch | Menu | Stitches sub-groups of n primitives or patterns of primitives. |
| `inc` | N | Int | The value entered for N determines the pattern of primitives stitched. |
| `loop` | Wrap Last to First | Toggle | If enabled, it connects the beginning of the first primitive in the left input to the end of the last primitive in the same input. If only one primitive exists, its ends will be stitched together. |
| `dir` | Direction | Menu | Allows stitching along either the U or V parametric direction. |
| `tolerance` | Tolerance | Float | This parameter minimizes modification to the input sources. A smaller value creates less modification. |
| `bias` | Bias | Float | Determines which primitive remains unaffected. The values go from 0 - 1, where 0 - first, and 1 - last. |
| `leftuv` | Left UV | Float | Point on each left / right primitive at which to begin / end the stitch. |
| `rightuv` | Right UV | Float | Point on each left / right primitive at which to begin / end the stitch. |
| `lrwidth` | LR Width | Float | The first value represents the width of the left stitch. The second value represents the width of the right stitch. |
| `dostitch` | Stitch | Toggle | If selected, move a single row from each primitive to coincide. |
| `dotangent` | Tangent | Toggle | If selected, modifies neighbouring rows on each primitive to create identical slopes at the given rows. |
| `sharp` | Sharp Partials | Toggle | If selected, creates sharp corners at the ends of the stitch when the stitch partially spans a primitive. |
| `fixed` | Fixed Intersection | Toggle | When the tangent option is on, this option allows some flexibility as to which side of each slope is modified. |
| `lrscale` | LR Scale | Float | Use this parameter to control the direction and position of the tangential slopes. |

## Usage Examples

### Basic Usage

```python
# Access the SOP stitchSOP operator
stitchsop_op = op('stitchsop1')

# Get/set parameters
freq_value = stitchsop_op.par.active.eval()
stitchsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
stitchsop_op = op('stitchsop1')
output_op = op('output1')

stitchsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(stitchsop_op)
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
