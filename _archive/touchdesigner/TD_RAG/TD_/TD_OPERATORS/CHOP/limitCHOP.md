# CHOP limitCHOP

## Overview

The Limit CHOP can limit the values of the input channels to be between a minimum and maximum, and can quantize the input channels in time and/or value such that the value steps over time.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | Select limit options such as loop, clamp, or zigzag from the menu. The value will remain in the range from Min to less than Max. |
| `min` | Minimum | Float | The minimum value the output channel can have. |
| `max` | Maximum | Float | The maximum value the output channel can have. |
| `positive` | Positive Only | Toggle | Takes the absolute value of the channel, making all negative values positive. |
| `norm` | Normalize | Toggle | Scale and offset the channel so that it lies between -1 and +1. The Normalize function does not work with Time Slicing on. |
| `underflow` | Fix Underflows | Toggle | This will cause extremely tiny numbers to be rounded to 0. |
| `quantvalue` | Quantize Value | Menu | Selects the quantization method to use: |
| `vstep` | Value Step | Float | The increment between quantized values. |
| `voffset` | Value Offset | Float | The offset for quantized values, to allow steps to not lie at zero, the default. |
| `quantindex` | Quantize Index | Menu | Selects whether to quantize the index relative to the sample 0, or the start index of the CHOP. |
| `istep` | Step | Float | The increment between quantized indices, in seconds, frames or samples. |
| `istepunit` | Step Unit | Menu |  |
| `ioffset` | Offset | Float | The offset for quantized indices. |
| `ioffsetunit` | Offset Unit | Menu |  |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP limitCHOP operator
limitchop_op = op('limitchop1')

# Get/set parameters
freq_value = limitchop_op.par.active.eval()
limitchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
limitchop_op = op('limitchop1')
output_op = op('output1')

limitchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(limitchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
