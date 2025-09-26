# TOP screengrabTOP

## Overview

The Screen Grab TOP turns the main screen output into a TOP image.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When On, the TOP will grab the screen contents. |
| `activepulse` | Active Pulse | Pulse | Instantly grab the frame. Useful when Active is Off to update the screen-grabbed image for an single frame capture. |
| `source` | Source | StrMenu | Select which source to grab, the 'Full Desktop' canvas, a specific display, or an individual application (Windows only). |
| `refreshsource` | Refresh Sources | Pulse | Click this button to refresh the source list in the menu above after connecting or disconnecting displays or opening or closing application windows. |
| `left` | Left | Float | Sets the left edge of the area to be grabbed. |
| `leftunit` | Left Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `right` | Right | Float | Sets the right edge of the area to be grabbed. |
| `rightunit` | Right Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `bottom` | Bottom | Float | Sets the bottom edge of the area to be grabbed. (Bottom = 0) |
| `bottomunit` | Bottom Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `top` | Top | Float | Sets the top edge of the area to be grabbed. |
| `topunit` | Top Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `delayed` | Delayed (Faster) | Toggle | Faster when On but may not work on some systems (Optimus equipped laptops are problematic). |
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
# Access the TOP screengrabTOP operator
screengrabtop_op = op('screengrabtop1')

# Get/set parameters
freq_value = screengrabtop_op.par.active.eval()
screengrabtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
screengrabtop_op = op('screengrabtop1')
output_op = op('output1')

screengrabtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(screengrabtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
