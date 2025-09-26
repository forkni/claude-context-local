# CHOP waveCHOP

## Overview

The Wave CHOP makes repeating waves with a variety of shapes.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `wavetype` | Type | Menu | There is a choice of waveforms shapes: |
| `period` | Period | Float | The period is the number of seconds, frames or samples that the waveform repeats in. It is expressed in the chop's Units (default is Seconds), found on the Common page. |
| `periodunit` | Period Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `phase` | Phase | Float | The phase shifts the waveform in time, and is expressed as a fraction of a period, usually between 0 and 1. |
| `bias` | Bias | Float | You can vary the shape of some of the waveform types by changing the bias within the range -1 to +1. |
| `offset` | Offset | Float | The waveform's value can be offset. A sine wave can remain always positive by setting Offset to 1. |
| `amp` | Amplitude | Float | The wave's value can be scaled. |
| `decay` | Decay Rate | Float | The wave's amplitude can be reduced over time with an "exponential decay". For example, if the Decay is 0.2 and the Units are seconds, then the amplitude will decay to 0.8 after 1 second, and 0.8 o... |
| `decayunit` | Decay Rate Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `ramp` | Ramp Slope | Float | Then a ramp is added to the result with a slope of Ramp. The channel increases by the Ramp Slope value every Unit of time. For example, if Ramp is 1.2, the channel increases by 1.2 every second, in... |
| `rampunit` | Ramp Slope Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `exprs` | Expression | Float | If the waveform type is Expression, the Expression parameter is used to input a math expression. Some local variables are available: $I (Index), $L (the loop variable over the period 0 to 1), $C (t... |
| `channelname` | Channel Names | Str | You can creates many channels with simple patterns like "chan[1-20]", which generates 20 channels from chan1 to chan20. See the section, Common CHOP Parameters for a description of this and all Opt... |
| `start` | Start | Float | Start of the interval, expressed in Units (seconds, frames or samples). |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | End of the interval, expressed in Units (seconds, frames or samples). |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before/after range). |
| `right` | Extend Right | Menu | The right extend conditions (before/after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP waveCHOP operator
wavechop_op = op('wavechop1')

# Get/set parameters
freq_value = wavechop_op.par.active.eval()
wavechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
wavechop_op = op('wavechop1')
output_op = op('output1')

wavechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(wavechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **27** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
