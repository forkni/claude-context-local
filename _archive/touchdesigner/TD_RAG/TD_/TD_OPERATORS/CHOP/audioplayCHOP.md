# CHOP audioplayCHOP

## Overview

The Audio Play CHOP plays back a sound file through any attached audio output device using DirectSound.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `device` | Device | StrMenu | A menu of available audio devices to output to. Selecting default sets the audio device to that which is selected in Windows Control Panel>Sound>Playback. |
| `outputs` | Outputs | StrMenu |  |
| `file` | Sound File | File | .aif, .mp3, .mid, .wav or .m4a audio file. The file can be mono or stereo. |
| `datlist` | DAT List | DAT | Links to a Table DAT which can be used as list of audio files to choose from. When using the DAT List, the first input (Input 0: Triggers) on the CHOP can contain mulitiple channels to fire the fil... |
| `volume` | Volume | Float | 0 = mute, 1 = full volume. Using the second input (Input 1: Volume) or the python .play(volume=val) method, will override the value of this parameter. |
| `mode` | Mode | Menu | Determines how the audio is triggered when using the first input to trigger. |
| `trigger` | Trigger | Pulse | Triggers the audio to play. |
| `cookalways` | Cook Every Frame | Toggle | Forces CHOP to cook every frame. |
| `stereo` | Stereo Mode | Toggle | Sets output to just 2 channels, front left and front right.       Outputs - The outputs on this page and the following Output 2 page are for routing to an audio device's different speaker outputs. ... |
| `frontleft` | Front Left | Int | Play audio on this output based on mapping table above. |
| `frontright` | Front Right | Int | Play audio on this output based on mapping table above. |
| `frontcenter` | Front Center | Int | Play audio on this output based on mapping table above. |
| `lowfrequency` | Low Frequency | Int | Play audio on this output based on mapping table above. |
| `backleft` | Back Left | Int | Play audio on this output based on mapping table above. |
| `backright` | Back Right | Int | Play audio on this output based on mapping table above. |
| `frontleftcenter` | Front Left of Center | Int | Play audio on this output based on mapping table above. |
| `frontrightcenter` | Front Right of Center | Int | Play audio on this output based on mapping table above. |
| `backcenter` | Back Center | Int | Play audio on this output based on mapping table above. |
| `sideleft` | Side Left | Int | Play audio on this output based on mapping table above. |
| `sideright` | Side Right | Int | Play audio on this output based on mapping table above. |
| `topcenter` | Top Center | Int | Play audio on this output based on mapping table above. |
| `topfrontleft` | Top Front Left | Int | Play audio on this output based on mapping table above. |
| `topfrontcenter` | Top Front Center | Int | Play audio on this output based on mapping table above. |
| `topfrontright` | Top Front Right | Int | Play audio on this output based on mapping table above. |
| `topbackleft` | Top Back Left | Int | Play audio on this output based on mapping table above. |
| `topbackcenter` | Top Back Center | Int | Play audio on this output based on mapping table above. |
| `topbackright` | Top Back Right | Int | Play audio on this output based on mapping table above. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audioplayCHOP operator
audioplaychop_op = op('audioplaychop1')

# Get/set parameters
freq_value = audioplaychop_op.par.active.eval()
audioplaychop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audioplaychop_op = op('audioplaychop1')
output_op = op('output1')

audioplaychop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audioplaychop_op)
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
