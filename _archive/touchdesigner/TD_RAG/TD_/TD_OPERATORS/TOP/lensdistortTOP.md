# TOP lensdistortTOP

## Overview

Applies or removes lens distortion from an image using the Brown-Conrady model.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `invert` | Invert Distortion | Toggle | Reverse the lens distortion. This will *mostly* undo the distortion applied by another Lens Distort TOP with the same parameters and Inverse disabled.     The lens distortion algorithm does not hav... |
| `k1` | K1 | Float | The first radial distortion constant. The k constants move pixels towards or away from the center of the image. Values greater than 0 produce a barrel or fisheye effect, while values less than zero... |
| `k2` | K2 | Float | The second radial distortion constant. See K1. |
| `p1` | P1 | Float | The first tangential distortion constant. Tilts the image up and down. |
| `p2` | P2 | Float | The second tangential distortion constant. Tilts the image left or right. |
| `k3` | K3 | Float | The third radial distortion constant (not used in the inverse distortion). See K1. |
| `center` | Optical Center | Float | The position in the image that should be the center of the distortion. Depending on the unit mode selected, the position can be entered as an absolute position measured from the bottom-left corner,... |
| `centerunit` | Optical Center Units | Menu |  |
| `focallength` | Focal Lengths | Float | The focal length components of the camera matrix descibed either as normalized resolution-independent values or as pixels. The focal length acts as a scalar on the other distortion parameters. The ... |
| `focallengthunit` | Focal Length Units | Menu |  |
| `layout` | Layout | Menu | Determines how the transformed image is arranged inside the final output image space. This value can be useful to preserve the native pixel resolution of the input image, or ensuring a final output... |
| `extendmode` | Extend Mode | Menu | Determines what values are used when the output image exceeds the bounds of the input image. |
| `alpha` | Optimal Alpha | Float | Determines how much of the image is preserved when calculating the optimal post transform. When zero, the optimal transform will include only the region of interest. When one, the transform will in... |
| `transformmode` | Post Transform | Menu | Choose whether to preform an addition transformation to the image after the lens distortion is applied. This is useful for positioning and scaling the distorted image within the final image frame a... |
| `newcenter` | New Center | Float | A new optical center position that allows for shifting the transformed image within the output image frame. Using the same value as the Optical Center parameter will result in no post distortion of... |
| `newcenterunit` | New Center Unit | Menu | Determines how the new center values are interpreted. |
| `newfocallength` | New Focal Lengths | Float | A new focal length that allows for scaling the transformed image relative to output image frame. Using the same value as the Focal Lengths parameter will result in no post distortion scaling. Using... |
| `newfocallengthunit` | New Focal Length Units | Menu |  |
| `centeroffset` | Center Offset | Float | Shifts the distorted image within the output image frame. |
| `centeroffsetunit` | Center Offset Unit | Menu |  |
| `scale` | Scale | Float | Performs an additional post-distortion scale on the image. The scale is relative to the original camera matrix, so values greater than 1 will stretch the image, while values less than 1 will shrink... |
| `cropmode` | Cropping | Menu | Crop the transformed image so that only part of the image will appear in the final output. Unless a custom resolution is given, the cropped region will be used to determine the final output resolut... |
| `cropregion` | Custom Region | XYZ | Defines a custom cropping region in the order of Left, Bottom, Right, Top. The values can either be as a fraction of the image (0-1) or as pixels of the input image size. Entering the ROI values fr... |
| `cropunit` | Crop Unit | Menu | The units used to interpret the values of the custom cropping region. Can be as fractions (0-1) of the image or as pixels of the input image size. |
| `scaleunit` | Scale Unit | Menu | Determines how the scale values are used. |
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
# Access the TOP lensdistortTOP operator
lensdistorttop_op = op('lensdistorttop1')

# Get/set parameters
freq_value = lensdistorttop_op.par.active.eval()
lensdistorttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
lensdistorttop_op = op('lensdistorttop1')
output_op = op('output1')

lensdistorttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(lensdistorttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **38** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
