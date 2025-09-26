# CHOP audiodeviceinCHOP

## Overview

The Audio Device In CHOP receives audio from any of the attached audio input devices using DirectSound/CoreAudio or ASIO.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turns the audio input on or off. |
| `driver` | Driver | Menu | Select between default DirectSound/CoreAudio, ASIO, or native device supported drivers. |
| `device` | Device | StrMenu | A menu of available audio devices to receive input from. Selecting default sets the audio device to that which is selected in Windows Control Panel>Sounds and Audio Devices>Audio>Sound Recording. |
| `errormissing` | Error if Missing | Toggle | The CHOP will error if the specified device is not found. |
| `inputs` | Inputs | StrMenu | When Driver is set to ASIO on Windows or CoreAudio on macOS, this parameter lets you pick which input channels to use. |
| `format` | Format | Menu | When Driver is set to DirectSound, this set mono, stereo, or multi-channel. Also determines how many channels are created 1(mono) or 2(stereo left and stereo right), or when set to multi-channel se... |
| `rate` | Rate | Float | Audio input sample rate expressed in samples per second. |
| `bufferlength` | Buffer Length | Float | The size of the input buffer, will effect latency.  The larger the buffer the more latency is introduced. |
| `numchan` | Number of Channels | Int | When using Driver Blackmagic or AJA, use this parameter to set the number of channels. |
| `frontleft` | Front Left | Toggle | Enable this input if available (or simply adds another input channel). |
| `frontright` | Front Right | Toggle | Enable this input if available (or simply adds another input channel). |
| `frontcenter` | Front Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `lowfrequency` | Low Frequency | Toggle | Enable this input if available (or simply adds another input channel). |
| `backleft` | Back Left | Toggle | Enable this input if available (or simply adds another input channel). |
| `backright` | Back Right | Toggle | Enable this input if available (or simply adds another input channel). |
| `frontleftcenter` | Front Left of Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `frontrightcenter` | Front Right of Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `backcenter` | Back Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `sideleft` | Side Left | Toggle | Enable this input if available (or simply adds another input channel). |
| `sideright` | Side Right | Toggle | Enable this input if available (or simply adds another input channel). |
| `topcenter` | Top Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `topfrontleft` | Top Front Left | Toggle | Enable this input if available (or simply adds another input channel). |
| `topfrontcenter` | Top Front Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `topfrontright` | Top Front Right | Toggle | Enable this input if available (or simply adds another input channel). |
| `topbackleft` | Top Back Left | Toggle | Enable this input if available (or simply adds another input channel). |
| `topbackcenter` | Top Back Center | Toggle | Enable this input if available (or simply adds another input channel). |
| `topbackright` | Top Back Right | Toggle | Enable this input if available (or simply adds another input channel). |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiodeviceinCHOP operator
audiodeviceinchop_op = op('audiodeviceinchop1')

# Get/set parameters
freq_value = audiodeviceinchop_op.par.active.eval()
audiodeviceinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiodeviceinchop_op = op('audiodeviceinchop1')
output_op = op('output1')

audiodeviceinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiodeviceinchop_op)
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
