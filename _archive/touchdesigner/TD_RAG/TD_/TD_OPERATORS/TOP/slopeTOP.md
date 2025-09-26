# TOP slopeTOP

## Overview

The Slope TOP generates pixels that represent the difference between its value and its neighbouring pixels' values.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `red` | Red | Menu | Select which method is used to calculate the slope of the Red channel. Horizontal and Vertical options let you calculate the slope by sampling points horizontally or vertically. |
| `green` | Green | Menu | Select which method is used to calulate the slope of the Green channel. Horizontal and Vertical options let you calculate the slope by sampling points horizontally or vertically. |
| `blue` | Blue | Menu | Select which method is used to calulate the slope of the Blue channel. Horizontal and Vertical options let you calculate the slope by sampling points horizontally or vertically. |
| `alpha` | Alpha | Menu | Select which method is used to calculate the slope of the Alpha channel. Horizontal and Vertical options let you calculate the slope by sampling points horizontally or vertically. |
| `method` | Method | Menu | Determines what pixels to use when calculating the slope at each pixel in the image. |
| `zeropoint` | Zero Point | Float | Sets the value to output when the slope is zero, similar to a midpoint. Default is .5 since 8-bit pxels are 0 to 1. But with Pixel Format et to 32-bit Float you should set this to 0, and look at th... |
| `strength` | Strength | Float | Set the strength of the output using this multiplier. Higher values result in higher slope values. |
| `offset` | Sample Step | Float | When sampling the image, this determines the distance from each pixel to the sample pixel. When units are set to pixels, it is the number of pixels away from the current pixel which is sampled to f... |
| `offsetunit` | Sample Step Unit | Menu |  |
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
# Access the TOP slopeTOP operator
slopetop_op = op('slopetop1')

# Get/set parameters
freq_value = slopetop_op.par.active.eval()
slopetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
slopetop_op = op('slopetop1')
output_op = op('output1')

slopetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(slopetop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
