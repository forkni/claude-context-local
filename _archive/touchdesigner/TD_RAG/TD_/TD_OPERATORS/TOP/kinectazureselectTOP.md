# TOP kinectazureselectTOP

## Overview

The Kinect Azure Select TOP can be used to capture additional images from a Microsoft Kinect Azure or Kinect compatible Orbbec camera that is controlled by a Kinect Azure TOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Controls whether this TOP is retrieving image data from the device. The primary Kinect Azure TOP must also be active to receive data. |
| `top` | Kinect Azure TOP | TOP | The name of the primary Kinect Azure TOP that is configuring the camera. The primary TOP controls which camera the select TOP receives data from, as well as all device configuration such as resolut... |
| `image` | Image | Menu | A list of available image types to capture from the device and display in this TOP. All image types have a second version that is mapped (aligned) to the image space of the other camera so that col... |
| `remapimage` | Align Image to Other Camera | Toggle | When enabled, the current image will be remapped to align with images from the other camera. For example, use this feature to create a color camera image that maps to the pixels of the depth camera... |
| `bodyimage` | Sync Image to Body Tracking | Toggle | When enabled, the image produced will be delayed so that it corresponds to the most recent data from the body tracking system. |
| `mirrorimage` | Mirror Image | Toggle | Flip the image in the horizontal axis. |
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
# Access the TOP kinectazureselectTOP operator
kinectazureselecttop_op = op('kinectazureselecttop1')

# Get/set parameters
freq_value = kinectazureselecttop_op.par.active.eval()
kinectazureselecttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
kinectazureselecttop_op = op('kinectazureselecttop1')
output_op = op('output1')

kinectazureselecttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(kinectazureselecttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
