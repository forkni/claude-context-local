# TOP orbbecTOP

## Overview

The Orbbec TOP can be used to retrieve video streams and IMU data from an Orbbec camera.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Turn this parameter off to disable communication with the camera. This will also stop any Orbbec Select TOPs that rely on this TOP. |
| `device` | Device | Menu | Use this parameter to select the serial number of the camera you wish to connect to. Only one Orbbec TOP can connect to any camera at one time. Use an Orbbec Select TOP to obtain additional video s... |
| `specifyip` | Specify IP | Toggle | Enable this parameter to connect to a camera over ethernet. |
| `ip` | IP | Str | The IP address of the camera to connect to. You must turn on the 'Specify IP' parameter to enter an IP address. This is not necessary for cameras connected by USB. |
| `colorres` | Color Resolution | Menu | Select the resolution of the sensor's color camera. Every camera has a default resolution that it will use automatically. Additional options will appear in the menu depending on the camera model. N... |
| `colorfps` | Color FPS | Menu | Set the frame rate in frames-per-second for the color camera. The camera will assume a default frame rate automatically, but additional rates will appear in this list depending on the camera model.... |
| `depthres` | Depth Resolution | Menu | Select the resolution of the sensor's depth camera. Every camera has a default resolution that it will use automatically. Additional options will appear in the menu depending on the camera model. N... |
| `depthfps` | Depth FPS | Menu | Set the frame rate in frames-per-second for the depth camera. The camera will assume a default frame rate automatically, but additional rates will appear in this list depending on the camera model.... |
| `depthalignmode` | Depth Align Mode | Menu | This parameter can be used to transform the depth image to match the resolution of the color camera. This may be done in either hardware or software depending on the camera model. Some resolutions ... |
| `image` | Image | Menu | Select which of the camera's video streams to display in the node's output image. Additional streams can be obtained for the same camera using the Orbbec Select TOP. |
| `gyro` | Enable Gyro Sensor | Toggle | Enable rotational IMU data from the gyro sensor if it is available on the current camera. The data is measured in degrees/sec and accessible as CHOP channels by attaching an Info CHOP. |
| `accel` | Enable Accel Sensor | Toggle | Enable linear acceleration IMU data from the accel sensor if it is available on the current camera. The data is measured in m/s^2 and accessible as CHOP channels by attaching an Info CHOP. |
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
# Access the TOP orbbecTOP operator
orbbectop_op = op('orbbectop1')

# Get/set parameters
freq_value = orbbectop_op.par.active.eval()
orbbectop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
orbbectop_op = op('orbbectop1')
output_op = op('output1')

orbbectop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(orbbectop_op)
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
