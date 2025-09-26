# TOP realsenseTOP

## Overview

The RealSense TOP connects to Intel RealSense devices and outputs color, depth and IR data from it.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When set to 1 the TOP captures the image stream from the camera. |
| `model` | Model | Menu | Select the model of device to use. |
| `sensor` | Sensor | StrMenu | Select which device to use. |
| `image` | Image | Menu | Select the image type to output. |
| `colorres` | Color Camera Resolution | StrMenu | Select the resolution of the video. Currently only usable for the Color image. |
| `maxdepth` | Max Depth | Float | The depth value pixels with a value of 1 will be set to. Specified in Meters. Pixels with a depth larger than this will be clamped to 1 for fixed point texture output, or go above 1 for floating po... |
| `mirrorimage` | Mirror Image | Toggle | Flip the image horizontally. |
| `defaulttradeoff` | Use Default Tradeoff | Toggle | Use the default Motion Range Tradeoff specified by the device. |
| `tradeoff` | Motion Range Tradeoff | Int | Specifies the tradeoff between motion and range. Value is from 0 (short exposure, short range, and better motion) to 100 (long exposure and long range). |
| `optionschop` | Options CHOP | CHOP | Channels specified in this CHOP allow for setting all of the options that the RealSense camera supports. Channel names should be the same as the C enumeration, with the RS2_OPTION_ prefix removed, ... |
| `skeltracking` | Skeleton Tracking | Toggle | When enabled, performs skeleton tracking using the Cubemos Skeleton Tracking API. The results can be fetched via the RealSense CHOP. A Cubemos license is required for usage. A trial license is avai... |
| `usedefaultpaths` | Use Default Paths | Toggle | When enabled, will search for the license and model files in the default location (LOCALAPPDATA). For the files to appear there the Cubemos SDK will need to be installed. If a specific license dire... |
| `licensedir` | License Directory | Folder | Specify the directory with the license files (activation_key.json and cubemos_license.json). |
| `modelfile` | Skeleton Tracking Model File | File | Specify the model file (.cubemos) |
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
# Access the TOP realsenseTOP operator
realsensetop_op = op('realsensetop1')

# Get/set parameters
freq_value = realsensetop_op.par.active.eval()
realsensetop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
realsensetop_op = op('realsensetop1')
output_op = op('output1')

realsensetop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(realsensetop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **27** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
