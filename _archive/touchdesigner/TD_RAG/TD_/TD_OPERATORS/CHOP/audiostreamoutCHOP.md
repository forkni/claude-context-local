# CHOP audiostreamoutCHOP

## Overview

The Audio Stream Out CHOP can stream audio out to any rtsp client such as VideoLAN's VLC media player and Apple's Quicktime, or to a WebRTC peer.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Toggle's the rtsp server on or off. |
| `mode` | Mode | Menu | Select the stream out mode: either RTSP or WebRTC. |
| `port` | Port | Int | Port number used to transmit the audio stream. This number is needed in the URL supplied to the client receiving the stream. See example in Summary at top. |
| `streamname` | Stream Name | Str | Name assigned to the stream. This stream name is needed in the URL supplied to the client receiving the stream. See example in Summary at top. |
| `webrtc` | WebRTC | DAT | Set the WebRTC DAT (ie. peer) to send the audio stream over. Setting this will automatically populate the WebRTC Connection parameter menu with available connections. |
| `webrtcconnection` | WebRTC Connection | StrMenu | Select the WebRTC peer-to-peer connection. Selecting this will automatically population the WebRTC Track parameter menu with available audio output tracks. |
| `webrtctrack` | WebRTC Track | StrMenu | Select the audio output track that's a part of the WebRTC peer-to-peer connection. The audio stream will be sent over this track. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiostreamoutCHOP operator
audiostreamoutchop_op = op('audiostreamoutchop1')

# Get/set parameters
freq_value = audiostreamoutchop_op.par.active.eval()
audiostreamoutchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiostreamoutchop_op = op('audiostreamoutchop1')
output_op = op('output1')

audiostreamoutchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiostreamoutchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **13** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
