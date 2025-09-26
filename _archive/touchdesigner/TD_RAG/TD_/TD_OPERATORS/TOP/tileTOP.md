# TOP tileTOP

## Overview

The Tile TOP tiles images in a repeating pattern.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `cropleft` | Crop Left | Float | Positions the left edge of the image. |
| `cropleftunit` | Crop Left Unit | Menu |  |
| `cropright` | Crop Right | Float | Positions the right edge of the image. |
| `croprightunit` | Crop Right Unit | Menu |  |
| `cropbottom` | Crop Bottom | Float | Positions the bottom edge of the image. |
| `cropbottomunit` | Crop Bottom Unit | Menu |  |
| `croptop` | Crop Top | Float | Positions the top edge of the image. |
| `croptopunit` | Crop Top Unit | Menu |  |
| `extend` | Extend | Menu | This parameter determines what happens at the edges of the tiles. |
| `flop` | Transpose | Toggle | Similar to performing a flop on the image (See Flip TOP) without changing the resolution. It swaps the position of the bottom-right corner with the upper-left corner, while maintaining the original... |
| `repeatx` | Repeat X | Int | Number of tiles in X direction. |
| `repeaty` | Repeat Y | Int | Number of tiles in Y direction. |
| `flipx` | Flip X | Toggle | Flips the image in X. |
| `flipy` | Flip Y | Toggle | Flips the image in Y. |
| `reflectx` | Reflect X | Toggle | Reflects the tiles in X. NOTE: Must have Tile Y set to 2. |
| `reflecty` | Reflect Y | Toggle | Reflects the tiles in Y. NOTE: Must have Tile X set to 2. |
| `overlapu` | Overlap U | Float | Blends the edges together on the right and left edges of the tiles. |
| `overlapuunit` | Overlap U Unit | Menu |  |
| `overlapv` | Overlap V | Float | Blends the edges together on the bottom and top edges of the tiles. |
| `overlapvunit` | Overlap V Unit | Menu |  |
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
# Access the TOP tileTOP operator
tiletop_op = op('tiletop1')

# Get/set parameters
freq_value = tiletop_op.par.active.eval()
tiletop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tiletop_op = op('tiletop1')
output_op = op('output1')

tiletop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tiletop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **33** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
