# TOP svgTOP

## Overview

The SVG TOP loads SVG files into TouchDesigner.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | The path and name of the SVG file to load. File format .svg supported. |
| `dat` | DAT | DAT | Not currently used. |
| `reload` | Reload | Toggle | Change from 0 to 1 to force the file to reload, useful when the file changes or did not exist at first. |
| `antialias` | Anti-Alias | Menu | Sets the level of anti-aliasing in the scene. Setting this to higher values uses more graphics memory. |
| `bgcolor` | Background Color | RGB | Sets the background color in the image. |
| `bgalpha` | Background Alpha | Float | Sets the background alpha in the image. |
| `xord` | Transform Order | Menu | The menu attached to this parameter allows you to specify the order in which the changes to your TOP will take place. Changing the Transform order will change where things go much the same way as g... |
| `rord` | Rotate Order | Menu | The rotational matrix presented when you click on this option allows you to set the transform order for the TOP's rotations. As with transform order (above), changing the order in which the TOP's r... |
| `t` | Translate | XY | The two fields for Translate allows you to specify transforms in x and y axes. |
| `tunit` | Translate Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `r` | Rotate | XYZ | The three fields for Rotate allow you to specify the amount of rotation along any of the three axes. |
| `s` | Scale | XY | The two fields for Scale allows you to specify transforms in x and y axes. |
| `p` | Pivot | XY | The Pivot point edit fields allow you to define the point about which the TOP scales and rotates. Altering the pivot point of a TOP produces different results depending on the transformation perfor... |
| `punit` | Pivot Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
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
# Access the TOP svgTOP operator
svgtop_op = op('svgtop1')

# Get/set parameters
freq_value = svgtop_op.par.active.eval()
svgtop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
svgtop_op = op('svgtop1')
output_op = op('output1')

svgtop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(svgtop_op)
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
