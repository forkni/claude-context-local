# TOP ndioutTOP

## Overview

The NDI Out TOP will send image and audio data over IP to other NDI (Network Data Interface) enabled applications.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Makes itself available as a source and sends out image data when active. |
| `name` | Source Name | Str | Specify the name for this source. |
| `failovername` | Failover Source Name | Str | If this source fails while receivers are connected to it, they will instead try to connect to the specified Failover Source. This format of this should be MACHINENAME (SourceName). This format is t... |
| `fps` | FPS | Float | Specify the frame rate to send at. Note that NDI uses the FPS partially as a guide to control how to compress the frames. The higher the FPS, the more compressed the frames will be. So for example ... |
| `lowperformancebehavior` | Low-Performance Behavior | Menu | When the NDI sending thread isn't able to keep up due to insufficient system resources (usually available CPU time), this controls the resulting behavior of the node. |
| `outputpixelformat` | Output Pixel Format | Menu | Controls the pixel format the output is encoded into. |
| `includealpha` | Include Alpha | Toggle | Also sends the alpha channel when this is turned on. If this is off the alpha will be 1.0. |
| `grouptable` | Group Names Table | DAT | Can be DAT table with a column with the header 'groups'. Each cell listed under that heading is added as one of the NDI groups this output annouces itself as part of. |
| `audiochop` | Audio CHOP | CHOP | Specify the CHOP (containing audio data) to send out on the NDI stream. |
| `metadata` | Metadata DAT | DAT | Specify the DAT (containing the metadata in table format or valid XML format) to send out on the NDI stream. The metadata can be read in by the NDI In TOP using an Info DAT. |
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
# Access the TOP ndioutTOP operator
ndiouttop_op = op('ndiouttop1')

# Get/set parameters
freq_value = ndiouttop_op.par.active.eval()
ndiouttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
ndiouttop_op = op('ndiouttop1')
output_op = op('output1')

ndiouttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(ndiouttop_op)
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
