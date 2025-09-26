# TOP mathTOP

## Overview

The Math TOP performs specific mathematical operations on the pixels of the input image.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `preop` | Channel Pre OP | Menu | A menu of unary operations that are performed on each channel as it comes in to the Math TOP include: |
| `chanop` | Combine Channels | Menu | A choice of operations is performed between the channels of the input TOP. Input and output channels are selected by the 'Combine Channels Input' and 'Combine Channels Output' parameters below. The... |
| `postop` | Channel Post OP | Menu | A menu (same as Channel Pre OP) is performed as the finale stage upon the channels resulting from the above operations. |
| `integer` | Integer | Menu | The resulting values can be converted to integers. |
| `inputmask` | Combine Channels Input | Menu | Select which channels are included in the input. |
| `outputchannels` | Combine Channels Output | Menu | Select which channels are included in the output result. |
| `preoff` | Pre-Add | Float | First, add this value to each pixel of each channel. |
| `gain` | Multiply | Float | Then multiply by this value. |
| `postoff` | Post-Add | Float | Then add this value. |
| `op` | Operation | Menu | The math operation performed. |
| `fromrange` | From Range | Float | Working on all channels, converts the specified From Range (low-high range) into the To Range below. |
| `torange` | To Range | Float | Working on all channels, converts the specified From Range (low-high range) above into this To Range. |
| `fromranger` | From Range R | Float | Working on the red channel, converts the specified From Range (low-high range) into the To Range below. |
| `toranger` | To Range R | Float | Working on the red channel, converts the specified From Range (low-high range) above into this To Range. |
| `fromrangeg` | From Range G | Float | Working on the green channel, converts the specified From Range (low-high range) into the To Range below. |
| `torangeg` | To Range G | Float | Working on the green channel, converts the specified From Range (low-high range) above into this To Range. |
| `fromrangeb` | From Range B | Float | Working on the blue channel, converts the specified From Range (low-high range) into the To Range below. |
| `torangeb` | To Range B | Float | Working on the blue channel, converts the specified From Range (low-high range) above into this To Range. |
| `fromrangea` | From Range A | Float | Working on the alpha channel, converts the specified From Range (low-high range) into the To Range below. |
| `torangea` | To Range A | Float | Working on the alpha channel, converts the specified From Range (low-high range) above into this To Range. |
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
# Access the TOP mathTOP operator
mathtop_op = op('mathtop1')

# Get/set parameters
freq_value = mathtop_op.par.active.eval()
mathtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mathtop_op = op('mathtop1')
output_op = op('output1')

mathtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mathtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
