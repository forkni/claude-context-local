# TOP functionTOP

## Overview

The Function TOP can perform mathematical operations like sin, cos, or exp on the color values of the input image.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `rerange` | Re-Range Integers | Float | Applies a scale and shift to the input values before the function is calculated i.e. input = (input * rerange2) + rerange1. Note: This feature only affects integer texture formats and is not used o... |
| `funcrgba` | Function RGBA | Menu | Applies the selected function to the R, G, B, and A channels. |
| `funcrgb` | Function RGB | Menu | Applies the selected function to the R, G, and B channels. |
| `funcr` | Function R | Menu | Applies the selected function to the R (red) channel. |
| `funcg` | Function G | Menu | Applies the selected function to the G (green) channel. |
| `funcb` | Function B | Menu | Applies the selected function to the B (blue) channel. |
| `funca` | Function A | Menu | Applies the selected function to the A (alpha) channel. |
| `baseval` | Base Value | Float | Supplies the base value for functions like 'Log Base N' and 'Base ^ Input' |
| `expval` | Exponent Value | Float | Supplies the exponent value for the function 'Input ^ Base'. |
| `constval` | Constant Value | Float | Allows setting the output to a specific constant value using the 'Constant' function. |
| `angunit` | Angle Units | Menu | Determines whether the input values are measured in degrees, radians, etc for functions that require an angle input e.g. sine, cosine, etc. |
| `replace` | Replace Errors | Toggle | When enabled, output values that would otherwise be invalid will be replaced with the value of the 'Error Value' parameter. For example, when using the log function, the output will be replaced whe... |
| `errval` | Error Value | Float | The output value to use when an input error is detected e.g. log(-1). |
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
# Access the TOP functionTOP operator
functiontop_op = op('functiontop1')

# Get/set parameters
freq_value = functiontop_op.par.active.eval()
functiontop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
functiontop_op = op('functiontop1')
output_op = op('output1')

functiontop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(functiontop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
