# TOP transformTOP

## Overview

The Transform TOP applies 2D transformations to a TOP image like translate, scale, rotate, and multi-repeat tiling.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `xord` | Transform Order | Menu | The menu attached to this parameter allows you to specify the order in which the changes to your TOP will take place. Changing the Transform order will change where things go much the same way as g... |
| `t` | Translate | XY | The two fields for Translate allows you to specify transforms in x and y axes. |
| `tunit` | Translate Unit | Menu | Sets the units used in the Translate parameter. |
| `rotate` | Rotate | Float | The field for rotation allows you to specify the amount of rotation of the image. |
| `s` | Scale | XY | The two fields for Scale allows you to specify transforms in x and y axes. |
| `growshrink` | Grow / Shrink | XY | Grow/Shrink is a scale that is given in pixel units. A positive value will cause the image to grow that many pixels while a negative will cause the image to shrink that many pixels. |
| `p` | Pivot | XY | The Pivot point edit fields allow you to define the point about which the TOP scales and rotates. Altering the pivot point of a TOP produces different results depending on the transformation perfor... |
| `punit` | Pivot Unit | Menu | Sets the units used in the Pivot parameter. |
| `bgcolor` | Backgound Color | RGBA | Color applied behind the foreground image. The background is visible when the image is translated or scaled down. Try scaling an image down 50% in size (Scale = 0.5,0.5) and setting the background ... |
| `premultrgbbyalpha` | Pre-Multiply RGB by Alpha | Toggle | This option allows the Background Color to be pre-multiplied by alpha. |
| `compover` | Comp Over Background Color | Toggle | Fill any area with the background color if it has alpha less than 1. |
| `mipmapbias` | Mipmap Bias | Float | If the input is sampled using mipmapping, this applies a bias to which mip level(s) are used when sampling the texture. 0 means the levels that would be normally used. Negative will selected higher... |
| `extend` | Extend | Menu | This parameter determines what happens at the edges of the tiles. |
| `limittiles` | Limit Tiles | Toggle | Turn this On to limit the number of tiles in the U and V directions using the parameters below. |
| `tileu` | Tile U | Float | The first Tile U parameter sets the number of tiles to repeat on the left of the source image. The second Tile U parameter sets the number of tiles to repeat on the right of the source image. The i... |
| `tilev` | Tile V | Float | The first Tile V parameter sets the number of tiles to repeat on the botttom of the source image. The second Tile V parameter sets the number of tiles to repeat on the top of the source image. The ... |
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
# Access the TOP transformTOP operator
transformtop_op = op('transformtop1')

# Get/set parameters
freq_value = transformtop_op.par.active.eval()
transformtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
transformtop_op = op('transformtop1')
output_op = op('output1')

transformtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(transformtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **29** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
