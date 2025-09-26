# TOP displaceTOP

## Overview

The Displace TOP will cause one image to be warped by another image.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `horzsource` | Horizontal Source | Menu | Instead of using the Red channel to displace horizontally, you can choose a different channel. |
| `vertsource` | Vertical Source | Menu | Instead of using the Blue channel to displace vertically, you can choose a different channel. |
| `midpoint` | Source Midpoint | XY | This value is the color values that will result in no displacement. Values below this will cause the displacement to come from the left/bottom of the pixel, while values above this will cause the d... |
| `displaceweight` | Displace Weight | XY | This scales the offset caused by the Displace Image. It will cause the pixels fetched to be closer/farther along the sample vector created by the Horizontal and Vertical Source. |
| `uvweight` | UV Weight | Float | This reduces the influence of the pixel's position when brought toward 0. At its default of 1, it doesn't zoom into the Displace Image. When 0, it anchors the displacements relative to one pixel in... |
| `offset` | Offset | XY | The Offset is first multiplied by the Offset Weight. Then it will be added to the coordinates caluclated after looking up into the displacement map. These final coordinates is what will be used to ... |
| `offsetweight` | Offset Weight | Float | Scales the Offset parameter values. When this is 0 the Offset parameter will have no effect. |
| `extend` | Extend | Menu | This parameter determines what happens at the edges of the tiles. |
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
# Access the TOP displaceTOP operator
displacetop_op = op('displacetop1')

# Get/set parameters
freq_value = displacetop_op.par.active.eval()
displacetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
displacetop_op = op('displacetop1')
output_op = op('output1')

displacetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(displacetop_op)
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
