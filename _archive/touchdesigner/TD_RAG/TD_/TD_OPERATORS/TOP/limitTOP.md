# TOP limitTOP

## Overview

The Limit TOP can limit the pixel values of the input image to fall between a minimum and maximum value, and can quantize the pixels by value or position.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `minop` | Minimum Function | Menu | The wrapping method used when applying limits to the pixel values in the image. |
| `maxop` | Maximum Function | Menu | The wrapping method used when applying limits to the pixel values in the image. |
| `min` | Minimum Value | Float | The minimum value that any of the channels in the output image can have. |
| `max` | Maximum Value | Float | The maximum value that any of the channels in the output image can have. |
| `positive` | Positive Only | Toggle | Apply an absolute value function after all other limits and quantizations are calculated e.g. all negatives are made positive. |
| `norm` | Normalize | Toggle | Normalize values in the output image so that they are all scaled and shifted to fall between the Normalized Minimum and Maximum (0 to 1 by default). This operation requires multiple internal render... |
| `normmin` | Normalize Minimum | Float | The minimum value for pixels after normalization. |
| `normmax` | Normalize Maximum | Float | The maximum value for pixels after normalization. |
| `quantvalue` | Quantize Value | Menu | The function used to quantize the pixel values in the output image. |
| `vstep` | Value Step | Float | The quantization step size for pixel values. |
| `voffset` | Value Offset | Float | An offset for the quantization step so that it doesn't have to lie on zero. |
| `quantpos` | Quantize Position | Menu | The function used for spacial quantization e.g. quantizing the UV coordinates so that pixel values are merged into larger blocks. |
| `posstep` | Position Step | Float | The size of the spacial quantization step in UV space (0-1) |
| `posoffset` | Position Offset | Float | An offset applied to the spacial quantization so that the steps do not have to start at 0,0 (measured in 0-1 UV space). |
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
# Access the TOP limitTOP operator
limittop_op = op('limittop1')

# Get/set parameters
freq_value = limittop_op.par.active.eval()
limittop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
limittop_op = op('limittop1')
output_op = op('output1')

limittop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(limittop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **27** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
