# TOP kinectTOP

## Overview

The Kinect TOP captures video from the Kinect depth camera or RGB color camera.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When 'On' data is captured from the Kinect sensor. |
| `hwversion` | Hardware Version | Menu | Choose between Kinect  v1 or Kinect v2 sensors. |
| `sensor` | Sensor | StrMenu | Selects which Kinect sensor to use. Only available when using Kinect v1. |
| `image` | Image | Menu | Selects between the Color, Depth, Infrared, Player Index, or Color Point Cloud modes. |
| `camerares` | Camera Resolution | Menu | Only used for Kinect 1 devices. Selects the resolution of the camera capture. |
| `skeleton` | Skeleton | Menu | Only used for Kinect 1 devices. Specify whether to track full skeleton or seated skeleton. |
| `neardepthmode` | Near Depth Mode | Toggle | Only used for Kinect 1 devices. Enables near mode for the depth camera, which allows the depth camera to see objects as close as 40cm to the camera (instead of the default 80cm). |
| `mirrorimage` | Mirror Image | Toggle | Flips the image in the y-axis. |
| `remap` | Camera Remap | Toggle | Only used for Kinect 2 devices. Enabling this will remap images that are natively from the depth camera (Depth, Infrared, Player Index) to be in the space and resolution of the Color camera instead. |
| `tooclosevalue` | Too Close Value | Float | Only used for Kinect 1 devices. For depth pixels that are too close to resolve, this pixel value will be output instead. |
| `toofarvalue` | Too Far Value | Float | Only used for Kinect 1 devices. For depth pixels that are too far to resolve, this pixel value will be output instead. |
| `unknownvalue` | Unknown Value | Float | For depth pixels whose depth can not be determined, output this value instead. |
| `unknownpointvalue` | Unknown Point Value | Menu | When using the 'Color Point Cloud' some pixel's position can not be determined. This parameter controls what value to assign those pixels instead. |
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
# Access the TOP kinectTOP operator
kinecttop_op = op('kinecttop1')

# Get/set parameters
freq_value = kinecttop_op.par.active.eval()
kinecttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
kinecttop_op = op('kinecttop1')
output_op = op('output1')

kinecttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(kinecttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
