# CHOP timecodeCHOP

## Overview

The Timecode CHOP generates Timecode data (channels, a .timecode python object and other python members). Its Mode menu provides a variety of ways to get, set and generate timecode through its parameters, including being driven from a timecode string, a set of channels, or other OPs that have timecode such as video input devices. You can also set t

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `smpte` | SMPTE | Toggle | When enabled the generated timecode will follow the SMPTE timecode standard, meaning no negative timecodes, and the timecode will loop at 24 hours. When disabled, the format will be more general, a... |
| `mode` | Mode | Menu | The source used for generating the timecode |
| `rate` | Rate | Float | The timecode FPS. The timecode's max frame value is equal to rate-1. If a fractional rate is provided then the rate is rounded up to the nearest whole number and drop-frames will be calculated if e... |
| `dropframe` | Drop Frame | Menu | Specify how to calculate drop-frames. Drop frames are used when the FPS is fractional. FPS cannot increment a fractional amount per frame so FPS is rounded to the next whole number and the accumula... |
| `index` | Index | Float | The index used to generate the timecode. Value is used in conjunction with the specified units. |
| `indexunit` | Index Unit | Menu | The index value units. |
| `timecodestr` | Timecode String | Str | A timecode string following the format: hh:mm:ss:ff or hh:mm:ss.ff |
| `frame` | Frame | Int | Frame component of the timecode. |
| `second` | Second | Float | Second component of the timecode. |
| `minute` | Minute | Float | Minute component of the timecode. Allows for overflow. |
| `hour` | Hour | Float | Hour component of the timecode. |
| `init` | Initialize | Pulse | Used in sequential mode. Initializes the timecode value. |
| `start` | Start | Pulse | Used in sequential mode. Starts the timecode sequential increment. |
| `play` | Play | Toggle | When enabled, the sequential timecode will step forward. |
| `timecodeobj` | Timecode Object | Str | A timecode object. |
| `chop` | CHOP | CHOP | A CHOP reference which contains some or all of the following channels: negative, hour, minute, second, frame. |
| `op` | OP | OP | An OP reference that contains a timecode Python member: eg. MoviefileinTOP_Class. |
| `customlength` | Custom Length | Toggle | When enabled, a custom length can be specified for the timecode. If not, the default length will be 23:59:59:ff-1 for a SMPTE timecode and 99:59:59:ff-1 otherwise. |
| `length` | Length | Float | Specifies the custom length in either samples, frames, or seconds. If it is desired to reference a Timecode Object then either tdu.Timecode().totalSeconds or tdu.Timecode().totalFrames, depending o... |
| `lengthunits` | Length Units | Menu | The unit of the custom length. |
| `cycle` | Cycle | Toggle | When enabled, the timecode value will cycle back to 00:00:00:00 upon reaching the custom length, rather than holding the last value. |
| `negativechan` | Negative Chan | Toggle | When enabled, outputs the negative channel, which is true when the timecode is negative. Always false when using SMPTE standard. |
| `framechan` | Frame Chan | Toggle | When enabled, outputs the frame channel. |
| `secondchan` | Second Chan | Toggle | When enabled, outputs the second channel. |
| `minutechan` | Minute Chan | Toggle | When enabled, outputs the minute channel. |
| `hourchan` | Hour Chan | Toggle | When enabled, outputs the hour channel. |
| `totalseconds` | Total Seconds Chan | Toggle | When enabled, outputs the total_seconds channel, which is the timecode converted into seconds. |
| `totalframes` | Total Frames Chan | Toggle | When enabled, outputs the total_frames channel, which is the timecode into frames. |
| `dropframechan` | Drop Frame Chan | Toggle | When enabled, outputs the drop_frame channel, which is true when the timecode is drop-frame. |
| `fpschan` | FPS Chan | Toggle | When enabled, outputs the fps channel. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP timecodeCHOP operator
timecodechop_op = op('timecodechop1')

# Get/set parameters
freq_value = timecodechop_op.par.active.eval()
timecodechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
timecodechop_op = op('timecodechop1')
output_op = op('output1')

timecodechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(timecodechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **36** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
