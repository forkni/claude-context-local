# TOP pointtransformTOP

## Overview

The Point Transform TOP treats the RGB values of the input image as a point cloud of XYZ positions or vectors and performs 3D transformations and alignments.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `inputtype` | Input Type | Menu | Choose if the RGB channels of the input texture should be treated as positions or vectors. Vectors will not have the translation portion of the transform applied to them, and can be normalized befo... |
| `innormalize` | Normalize Input | Toggle | RGB input vectors are rescaled to a length of one before they are transformed. |
| `outnormalize` | Normalize Output | Toggle | RGB vectors are rescaled to a length of one after they are transformed. |
| `xord` | Transform Order | Menu | Changes the order that the translate, rotate and scale operations are performed on the input. Analogous to how you would end up in different locations if you were to move a block and turn east, ver... |
| `rord` | Rotate Order | Menu | As with transform order (above), changing the order in which the rotations take place will alter the final position and orientation. A Rotation order of Rx Ry Rz would create the final rotation mat... |
| `t` | Translate | XYZ | Move the input positions in the X, Y and Z axes. If the input is set to 'Vector', the translate values will have no effect. |
| `r` | Rotate | XYZ | Rotate the input RGB values around the corresponding X, Y and Z axes. Angles are given in degrees. |
| `s` | Scale | XYZ | Scale the input RGB values in the corresponding X, Y and Z axes. If 'Normalize Output' is on, then all output values will be rescaled to a length of one regardless of the scale values. |
| `p` | Pivot | XYZ | The pivot is the point about which the input points or vectors are scaled and rotated. Altering the pivot point produces different results depending on the transformation performed on the object. |
| `scale` | Uniform Scale | Float | Scale the input values along all axes simultaneously. |
| `invert` | Invert | Toggle | Invert the transformation i.e. preform the reverse movements. |
| `lookat` | Look At | Object | Allows you to orient your input points by naming the object you would like them to Look At, or point to. Once you have designated this object to look at, it will continue to face that object, even ... |
| `upvector` | Up Vector | XYZ | When orienting an object towards the 'Look At' target, the Up Vector is used to determine where the positive Y axis points. |
| `forwarddir` | Forward Direction | Menu | Sets which axis and direction is considered the forward direction. |
| `chopinput` | Transform CHOP | CHOP | Path to a CHOP node with channels describing a 3D transformation. These channels may come from a Transform CHOP or another CHOP with the correct channels defined. |
| `multiplyorder` | Multiply Order | Menu | Controls whether the transformation from the given CHOP is applied to the input values before or after the transformation describe by this node. |
| `weightchannel` | Weight Channel | Menu | Select how to use the colors of the second input image as weights for transforming the points of the first input. |
| `weightrange` | Weight Range | Float | Set the range of weight values used to control how much of the transformation is applied to a point. Points with the minimum weight will not be transformed, while points with the maximum weight wil... |
| `alignxformorder` | Align Transform Order | Menu | Determines the order that align operations are performed on the input points. Note: Unlike Scaling on the transform page, the alignment scale is always done relative to the center of the point clou... |
| `alignref` | Reference Node | OP | A path to a TOP or SOP node used to align the input points after the transformation. Note Using another point cloud TOP as a reference will incur additional performance costs because of the need to... |
| `alignopord` | Align Operation Order | Menu | Set the order in which scale and transform is applied when aligning. |
| `aligntx` | Align Translate X | Menu | Determines the final position of points along the X axis i.e. shifts values in the red channel. |
| `fromx` | From Input | Menu | Determines how the points are aligned relative to the dimensions of the input points. |
| `tox` | To Reference | Menu | Determines how the final points are aligned relative to the reference node. |
| `alignty` | Align Translate Y | Menu | Determines the final position of points along the Y axis i.e. shifts values in the green channel. |
| `fromy` | From Input | Menu | Determines how the points are aligned relative to the dimensions of the input points. |
| `toy` | To Reference | Menu | Determines how the final points are aligned relative to the reference node. |
| `aligntz` | Align Translate Z | Menu | Determines the final position of points along the Z axis i.e. shifts values in the blue channel. |
| `fromz` | From Input | Menu | Determines how the points are aligned relative to the dimensions of the input points. |
| `toz` | To Reference | Menu | Determines how the final points are aligned relative to the reference node. |
| `alignscale` | Align Scale | Menu | The Align Scale can be used to resize the point cloud to fit inside the given bounds. Scaling can be done per axis (maintaining proportions or stretching), or on all axes. |
| `alignscalex` | Align Scale X | Menu | The point cloud is resized based on its width in the X axis. |
| `alignscaley` | Align Scale Y | Menu | The point cloud is resized based on its height in the Y axis. |
| `alignscalez` | Align Scale Z | Menu | The point cloud is resized based on its depth in the Z axis. |
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
# Access the TOP pointtransformTOP operator
pointtransformtop_op = op('pointtransformtop1')

# Get/set parameters
freq_value = pointtransformtop_op.par.active.eval()
pointtransformtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
pointtransformtop_op = op('pointtransformtop1')
output_op = op('output1')

pointtransformtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(pointtransformtop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **47** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
