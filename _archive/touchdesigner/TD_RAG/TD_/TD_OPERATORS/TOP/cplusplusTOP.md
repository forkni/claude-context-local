# TOP cplusplusTOP

## Overview

The CPlusPlus TOP allows you to make custom TOP operators by writing your own plugin using C++.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `plugin` | Plugin Path | File | The path to the plugin you want to load. |
| `reinit` | Re-Init Class | Toggle | When this parameter is On, it will delete the instance of the class created by the plugin, and create a new one. |
| `reinitpulse` | Re-Init Class | Pulse | Instantly reinitialize the class. |
| `unloadplugin` | Unload Plugin | Toggle | When this parameter goes above 1, it will delete the instance of the class created by the plugin and unload the plugin. If multiple TOPs have loaded the same plugin they will all need to unload it ... |
| `antialias` | Anti-Alias | Menu | The level of anti-aliasing you want the framebuffer that will be created for you to have. |
| `depthbuffer` | Depth Buffer | Menu | Specifies the pixel format of the depth buffer you want, if any. |
| `stencilbuffer` | Stencil Buffer | Toggle | Turn on if you want a stencil buffer. |
| `numcolorbufs` | # of Color Buffers | Int | Any shader you write can output to more than one RGBA buffer at a time. Instead of writing to gl_FragColor in your shader, you write to gl_FragData[i] where i is the color buffer index you want to ... |
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
# Access the TOP cplusplusTOP operator
cplusplustop_op = op('cplusplustop1')

# Get/set parameters
freq_value = cplusplustop_op.par.active.eval()
cplusplustop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
cplusplustop_op = op('cplusplustop1')
output_op = op('output1')

cplusplustop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(cplusplustop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **21** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
