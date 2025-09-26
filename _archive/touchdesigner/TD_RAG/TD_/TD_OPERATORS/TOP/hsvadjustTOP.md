# TOP hsvadjustTOP

## Overview

The HSV Adjust TOP adjust color values using hue, saturation, and value controls.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `startcolor` | Start Color | RGB | The start color is the hue that the HSV adjustment is centered around. When adjusting a small hue range, this is the color that will be altered. In the example image above, the Start Color color is... |
| `huerange` | Hue Range | Float | This is the range of color from the Start Color that will be adjusted. A range of 1 will only adjust the colors that are the same as the start color. A range of 360 will adjust all colors. For exam... |
| `huefalloff` | Hue Falloff | Float | This controls the falloff from the Hue Range. Higher values give more falloff, blending the hue range softly from hues that are adjusted to hues that are not. |
| `saturationrange` | Saturation Range | Float | This is the range of saturation to adjust from the saturation of the Start Color. The Range is from 0 to 1. |
| `saturationfalloff` | Saturation Falloff | Float | This controls the falloff from the Saturation Range selected. |
| `valuerange` | Value Range | Float | This is the range of value to adjust from the value of the Start Color. The Range is from 0 to 1. |
| `valuefalloff` | Value Falloff | Float | This controls the falloff from the Value Range selected. |
| `hueoffset` | Hue Offset | Float | Adjust the hues selected above. The Hue Offset ranges from 0 to 360. For example, if the initial pixel color is 180 then a Hue Offset of 100 will change the hue  of 180 (cyan) to be a hue of 280 (v... |
| `saturationmult` | Saturation Multiplier | Float | Adjusts the saturations selected above. This will multiply the saturation values specified by Saturation Range and Falloff parameters above. Setting this to 0 will reduce the selected saturation to... |
| `valuemult` | Value Multiplier | Float | Adjusts the values selected above. This will multiply the values specified by Value Range and Falloff parameters above. |
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
# Access the TOP hsvadjustTOP operator
hsvadjusttop_op = op('hsvadjusttop1')

# Get/set parameters
freq_value = hsvadjusttop_op.par.active.eval()
hsvadjusttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
hsvadjusttop_op = op('hsvadjusttop1')
output_op = op('output1')

hsvadjusttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(hsvadjusttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
