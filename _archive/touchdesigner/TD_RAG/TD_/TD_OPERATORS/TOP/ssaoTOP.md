# TOP ssaoTOP

## Overview

The SSAO TOP performs Screen Space Ambient Occlusion on the output of a Render TOP or Render Pass TOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `quality` | Quality | Menu | Determines the visual quality of the results. The higher the quality, the more computationally expensive it is. |
| `sampledirs` | Sample Directions | Int | For each pixel, rays are sent out in random directions to see if there is a surface nearby that would occlude the ambient light to this pixel. This parameter controls how many rays are sent out per... |
| `samplesteps` | Sample Steps | Int | Since this is a 2D pixel-based operation, the rays need to sample multiple neighboring pixels along its path to check for points of interest. This parameter controls how many of these samples each ... |
| `surfaceavoid` | Surface Avoid Angle | Float | This parameter biases the angle of the rays so they don't travel too close to the plane that the starting point lays on (as determined by the point's normal). |
| `ssaopassres` | SSAO Pass Resolution | Menu | The SSAO pass can be set to Full, Half, or Quarter the resolution of the input image. |
| `ssaoradius` | SSAO Radius | Float | The distance it searches from the current point for occluders (in object space units). |
| `contrast` | Contrast | Float | Controls the contrast of the SSAO contribution. |
| `attenuation` | Attenuation | Float | Controls the attenuation of the ambient lighting. |
| `edgethresh` | Edge Threshold | Float | To avoid the ambient occlusion from bleeding across the edges of objects onto other objects, an edge detect is done using the depth buffer to figure where one object ends and the next one begins. T... |
| `blurradius` | Blur Radius | Float | The amount of blur in pixels. |
| `blursharpness` | Blur Sharpness | Float | Controls the sharpness of the blur operation. |
| `combinewithcolor` | Combine with Color | Toggle | By default the final ambient occlusion result will be multiplied by the color output of the Render TOP. You can just output the ambient occlusion results by turning this parameter off. |
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
# Access the TOP ssaoTOP operator
ssaotop_op = op('ssaotop1')

# Get/set parameters
freq_value = ssaotop_op.par.active.eval()
ssaotop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ssaotop_op = op('ssaotop1')
output_op = op('output1')

ssaotop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ssaotop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **25** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
