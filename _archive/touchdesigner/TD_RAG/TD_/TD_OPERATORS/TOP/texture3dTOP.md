# TOP texture3dTOP

## Overview

The Texture 3D TOP creates a 3D texture map. It saves a series of images in one array of pixels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Type | Menu | Specifies the texture type to create. |
| `active` | Active | Toggle | When set to 1, the Texture 3D TOP will fill up it cache with images. The texture3D TOP replaces a slice of its 3d data with its input every frame. When it has filled up all of its slices it wraps a... |
| `replacesingle` | Replace Single | Toggle | While this is set > 0, the Texture 3D TOP will replace the slice at 'Replace Index' with the input image. This allows you to replace specific slices of the 3D texture at will. |
| `replacesinglepulse` | Replace Single Pulse | Pulse | Replace an image for the single frame this was pulsed. |
| `replaceindex` | Replace Index | Int | Select the slice index that will be replaced by the input, when 'Replace Single' is turned on. |
| `prefill` | Pre Fill | Toggle | This feature is used to pre-setup all of the slices of the 3D texture in a single cook. When set to 1, it will fill the cache. If set to 1 during playback, it will fill immediately. If set to 1 and... |
| `prefillpulse` | Pre Fill Pulse | Pulse | Pre-fills a single image during the frame this was pulsed. |
| `cachesize` | Cache Size | Int | The number of images the Texture 3D TOP will hold. This is the number of 3D slices in the texture. |
| `step` | Step Size | Int | This parameter sets how many frames pass before the TOP grabs one into cache. A Sample Step of 1 will grab each consecutive frame, a Sample Step of 2 will grab every other frame, and so on.      Wh... |
| `reset` | Reset | Toggle | When set to 1, the cache is flushed and the TOP is reset. |
| `resetpulse` | Reset Pulse | Pulse | Instantly empty the cache. |
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
# Access the TOP texture3dTOP operator
texture3dtop_op = op('texture3dtop1')

# Get/set parameters
freq_value = texture3dtop_op.par.active.eval()
texture3dtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
texture3dtop_op = op('texture3dtop1')
output_op = op('output1')

texture3dtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(texture3dtop_op)
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
