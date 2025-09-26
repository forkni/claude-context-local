# CHOP audiofileinCHOP

## Overview

The Audio File In CHOP reads audio from files on disk or at http:// addresses.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | Path of source. |
| `reloadpulse` | Reload | Pulse | Instantly reload the file from disk. |
| `play` | Play | Toggle | Audio will playback when this is set to 1 and stop when set to 0. |
| `playmode` | Play Mode | Menu | Specifies the method used to playback the audio, there are 3 options. |
| `speed` | Speed | Float | This is a speed multiplier which only works when Play Mode is Sequential. A value of 1 is the default playback speed. A value of 2 is double speed, 0.5 is half speed and so on. This node can not pl... |
| `cue` | Cue | Toggle | Jumps to Cue Point when set to 1. Only available when Play Mode is Sequential. |
| `cuepulse` | Cue Pulse | Pulse | Instantly jumps to the Cue Point. |
| `cuepoint` | Cue Point | Float | Set any index in the song as a point to jump to. |
| `cuepointunit` | Cue Point Unit | Menu | Units used when setting the Cue Point parameter. |
| `index` | Index | Float | This parameter explicitly sets the song position when Play Mode is set to Specify Index. The units menu on the right lets you specify the index in the following units: Index, Frames, or Seconds. |
| `indexunit` | Index Unit | Menu | Units used for the Index parameter. |
| `timecodeop` | Timecode Object/CHOP/DAT | Str | Set the audio file index with a reference to a timecode. Should be a reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or... |
| `repeat` | Repeat | Menu | Repeats the audio stream when the end is reached. |
| `trim` | Trim | Toggle | Enables the Trim parameters below. |
| `trimstart` | Trim Start | Float | Sets an In point from the beginning of the audio, allowing you to trim the starting position of the audio stream. The units menu on the right let you specify this position by index, frames, or seco... |
| `trimstartunit` | Trim Start Unit | Menu | Units used for the Trim Start parameter. |
| `trimend` | Trim End | Float | Sets an Out point from the end of the audio, allowing you to trim the ending position of the audio stream. The units menu on the right let you specify this position by index, frames, or seconds. |
| `trimendunit` | Trim End Unit | Menu | Units used for the Trim End parameter. |
| `prereadlength` | Pre-Read Length | Float | The amount of audio to buffer to maintain smooth playback. This will slightly impact memory usage, but does not create any delay in the audio. |
| `prereadlengthunit` | Pre-Read Length Unit | Menu | Units used for the Pre-Read Length parameter. |
| `opentimeout` | Open Timeout | Float | The time (in milliseconds) TouchDesigner will wait for the audio file to open. If the Open Timeout time is reached, the Audio File In CHOP will stop waiting, and play silence. If the file still isn... |
| `mono` | Mono | Toggle | Output mono channel only even if file has multiple channels. |
| `volume` | Volume | Float | Set the level the file is read in at. A setting of 1 is full signal while 0 is muted. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiofileinCHOP operator
audiofileinchop_op = op('audiofileinchop1')

# Get/set parameters
freq_value = audiofileinchop_op.par.active.eval()
audiofileinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiofileinchop_op = op('audiofileinchop1')
output_op = op('output1')

audiofileinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiofileinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **29** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
