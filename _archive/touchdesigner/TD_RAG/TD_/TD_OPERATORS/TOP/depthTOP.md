# TOP depthTOP

## Overview

The Depth TOP reads an image containing depth information from a scene described in a specified Render TOP. The resulting image is black (0) at pixels where the surface is at the near depth value (Camera's parameter "Near"). It is white (1) at pixels where the surface is at the far depth value (parameter "Far").

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `rendertop` | Render TOP | OP | Specifies the Render TOP used for depth values. |
| `cameraindex` | Camera Index | Int | When using Multi-Camera Rendering, chooses which camera's output to select. |
| `peellayerindex` | Peel Layer Index | Int | When using the 'Depth-Peeling' feature in the Render TOP, this chooses which peel layer to select. |
| `pixelformat` | Pixel Format | Menu | The pixel format the Depth texture should be output as. |
| `depthspace` | Depth Space | Menu | The space the depth values should be output in. |
| `rangefrom` | Range from | Float | The range to convert from when using 'Rerange from Camera Space'. This would often be your area of interest in the camera's depth. |
| `rangeto` | Range to | Float | The range of values you want to convert the depth values to. This is the range you would find the depth to more useful for processing, often 0-1. |
| `clamp` | Clamp to [0-1] | Toggle | Enable to clamp the depth values between 0 and 1. |
| `gamma` | Gamma | Float | Apply a  gamma curve to the depth values. |
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
# Access the TOP depthTOP operator
depthtop_op = op('depthtop1')

# Get/set parameters
freq_value = depthtop_op.par.active.eval()
depthtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
depthtop_op = op('depthtop1')
output_op = op('output1')

depthtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(depthtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **22** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
