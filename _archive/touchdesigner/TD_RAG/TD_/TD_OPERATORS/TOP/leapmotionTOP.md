# TOP leapmotionTOP

## Overview

The Leap Motion TOP gets the image from the Leap Motion Controller's cameras.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | If set, this TOP will capture data from the cameras. |
| `api` | API | Menu | Select between Leap Motion V2 or V4/V5 SDKs for tracking. V5 offers the fastest and most stable tracking, V2 offers some legacy features like gestures. |
| `libfolder` | Library Folder | Folder | This parameter should point to the location of the library file (.dll on Windows) that corresponds to the selected API version. The dll file can be found in the driver kit downloaded from the Ultra... |
| `camera` | Camera | StrMenu | Select between the two cameras in the Leap Motion Controller. |
| `flipx` | Flip X | Toggle | Flips the image in X. |
| `flipy` | Flip Y | Toggle | Flips the image in Y. |
| `correction` | Image Correction | Toggle | Corrects the image for lens distortion. |
| `hmd` | HMD Mode | Menu | Switches the device to Head Mounted Display mode. |
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
# Access the TOP leapmotionTOP operator
leapmotiontop_op = op('leapmotiontop1')

# Get/set parameters
freq_value = leapmotiontop_op.par.active.eval()
leapmotiontop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
leapmotiontop_op = op('leapmotiontop1')
output_op = op('output1')

leapmotiontop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(leapmotiontop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **21** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
