# CHOP pulseCHOP

## Overview

The Pulse CHOP generates pulses in one channel at regular intervals.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `number` | Number of Pulses | Int | The number of pulses to generate. |
| `interp` | Interpolate | Menu | You can interpolate the values between pulses using the following function curves: |
| `width` | Pulse Width | Float | By default, the pulses are a single sample long, but you can increase the Pulse Width so that the pulses are steps to the next pulse. |
| `widthunit` | Pulse Width Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `limit` | Limit Type | Menu | Enable the Minimum and Maximum clamping values below with this menu. |
| `min` | Minimum | Float | The pulses can be restricted to a Minimum limit. If the Limit Type is Clamp, the graph has additional convenient handles at the minimum for each pulse. |
| `max` | Maximum | Float | The pulses can be restricted to a Maximum limit. If the Limit Type is Clamp, the graph has additional convenient handles at the maximum for each pulse. |
| `minspacing` | Minimum Spacing | Float | When creating pulses via the second input, the Minimum Spacing parameter will separate out pulses from each other with the minimum distance specified here. The unit of the spacing is controlled by ... |
| `cascade` | Cascade when Spacing | Toggle | When minimum spacing between pulses is enabled, cascading will shift pulses by the amount of samples added via the minimum spacing. |
| `outpulse` | Outside Pulses | Menu | Control how to deal with pulse positions specified outside the operators range. |
| `pulseunit` | Pulse Index Unit | Menu | Control what unit the in the second input specified values should be interpreted as. |
| `separateoutchan` | Separate Output Channels | Toggle | When toggled on, will create a seperate channel per pulse. |
| `nonadditives` | Non-Additives | Toggle | When enabled will not add up amplitudes of pulses specified on the same sample index. |
| `lastpulse` | Last Pulse at Last Sample | Toggle | In order to set the value at the last sample, the option Last Pulse at Last Sample is provided. Otherwise, the last pulse is prior to the last sample. |
| `pulse` | Pulse | Sequence | Sequence of pulse values |
| `channelname` | Channel Names | Str | You can creates many channels with simple patterns like "chan[1-20]", which generates 20 channels from chan1 to chan20. See the section, Common CHOP Parameters for a description of this and all Opt... |
| `start` | Start | Float | Start of the interval, expressed in Units (seconds, frames or samples). |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | End of the interval, expressed in Units (seconds, frames or samples). |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. Default: me.time.rate |
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
# Access the CHOP pulseCHOP operator
pulsechop_op = op('pulsechop1')

# Get/set parameters
freq_value = pulsechop_op.par.active.eval()
pulsechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pulsechop_op = op('pulsechop1')
output_op = op('output1')

pulsechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pulsechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **30** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
