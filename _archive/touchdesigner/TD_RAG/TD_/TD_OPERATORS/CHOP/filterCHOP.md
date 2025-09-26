# CHOP filterCHOP

## Overview

The Filter CHOP smooths or sharpens the input channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | There are seven types of filters: |
| `effect` | Effect | Float | The extent to which the filter affects the channel (0 - not at all, 1 - maximum effect). |
| `width` | Filter Width | Float | The amount of surrounding samples used in the calculation of the current sample. It is expressed in the Units. |
| `widthunit` | Filter Width Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `spike` | Spike Tolerance | Float | For the De-spike filter type, this is the amount that a sample can differ from its neighbours without being considered a spike. |
| `ramptolerance` | Ramp Tolerance | Float | When using a Ramp Preserve filter, if the input value deviates from the current output ramp value by this much, then the ramp will reset to the new input value. Otherwise the Ramp Preserve will con... |
| `ramprate` | Ramp Rate | Float | When using a Ramp Preserve filter, this is the rate that the CHOP's output channel will increase. Only if the input channel value deviates from the desired output value by 'Ramp Tolerance' amount w... |
| `passes` | Number of Passes | Int | The number of times the filter is applied to the channel. |
| `cutoff` | Cutoff Frequency (Hz) | Float | Decrease it if slow speed jitter is a problem. |
| `speedcoeff` | Speed Coefficient | Float | Increase if high speed lag is a problem. |
| `slopecutoff` | Slope Cutoff Frequency (Hz) | Float | Avoids high derivative bursts caused by jitter. |
| `slopedownreset` | Slope Down Reset | Toggle | When On resets (bypasses) the filter effect when the downward slope exceeds the Slope Down Max value to the right. |
| `slopedownmax` | Slope Down Max | Toggle | Set the maximum value of the slope downwards beyond which the filter resets when the toggle to the left is On. |
| `slopeupreset` | Slope Up Reset | Toggle | When On resets (bypasses) the filter effect when the upward slope exceeds the Slope Up Max value to the right. |
| `slopeupmax` | Slope Up Max | Toggle | Set the maximum value of the slope upwards beyond which the filter resets when the toggle to the left is On. |
| `reset` | Reset | Toggle | When On resets (bypasses) the filter effect. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets the filter effect. |
| `filterpersample` | Filter per Sample | Toggle | Applies the filter to each sample of the channel instead of across the whole channel. Useful for working with multi-sample channels. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP filterCHOP operator
filterchop_op = op('filterchop1')

# Get/set parameters
freq_value = filterchop_op.par.active.eval()
filterchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
filterchop_op = op('filterchop1')
output_op = op('output1')

filterchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(filterchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
