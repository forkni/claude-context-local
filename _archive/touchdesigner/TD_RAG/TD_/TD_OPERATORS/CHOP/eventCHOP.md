# CHOP eventCHOP

## Overview

The Event CHOP manages the birth and life of overlapping events triggered by devices like a MIDI keyboard.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `id` | ID | Str | The sequence # of the event, starting from 0 and incrementing by 1 for each event. |
| `index` | Index | Str | The channel index of the incoming CHOP that caused the event. |
| `active` | Active | Str | While the input is greater than 0 this channel goes to 1, ie when the input channel goes "On". |
| `input` | Input | Str | The value of the input channel when the input went on (at the birth of the event). It is often the note velocity value. If you pass the Midi In CHOP into the Event CHOP, and set the Midi In option ... |
| `time` | Time | Str | Time in seconds from the start of the event. |
| `adsr` | ADSR | Str | The value according to the Attack, Decay, Sustain, Release. It uses the parameters on the ADSR page, regulating the speed and values, with extended parameters: Attack Time, Attack Level, Decay Time... |
| `state` | State | Str | This is good for playing back movies. You divide your movie into 4 parts that correspond to the (0=attack, 1=decay, 2=sustain, 3=release) phases. The state channel outputs fractional values, so you... |
| `resetcondition` | Reset Condition | Menu | Determines the reset behavior of using the 2nd Input Reset Trigger. This parameter is only active if there is an input connected to the CHOP's 2nd input. |
| `reset` | Reset | Toggle | When set to 'On' it resets the CHOP clearing all events. |
| `resetpulse` | Reset Pulse | Pulse | Immediately resets the CHOP and clears all events in the frame it was clicked. |
| `callbacks` | Callbacks DAT | DAT | The path to a DAT containing onCreate() and onDestroy() callbacks for each event. |
| `attacktime` | Attack Time | Float | Affects adsr and state channel. Time to rise to max attack level. |
| `attacktunit` | Attack Time Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `attacklevel` | Attack Level | Float | Affects adsr channel. Peak attack level. |
| `decaytime` | Decay Time | Float | Affects adsr channel and state channel. Time after peak to sustain level. |
| `decaytunit` | Decay Time Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `sustaintime` | Sustain Time | Float | Affects adsr channel. |
| `sustaintunit` | Sustain Time Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `sustainmin` | Sustain Min | Float | Affects adsr channel. Level at start of sustain time. |
| `sustainmax` | Sustain Max | Float | Affects adsr channel. Level at end of sustain time. |
| `releasetime` | Release Time | Float | Affects adsr and state channels. |
| `releasetunit` | Release Time Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `releaselevel` | Release Level | Float | Affects adsr channel. Level at end of life cycle. |
| `speed` | Speed | Float | Affects the speed of the event, letting you stretch out or shorten the life of an event. |
| `globalspeed` | Global Speed | Float |  |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP eventCHOP operator
eventchop_op = op('eventchop1')

# Get/set parameters
freq_value = eventchop_op.par.active.eval()
eventchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
eventchop_op = op('eventchop1')
output_op = op('output1')

eventchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(eventchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
