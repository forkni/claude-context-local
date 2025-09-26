# SOP fontSOP

## Overview

Note: Font SOP deprecated build 2019.14650, use Text TOP. The Font SOP allows you to create text in your model from Adobe Type 1 Postscript Fonts.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `type` | Primitive Type |  | Select from the following types. For information on the different types, see the Geometry Types section. Bzier Curves and Polygons provide the most efficient use of memory, because they use polygon... |
| `file` | Font |  | Choose the font to create the text. By clicking on the + button a File Dialog will appear, and clicking menu drop down brings up a menu of the most used fonts. |
| `text` | Text |  | Enter the text you want to generate here.     Your text can contain the following special characters:        \  - Take the next character literally (so you can use the / and ` characters in your te... |
| `hcenter` | Center Text Horizontally |  | This check box allows you to center the text horizontally about X = 0. |
| `vcenter` | Center Text Vertically |  | This check box allows you to center the text vertically about Y = 0. |
| `t` | Translate |  | Translates the geometry in x, y and z. |
| `s` | Scale |  | Scales the text in the X and Y axis. |
| `kern` | Kerning |  | Letter spacing in the X direction. Line spacing in the Y direction if there are multiple lines. If you need manual character-by-character, you can do it in Model mode. |
| `italic` | Italic Angle |  | Doesn't actually give an italic version of the font, but rather obliques the text by shearing it the specified number of degrees. A negative number makes the text slant to the left. |
| `lod` | Level of Detail |  | Adobe fonts are defined by Bzier curves. If polygons only is selected, the Font SOP converts these to polygons. This value adjusts the number of points in the polygons that it gets converted to. |
| `hole` | Hole Faces |  | Generates holes in polygons and Bzier faces. |
| `texture` | Texture Coordinates |  | This adds uv coordinates to the geometry created by the Font SOP. |

## Usage Examples

### Basic Usage

```python
# Access the SOP fontSOP operator
fontsop_op = op('fontsop1')

# Get/set parameters
freq_value = fontsop_op.par.active.eval()
fontsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
fontsop_op = op('fontsop1')
output_op = op('output1')

fontsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(fontsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
