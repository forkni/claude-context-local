# CHOP constantCHOP

## Overview

The Constant CHOP creates new constant-value channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `const` | Constant | Sequence | Sequence of name/value pairs defining the channels |
| `snap` | Snapshot Input | Pulse | The optional first CHOP input on Constant is used when the Snapshot Input button is pressed. At this time, the channel names and values at the CHOP input at the current frame are used to initialize... |
| `first` | First Channel | Int | The First Channel parameter is used to select a smaller set of the incoming channels. This is useful if the number of incoming channels is greater than the 40 channels the Constant CHOP can hold, a... |
| `current` | Active Needs Current | Toggle | This is used with the second input as described above, when you want to add a displacement to channels by using external devices or sources.   When Active Needs Current is On, the second CHOP input... |
| `single` | Single Sample | Toggle | Turn this Off to make constant channels that are longer than one Sample. |
| `start` | Start | Float | Start and end of the interval, expressed in Units (seconds, frames or samples). The parameters are expressed in the Units found on the Common page. To set the CHOP to be 100 samples long, Set Units... |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | Start and end of the interval, expressed in Units (seconds, frames or samples). The parameters are expressed in the Units found on the Common page. To set the CHOP to be 100 samples long, Set Units... |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before range). |
| `right` | Extend Right | Menu | The right extend conditions (after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP constantCHOP operator
constantchop_op = op('constantchop1')

# Get/set parameters
freq_value = constantchop_op.par.active.eval()
constantchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
constantchop_op = op('constantchop1')
output_op = op('output1')

constantchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(constantchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
