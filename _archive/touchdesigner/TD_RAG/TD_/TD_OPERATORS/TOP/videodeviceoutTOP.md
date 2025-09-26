# TOP videodeviceoutTOP

## Overview

The Video Device Out TOP routes video and audio to output devices using their native driver libraries.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enable or disable the output card. |
| `library` | Library | Menu | Select the driver library to use. |
| `device` | Device | StrMenu | A menu of available video devices to output to. Set the Library parameter above prior to selecting your device. |
| `signalformat` | Signal Format | StrMenu | The signal format to output at. This is the resolution and the frame rate, as well as if the frames are progressive or interlaced. Note that when using an interlaced format, the rate refers to fiel... |
| `outputpixelformat` | Output Pixel Format | Menu | Set the pixel format of the output when possible (depends what type of device is used). Data may be converted to YUV colorspace depending on what the device and settings require. |
| `outputcolorspace` | Output Color Space | Menu | Set the color space of the data sent out, for supported devices. |
| `chop` | Audio CHOP | CHOP | If you want to embed audio data into the output, put the path to a Time Sliced CHOP here. |
| `referencesource` | Reference Source | Menu | On AJA devices what input to use as a reference source input. |
| `audiochop` | Audio CHOP | CHOP | If you want to embed audio data into the output, put the path to a Time Sliced CHOP here. |
| `bufferlength` | Buffer Length | Float | The length in seconds to buffer the audio data, to avoid crackles and pops. |
| `audiobitdepth` | Audio Bit Depth | Menu | Describes the number of bits of information used for each sample. |
| `manualfield` | Manual Field Control | Toggle | When outputting interlaced video if you are using a source video that is also interlaced, it's likely you'll want to make sure you are keeping the odd/even fields in sync, otherwise the video will ... |
| `firstfield` | First Field | Toggle | Tells the Video Device Out TOP if the current frame being given as it's input is the First or Second field in the final output image, when outputting an interlaced video. Look at the description fo... |
| `timecodeop` | Timecode Object/CHOP/DAT | CHOP | Embed timecode into the output. A reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or a Timecode Class object. |
| `transfermode` | Transfer Mode | Menu | Controls how the image data is transfered between the GPU and the output card. |
| `syncoutputs` | Sync Outputs | Toggle | Only currently supported on the Deltacast FLEX line of cards. This will cause multiple FLEX cards to output their content in sync with each other. |
| `syncgroupindex` | Sync Group Index | Int | For different groups of cards, they can be ganged together into different sync groups by specifying the same index for multiple cards in the same group. |
| `resetstats` | Reset Stats | Pulse | A pulse to reset the statistics in an attached Info CHOP. |
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
# Access the TOP videodeviceoutTOP operator
videodeviceouttop_op = op('videodeviceouttop1')

# Get/set parameters
freq_value = videodeviceouttop_op.par.active.eval()
videodeviceouttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
videodeviceouttop_op = op('videodeviceouttop1')
output_op = op('output1')

videodeviceouttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(videodeviceouttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
