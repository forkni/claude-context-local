# TOP rectangleTOP

## Overview

The Rectangle TOP can be used to generate Rectangles with rounded corners.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `size` | Size | XY | Width and Height of the rectangle to draw. |
| `sizeunit` | Size Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `rotate` | Rotate | Float | Rotates the shape by the specified number of degrees. |
| `center` | Center | XY | Coordinates of the center of the shape. (0,0) corresponds to a perfectly centered shape. |
| `centerunit` | Center Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `justifyh` | Justify Horizontal | Menu | Specify the horizontal alignment of the rectangle. |
| `justifyv` | Justify Vertical | Menu | Specify the vertical alignment of the rectangle. |
| `fillcolor` | Fill Color | RGB | Color to use for the fill of the shape. |
| `fillalpha` | Fill Alpha | Float | Alpha of the fill color. |
| `border` | Border Color | RGB | Color to use for the border of the shape. |
| `borderalpha` | Border Alpha | Float | Alpha of the border color. |
| `bgcolor` | Background Color | RGB | Color to use for the background. |
| `bgalpha` | Background Alpha | Float | Alpha of the background color. |
| `multrgbbyalpha` | Multiply RGB by Alpha | Toggle | Multiplies the RGB values by the Alpha values |
| `borderwidth` | Border Width | Float | Width of the border to draw on the shape. |
| `borderwidthunit` | Border Width Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `borderoffset` | Border Offset | Float | Value from 0 to 1 indicating the fraction of the border that extends beyond the radius of the shape. Effectively sets the radius to radius + borderoffset*borderwidth. |
| `cornerradius` | Corner Radius | Float | Specifies the radius to be used for rounding the corners of the rectangle. |
| `cornerradiusunit` | Corner Radius Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `antialias` | Anti-Alias | Toggle | When on, the shape will be anti-aliased. |
| `softness` | Softness | Float | Specifies the amount that the background color should be blended into the shape. |
| `softnessunit` | Softness Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `compoverinput` | Comp Over Input | Toggle | Turning this On will composite the input with the image. |
| `operand` | Operation | Menu | Choose which composite operation is performed from this menu. Search the web for 'blend modes' for more detailed information on the effects of each type. |
| `swaporder` | Swap Order | Toggle | Swaps the order of the composite with the input. |
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
# Access the TOP rectangleTOP operator
rectangletop_op = op('rectangletop1')

# Get/set parameters
freq_value = rectangletop_op.par.active.eval()
rectangletop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
rectangletop_op = op('rectangletop1')
output_op = op('output1')

rectangletop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(rectangletop_op)
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
