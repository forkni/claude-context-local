# TOP videostreaminTOP

## Overview

The Video Stream In TOP creates a client to receive video and audio across the network from RTSP, HLS, or SRT sources; or from a WebRTC peer via a WebRTC DAT.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When set to one, the TOP captures the image stream from the specified url. |
| `mode` | Mode | Menu | Select the mode: either a Server (for RTSP, HLS or SRT URLs), or WebRTC. |
| `url` | Server URL | Str | The URL (address) of the stream, see summary above for specific details. |
| `reload` | Reload | Toggle | Reload the stream by attempting to reconnect. |
| `reloadpulse` | Reload Pulse | Pulse | Triggers the Reload immediately on release (button-up). This can be accessed in python using the pulse() method. |
| `play` | Play | Toggle | The stream will play forward when Play = On, it will be paused when Off. |
| `deinterlace` | Deinterlace | Menu | For movies that are stored as fields, where each image is made of two images interleaved together. A 30-frame per second movie would contain 60 fields per second. For each image, the even scanlines... |
| `precedence` | Field Precedence | Menu | Where fields are extracted one field at a time, this will extract the Even field first by default, otehrwise it will extract the odd field first. The industry has not standardized on one or the other. |
| `bottomhalfalpha` | Bottom Half is Alpha (AAA) | Toggle | This is a way of encoding alpha into RGB-only formats like H.264. and several other QuickTime formats. You need to create your movies so that the bottom half of the image is the alpha (RGB = AAA). ... |
| `prereadframes` | Pre-Read Frames | Int | Sets how many video frames TouchDesigner reads ahead and stores in memory. Using this, smooth reading of an image stream is possible even when the disk files are fragmented. The Movie File In TOP w... |
| `maxdecodecpus` | Max Decode CPUs | Int | Limit the maximum number of CPUs that will be used to decode certain codecs that are capable of multi-CPU decoding, such as H264. |
| `networkbuffersize` | Network Buffer Size (KB) | Float | Specify the size of the network input buffer in kilobytes. |
| `networkqueuesize` | Network Queue Size (4KB Each) | Int | Specify the number of 4KB chunks to assign to the network queue. This is data stored after being read off of the network input buffer. |
| `disablebuffering` | Disable Buffering | Toggle |  |
| `hwdecode` | Hardware Decode | Toggle | Enables hardware decoding on Nvidia GPUs. |
| `webrtc` | WebRTC DAT | DAT | Set the WebRTC DAT (ie. peer) to get the video stream from. Setting this will automatically populate the WebRTC Connection parameter menu with available connections. |
| `webrtcconnection` | WebRTC Connection | StrMenu | Select the WebRTC peer-to-peer connection. Selecting this will automatically population the WebRTC Track parameter menu with available video input tracks. |
| `webrtctrack` | WebRTC Track | StrMenu | Select the video input track that's a part of the WebRTC peer-to-peer connection. |
| `outputresolution` | Output Resolution | Menu | quickly change the resolution of the TOP's data. |
| `resolution` | Resolution | Int | Enabled only when the Resolution parameter is set to Custom Resolution. Some Generators like Constant and Ramp do not use inputs and only use this field to determine their size. The drop down menu ... |
| `resmenu` | Resolution Menu | Pulse | A drop-down menu with some commonly used resolutions. |
| `resmult` | Use Global Res Multiplier | Toggle | Uses the Global Resolution Multiplier found in Edit>Preferences>TOPs. This multiplies all the TOPs resolutions by the set amount. This is handy when working on computers with different hardware spe... |
| `outputaspect` | Output Aspect | Menu | Sets the image aspect ratio allowing any textures to be viewed in any size. Watch for unexpected results when compositing TOPs with different aspect ratios. (You can define images with non-square p... |
| `aspect` | Aspect | Float | Use when Output Aspect parameter is set to Custom Aspect. |
| `armenu` | Aspect Menu | Pulse | A drop-down menu with some commonly used aspect ratios. |
| `inputfiltertype` | Input Smoothness | Menu | This controls pixel filtering on the input image of the TOP. |
| `fillmode` | Fill Viewer | Menu | Determine how the TOP image is displayed in the viewer. NOTE:To get an understanding of how TOPs work with images, you will want to set this to Native Resolution as you lay down TOPs when starting ... |
| `filtertype` | Viewer Smoothness | Menu | This controls pixel filtering in the viewers. |
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. For every pass after the first it takes the result of the previous pass and replaces the node's first input with the result of the... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP videostreaminTOP operator
videostreamintop_op = op('videostreamintop1')

# Get/set parameters
freq_value = videostreamintop_op.par.active.eval()
videostreamintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
videostreamintop_op = op('videostreamintop1')
output_op = op('output1')

videostreamintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(videostreamintop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
