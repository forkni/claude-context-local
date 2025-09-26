# TOP zedTOP

## Overview

The ZED TOP captures video from the ZED depth camera.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | When set to 1 the TOP captures the image stream from the camera. |
| `inputsource` | Input Source | Menu | Select which input type to use between USB, recorded SVO file, or network streaming |
| `camera` | Camera | Menu | Selects which ZED camera to use. |
| `file` | File | File | The path and name of the recorded SVO file to load. SVO and SVO2 playback is supported. |
| `streamip` | Stream IP | Str | The IP address of the streaming camera. |
| `streamport` | Stream Port | Int | The port of the streaming camera. |
| `initialize` | Initialize | Pulse | (pulse) Initializes the SVO playback: sets the SVO position to zero. |
| `start` | Start | Pulse | (pulse) Start is the signal to commence the SVO playback. |
| `play` | Play | Toggle | SVO plays when 1, SVO stops when 0. |
| `cue` | Cue | Toggle | Jumps to Cue Point when set to 1. |
| `cuepoint` | Cue Point | Float | Set the SVO position in the SVO playback as a point to jump to. |
| `cueunit` | Cue Unit | Menu | Select the units for this parameter from Index, Frames, and Seconds. |
| `perspective` | Perspective | Menu | Choose between Left or Right camera. |
| `image` | Image | Menu | Selects between the Color, Depth, Confidence, Disparity, Normals, Point Cloud or Spatial Texture modes. |
| `cameraresolution` | Camera Resolution | Menu | Selects the resolution of the camera capture. |
| `camerafps` | Camera FPS | Float | Sets the frame rate of the camera capture. |
| `sensingmode` | Sensing Mode | Menu | Selects betweem Standard and Fill mode. |
| `depthquality` | Depth Quality | Menu | Selects the depth computation mode of the camera. |
| `mindepth` | Minimum Depth | Float | Sets the minimum depth in meters that will be computed. |
| `maxdepth` | Maximum Depth | Float | Sets the maximum depth in meters. |
| `toocloseval` | Too Close Value | Float | For depth pixels that are too close to resolve, this pixel value will be output instead. |
| `toofarval` | Too Far Value | Float | For depth pixels that are too far to resolve, this pixel value will be output instead. |
| `unknownval` | Unknown Value | Float | For depth pixels whose depth can not be determined, output this value instead. |
| `depthstabilization` | Depth Stabilization | Toggle | Enables depth stabilization for the camera. |
| `rerange` | Rerange | Toggle | Enabling this will remap pixel values to 0-1. |
| `referenceframe` | Reference Frame | Menu | Select between World and Camera reference frames for the Point Cloud pixels. |
| `resetcameratransform` | Camera Transform | Pulse | Resets the camera position used for the reference frame above. |
| `mirrorimage` | Mirror Image | Toggle | Flips the image in the y-axis. |
| `bright` | Brightness | Toggle | Turn on to enable brightness adjustment controls for the camera. When disabled, the camera will use default brightness. |
| `brightval` | Brightness | Int | The brightness of the camera feed. |
| `cont` | Contrast | Toggle | Turn on to enable contrast adjustment controls for the camera. When disabled, the camera will use default contrast. |
| `contval` | Contrast | Int | The contrast of the camera feed. |
| `hue` | Hue | Toggle | Turn on to enable hue adjustment controls for the camera. When disabled, the camera will use default hue. |
| `hueval` | Hue | Int | The hue of the camera feed. |
| `sat` | Saturation | Toggle | Turn on to enable saturation adjustment controls for the camera. When disabled, the camera will use default saturation. |
| `satval` | Saturation | Int | The saturation of the camera feed. |
| `sharp` | Sharpness | Toggle | Turn on to enable sharpness adjustment controls for the camera. When disabled, the camera will use default sharpness. |
| `sharpval` | Sharpness | Int | The sharpness of the camera feed. |
| `gamma` | Gamma | Toggle | Turn on to enable gamma adjustment controls for the camera. When disabled, the camera will use default gamma. |
| `gammaval` | Gamma | Int | The gamma of the camera feed. |
| `autogainexp` | Auto Gain-Exposure | Toggle | Turn on to enable auto gain and exposure for the camera. When disabled, the camera will not apply auto gain and exposure. |
| `gain` | Gain | Toggle | Turn on to enable gain adjustment controls for the camera. When disabled, the camera will use default gain. |
| `gainval` | Gain | Int | The gain of the camera feed. |
| `exp` | Exposure | Toggle | Turn on to enable exposure adjustment controls for the camera. When disabled, the camera will use default exposure. |
| `expval` | Exposure | Int | The exposure of the camera feed. |
| `roi` | Region of Interest | Toggle | Turn on to enable region of interest adjustment controls for the camera when auto gain and exposure is enabled. When disabled, the region of interest will be the full image. The region of interest ... |
| `coord` | ROI Coordinate | Int | The coordinate of the top-left corner of the region of interest rectangle. |
| `dim` | ROI Dimension | Int | The dimensions of the region of interest rectangle. |
| `autowhitebal` | Auto White Balance | Toggle | Turn on to enable auto white balance for the camera. When disabled, the camera will not apply auto white balance. |
| `whitebal` | White Balance | Toggle | Turn on to enable white balance controls for the camera. When disabled, the camera will use default white balance. |
| `whitebalval` | White Balance | Int | The white balance of the camera feed. White balance values are internally multiplied by 100 to be within the range of [2800, 6500]. |
| `ledstat` | LED Status | Toggle | Turn on to enable the front LED of camera. When disabled, the camera LED will be disabled. |
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
# Access the TOP zedTOP operator
zedtop_op = op('zedtop1')

# Get/set parameters
freq_value = zedtop_op.par.active.eval()
zedtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
zedtop_op = op('zedtop1')
output_op = op('output1')

zedtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(zedtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **65** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
