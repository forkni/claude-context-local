# TOP photoshopinTOP

## Overview

The Photoshop In TOP can stream the output from Photoshop into TouchDesigner.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the TOP will receive data from Photoshop. |
| `address` | Address | Str | The IP address of the computer that Photoshop is running on.  If Photoshop is running on the same computer as TouchDesigner, localhost can be used in this parameter.  Otherwise, Photoshop's Remote ... |
| `password` | Password | Str | Enter the password specified in Photoshop's Remote Connection dialog. |
| `imageformat` | Image Format | Menu | Determines what format the Photoshop stream is transferred with. |
| `lockeddocument` | Locked Document Name | Str | This parameter can be used to lock the Photoshop In TOP's input to a particular file that is open in Photoshop. |
| `locktocurrent` | Lock to Current Document | Pulse | click this button to lock the Photoshop In TOP's input to the currently active file in Photoshop.  Clicking this button fills out the parameter above Locked Document Name. |
| `unlock` | Unlock | Pulse | Clears the Locked Document Name parameter.  When unlocked, the Photoshop In TOP will grab whichever document is currently active in Photoshop. |
| `updatemode` | Update Mode | Menu | Determines how the image is updated. |
| `maxupdaterate` | Max Update Rate | Float | The maximum update rate of the image when Update Mode is set to automatic. |
| `update` | Update | Pulse | Click to anually update the image. |
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
# Access the TOP photoshopinTOP operator
photoshopintop_op = op('photoshopintop1')

# Get/set parameters
freq_value = photoshopintop_op.par.active.eval()
photoshopintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
photoshopintop_op = op('photoshopintop1')
output_op = op('output1')

photoshopintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(photoshopintop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **23** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
