# TOP timemachineTOP

## Overview

The Time Machine TOP combines pixels in a sequence of images stored in a Texture 3D TOP. Whereas "morphing" warps an image "spatially" (in xy), Time Machine warps images only in time (specifically, the third dimension of a 3D texture map).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `blackoffset` | Black Offset | Float | Sets the time offset for black areas of the Input 2 image. |
| `blackoffsetunit` | Black Offset Unit | Menu | Set the units for this parameter to index, frames, seconds or a fraction. |
| `whiteoffset` | White Offset | Float | Sets the time offset for white areas of the Input 2 image. |
| `whiteoffsetunit` | White Offset Unit | Menu | Set the units for this parameter to index, frames, seconds or a fraction. |
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
# Access the TOP timemachineTOP operator
timemachinetop_op = op('timemachinetop1')

# Get/set parameters
freq_value = timemachinetop_op.par.active.eval()
timemachinetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
timemachinetop_op = op('timemachinetop1')
output_op = op('output1')

timemachinetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(timemachinetop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
