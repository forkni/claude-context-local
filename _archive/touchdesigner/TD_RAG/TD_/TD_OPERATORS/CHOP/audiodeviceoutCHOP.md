# CHOP audiodeviceoutCHOP

## Overview

The Audio Device Out CHOP sends audio to any of the attached audio output devices using DirectSound/CoreAudio or ASIO.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turns the audio output on or off. |
| `driver` | Driver | Menu | Select between default DirectSound/CoreAudio or ASIO drivers. |
| `device` | Device | StrMenu | A menu of available audio devices to output to. Selecting default sets the audio device to that which is selected in Windows Control Panel>Sounds and Audio Devices>Audio>Sound Playback. |
| `errormissing` | Error if Missing | Toggle | The CHOP will error if the specified device is not found. |
| `outputs` | Outputs | StrMenu | When Driver is set to ASIO on Windows or CoreAudio on macOS, this parameter lets you pick which output channels to use. |
| `bufferlength` | Buffer Length | Float | The length of the audio buffer in seconds. Audio output is delayed by this amount. For example, if the Buffer Length is 0.25 then the sound will occur 250ms = 0.25 seconds later than this CHOP rece... |
| `adjustspeed` | Adjust Speed | Float | This value controls how forcefully the output queue is modified when it grows too long or too short. A larger value recovers the queue size more quickly, but results in audible pitch changes. |
| `volume` | Volume | Float | 0 = mute, 1 = full volume. |
| `pan` | Pan | Float | 0 = left, 0.5 = centered, 1 = right. |
| `clampoutput` | Clamp Output | Toggle | Clamps the output between -1 and 1 to avoid clipping and overdriving of the audio system. |
| `cookalways` | Cook Every Frame | Toggle | Forces the CHOP to cook every frame. This should be checked on at all times when outputing audio. It can be turned off when the CHOP is not in use. |
| `stereo` | Stereo Mode |  | Set to simple stereo left/right output mode. |
| `frontleft` | Front Left | Toggle | Enable this output if available. |
| `frontright` | Front Right | Toggle | Enable this output if available. |
| `frontcenter` | Front Center | Toggle | Enable this output if available. |
| `lowfrequency` | Low Frequency | Toggle | Enable this output if available. |
| `backleft` | Back Left | Toggle | Enable this output if available. |
| `backright` | Back Right | Toggle | Enable this output if available. |
| `frontleftcenter` | Front Left of Center | Toggle | Enable this output if available. |
| `frontrightcenter` | Front Right of Center | Toggle | Enable this output if available. |
| `backcenter` | Back Center | Toggle | Enable this output if available. |
| `sideleft` | Side Left | Toggle | Enable this output if available. |
| `sideright` | Side Right | Toggle | Enable this output if available. |
| `topcenter` | Top Center | Toggle | Enable this output if available. |
| `topfrontleft` | Top Front Left | Toggle | Enable this output if available. |
| `topfrontcenter` | Top Front Center | Toggle | Enable this output if available. |
| `topfrontright` | Top Front Right | Toggle | Enable this output if available. |
| `topbackleft` | Top Back Left | Toggle | Enable this output if available. |
| `topbackcenter` | Top Back Center | Toggle | Enable this output if available. |
| `topbackright` | Top Back Right | Toggle | Enable this output if available. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiodeviceoutCHOP operator
audiodeviceoutchop_op = op('audiodeviceoutchop1')

# Get/set parameters
freq_value = audiodeviceoutchop_op.par.active.eval()
audiodeviceoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiodeviceoutchop_op = op('audiodeviceoutchop1')
output_op = op('output1')

audiodeviceoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiodeviceoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **36** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
