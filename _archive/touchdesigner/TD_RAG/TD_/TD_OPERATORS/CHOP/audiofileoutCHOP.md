# CHOP audiofileoutCHOP

## Overview

The Audio File Out CHOP saves an audio stream out to a file using a variety of different codecs.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `filetype` | File Type | Menu | Select the file type (container) of the output file. |
| `uniquesuff` | Unique Suffix | Toggle | When enabled, me.fileSuffix will be a unique suffix when used in the file parameter. |
| `n` | N | Int | When unique suffix is disabled, me.fileSuffix will simply contain the value of N, instead of being unique |
| `file` | File | File | Sets the path and filename of the audio file that is saved out. The file extension must match the file type parameter. |
| `codec` | Codec | Menu | Select the compression codec for the WAV file type. |
| `bitrate` | Bit Rate | Menu | Selects the bit rate for the MP3 file type. |
| `record` | Record | Toggle | When toggled on, it will open the audio file and begin recording. When toggled off, it will close the file and release the read/write lock. |
| `pause` | Pause | Toggle | Pauses the recording of the audio to the audio file. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiofileoutCHOP operator
audiofileoutchop_op = op('audiofileoutchop1')

# Get/set parameters
freq_value = audiofileoutchop_op.par.active.eval()
audiofileoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiofileoutchop_op = op('audiofileoutchop1')
output_op = op('output1')

audiofileoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiofileoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
