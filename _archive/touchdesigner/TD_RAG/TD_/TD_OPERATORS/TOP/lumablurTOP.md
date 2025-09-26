# TOP lumablurTOP

## Overview

The Luma Blur TOP blurs image on a per-pixel basis depending on the luminance or greyscale value of its second input.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | Determines the mathematical function used to create the blur. |
| `widthchan` | Kernel Width Channel | Menu | The greyscale can be any channel of the second input, or composites like luminance and RGB average. |
| `blackvalue` | Black Value | Float | The pixel luminance value used for the Black Filter Size parameter below. |
| `whitevalue` | White Value | Float | The pixel luminance value used for the White Filter Size parameter below. |
| `blackwidth` | Black Filter Width | Int | The amount of blur where the second input is black. |
| `whitewidth` | White Filter Width | Int | The amount of blur where the second input is white. |
| `extend` | Extend | Menu | Sets the extend conditions to determine what happens to the blur at the edge of the image. |
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
# Access the TOP lumablurTOP operator
lumablurtop_op = op('lumablurtop1')

# Get/set parameters
freq_value = lumablurtop_op.par.active.eval()
lumablurtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lumablurtop_op = op('lumablurtop1')
output_op = op('output1')

lumablurtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lumablurtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
