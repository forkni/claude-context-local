# SOP importselectSOP

## Overview

The Import Select SOP is used to import and load the geometry types primitives defined in USD COMP and FBX COMP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `parent` | Import Parent | comp | Specify the import parent (eg. USD/FBX COMP) to search for the asset. When no COMP is specified it will by default search in the first import parent in its path. |
| `geometry` | Geo Path | minimenu dynamicmenu | The geometry path from the imported file. |
| `reload` | Reload | pulse | Reloads the asset from the import parent. |
| `comptang` | Compute Tangents | toggle | A toggle to compute the tangents for this SOP. |
| `useparentanim` | Use Parent Animation | toggle | A toggle to specify whether to use the parent COMP animation controls or have a custom setting for this SOP. |
| `shiftanimationstart` | Shift Animation Start | toggle | A toggle to specify whether to shift the animation to the start of animation indicated in the importing file. |
| `sampleratemode` | Sample Rate Mode | dropmenu | A menu to choose between the FPS or use a custom sample rate. |
| `samplerate` | Sample Rate | float | It is used to specify the sample rate (FPS) for the animation. This parameter is disabled by default and can be enabled once the Custom option is selected from the Sample Rate Menu. |
| `playmode` | Play Mode | dropmenu | A menu to specify the method used to play the animation. |
| `initialize` | Initialize | button | Resets the animation to its initial state. |
| `start` | Start | button | Resets the animation to its initial state and starts playback. |
| `cue` | Cue | joinpair toggle | A toggle to jump to Cue Point when it is set to ON and it stays at that position. Only available when Play Mode is Sequential. |
| `cuepulse` | Cue Pulse | nolabel button | When pressed the animation jumps to the Cue Point and continues from that point. |
| `cuepoint` | Cue Point | joinpair float | Set any index in the animation as a point to jump to. |
| `cuepointunit` | Cue Point Unit | nolabel shortvalues dropmenu | Specifies a unit type for Cue Point. Changing this will convert the previous unit to the selected unit. |
| `play` | Play | toggle | A toggle that makes the animation to play when it sets to ON. This Parameter is only available/enabled if the Sequential mode is selected from the Play Mode. |
| `index` | Index | joinpair float | This parameter explicitly sets the animation position when Play Mode is set to Specify Index. The units menu on the right lets you specify the index in the following units: Index, Frames, Seconds, ... |
| `indexunit` | Index Unit | nolabel shortvalues dropmenu | Specifies a unit type for Index. Changing this will convert the previous unit to the selected unit. |
| `speed` | Speed | float | This is a speed multiplier which only works when Play Mode is Sequential. A value of 1 is the default playback speed. A value of 2 is double speed, 0.5 is half speed and so on. |
| `trim` | Trim | toggle | A toggle to enable the Trim Start and Trim End parameters. |
| `tstart` | Trim Start | joinpair float | Sets an in point from the beginning of the animation, allowing you to trim the starting index of the animation. The units menu on the right let you specify this position by index, frames, seconds, ... |
| `tstartunit` | Trim Start Unit | nolabel shortvalues dropmenu | Specifies a unit type for Trim Start. Changing this will convert the previous unit to the selected unit. |
| `tend` | Trim End | joinpair float | Sets an end point from the end of the movie, allowing you to trim the ending index of the animation. The units menu on the right let you specify this position by index, frames, seconds, or fraction... |
| `tendunit` | Trim End Unit | nolabel shortvalues dropmenu | Specifies a unit type for Trim End. Changing this will convert the previous unit to the selected unit. |
| `textendleft` | Extend Left | dropmenu | Determines how the parent COMP handles animation positions that lie before the Trim Start position. For example, if Trim Start is set to 1, and the animation current index is -10, the Extend Left m... |
| `textendright` | Extend Right | dropmenu | Determines how the parent COMP handles animation positions that lie after the Trim End position. For example, if Trim End is set to 20, and the animation current index is 25, the Extend Right menu ... |

## Usage Examples

### Basic Usage

```python
# Access the SOP importselectSOP operator
importselectsop_op = op('importselectsop1')

# Get/set parameters
freq_value = importselectsop_op.par.active.eval()
importselectsop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
importselectsop_op = op('importselectsop1')
output_op = op('output1')

importselectsop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(importselectsop_op)
```

## Technical Details

### Operator Family

**SOP** - Surface Operators - Process and manipulate 3D geometry

### Parameter Count

This operator has **26** documented parameters.

## Navigation

- [Back to SOP Index](../SOP/SOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
