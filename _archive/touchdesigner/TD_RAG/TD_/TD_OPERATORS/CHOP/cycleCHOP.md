# CHOP cycleCHOP

## Overview

The Cycle CHOP creates cycles. It can repeat the channels any number of times before and after the original.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `before` | Cycles Before | Float | The number of cycles to loop before the input CHOP. This parameter can be fractional. |
| `after` | Cycles After | Float | The number of cycles to loop after the input CHOP. This parameter can be fractional. |
| `mirror` | Mirror Cycles | Toggle | If enabled, consecutive cycles are mirror images (reversed) of each another. The first cycle is never mirrored. |
| `extremes` | Blend Start to End | Toggle | If on, the end of the CHOP is blended into the start of the CHOP to produce a smooth loop. If Cycles Before and Cycles After are 0, Region is non-zero, and Extend Conditions are "Cycle", it loops s... |
| `blendmethod` | Method | Menu | How to blend between cycles: |
| `blendfunc` | Shape | Menu | The shape of the blending function: |
| `blendregion` | Region | Float | The size of the blend region, in either seconds, samples or frames (set with Units in the Common page). |
| `blendregionunit` | Blend Region Units | Menu |  |
| `blendbias` | Bias | Float | The bias of the blend. A -1 biases the blend toward the beginning of the blend region, 0 is no bias and +1 biases towards the end of the blend region. |
| `step` | Step | Float | If set to 1, the next cycle will be shifted up or down in value, so that it begins where the last cycle ended. Suitable for the root object of walk cycles. |
| `stepscope` | Step Scope | Str | The names of those channels that will be affected by the Step parameter. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP cycleCHOP operator
cyclechop_op = op('cyclechop1')

# Get/set parameters
freq_value = cyclechop_op.par.active.eval()
cyclechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cyclechop_op = op('cyclechop1')
output_op = op('output1')

cyclechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cyclechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
