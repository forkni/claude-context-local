# TOP videodeviceinTOP

## Overview

The Video Device In TOP can be used to capture video from an external camera, capture card, capture dongle, or dideo decoder connected to the system.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When set to one the TOP captures the image stream from the camera or decoder. |
| `driver` | Driver | Menu | Selects the library to use to interface with the cameras. |
| `device` | Device | Menu | Select which camera or decoder you want from this menu. |
| `specifyip` | Specify IP | Toggle | When using Allied Vision library allows you to specify the camera address by IP. |
| `ip` | IP | Str | The IP address used when Specify IP above is turned on. |
| `options` | Options | Pulse | Opens the options or control panel for the camera. NOTE: Only works when using DirectShow (WDM) cameras. |
| `deinterlace` | Deinterlace | Menu | Sets which fields to capture. |
| `precedence` | Field Precedence | Menu | When using Bob (Split) deinterlacing, this selects which field is shown first for each frame. |
| `channel` | TV Channel | Int | Selects the TV channel if a TV tuner is used as the video input. |
| `signalformat` | Signal Format | Menu | The signal format to capture input at. This is the resolution and the frame rate, as well as if the frames are progressive or interlaced. Note that when using an interlaced format, the rate refers ... |
| `quadlink` | Quad Link | Toggle | Used for cards that support quad-link formats. Quad-link esstenially takes 4 inputs and creates one single larger input out of them, for example 4 1080p inputs become a single 4K input. |
| `inputpixelformat` | Input Pixel Format | Menu | Some capture devices support pixel formats other than 8-bit. For supported devices (Blackmagic Design) this will make the node attempt to use that capability. |
| `transfermode` | Transfer Mode | Menu | Controls how the frames are transferred from the input device to CPU memory, and how they are transferred from CPU memory to the GPU. |
| `memorymode` | Memory Mode | Menu | Controls the memory type used to transfer data between the capture card and the GPU. |
| `syncinputs` | Sync Inputs | Toggle | Enabling syncing of multiple Video Device In TOPs. Syncing allows multiple nodes using multiple inputs and capture cards on a single system to ensure they are outputting frames in sync. Without thi... |
| `syncgroupindex` | Sync Group Index | Int | There can be multiple sync groups active in a .toe file. Nodes will only sync to other nodes that are part of the same sync group. |
| `maxsyncoffset` | Max Sync Offset (ms) | Float | Specified in milliseconds. The maximum difference in time two image could have arrived at be considered in-sync. Images that arrive at times more different than this offset will be considered to be... |
| `synctimeout` | Sync Timeout (ms) | Float | How much time to wait for all frames in a sync group to become available before giving up trying to sync. Expressed in milliseconds. If this timeout elapses when waiting for a frame from one or mor... |
| `resetstats` | Reset Stats | Pulse | A pulse to reset the statistics in an attached Info CHOP. |
| `preset` | Preset | Menu |  |
| `autoge` | Auto Gain/Exposure | Toggle |  |
| `autogebias` | Auto Gain/Exposure Bias | Float |  |
| `autogelevel` | Auto Gain/Exposure Level | Float |  |
| `maxgain` | Max Gain | Float |  |
| `maxexposure` | Max Exposure (ms) | Float |  |
| `gain` | Gain | Float |  |
| `exposure` | Exposure (ms) | Float |  |
| `cgamma` | Chromaticity Gamma | Float |  |
| `lgamma` | Luminosity Gamma | Float |  |
| `limitfps` | Limit FPS | Toggle |  |
| `limitedfps` | FPS | Float |  |
| `capture` | Capture | Toggle |  |
| `capturepulse` | Capture Pulse | Pulse |  |
| `autowb` | Auto White-Balance | Toggle |  |
| `wbcoeffs` | White-Balance Coeffs | RGB |  |
| `custombandwidth` | Custom Bandwidth | Menu |  |
| `bandwidthlimit` | Bandwidth Limit (Mb/s) | Int |  |
| `camerabitdepth` | Camera Bit Depth | Menu |  |
| `gpudemosaic` | GPU Demosaic | Toggle |  |
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
# Access the TOP videodeviceinTOP operator
videodeviceintop_op = op('videodeviceintop1')

# Get/set parameters
freq_value = videodeviceintop_op.par.active.eval()
videodeviceintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
videodeviceintop_op = op('videodeviceintop1')
output_op = op('output1')

videodeviceintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(videodeviceintop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **52** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
