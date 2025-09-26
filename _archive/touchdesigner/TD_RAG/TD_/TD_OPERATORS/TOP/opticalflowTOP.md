# TOP opticalflowTOP

## Overview

Optical Flow detects patterns of motion in its input. The motion detected in the X-direction is output in the red (R) channel, while the motion in the Y-direction is output in the green (G) channel. The pixel values stored in the red and green channels are 32-bit floating point numbers. A value of 1.0 in a pixel of the red channel means that the ho

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `gridsize` | Grid Size | Menu | Determines the output resolution. A smaller grid corresponds to a larger output image. Turing GPUs only support `4x4`, whereas newer GPUs can use any option. |
| `quality` | Quality | Menu | Specify the optical flow model. Higher quality is slower to compute, and low quality is faster to compute. |
| `costoutput` | Cost Output | Toggle | Toggle whether the "cost" of the optical flow is output in the blue channel of the TOP. Higher cost means higher uncertainty in the optical flow estimate in the RG channels. The cost values are int... |
| `gain` | Gain | XY | A post-multiply for the optical flow in the RG channels, allowing control of output intensity. |
| `manualtiming` | Manual Timing | Toggle | The Optical Flow TOP works in both real-time mode and non-real-time mode. However, if you have a video source whose frame rate differs from the project rate, you might be able to get better optical... |
| `timestamp` | Timestamp | Float | This is a timestamp in seconds of the video frame. See the discussion of Manual Timing in the parameter above. |
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
# Access the TOP opticalflowTOP operator
opticalflowtop_op = op('opticalflowtop1')

# Get/set parameters
freq_value = opticalflowtop_op.par.active.eval()
opticalflowtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
opticalflowtop_op = op('opticalflowtop1')
output_op = op('output1')

opticalflowtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(opticalflowtop_op)
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
