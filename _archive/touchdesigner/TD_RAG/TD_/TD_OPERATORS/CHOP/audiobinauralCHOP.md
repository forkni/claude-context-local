# CHOP audiobinauralCHOP

## Overview

The Audio Binaural CHOP uses the Steam Audio API to convert from multi-channel speaker-based audio (eg. stereo, quadraphonic, 5.1, 7.1, etc.) to binaural using HRTF-based binaural rendering. The HRTF used is the default provided by Steam Audio. The Audio Binaural CHOP is useful for converting audio from a variety of formats to a 2-channel binaural

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When enabled, will be actively performing binaural rendering. When disabled, the channels will be zeroed. |
| `inputformat` | Input Format | Menu | Select the input format to convert from. The input CHOP is required to have the correct number of channels (eg. 6 for 5.1 Surround). |
| `ambisonicsorder` | Ambisonics Order | Int | Used in conjunction with ambisonics input format. Supports ambisonics order 1-3 Determines how many channels are required from the input. Ambisonics order 1, 2, 3 require 4, 9, 16 channels respecti... |
| `listener` | Listener | Int | Optionally specify a listener object when using an ambisonics input. The listener's orientation will be applied before binaural rendering. |
| `mappingtable` | Mapping Table | DAT | A DAT Table that specifies the various speakers in the setup and their position. The Table must have 3 columns named x, y, z. Each row specifies an individual speaker, and the 3 columns specify its... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiobinauralCHOP operator
audiobinauralchop_op = op('audiobinauralchop1')

# Get/set parameters
freq_value = audiobinauralchop_op.par.active.eval()
audiobinauralchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiobinauralchop_op = op('audiobinauralchop1')
output_op = op('output1')

audiobinauralchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiobinauralchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
