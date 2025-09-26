# CHOP lagCHOP

## Overview

The Lag CHOP adds lag and overshoot to channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `lagmethod` | Method | Menu | The method by which lag is applied to the channels. |
| `lag` | Lag | Float | Applies a lag to a channel. The first value is for lagging up, and the second is for lagging down. It is approximately the time that the output follows 90% of a change to the input. |
| `lagunit` | Lag Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `overshoot` | Overshoot | Float | Applies overshoot to a channel. The first value is for overshoot while moving up, and the second is for overshoot while moving down. |
| `overshootunit` | Overshoot Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for this parameter. |
| `clamp` | Clamp Slope | Toggle | Clamps the slope (or velocity) to lie between the values listed in Max Slope below. Slope is expressed as value/Units. |
| `slope` | Max Slope | Float | The first value limits the slope when it is rising, and the second value limits the slope when it is decreasing. |
| `aclamp` | Clamp Acceleration | Toggle | Clamps the acceleration to lie between the values listed in Max Acceleration below. Acceleration is expressed as value/(Units*2) . |
| `accel` | Max Acceleration | Float | The first value limits the acceleration when it is rising, and the second value limits the acceleration when it is decreasing. |
| `lagsamples` | Lag per Sample | Toggle | Applies the lag to each sample of the channel instead of across the whole channel. Useful for working with multi-sample channels. |
| `reset` | Reset | Toggle | When On resets (bypasses) the lag effect. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets the lag effect. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP lagCHOP operator
lagchop_op = op('lagchop1')

# Get/set parameters
freq_value = lagchop_op.par.active.eval()
lagchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lagchop_op = op('lagchop1')
output_op = op('output1')

lagchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lagchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **18** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
