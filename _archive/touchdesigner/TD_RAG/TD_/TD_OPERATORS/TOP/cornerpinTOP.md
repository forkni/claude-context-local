# TOP cornerpinTOP

## Overview

The Corner Pin TOP can perform two operations.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `extractp3` | Bottom Left | XY | The x and y position of the bottom left corner of the extraction. |
| `extractp3unit` | Bottom Left Unit | Menu |  |
| `extractp4` | Bottom Right | XY | The x and y position of the bottom right corner of the extraction. |
| `extractp4unit` | Bottom Right Unit | Menu |  |
| `extractp1` | Top Left | XY | The x and y position of the top left corner of the extraction. |
| `extractp1unit` | Top Left Unit | Menu |  |
| `extractp2` | Top Right | XY | The x and y position of the top right corner of the extraction. |
| `extractp2unit` | Top Right Unit | Menu |  |
| `extend` | Extend | Menu | Determines how the image is handled at its edges. |
| `extractmapping` | Mapping | Menu | Pick between Bilinear or Perspective Extraction. |
| `pinp3` | Bottom Left | XY | The x and y position of the bottom left corner of the extraction. |
| `pinp3unit` | Bottom Left Unit | Menu |  |
| `pinp4` | Bottom Right | XY | The x and y position of the bottom right corner of the extraction. |
| `pinp4unit` | Bottom Right Unit | Menu |  |
| `pinp1` | Top Left | XY | The x and y position of the top left corner of the extraction. |
| `pinp1unit` | Top Left Unit | Menu |  |
| `pinp2` | Top Right | XY | The x and y position of the top right corner of the extraction. |
| `pinp2unit` | Top Right Unit | Menu |  |
| `gridrefine` | Grid Refinement | Int | To perform the Extract and Pin operations, the image is placed on a polygonal grid to break it up into blocks that can be distorted. Grid Refinement sets the number of divisions in this grid. |
| `bgcolor` | Background Color | RGBA | Color applied behind the foreground image. The background is visible when the corners of the Corner Pin have been positioned inside the original image space. Set the Bottom Left x-position to 1.0 a... |
| `premultrgbbyalpha` | Pre-Multiply RGB by Alpha | Toggle | This option allows the Background Color to be pre-multiplied by alpha. |
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
# Access the TOP cornerpinTOP operator
cornerpintop_op = op('cornerpintop1')

# Get/set parameters
freq_value = cornerpintop_op.par.active.eval()
cornerpintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cornerpintop_op = op('cornerpintop1')
output_op = op('output1')

cornerpintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cornerpintop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **34** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
