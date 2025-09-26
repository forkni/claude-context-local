# TOP bloomTOP

## Overview

=The Bloom TOP creates a glow effect around bright parts of the input image that simulates light bouncing around a lens assembly of a camera. Parameters control how much of the bright spots of your input image get bloomed, how wide the bloom gets spread, and how it rolls off into the un-bloomed areas.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `preblacklevel` | Pre-Black Level | Float | Similar to the Black Level parameter of a Luma Level TOP. Pixels with a luminosity less than this value are pushed to black. |
| `pregamma` | Pre-Gamma | Float | Similar to the Gamma parameter of a Luma Level TOP, applies a gamma adjustment to the pixel value after the Pre-Black Level stage, which makes all non-zero values closer to RGB = 1, 1, 1. |
| `prebrightness` | Pre-Brightness | Float | Similar to the Brightness parameter of a Luma Level TOP, it is a multiplier for the pixel value after the Pre-Gamma stage. |
| `minbloomradius` | Min Bloom Radius | Float | Determines the minimum blur level to start sampling from. It is 0 to 1, so given a 1024x1024 image has 10 blur levels, if Minimum Bloom Size is set to .2, we will begin sampling from blur level 2 (... |
| `maxbloomradius` | Max Bloom Radius | Float | Determines the maximum blur level we sample from. It is 0 to 1, so if the image has 10 blur levels and a Maximum Bloom Size is set to .8, we will sample mipmap levels up to level 8. If Max<Min, Max... |
| `bloomthreshold` | Bloom Threshold | Float | After the blur levels have been mixed, this cuts away the darkest part of the image, or, when < 0, it adds more of the full-image average. |
| `bloomscurve` | Bloom S-Curve | Float | Reshapes the bloom rolloff so that it is tighter/steeper to the hot spots. |
| `bloomfill` | Bloom Fill | Float | Makes the bloom wider. |
| `bloomintensity` | Bloom Intensity | Float | Final multiplier of accumulated bloom value. |
| `output` | Output | Toggle | Permits the user to select the image that is output; useful for previewing the outputs of each stage of the bloom pipeline. If set to "Input", the original image is output; if set to "Preprocess", ... |
| `inputimage0` | Input Image | Float | Multiplier for the input image value that is added in to the final bloom value. |
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
# Access the TOP bloomTOP operator
bloomtop_op = op('bloomtop1')

# Get/set parameters
freq_value = bloomtop_op.par.active.eval()
bloomtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
bloomtop_op = op('bloomtop1')
output_op = op('output1')

bloomtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(bloomtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
