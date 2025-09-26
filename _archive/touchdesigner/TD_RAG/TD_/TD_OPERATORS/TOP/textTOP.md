# TOP textTOP

## Overview

The Text TOP displays text strings in an image. It allows for multiple fonts, sizes, colors, borders, character separation and line separation.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `field` | Field Component | PanelCOMP | Specifies a Field Component to use as the source of the text. The font and style of the text displayed in the Field Component are set using the parameters in the Text TOP. |
| `dat` | DAT | DAT | Specifies a DAT to use for the source of the text. Drag and Drop a DAT onto this field, or manually enter the DAT's path. |
| `rowindex` | DAT Row | Int | The row number (starting from 0) of the cell, if the DAT is a table. |
| `colindex` | DAT Col | Int | The column number of the cell, if the DAT is a table. |
| `specdat` | Specification DAT | DAT | A Table DAT that allows you to specify and position text by pixel, with the lower left corner being at 0, 0.  Column headers must include position1 or x, position2 or y, and text.  A sample table c... |
| `text` | Text | Str | A string of text. It optionally can be followed by a numeric value and another post-string, as set with Value and Post Text below. If newlines or tabs are desired, the recommended way is to change ... |
| `legacyparsing` | Legacy Parsing | Toggle | In older builds the syntax \XXX (E.g \200 would be character 200), ,   as well as [] and {} (to position strings) was parsed in the string. This is now deprecated. For specifying characters codes, ... |
| `appendvalue` | Append Value | Toggle | Enables the Value field defined below. This value is inserted between the Text string and the Post Text string. |
| `valuetouse` | Value | Float | The numeric value to display. |
| `totaldigits` | Total Digits | Int | The total number of digits in the value displayed. |
| `decimaldigits` | Decimal Digits | Int | The number of digits displayed after the decimal place. |
| `posttext` | Post Text | Str | The text string appended after Text and Value (if present). |
| `chopvaluereplace` | CHOP Value %-Replace | Toggle | Allows portions of the strings to be replaced by CHOP values via a syntax similar to C-style printf()/sprintf(). More details of the syntax are provided in the next parameter, 'CHOP' . |
| `chop` | CHOP | CHOP | The CHOP containing all the values to insert in the Text strings. The Text TOP will repeat the Text string until all CHOP channels are displayed. They are displayed by using a special syntax in you... |
| `wordwrap` | Word Wrap | Toggle | When checked text is automatically line wrapped so it doesn't extend outside the TOP's borders.  When using Word Wrap and Auto-Size together, the text will first word-wrap based on the specified fo... |
| `smartquote` | Smart Quote | Toggle | Enables smart quotes which use a left (opening) quotation mark and a right (closing) quotation mark instead of straight quotes. |
| `font` | Font | StrMenu | Select the font for the text from this drop down menu. All fonts are provided by Windows, any TrueType font that is loaded into Windows can be used. |
| `fontfile` | Font File | File | Specify any TrueType font file (.ttf file) to use for the text.  When using a font file, the Font menu above is disabled. |
| `charset` | Character Set |  | Select which character set to use. |
| `dispmethod` | Display Method | Menu | The display method used. |
| `antialias` | Anti-Alias | StrMenu | Smoothes out the edges of the text. Not available for Texture Display Mode. |
| `strokewidth` | Stroke Width | Int | Controls the width of the outline when using Stroke Display Method. |
| `bold` | Bold | Toggle | Displays the text in bold. |
| `italic` | Italic | Toggle | Displays the text in Italic. |
| `fontautosize` | Auto-Size Font | Menu | Automatically controls font size using one of the following 3 options. When using this feature along with Word Wrap turned on, it will first word-wrap the text based on the specified font size, the... |
| `fontsizex` | Font Size X | Float | Sets the font size in X (horizontal). Note: Floating point font sizes are permissable when using Polygon and Outline Display Methods. |
| `fontsizexunit` | Font Size X Unit | Menu | Select the units for this parameter from Pixels, Fraction, Fraction Aspect or Points (font point size). A Point is defined using the Windows conventions for 100% scaling, which is 96 pixels to 72 p... |
| `fontsizey` | Font Size Y | Float | Sets the font size in Y (vertical). Note: Floating point font sizes are permissable when using Polygon and Outline Display Methods. |
| `fontsizeyunit` | Font Size Y Unit | Menu | Select the units for this parameter from Pixels, Fraction, Fraction Aspect or Points (font point size). |
| `keepfontratio` | Keep Font Ratio | Toggle | Ignores Y value in Font Size. Sets both X and Y size to Font Size X. |
| `breaklang` | Break Language | menu | Language type hint to help format the glyphs correctly. |
| `readingdirection` | Reading Direction | Menu | Use to set whether the language reads Left to Right or Right to Left. |
| `tracking` | Tracking | Float | The amount of space to add between letters in X and Y. Tracking is way of adding an arbitrary offset between letters. There already is a default offset associated with each font so the letters are ... |
| `position` | Position | Float | The starting position of the text in X and Y.        TIP: Inside the Text and Post Text fields the position can be overridden by using brackets.           [x,y] - "bleh[x,y]newtext" will place newt... |
| `positionunit` | Position Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `linespacing` | Line Spacing | Float | Determines the amount of space between lines of text. |
| `linespacingunit` | Line Spacing Unit | Menu | Select the units for this parameter from Pixels, Fraction (0-1), Fraction Aspect (0-1 considering aspect ratio). |
| `alignx` | Horizontal Align | menu | Sets the horizontal alignment. |
| `alignxmode` | Horizontal Align Mode | menu | Determines how horizontal alignment is calculated. |
| `aligny` | Vertical Align | Menu | Sets the vertical alignment. |
| `alignymode` | Vertical Align Mode | menu | Determines how vertical alignment is calculated. |
| `borderspace` | Border Space | Float | When using Auto-Size Font, it will further shrink the text to give it a border. |
| `multrgbbyalpha` | Multiply RGB by Alpha | Toggle | Multiplies the RGB channels by the alpha channel. |
| `fontcolor` | Font Color | RGB | RGBA values for the text displayed. (default: white (1,1,1,1)) |
| `fontalpha` | Font Alpha | Float | Set the alpha value for the font. |
| `bgcolor` | Background Color | RGB | RGBA values for the background. (default: black (0,0,0,0)) |
| `bgalpha` | Background Alpha | Float | Set the alpha value for the background. |
| `bordera` | Border A | RGB | RGBA values for border A color. |
| `borderaalpha` | Border A Alpha | Float | Set the alpha value for border A. |
| `borderb` | Border B | RGB | RGBA values for border B color. |
| `borderbalpha` | Border B Alpha | Float | Set the alpha value for border B. |
| `leftborder` | Left Border | Menu | What color the 2 left-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `leftborderi` | Left Border Inside | Menu | Same as above parameter but used for an inside border. |
| `rightborder` | Right Border | Menu | What color the 2 right-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `rightborderi` | Right Border Inside | Menu | Same as above parameter but used for an inside border. |
| `bottomborder` | Bottom Border | Menu | What color the 2 bottom-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `bottomborderi` | Bottom Border Inside | Menu | Same as above parameter but used for an inside border. |
| `topborder` | Top Border | Menu | What color the 2 top-most pixels are. Options are 0 (no change), Border A (uses color defined in Border A), or Border B (uses color defined in Border B). |
| `topborderi` | Top Border Inside | Menu | Same as above parameter but used for an inside border. |
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
# Access the TOP textTOP operator
texttop_op = op('texttop1')

# Get/set parameters
freq_value = texttop_op.par.active.eval()
texttop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
texttop_op = op('texttop1')
output_op = op('output1')

texttop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(texttop_op)
```

## Technical Details

### Operator Family

**TOP** - Texture Operators - Process and manipulate image/texture data

### Parameter Count

This operator has **75** documented parameters.

## Navigation

- [Back to TOP Index](../TOP/TOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
