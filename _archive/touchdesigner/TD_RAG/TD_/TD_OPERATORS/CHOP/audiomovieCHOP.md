# CHOP audiomovieCHOP

## Overview

The Audio Movie CHOP plays the audio of a movie file that is played back with a Movie File In TOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `play` | Play | Toggle | Audio playback is enabled when this is set to On. No audio output when Off. |
| `moviefileintop` | Movie File In TOP | TOP | Put the path of a Movie File In TOP in this parameter. The file named in the Movie File In TOP will be the source for the audio. |
| `prereadlength` | Pre-Read Length | Float | Use to read-ahead the audio into cache. You can specify in samples, frames and in seconds using the Units menu. |
| `prereadlengthunit` | Pre-Read Length Unit | Menu | Specify which units to use for the Pre-Read Length parameter. |
| `opentimeout` | Open Timeout | Float | The amount of time TouchDesigner will wait for the audio samples to be read from the movie file. On file opening, if this timeout period is reached and the read-ahead has not finished, the audio wi... |
| `syncoffset` | Audio Sync Offset | Float | Offsets the audio playback of the movie. This can be used to get better sync between the audio and images in the movie when there is audio latency in the system (For example, audio latency from the... |
| `syncoffsetunit` | Audio Sync Offset Unit | Menu | Specify which units to use for the Audio Sync Offset parameter. |
| `index` | Index Channel | Toggle | Turn this parameter On to output an additional channel which reports the current position in the movie ie. 0 = start, 1 = end. |
| `audiotrack` | Audio Track Index | Int | When the movie has multiple audio tracks available this parameter can select between them. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiomovieCHOP operator
audiomoviechop_op = op('audiomoviechop1')

# Get/set parameters
freq_value = audiomoviechop_op.par.active.eval()
audiomoviechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiomoviechop_op = op('audiomoviechop1')
output_op = op('output1')

audiomoviechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiomoviechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
