# TOP lookupTOP

## Overview

The Lookup TOP replaces color values in the TOP image connected to its first input with values derived from a lookup table created from its second intput or a lookup table created using the CHOP parameter.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Method | Menu | Choose to use a line from the 2nd input (defined using UV coordinates) or CHOP values to define the lookup table. |
| `index` | Index Range | Float | The Index Range maps the index values to the lookup table's start and end and defaults to 0 and 1. The first parameter represents the start of the lookup table. When the index color has this value,... |
| `channel` | Index Channel | Menu | The Index Channel controls how the color from the input is turned into a index to do the lookup. By default, the RGBA Independent option will do a separate lookup in each channel i.e. the red outpu... |
| `independentalpha` | Independent Alpha | Toggle | When enabled, the Alpha value of the output image is retrieved independently from the lookup table based on the alpha channel of the index image (the first input). This option can reproduce the leg... |
| `darkuv` | Dark UV | Float | Set the UV position to use for dark end of the lookup table. In the original image connected to the first input, any pixel with a value of (0,0,0) will be replaced by the value found at this UV pos... |
| `darkuvunit` | Dark UV Unit | Menu |  |
| `lightuv` | Light UV | Float | Set the UV position to use for light end of the lookup table. In the original image connected to the first input, any pixel with a value of (1,1,1) will be replaced by the value found at this UV po... |
| `lightuvunit` | Light UV Unit | Menu |  |
| `chop` | CHOP | CHOP | Reference the CHOP to use to define the RGBA (A is optional) values in the lookup table. |
| `clampchopvalues` | Clamp CHOP Values | Toggle | Clamps CHOP values between 0-1. |
| `displaylookup` | Output Lookup | Toggle | Outputs the lookup table itself, instead of replacing the color values of the first input. |
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
# Access the TOP lookupTOP operator
lookuptop_op = op('lookuptop1')

# Get/set parameters
freq_value = lookuptop_op.par.active.eval()
lookuptop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lookuptop_op = op('lookuptop1')
output_op = op('output1')

lookuptop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lookuptop_op)
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
