# CHOP lfoCHOP

## Overview

The LFO CHOP (low frequency oscillator) generates waves in real-time in two ways.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `wavetype` | Type | Menu | The shape of the waveform to repeat, unless overridden by the Source Wave: |
| `play` | Play | Toggle | The LFO oscillates when 1, and stops when 0. Think of it like play and pause. |
| `frequency` | Frequency | Float | The cycles per second of the oscillation. When the Octave Control input is connected, it alters the frequency exponentially. |
| `offset` | Offset | Float | Values output from the CHOP can have an offset added to them. |
| `amp` | Amplitude | Float | Values output from the CHOP can be scaled. |
| `bias` | Bias | Float | Shape control for Triangle, Gaussian and Square waves. For triangle waves, it moves the peak. For square waves, it alters the width of the peak. Zero means no bias. |
| `phase` | Phase | Float | A value of .5 is a phase shift of 180 degrees, or one half cycle. |
| `resetcondition` | Reset Condition | Menu | This menu determines how the Reset input triggers resetting the channel(s). |
| `reset` | Reset | Toggle | This toggle resets the channel(s) to 0 while On. |
| `resetpulse` | Reset Pulse | Pulse | This button instantly resets the channel(s) to 0. |
| `channelname` | Channel Name | Str | A list of the names of the channels. You can put patterns like chan[1-10] to generate 10 channels. See Pattern Expansion.      Each channel can be different by putting the channel index variable, $... |
| `rate` | Sample Rate | Float | The sample rate of the CHOP. The default sample rate is 60 samples per second. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP lfoCHOP operator
lfochop_op = op('lfochop1')

# Get/set parameters
freq_value = lfochop_op.par.active.eval()
lfochop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lfochop_op = op('lfochop1')
output_op = op('output1')

lfochop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lfochop_op)
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
