# CHOP midioutCHOP

## Overview

The MIDI Out CHOP sends MIDI events to any available MIDI devices when its input channels change.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enable or disable the MIDI Out CHOP. |
| `destination` | MIDI Destination | Menu | Where the MIDI events are sent to. MIDI Mapper is the default destination. |
| `device` | Device Table | DAT | Path to the MIDI device Table DAT. |
| `id` | Device ID | Str | Specify the id of which device to use. |
| `onebased` | One Based Index | Toggle | Make the index 1 based instead of the default 0 based. |
| `file` | MIDI File | File | The filename of the output MIDI file. |
| `writefile` | Write MIDI File | Pulse | Writes all the data to a MIDI file. |
| `prefix` | Channel Prefix | Str | The prefix string that all input channels must have in order to extract the channel number from their name (i.e. "ch1note44", with a channel prefix of "ch"). |
| `cookalways` | Cook Every Frame | Toggle | Forces a cook of the CHOP every frame. It should be On because the MIDI Out CHOP will otherwise only cook if the CHOP leads to a graphics display viewer. You want it to cooks whether you are displa... |
| `autonoteoff` | Automatic Note Off | Menu | A MIDI 'All Note Off' event can be sent upon the start and/or end of the output. |
| `reset` | All Notes Off | Pulse | Sends an All Notes Off message to all MIDI channels. |
| `volumeoff` | All Volume Off | Pulse | Sends an All Notes Off message to all MIDI channels. |
| `volumeon` | All Volume On | Pulse | Sends an All Notes On message to all MIDI channels. |
| `startstop` | Send Start/Stop/Continue Events | Toggle | Sends the appropriate events when the framebar starts or stops. |
| `sendmtc` | Send MIDI Timecode | Toggle | While enabled, the MIDI Out CHOP will send MIDI Timecode (MTC) as a stream of quarter frame messages. |
| `timecodeop` | Timecode Object/CHOP/DAT | Str | The MIDI Timecode value to send. Should be a reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or a Timecode Class object. |
| `notename` | Note Name | Str | The base name of the note channels. If input channels have a number after the name, it is assumed to be the note number. If not, the channel value is assumed to contain the note number. |
| `aftername` | Aftertouch Name | Str | The name of the aftertouch channel. |
| `pressname` | Pressure Name | Str | The name of the channel pressure channel. |
| `notenorm` | Normalize | Menu | Values in the range 0-1 are mapped to MIDI value 0-127. |
| `pitchname` | Pitch Wheel Name | Str | The name of the pitch wheel channel. |
| `controlname` | Controller Name | Str | The base name of the controller channels. |
| `controlformat` | Controller Format | Menu | Sends 7 or 14 bit controller events. |
| `controlnorm` | Normalize | Menu | Maps channel values from different ranges to 0-127. |
| `progname` | Program Change | Str | The name of the program change channel. |
| `barname` | Bar Ramp Name | StrMenu | Clock ticks frequency is determined by the period of the ramp. The ramp must be 0 to 1. An incoming channel name for a 0 to 1 ramp over each 4-beat bar. |
| `barticks` | Ticks per Bar | Int | Default is 96 = 4 beats * 24 ticks per beat. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP midioutCHOP operator
midioutchop_op = op('midioutchop1')

# Get/set parameters
freq_value = midioutchop_op.par.active.eval()
midioutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
midioutchop_op = op('midioutchop1')
output_op = op('output1')

midioutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(midioutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
