# TOP substanceTOP

## Overview

There is a tight integration between TouchDesigner and Allegorithmic (Adobe) Substance Designer, a material creation package that is also node-based and has extensive material libraries.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | Substance Designer File | File | Specify the .sbsar material file from Substance Designer. |
| `reloadconfig` | Reload File | Pulse | Reloads the file from disk. |
| `graph` | Graph | StrMenu | Specify which graph in the .sbsar file to use. See Substance's Graph Help for more details. |
| `output` | Output | StrMenu | Choose what the output of the TOP will be. Grid Preview can be used to see all the texture maps inside the material at once. |
| `invertnormal` | Invert Normal Map | Toggle | Inverts the normal map coming from the sbsar file. This parameter should be used when the normal map in the sbsar is -Y (DirectX) since normal map usage in TouchDesigner expects the normal map as Y... |
| `engine` | Engine | Menu | Select the Substance Engine used for rendering. The GPU engine has much lower render times and is the default engine, while the CPU is included as a legacy mode and was the engine used in TouchDesi... |
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
| `npasses` | Passes | Int | Duplicates the operation of the TOP the specified number of times. For every pass after the first it takes the result of the previous pass and replaces the node's first input with the result of the... |
| `chanmask` | Channel Mask | Menu | Allows you to choose which channels (R, G, B, or A) the TOP will operate on. All channels are selected by default. |
| `format` | Pixel Format | Menu | Format used to store data for each channel in the image (ie. R, G, B, and A). Refer to Pixel Formats for more information. |

## Usage Examples

### Basic Usage

```python
# Access the TOP substanceTOP operator
substancetop_op = op('substancetop1')

# Get/set parameters
freq_value = substancetop_op.par.active.eval()
substancetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
substancetop_op = op('substancetop1')
output_op = op('output1')

substancetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(substancetop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
