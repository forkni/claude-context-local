# CHOP audiostreaminCHOP

## Overview

The Audio Stream In CHOP can stream audio into TouchDesigner from any rtsp server.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `srctype` | Source Type | Menu | Select the source type: either from a server URL, or a WebRTC peer. |
| `url` | Server URL | Str | The URL address of the stream. E.g rtsp://localhost:554/tdaudio |
| `videostreamintop` | Video Stream In TOP | TOP | Point to a Video Stream In TOP whose stream has audio embedded to extract the audio channels. |
| `play` | Play | Float | Turns the audio streaming on (1) or off (0). |
| `opentimeout` | Open Timeout | Float | The time (in milliseconds) TouchDesigner will wait attempting to open the audio stream. |
| `syncoffset` | Audio Sync Offset | Float | Offsets the audio playback of the movie. This can be used to get better sync between the audio and images in the stream when there is audio latency in the system (For example, audio latency from th... |
| `syncoffsetunit` | Audio Sync Offset Unit | Menu | Specify which units to use for the Audio Sync Offset parameter. |
| `volume` | Volume | Float | 0 = mute, 1 = full volume. |
| `webrtc` | WebRTC DAT | DAT | Set the WebRTC DAT (ie. peer) to get the audio stream from. Setting this will automatically populate the WebRTC Connection parameter menu with available connections. |
| `webrtcconnection` | WebRTC Connection | StrMenu | Select the WebRTC peer-to-peer connection. Selecting this will automatically population the WebRTC Track parameter menu with available audio input tracks. |
| `webrtctrack` | WebRTC Track | StrMenu | Select the audio input track that's a part of the WebRTC peer-to-peer connection. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiostreaminCHOP operator
audiostreaminchop_op = op('audiostreaminchop1')

# Get/set parameters
freq_value = audiostreaminchop_op.par.active.eval()
audiostreaminchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiostreaminchop_op = op('audiostreaminchop1')
output_op = op('output1')

audiostreaminchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiostreaminchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
