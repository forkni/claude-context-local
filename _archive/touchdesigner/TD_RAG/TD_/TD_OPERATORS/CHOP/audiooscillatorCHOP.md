# CHOP audiooscillatorCHOP

## Overview

The Audio Oscillator CHOP generates sounds in three ways.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `wavetype` | Type | Menu | The shape of the waveform to repeat, unless overridden by the Playback Source: |
| `frequency` | Base Frequency | Float | The cycles per second when the Pitch Control is zero. |
| `octave` | Units per Octave | Float | Amount that the Pitch Control needs to increase by to raise the pitch by one octave. The default of 1 means that Pitch Control of 1 raises the pitch by 1 octave. Units per Octave of .08333 means th... |
| `offset` | Offset | Float | Values output from the CHOP can have an offset added to them. |
| `amp` | Amplitude | Float | Values output from the CHOP can be scaled. |
| `bias` | Bias | Float | Shape control for Triangle, Gaussian and Square waves. For triangle waves, it moves the peak. For square waves, it alters the width of the peak. Zero means no bias. |
| `phase` | Phase | Float | A value of .5 is a phase shift of 180 degrees, or one half cycle. |
| `smooth` | Smooth Pitch Changes | Toggle | If the Pitch Control channel input to the Audio Oscillator CHOP is rising and is running at the Touch default of 60 frames per second, then the pitch will hold for 1/60 second before stepping up fo... |
| `resetcondition` | Reset Condition | Menu | This menu determines how the Reset input triggers a reset of the channel(s). |
| `reset` | Reset | Toggle | This button resets the channel(s) to 0 when On. |
| `resetpulse` | Reset Pulse | Pulse | Instantly resets the channel(s) to 0. |
| `rate` | Sample Rate | Float | Set the sample rate of the CHOP in samples per second. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiooscillatorCHOP operator
audiooscillatorchop_op = op('audiooscillatorchop1')

# Get/set parameters
freq_value = audiooscillatorchop_op.par.active.eval()
audiooscillatorchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiooscillatorchop_op = op('audiooscillatorchop1')
output_op = op('output1')

audiooscillatorchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiooscillatorchop_op)
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
