# TOP cacheTOP

## Overview

The Cache TOP stores a sequence of images into GPU memory.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While this is On, the Cache TOP will capture images into its memory. |
| `activepulse` | Active Pulse | Pulse | Captures an image for the single frame this was pulsed. |
| `cacheonce` | Get One Image on Startup | Toggle | Checking this On will cook the TOP once after startup to load an initial image. |
| `replace` | Replace Single | Toggle | While this is On, the Cache TOP will replace the image at 'Replace Index' with the input image. This allows you to replace specific images in the cache at will. |
| `replacespulse` | Replace Pulse | Pulse | Replace an image for the single frame this was pulsed. |
| `replaceindex` | Replace Index | Int | Select the image index that will be replaced by the input, when 'Replace Single' is turned on. |
| `prefill` | Pre-Fill | Toggle | Cooks 'Cache Size' number of times to fill the Cache TOP with images. When set to 1, it will fill the cache. If set to 1 during playback, it will fill immediately. If set to 1 and saved out, then n... |
| `prefillpulse` | Pre-Fill Pulse | Pulse | Pre-fills a single image during the frame this was pulsed. |
| `cachesize` | Cache Size | Int | Determines the number of images that can be stored in this Cache TOP. |
| `step` | Step Size | Int | The number of cooks that go by before the Cache TOP grabs an image. A Step Size of 2 will cache an image every 2nd cook, a Step Size of 3 will cache every 3rd cook, and so on. |
| `outputindex` | Output Index | Float | Determines which image in cache the TOP outputs. 0 is the most recent image, negative integers output image further back in time. |
| `outputindexunit` | Output Index Unit | Menu | Sets the units used in the Output Index parameter. |
| `interp` | Interpolate Frames | Toggle | When On (On = 1), the Cache TOP will interpolate between frames when non-integer values are used in the Output Index parameter. For example, a value of -0.5 in Output Index will output a blended im... |
| `alwayscook` | Always Cook | Toggle | Forces the operator to cook every frame. |
| `reset` | Reset | Toggle | While On this will empty the cache of stored images and release the memory held by the TOP. |
| `resetpulse` | Reset | Pulse | Instantly empty the cache. |
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
# Access the TOP cacheTOP operator
cachetop_op = op('cachetop1')

# Get/set parameters
freq_value = cachetop_op.par.active.eval()
cachetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cachetop_op = op('cachetop1')
output_op = op('output1')

cachetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cachetop_op)
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
