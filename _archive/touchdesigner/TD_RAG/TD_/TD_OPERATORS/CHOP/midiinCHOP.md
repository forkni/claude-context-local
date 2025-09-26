# CHOP midiinCHOP

## Overview

The MIDI In CHOP reads Note events, Controller events, Program Change events, System Exclusive messages and Timing events from both MIDI devices and files.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enable or disable the MIDI In CHOP. |
| `source` | MIDI Source | Menu | Get MIDI input from a device or a file. |
| `device` | Device Table | DAT | Path to the MIDI device Table DAT |
| `id` | Device ID | Str | Specify the id of which device to use. |
| `file` | MIDI File | File | If MIDI file is selected as the MIDI source use this field to specify the name of the MIDI file to read. The file can be read in from disk or from the web. Use http:// when specifying a URL. |
| `entire` | Read Entire MIDI File | Toggle | If enabled, the entire MIDI file is read. Otherwise, the Start and End parameters on the Channel page determine the segment of the file to read. |
| `resetchannels` | Reset Channels | Toggle | Deletes all channels when set to On, new channels will not be added until Reset Channels is turned Off. |
| `resetchannelspulse` | Reset Channels Pulse | Pulse | Instantly resets all channels to 0. |
| `resetvalues` | Reset Values |  | Resets all channel values to 0 when On, channel values will not be updated until Reset Values is turned Off. |
| `simplified` | Simplified Output | Toggle | When this is on channels are automatically created when MIDI signal is detected from the selected MIDI device. |
| `preservepulses` | Preserve Pulses | Toggle | When on, quick value transitions (pulses) are spaced out over consecutive output samples. Use this option when pulse frequencies approach or exceed the timeline rate, otherwise they risk overlappin... |
| `onebased` | 1 Based Index | Toggle | Make the index 1 based instead of the default 0 based. |
| `channel` | MIDI Channels | Str | The CHOP may read from any number of MIDI channels, numbered 1-16. Ranges and multiple entries are supported (i.e. "1 4 6", "1-7 12", "1-5:2").       If Channel Prefix is left blank, then the input... |
| `prefix` | Channel Prefix | Str | When recording from multiple MIDI channels, putting a string like "ch" in this parameter causes the MIDI channel to be split into separate CHOP channels per MIDI channel. Otherwise the MIDI channel... |
| `recordtype` | Record Method | Menu | Determine what to record. |
| `record` | Record | Toggle | This parameter is used as a button to start and stop recording into the CHOP channels. |
| `notename` | Note Name | Str | Put an "n" in here to generate channels for note events. It is the base name of the CHOP channel used to record notes. If blank, notes are ignored. If the Note Output parameter is set to Separate C... |
| `notescope` | Note Scope | Str | The scope of notes to record. Multiple ranges and notes can be recorded (i.e., "50-60", "64 65 66 70-80"). |
| `notemeth` | Note Output | Menu | Describes how multiple notes are handled. (As one channel, or individual). |
| `velocity` | Velocity | Menu | Describes how multiple velocity events are recorded. (Separate channels or combined in one channel as separate samples). |
| `velname` | Velocity Name | Str | When Velocity is set to Separate Channels, this parameter is the base name of the Velocity CHOP channel (try "v"). If blank, no velocity channels will be recorded. |
| `aftername` | Aftertouch Name | Str | The base name of the polyphonic Aftertouch CHOP channels. One aftertouch channel is created for each note in the Note Scope. If blank, no aftertouch channels will be created. |
| `pressname` | Pressure Name | Str | The name of the Channel Pressure channel. If multiple channels are being recorded, all channel pressure changes of interest will be recording on this CHOP channel. If blank, this channel will not b... |
| `notenorm` | Normalize | Menu | Note values can be normalized for convenience: |
| `pitchname` | Pitch Wheel Name | Str | The name of the Pitch Wheel CHOP channel. Pitch wheel values range from -1 to +1. If blank, this channel will not be created. Put "p" in here to generate a channel. |
| `controlname` | Controller Name | Str | The base name of the Control Change CHOP channels. The channel names are appended with the controller index (0-127). If blank, control changes will not be recorded. It typically contains "c". |
| `controltype` | Controller Type | Menu | There are 128 different controllers available. By choosing By Index Only, you can specify any number of controllers in the Control Index parameter. Otherwise, you can select a controller from the l... |
| `controlind` | Controller Index | Str | Used to select controllers by number, or multiple controllers by ranges. When in By Index Only Controller Type mode, you can select up to the full 128 controllers or sub-ranges thereof (i.e. "1-10"... |
| `format` | Controller Format | Menu | Some controllers can be paired together to form 14 bit controllers, rather than the normal 7 bit controllers (controller indices 0-31, 98 and 100). Selecting 14 bit Controllers interprets a pair as... |
| `norm` | Normalize | Menu | Controller values can be normalized for convenience: |
| `unwrap` | Unwrap | Toggle | When on, values do not jump between min and max, but are modified to be continuous ramps. Use with knob controllers for examples. |
| `progname` | Program Change | Str | The name of the Program Change CHOP channel. All program change messages will be recorded onto this channel. If blank, this channel will not be created. |
| `pulsename` | Timer Pulse Name | Str | Record timer pulse messages. |
| `rampname` | Timer Ramp Name | Str | Record timer ramp messages. |
| `timerperiod` | Timer Period | Str | Record timer period messages. |
| `timerstart` | Timer Start | Str | Record timer start messages. |
| `ticks` | Ticks per Beat | Int | Specify the expected ticks per beat. This will influence the timer and bar output values. |
| `barname` | Bar Ramp Name | Str | Output the current bar position. |
| `barperiod` | Bar Period | Str | Output the current bar period events. |
| `barstart` | Bar Start | Str | Output when a bar starts. |
| `barmsg` | Bar Message | Str | Capture bar messages. Place a V in the message to specify which value the channel should have. |
| `songpos` | Song Pos Name | Str | Capture song position messages. |
| `sysex` | System Exclusive | Sequence | Sequence of system exclusive message handlers |
| `start` | Start | Float | Defines where recording begins. In "Tie to Time Line" mode, any events received before the start time will be ignored. In "Time Line Independent" mode, recording will start at this point and contin... |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | Defines the end of the segment to read for MIDI Files. |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `rate` | Sample Rate | Float | Defines the sample rate of this CHOP, in samples per second. If the sample rate is too low, a rapidly changing input may be misrepresented.      Note: If the sample rate is too low, you may miss MI... |
| `left` | Extend Left | Menu | The left extend conditions (before range). |
| `right` | Extend Right | Menu | The right extend conditions (after range). |
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
# Access the CHOP midiinCHOP operator
midiinchop_op = op('midiinchop1')

# Get/set parameters
freq_value = midiinchop_op.par.active.eval()
midiinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
midiinchop_op = op('midiinchop1')
output_op = op('output1')

midiinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(midiinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **57** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
