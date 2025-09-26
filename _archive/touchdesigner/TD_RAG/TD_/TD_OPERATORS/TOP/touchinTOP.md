# TOP touchinTOP

## Overview

The Touch In TOP will read in image data send over a TCP/IP network connection from a Touch Out TOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `address` | Computer Name / IP | Str | The IP address of the computer with the transmitting Touch Out TOP. Use localhost to reference the local machine. |
| `port` | Network Port | Int | The TCP/IP port that the Touch Out TOP is transmitting on. |
| `active` | Active | Toggle | Receives image data while Active is on. |
| `mintarget` | Minimum Target | Float | The smallest amount of queue data (represented in seconds) allowed without adjusting sampling speed. |
| `maxtarget` | Maximum Target | Float | The largest amount of queue data (represented in seconds) allowed without adjusting sampling speed. |
| `maxqueue` | Maximum Queue | Float | The maximum allowed size of the queue (represented in seconds). If the maximum queue size is exceeded, data will be removed from the front of the queue. |
| `targetdelay` | Queue Adjust Time |  | The maximum amount of time allowed for a queue to be above or below the maximum or minimum target without adjusting the sampling speed. |
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
# Access the TOP touchinTOP operator
touchintop_op = op('touchintop1')

# Get/set parameters
freq_value = touchintop_op.par.active.eval()
touchintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
touchintop_op = op('touchintop1')
output_op = op('output1')

touchintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(touchintop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **20** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
