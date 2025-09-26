# CHOP trailCHOP

## Overview

The Trail CHOP displays a history of its input channels back in time.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When On the Trail CHOP will record its input. |
| `growlength` | Grow Length | Toggle | When On the length of the Trail CHOP's recording will keep getting longer as the timeline moves forward. Use this for recording any length as needed. |
| `wlength` | Window Length | Float | The amount of history recorded is set by Window Length. The Units menu on the right determine which units to use in the parameter (Samples, Frames, Seconds). A setting of 4 seconds will show the va... |
| `wlengthunit` | Window Length Unit | Menu | Choose between using Samples, Frames, or Seconds as the units for the Window Length parameter. |
| `capture` | Capture | Menu | Determines when to capture values. |
| `resample` | Resample | Toggle | Enable parameter below to resample the output to a different length. |
| `samples` | Resample | Int | Resample the output to this specified length. |
| `setrate` | Rate | Toggle | Enable parameter below to use a different sample rate. |
| `rate` | Sample Rate | Float | Resample using this sample rate instead of the global frame rate ($FPS). |
| `reset` | Reset | Toggle | While On, this toggle resets the channel(s) to 0. |
| `resetpulse` | Reset Pulse | Pulse | Click to instantly resets the channel(s) to 0. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP trailCHOP operator
trailchop_op = op('trailchop1')

# Get/set parameters
freq_value = trailchop_op.par.active.eval()
trailchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
trailchop_op = op('trailchop1')
output_op = op('output1')

trailchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(trailchop_op)
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
