# CHOP timelineCHOP

## Overview

The Timeline CHOP outputs time-based CHOP channels for a specific component.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `op` | Reference Operator | OP | This node is used to specify the time referenced by the Timeline CHOP. The time is defined by the Time COMP found at me.time |
| `usetimecode` | Use Timecode | Toggle | When enabled, the CHOP will get its time from a timecode reference, rather than the Reference Operator. The Reference Operator will still be used for bpm, time signature, start, and end values. |
| `timecodeop` | Timecode Object/CHOP/DAT | Str | Reference a timecode that sets the time. Should be a reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or a Timecode Clas... |
| `frame` | Frame | Toggle | Output a channel for frame number. |
| `rate` | Rate | Toggle | Output a channel for the rate (frames per second). |
| `start` | Start | Toggle | Output a channel with the Start frame value. |
| `end` | End | Toggle | Output a channel with the End frame value. |
| `rangestart` | Range Start | Toggle | Output a channel with the Range Start frame value. |
| `rangeend` | Range End | Toggle | Output a channel with the Range End frame value. |
| `signature1` | Signature 1 | Toggle | Output a channel for the first number in the timing signature, how many beats are in a measure. |
| `signature2` | Signature 2 | Toggle | Output a channel for the second number in the timing signature, which kind of note constitutes one beat. |
| `bpm` | BPM | Toggle | Output a channel with the BPM value. |
| `play` | Play | Toggle | Output a channel with the current play state. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP timelineCHOP operator
timelinechop_op = op('timelinechop1')

# Get/set parameters
freq_value = timelinechop_op.par.active.eval()
timelinechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
timelinechop_op = op('timelinechop1')
output_op = op('output1')

timelinechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(timelinechop_op)
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
