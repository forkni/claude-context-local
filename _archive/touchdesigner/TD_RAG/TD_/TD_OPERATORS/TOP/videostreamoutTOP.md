# TOP videostreamoutTOP

## Overview

The Video Stream Out TOP creates an RTSP server to send H.264 video and MP3 audio across the network.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Controls if the server is active or not. If this is Off then the port this server uses will not be tied up. |
| `mode` | Mode | Menu | Selects if the mode works as an RTSP server, sends RTMP to a receiever such as a distribution service like YouTube or Twitch, or sends to an SRT destination. |
| `port` | Network Port | Int | The port the server should listen on. Multiple Video Stream Out TOPs can use the same port as long as each has a unique Stream Name. |
| `streamname` | Stream Name | Str | The name of the stream for this node. This name is what comes after the / in the URL after the ipaddress:port combination. |
| `multicast` | Multi-Cast | Toggle | Controls if RTSP server sends its video out using unicast or multicast UDP packets. |
| `url` | Destination URL | Str | The URL to sent the RTMP stream to. This should be in the format of {service url}/{stream key}. For example for twitch the URL would be something like rtmp://live-yto.twitch.tv/app/live_1234567_sdu... |
| `forceidr` | Force IDR | Pulse | For debugging, this will force the server to create a new video keyframe to send to all the clients. If clients aren't getting proper image this can be used to attempt to fix it. If you need to use... |
| `fps` | FPS | Float | The FPS to send video at. |
| `videocodec` | Video Codec | Menu | Select which codec to use for encoding the stream. |
| `profile` | Profile | Menu | The H.264 profile to use to encode the frames. Some decoders can only support H.264 encoder at certain profiles. |
| `quality` | Quality | Menu | The quality level of the encoding. |
| `keyframeinterval` | Keyframe Interval | Int | Set the keyframe interval for the H.264 encoder. |
| `maxbframes` | Max B-Frames | Int | The maximum number of bi-directional frames that can occur between keyframes. More will increase latency but reduce bandwidth. |
| `intrarefreshperiod` | Intra-Refresh Period | Int | Intra-refresh is a gradual keyframe that is applied across the image to clean up streaming artifacts over multiple frames, instead of one large keyframe. This controls the number of frames that ela... |
| `intrarefreshlength` | Intra-Refresh Length | Int | The number of frames the intra-refresh will be spread out across. |
| `bitratemode` | Bitrate Mode | Menu | Chooses between constant (CBR) and variable (VBR) bit rate modes. Mode streaming services prefer a constant bit rate mode. |
| `avgbitrate` | Average Bitrate (Mb/s) | Float | The target bitrate for the encoding. This is specified in Mb/s (megabits/second). |
| `perframemetadata` | Per-Frame Metadata CHOP/DAT | OP | Send metadata from this OP with each frame of the video stream. This data can be recevied from the Video Stream In TOP using an Info CHOP and Info DAT. |
| `maxbitrate` | Max Bitrate (Mb/s) | Float | The maximum bitrate for the encoding. This is specified in Mb/s (megabits/second). |
| `numslices` | Num H264 Slices per Frame | Int | This controls how many pieces (slices) each H.264 frame is separated into. Some decoders are able to decode multiple slices simultaneously so setting this to a value above 1 allows those decoders t... |
| `audiochop` | Audio CHOP | CHOP | A timesliced audio source to send along with the video. For RTSP, Audio will be resampled to 44100Hz before being encoded into MP3. For RTMP the sample rate must already be 44100. For WebRTC the sa... |
| `audiobitrate` | Audio Bit Rate | Menu | Set the bit rate used for encoding audio. |
| `includesilentaudio` | Include Silent Audio Stream | Menu | Some broadcasting services require an audio stream to be included. This will include a silent audio stream along with the video in the event there isn't actual audio being streamed video the CHOP p... |
| `webrtc` | WebRTC | DAT | Set the WebRTC DAT (ie. peer) to send the video stream over. Setting this will automatically populate the WebRTC Connection parameter menu with available connections. |
| `webrtcconnection` | WebRTC Connection | StrMenu | Select the WebRTC peer-to-peer connection. Selecting this will automatically population the WebRTC Track parameter menu with available video output tracks. |
| `webrtcvideotrack` | WebRTC Video Track | StrMenu | Select the video output track that's a part of the WebRTC peer-to-peer connection. |
| `webrtcaudiotrack` | WebRTC Audio Track | StrMenu | Optionally select the audio output track that's a part of the WebRTC peer-to-peer connection, to be sent along with the video. |
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
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. Making this larger than 1 is essentially the same as taking the output from each pass, and passing it into the first input of the ... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP videostreamoutTOP operator
videostreamouttop_op = op('videostreamouttop1')

# Get/set parameters
freq_value = videostreamouttop_op.par.active.eval()
videostreamouttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
videostreamouttop_op = op('videostreamouttop1')
output_op = op('output1')

videostreamouttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(videostreamouttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **40** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
