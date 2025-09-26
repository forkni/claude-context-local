# CHOP ltcinCHOP

## Overview

The LTC In CHOP reads SMPTE timecode data encoded into an audio signal.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `inputrate` | Input Frame Rate | Float | This specifies the number of complete frame messages per second the signal encodes. It is usually between 24 and 30. |
| `discrete` | Discrete Channels | Toggle | When enabled, adds frame, second, minute, and hour channels will be added to the output. |
| `totalframes` | Total LTC Frames | Toggle | When enabled, adds a channel to the output that reports total elapsed LTC frames at the current time. This value will change if up-sampling to the timeline FPS. |
| `totalsec` | Total Seconds | Toggle | When enabled, adds a channel to the output that reports total elapsed seconds. |
| `upsample` | Up-sample to Timeline FPS | Toggle | Resamples up to the project's FPS. |
| `userfields` | User Fields | Toggle | This enables channels for custom user fields which may be encoded in the audio signal. |
| `debugchans` | Debug Channels | Toggle | This enables the following debug channels.  quantized - Outputs the raw signal quantized to on and off levels.  bits - Outputs the above quantized signal into decoded bits. (Note:  Bits are decoded... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP ltcinCHOP operator
ltcinchop_op = op('ltcinchop1')

# Get/set parameters
freq_value = ltcinchop_op.par.active.eval()
ltcinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ltcinchop_op = op('ltcinchop1')
output_op = op('output1')

ltcinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ltcinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
