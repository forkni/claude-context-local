# TOP levelTOP

## Overview

The Level TOP adjusts image contrast, brightness, gamma, black level, color range, quantization, opacity and more.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `clampinput` | Clamp Input | Toggle | This option will clamp pixel values in between 0 and 1. When using higher bit depth floating pixel formats, it is recommended to set it to Unclamped to allow the full range of values to be operated... |
| `invert` | Invert | Float | Inverts the colors in the image. Black becomes white, white becomes black. Colors invert across the color wheel, so red becomes cyan, blue becomes yellow, green becomes magenta, and so on. |
| `blacklevel` | Black Level | Float | Any pixel with a value less than or equal to this will be black. |
| `brightness1` | Brightness 1 | Float | Increases or decreases the brightness of an image. Brightness can be considered the arithmetic mean of the RGB channels. The Brightness parameter adds or subtracts an offset into the R, G, and B ch... |
| `gamma1` | Gamma 1 | Float | The Gamma parameter applies a gamma correction to the image. Gamma is the relationship between the brightness of a pixel as it appears on the screen, and the numerical value of that pixel. This is ... |
| `contrast` | Contrast | Float | Contrast applies a scale factor (gain) to the RGB channels. Increasing contrast will brighten the light areas and darken the dark areas of the image, making the difference between the light and dar... |
| `inlow` | In Low | Float | Any pixel below this value appears black. |
| `inhigh` | In High | Float | Any pixel above this value appears white. |
| `outlow` | Out Low | Float | Clamps pixel values to this value or higher. |
| `outhigh` | Out High | Float | Clamps pixel values to this value or lower. |
| `lowr` | Low R | Float | Clamps the minimum level of the red channel. |
| `highr` | High R | Float | Clamps the maximum level of the red channel. |
| `lowg` | Low G | Float | Clamps the minimum level of the green channel. |
| `highg` | High G | Float | Clamps the maximum level of the green channel. |
| `lowb` | Low B | Float | Clamps the minimum level of the blue channel. |
| `highb` | High B | Float | Clamps the maximum level of the blue channel. |
| `lowa` | Low A | Float | Clamps the minimum level of the alpha channel. |
| `higha` | High A | Float | Clamps the maximum level of the alpha channel. |
| `stepping` | Apply Stepping | Toggle | Turns on stepping (posterizing) and enables the parameters below. |
| `stepsize` | Step Size | Float | Posterizes the image into bands or stripes. Number of bands equal to the inverse of this parameter (i.e., 0.25 = 4 bands). Use a default Ramp TOP to easily see this parameter's effect. |
| `threshold` | Threshold | Float | Offsets the position of the step boundaries. |
| `clamplow` | Clamp Low | Float | Clamps the image's minimum value. (value as in hue, saturation, and value) |
| `clamphigh` | Clamp High | Float | Clamps the image's maximum value. (value as in hue, saturation, and value) |
| `soften` | Soften | Float | Softens or blends the boundaries between steps. |
| `gamma2` | Gamma 2 | Float | A second gamma correction that is added after the Range, RGBA, and Step page adjustments have been applied. |
| `opacity` | Opacity | Float | Adjust the opacity, or transparency, of the image. |
| `brightness2` | Brightness 2 | Float | A second brightness adjustment that is added after the Range, RGBA, and Step page adjustments have been applied. |
| `clamp` | Clamp | Toggle | Clamps pixel values to this value or lower. |
| `clamplow2` | Clamp Low | Float | Clamps the image's minimum value. (value as in hue, saturation, and value) |
| `clamphigh2` | Clamp High | Float | Clamps the image's maximum value. (value as in hue, saturation, and value) |
| `premultrgbbyalpha` | Pre-Multiply RGB by Alpha | Toggle | This option makes the color channels pre-multiplied by alpha. |
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
# Access the TOP levelTOP operator
leveltop_op = op('leveltop1')

# Get/set parameters
freq_value = leveltop_op.par.active.eval()
leveltop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
leveltop_op = op('leveltop1')
output_op = op('output1')

leveltop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(leveltop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **44** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
