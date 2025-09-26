# TOP blurTOP

## Overview

The Blur TOP blurs the image with various kernel filters and radii.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Method | Menu | Determines how the blur is applied. |
| `type` | Type | Menu | Determines the mathematical function used to create the blur. |
| `extend` | Extend | Menu | Sets the extend conditions to determine what happens to the blur at the edge of the image. |
| `preshrink` | Pre-Shrink | Int | Reduces the image's resolution before applying the blur. This effectively applies a 2x2 box filter on the input and creates a smaller texture to do the full blur operation on. It behaves as if the ... |
| `size` | Filter Size | Int | The amount of blur in pixels. If you want a resolution-independent blur, use an expression like me.par.resolutionw/100 in this parameter (which would result in a 1% image blur). |
| `offset` | Sample Step | XY | When sampling the image, this determines the distance from each pixel to the sample pixel. When units are set to pixels, it is the number of pixels away from the current pixel which is sampled to b... |
| `offsetunit` | Sample Step Unit | Menu | Select between Pixel, Fraction, or Fraction Aspect as the units to use for the Sample Step parameter. |
| `rotate` | Rotate Kernel | Float | Rotates the blur filter. More noticeable when Method is set to Horizontal. |
| `dither` | Dither | Toggle | Enabling makes 8-bit blurs look smoother.  This can help if the blur operation introduces banding or other unexpected artifacts. |
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
# Access the TOP blurTOP operator
blurtop_op = op('blurtop1')

# Get/set parameters
freq_value = blurtop_op.par.active.eval()
blurtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
blurtop_op = op('blurtop1')
output_op = op('output1')

blurtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(blurtop_op)
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
