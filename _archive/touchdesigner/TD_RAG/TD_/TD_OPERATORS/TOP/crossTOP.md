# TOP crossTOP

## Overview

The Cross TOP blends between the two input images based on the value of the Cross parameter (refered to as Cross_value below).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `cross` | Cross | Float | Determines the amount each input is added to the output. When Cross = 0, Input1 is output; when Cross = 1, Input2 is output. |
| `size` | Fixed Layer | Menu | The selected input will become the fixed layer and the other input will be the overlay. This does not change the order of the composite (Input1 + Input2), only which layer is considered fixed and w... |
| `prefit` | Pre-Fit Overlay | Menu | Determines how the Overlay layer (Overlay layer is the input that is NOT the Fixed Layer) fills the composite. |
| `extend` | Extend Overlay | Menu | Sets the extend (or repeat) conditions of the Overlay layer. This parameter determines what happens at the edges of the Overlay layer. |
| `r` | Rotate | Float | Rotates the Overlay layer. Increasing values rotate clockwise, decreasing values rotate counter-clockwise. |
| `t` | Translate | XY | Translates the Overlay layer in x and y. |
| `tunit` | Translate Unit | Menu | Sets the units used in the Translate parameter. |
| `s` | Scale | XY | Scales the Overlay layer in x and y. |
| `p` | Pivot | XY | Allows you to define the point about which the Overlay layer scales and rotates. Altering the pivot point produces different results depending on the Transform Order. |
| `punit` | Pivot Unit | Menu | Sets the units used in the Pivot parameter. |
| `legacyxform` | Legacy Transform | Toggle | When enabled, will use the legacy method of building the transform matrix, which has inverted rotation and transform order. |
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
# Access the TOP crossTOP operator
crosstop_op = op('crosstop1')

# Get/set parameters
freq_value = crosstop_op.par.active.eval()
crosstop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
crosstop_op = op('crosstop1')
output_op = op('output1')

crosstop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(crosstop_op)
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
