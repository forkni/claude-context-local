# SOP textSOP

## Overview

The Text SOP creates text geometry from any TrueType or OpenType font that is installed on the system, or any TrueType/OpenType font file on disk.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `font` | Font | StrMenu | Select the font for the text from this drop down menu. All fonts are provided by the OS, any TrueType font that is loaded into the OS can be used. |
| `fontfile` | Font File | File | Specify any TrueType or OpenType font file (.ttf, .otf file) to use for the text. When using a font file, the Font menu above is disabled. |
| `bold` | Bold | Toggle | Displays the text in bold. |
| `italic` | Italic | Toggle | Displays the text in Italic. |
| `fontsizex` | Font Size X | Float | Sets the font size in X (horizontal). The font size defines the distance from the baseline to the top of the layout box for the given font. The default size of 1 of the default font is close to the... |
| `fontsizey` | Font Size Y | Float | Sets the font size in Y (vertical). |
| `keepfontratio` | Keep Font Ratio | Toggle | Ignores Y value in Font Size. Sets both X and Y size to Font Size X. |
| `scalefontobboxheight` | Scale Font to BBox Height | Toggle | Scale the fonts vertical size so its based on the vertical bounding box of the font. |
| `output` | Output | Menu | Specify geometry output of Triangles, Closed Polygons or Open Polygons. |
| `levelofdetail` | Level of Detail | Int | Controls the quality of the text's shape by adding/removing subdivisions to the geometry. |
| `language` | Language | Menu | Language type hint to help format the glyphs correctly. This should be a abbreviation from the Text TOP/SOP Unicode Language Abbreviations table. |
| `readingdirection` | Reading Direction | Menu | Use to set whether the language reads Left to Right or Right to Left. |
| `kerning` | Kerning | Float | The amount of space to add between letters in X and Y. Kerning is way of adding an arbitrary offset between letters. There already is a default offset associated with each font so the letters are f... |
| `linespacing` | Line Spacing | Float | Determines the amount of space between lines of text. |
| `alignx` | Horizontal Align | Menu | Sets the horizontal alignment. |
| `wordwrap` | Word Wrap | Toggle | When checked text is automatically line wrapped once it takes up the space set in Word Wrap Size parameter below. |
| `wordwrapsize` | Word Wrap Size | Float | Determines the amount of 3D space used before the line wraps. |
| `text` | Text | Str | The string of text to create as geometry.  If newlines or tabs are desired, the recommended way is to change this parameter to expression mode, and specify a Python string that includes   or  to si... |
| `legacyparsing` | Legacy Parsing | Toggle | Note, it's recommended to use a Python expression in the Text parameter instead of enabling legacy parsing, as this parsing can easily run into issues with more complex strings. When enabled and if... |
| `xord` | Transform Order | Menu | Sets the overall transform order for the transformations. The transform order determines the order in which transformations take place. Depending on the order, you can achieve different results usi... |
| `rord` | Rotate Order | Menu | Sets the order of the rotations within the overall transform order. |
| `t` | Translate | XYZ | These three fields move the geometry in the three axes. |
| `r` | Rotate | XYZ | These three fields rotate the geometry in the three axes. |
| `s` | Scale | XYZ | These three fields scale the geometry in the three axes. |
| `p` | Pivot | XYZ | The pivot point for the transformations (not the same as the pivot point in the pivot channels). The pivot point parameters allow you to define the point about which geometry scales and rotates. Al... |

## Usage Examples

### Basic Usage

```python
# Access the SOP textSOP operator
textsop_op = op('textsop1')

# Get/set parameters
freq_value = textsop_op.par.active.eval()
textsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
textsop_op = op('textsop1')
output_op = op('output1')

textsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(textsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **25** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
