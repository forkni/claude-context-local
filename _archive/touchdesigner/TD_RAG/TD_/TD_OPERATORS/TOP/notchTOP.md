# TOP notchTOP

## Overview

The Notch TOP will load a Notch Block (extension .dfxdll) compiled from Notch Builder. For Commercial and Educational licenses there is a limit of 2 active blocks at a resolution 1920x1080.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | The active state of the node/block. When active, the node will actively render the block. If disabled, the node will release its instance of the block, and unload it if there are no other instances... |
| `clearparams` | Clear Parameter Values on File Change | Toggle | When enabled, all parameters will be cleared. When disabled, it will keep parameter values for exposed parameters of the same name when the Notch Block file changes. |
| `block` | Block | File | Specify the .dfxdll file (ie. Notch Block). |
| `layer` | Layer | StrMenu | The layer used as the output to the Notch TOP. |
| `playmode` | Play Mode | Menu | A menu to specify the method used for playback of the block. |
| `init` | Initialize | Pulse | Initialize the playback of the block. This will reset it to the start, but not move forward with playback. |
| `start` | Start | Pulse | Start the playback of the block. This will reset it to the start and begin playback. |
| `play` | Play | Toggle | Enable playback of the block. When disabled and in Sequential mode the playback will be paused. |
| `speed` | Speed | Float | The speed of the playback. |
| `index` | Index | Float | The index of the playback when Index mode is selected. |
| `indexunit` | Index Unit | Menu | Sets the units used in the Index parameter. |
| `purge` | Purge GPU Mem | Pulse | Purge Video RAM used by the block. |
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
# Access the TOP notchTOP operator
notchtop_op = op('notchtop1')

# Get/set parameters
freq_value = notchtop_op.par.active.eval()
notchtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
notchtop_op = op('notchtop1')
output_op = op('output1')

notchtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(notchtop_op)
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
