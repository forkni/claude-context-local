# TOP kinectazureTOP

## Overview

The Kinect Azure TOP can be used to configure and capture data from a Microsoft Kinect Azure camera or a Kinect-compatible Orbbec Camera (Femto Mega, Femto Bolt, etc).

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | Enable or disable the camera. Note Disabling this TOP will also disable any other operators (Kinect Azure Select TOP or Kinect Azure CHOP) that rely on it. |
| `library` | Hardware Type | Menu | Choose whether you are using Microsoft Kinect Azure hardware or a Kinect compatible Orbbec camera (Femto Mega, Femto Bolt, etc). Both camera types can be used together in the same project, but only... |
| `sensor` | Sensor | Menu | The serial number of the connected Kinect Azure camera. The TOP will automatically fill the list with all available cameras. Note: Only one Kinect Azure TOP should be connected to a single camera. |
| `fps` | Camera FPS | Menu | Controls the frame rate of both the color and depth cameras. Some higher camera resolutions are not supported when running at 30FPS. Lower framerates can produce brighter color images in low light ... |
| `colorres` | Color Resolution | Menu | The resolution of images captured by the color camera. Different resolutions may have different aspect ratios. Note: 4096 x 3072 is not supported at 30 FPS. |
| `depthmode` | Depth Mode | Menu | The depth mode controls which of the Kinect's two depth cameras (Wide or Narrow FOV) are used to produce the depth image and whether any 'binning' is used to process the data. In 'binned' modes, 2x... |
| `modelpath` | Body Tracking Model | File | The file path to the onnx model that performs body tracking features. TouchDesigner includes the regular and lite models that are part of the Kinect Azure SDK. |
| `proccessingmode` | Body Tracking Processing Mode | Menu | Determines how the body tracking model is processed. The default mode runs mostly on the GPU (supports Nvidia, AMD and Intel), but this can also be switched to a CPU mode when a compatible GPU is n... |
| `gpu` | Body Tracking GPU Device | Int | The device number of the GPU to use when there are multiple GPUs in the system. The ordering system may be dependent on the GPU manufacturer. |
| `orientation` | Sensor Orientation | Menu | Used to indicate when the camera is mounted in a non-upright position. This can help improve body-tracking results. |
| `image` | Image | Menu | A list of available image types to capture from the device and display in this TOP. All image types have a second version that is mapped (aligned) to the image space of the other camera so that col... |
| `remapimage` | Align Image to Other Camera | Toggle | When enabled, the current image will be remapped to align with images from the other camera. For example, use this feature to create a color camera image that maps to the pixels of the depth camera... |
| `bodyimage` | Sync Image to Body Tracking | Toggle | When enabled, the image produced will be delayed so that it corresponds to the most recent data in the body tracking system. The amount of delay may fluctuate based on the power of the processor do... |
| `mirrorimage` | Mirror Image | Toggle | Flip the image in the horizontal axis. |
| `cpu` | CPU Body Tracking | Toggle | When enabled, body tracking calculations will be done on the CPU rather than on the graphics card. This method is much slower, but does not require a high-powered graphics card to function. |
| `resetcolors` | Reset Color Controls | Pulse | Reset all of the color controls to the camera's defaults. These vary per camera and may be different than the parameter defaults. |
| `enablecolors` | Enable Color Controls | Toggle | Turn on to enable adjustment controls for the color camera. When disabled, the previous color settings will remain in place. Use the Reset Color Controls button to switch the camera back to its def... |
| `manualexposure` | Manual Exposure | Toggle | Enable to allow setting the exposure time manually. When disabled, the camera will automatically choose an exposure based on the light levels and frame rate. Note: This feature may not work correct... |
| `exposure` | Exposure Time | Int | Adjust the exposure time of the color image measured in microseconds. The time must be less than one frame. Note: This feature may not work correctly due to issues in the current Kinect SDK. |
| `manualwhitebalance` | Manual White Balance | Toggle | Enable to allow setting the camera white balance manually. |
| `whitebalance` | White Balance | Int | Select the temperature in degrees Kelvin used to set the white balance of the image. The value is rounded to the nearest 10 degrees. |
| `brightness` | Brightness | Int | Used to adjust the brightness of the image from 0 to 255. 128 is the default. |
| `contrast` | Contrast | Int | Conrtols the contrast of the color image. |
| `saturation` | Saturation | Int | Controls the saturation of the color image. |
| `sharpness` | Sharpness | Int | Adjusts the sharpness of the color image. |
| `gain` | Gain | Int | The gain of the color image. |
| `backlight` | Backlight Compensation | Toggle | Enables compensation for bright back lighting in a scene. |
| `powerfreq` | Powerline Frequency | Menu | Select the frequency of the power supply for use in the cameras noise cancellation system. |
| `depthdelay` | Depth Image Delay | Int | A delay in microseconds between when the depth and color images are captured. The delay must be less than one frame in length based on the current framerate. |
| `syncmode` | Wired Sync Mode | Menu | When using more than one Kinect Azure camera, this setting can be used to determine which unit is the master and which are subordinates. |
| `subdelay` | Subordinate Delay | Int | A delay in microseconds between when the master unit captures an image and when this device captures an image. (Only applicable for subordinate devices). |
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
# Access the TOP kinectazureTOP operator
kinectazuretop_op = op('kinectazuretop1')

# Get/set parameters
freq_value = kinectazuretop_op.par.active.eval()
kinectazuretop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
kinectazuretop_op = op('kinectazuretop1')
output_op = op('output1')

kinectazuretop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(kinectazuretop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **44** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
