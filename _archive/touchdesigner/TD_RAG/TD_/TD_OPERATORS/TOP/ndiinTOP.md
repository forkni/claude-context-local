# TOP ndiinTOP

## Overview

The NDI In TOP will obtain its image data over IP from other NDI (Network Data Interface) enabled applications.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Receives image data while Active is on. |
| `name` | Source Name | StrMenu | Select which source stream to use. |
| `extraips` | Extra Search IPs | Str | By default NDI searches using mDNS, which is usually limited to locate networks. To find sources available on machines not reachable by mDNS, this parameter can be filled with a space-separated lis... |
| `bandwidth` | Bandwidth | Menu | Choose High or Low bandwidth option. |
| `hwdecode` | Hardware Decode | Toggle | Enable hardware decode for NDI\|HX encoded video streams. Hardware decoding is not supported for native NDI codec, only NDI\|HX (which is H264). The NDI Out TOP and other software based NDI solutio... |
| `inputpixelformat` | Input Pixel Format | Menu | Choose Native or 8-bit pixel format. |
| `grouptable` | Group Names Table | DAT | Sources can tag themselves as part of one or more 'Groups'. Fill in rows of this table with the names of one or more groups this node is interested in to limited the 'Sources' listed as available. |
| `audiobuflen` | Audio Buffer Length | Float | The length of the audio buffer in seconds. Audio output is delayed by this amount. For example, if the Buffer Length is 0.1 then the sound will occur 100ms = 0.1 seconds later than received (to kee... |
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
# Access the TOP ndiinTOP operator
ndiintop_op = op('ndiintop1')

# Get/set parameters
freq_value = ndiintop_op.par.active.eval()
ndiintop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ndiintop_op = op('ndiintop1')
output_op = op('output1')

ndiintop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ndiintop_op)
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
