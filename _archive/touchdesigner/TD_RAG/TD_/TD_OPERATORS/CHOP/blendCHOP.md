# CHOP blendCHOP

## Overview

The Blend CHOP combines two or more CHOPs in input 2, 3 and so on, by using a set of blending channels in input 1.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Method | Menu | The blend method: |
| `firstweight` | Omit First Weight Channel | Toggle | When using the Differencing method, the weight channel for the base input has no effect, so the channel is omitted if this option is On. |
| `underflow` | Fix Underflows | Toggle | Replace denormalized (very small) numerical values with 0. These values can otherwise cause performance issues. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP blendCHOP operator
blendchop_op = op('blendchop1')

# Get/set parameters
freq_value = blendchop_op.par.active.eval()
blendchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
blendchop_op = op('blendchop1')
output_op = op('output1')

blendchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(blendchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
