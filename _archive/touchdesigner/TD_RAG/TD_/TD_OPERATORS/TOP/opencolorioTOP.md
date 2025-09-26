# TOP opencolorioTOP

## Overview

The OpenColorIO TOP utilizes the OpenColorIO library (<http://opencolorio.org/>) to apply various transforms and lookup tables to your textures and images.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `config` | Configuration File | File | File holding all the relevant information, such as lookup tables, transforms, color spaces, views, and displays. Several sample configurations are provided in the application installation folder /S... |
| `reloadconfig` | Reload Config | Pulse | Manually reload the configuration file. |
| `usecolorspacetransform` | Use Transform | Toggle | Toggle this transform's effect on or off. Color space transforms convert an image from one color space to another. |
| `incolorspace` | Input | StrMenu | Specify the input color space, the color space of the incoming image. |
| `outcolorspace` | Output | StrMenu | Specify the output color space. The image will be converted to this color space from the input color space. |
| `usefiletransform` | Use Transform | Toggle | Toggle this transform's effect on or off. File transforms apply individual color space conversion files. Various file formats are supported, spi1d and spi3d to name a couple. |
| `filesource` | File Source | File | The file to be loaded.   Note that the file will expect a certain color space and file transforms do not internally handle this, so ensure that the image is in the correct color space before applyi... |
| `interpolation` | Interpolation | Menu | Interpolation method of the file. |
| `filedirection` | Direction | Menu | The direction of the transform. To invert the transform, select Inverse. |
| `cdlmode` | CDL Mode | Menu | Color Decision List - Select this transform's effect on the image, either manually using parameter values or using a color correction file (.cc). <https://en.wikipedia.org/wiki/ASC_CDL> |
| `slope` | Slope | XYZ | Adjust the gain. |
| `offset` | Offset | XYZ | Adjust the offset. |
| `power` | Power | XYZ | Adjust the gamma. |
| `saturation` | Saturation | Float | Adjust the saturation. |
| `cdldirection` | Direction | Menu | The direction of the transform. To invert the transform, select Inverse. |
| `ccfile` | Color Correction File | File | The slope, offset, power, and saturation information can instead be loaded from a color correction file (.cc). |
| `useoutput` | Use Output | Toggle | Toggle a display transform. Display transforms allow for color space conversion onto specific display devices. |
| `gain` | Gain | Float | Adjust exposure applied before the display transform. |
| `display` | Display | StrMenu | Color space of the device that will be used to view the image. |
| `view` | View | StrMenu | Specifies the color space transform to be applied to the image. |
| `colorspace` | Input Color Space | StrMenu | Specifies the input color space. |
| `gamma` | Gamma | Float | Adjust amount of gamma correction applied after the display transform. |
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
# Access the TOP opencolorioTOP operator
opencoloriotop_op = op('opencoloriotop1')

# Get/set parameters
freq_value = opencoloriotop_op.par.active.eval()
opencoloriotop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
opencoloriotop_op = op('opencoloriotop1')
output_op = op('output1')

opencoloriotop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(opencoloriotop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **35** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
