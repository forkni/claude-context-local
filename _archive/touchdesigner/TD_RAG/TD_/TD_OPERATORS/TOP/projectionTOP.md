# TOP projectionTOP

## Overview

TThe Projection TOP takes an image, often created with a Render TOP, in a Cube Map, Equirectangular, Fish Eye or Dual Paraboloid format, and converts that to a Fisheye or Equirectangular projection suitable for domes, or a Cube Map format. For Equirectangular images, u-v horizontal-vertical is the latitude-longitude, suitable for spheres. This produces superior-quality when it's based on the cube maps.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `input` | Input | Menu | At this time the only option is a Cube Map input. You can generate a Cube Map by rendering one using the Render TOP, or converting 2D images into one using the Cube Map TOP. |
| `output` | Output | Menu | Select output format from the menu. |
| `fov` | FOV Angle | Float | Only enabled in Fish-Eye output mode to specify the field of view of the Fish-Eye camera. |
| `r` | Rotate | XYZ | Use this parameter to rotate the map on any axis. |
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
# Access the TOP projectionTOP operator
projectiontop_op = op('projectiontop1')

# Get/set parameters
freq_value = projectiontop_op.par.active.eval()
projectiontop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
projectiontop_op = op('projectiontop1')
output_op = op('output1')

projectiontop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(projectiontop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **17** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
