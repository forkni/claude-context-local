# SOP spriteSOP

## Overview

The Sprite SOP creates geometry (quad sprites) at point positions defined by the CHOP referenced in the XYZ CHOP parameter.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `xyzchop` | XYZ CHOP | CHOP | A CHOP with 3 channels is required to specify the X, Y, and Z position of the quad to be generated. Each sample creates 1 quad. The created quads are centered at the points defined by each sample. |
| `camera` | Camera | Object | The geometry will always face the Camera COMP specified here. |
| `widthchop` | Width CHOP | CHOP | A 1 channel CHOP can be specified to set the width of the quad at that sample. |
| `colorchop` | Color CHOP | CHOP | A 3 channel CHOP can be specified to set the R, G, and B color values of the quad at that sample. |
| `alphachop` | Alpha CHOP | CHOP | A 1 channel CHOP can be specified to set the alpha of the quad at that sample. |
| `perspectivewidth` | Perspective Width | Float | The width of the geometry created. This parameter only has an effect when the Use Constant Width is less that 1.0. |
| `constantwidth` | Use Constant Width | Float | This blends between using Perspective Width and Constant Width. When Use Constant Width = 0, width is determined only by Perspective Width, when Use Constant Width = 1, width is determined only by ... |
| `constantwidthnear` | Constant Width Near | Float | The width used for quads located at a position Constant Width Falloff Start or closer. |
| `constantwitdhfar` | Constant Width Far | Float | The width used for quads located at a position Constant Width Falloff End or farther. |
| `falloffstart` | Constant Width Falloff Start | Float | At this position the or closer the geometry uses the Constant Width Near parameter for its width. |
| `falloffend` | Constant Width Falloff End | Float | At this position the or farther the geometry uses the Constant Width Far parameter for its width.   NOTE: Inbetween Falloff Start and Falloff End the width is determined using a half-cosine falloff... |

## Usage Examples

### Basic Usage

```python
# Access the SOP spriteSOP operator
spritesop_op = op('spritesop1')

# Get/set parameters
freq_value = spritesop_op.par.active.eval()
spritesop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
spritesop_op = op('spritesop1')
output_op = op('output1')

spritesop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(spritesop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **11** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
