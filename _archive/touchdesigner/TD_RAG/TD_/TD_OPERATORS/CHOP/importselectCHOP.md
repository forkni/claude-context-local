# CHOP importselectCHOP

## Overview

The Import Select CHOP is used to specify CHOP channels from an importing file such as FBX COMP or USD COMP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `parent` | Import Parent | comp | Specify the import parent (eg. USD/FBX COMP) to search for the asset. When no COMP is specified it will by default search in the first import parent in its path. |
| `taketype` | Take Type | dropmenu | Select between playback of an animation or a blend shape. |
| `blendshape` | Blend Shape | minimenu dynamicmenu | Specifices the blend shape name (if any is specified) from the importing file that this CHOP will playback. |
| `reload` | Reload | pulse | Reloads the asset from the import parent. |
| `useparentanim` | Use Parent Animation | toggle | A toggle to specify whether to use the parent COMP animation controls or have a custom setting for this SOP. |
| `animation` | Animation | minimenu dynamicmenu | Specifices the animation name (if any is specified) from the importing file that this CHOP will playback. |
| `shiftanimationstart` | Shift Animation Start | toggle | A toggle to specify whether to shift the animation to the start of animation indicated in the importing file. |
| `sampleratemode` | Sample Rate Mode | dropmenu | Select between using the 'File FPS' embedded in the FBX file or setting a 'Custom' sample rate. |
| `samplerate` | Sample Rate | float | Set the sample rate when the "Sample Rate Mode" parameter above is set to 'Custom'. |
| `playmode` | Play Mode | dropmenu | A menu to specify the method used to play the animation. |
| `index` | Index | joinpair float | This parameter explicitly sets the animation position when Play Mode is set to Specify Index. The units menu on the right lets you specify the index in the following units: Index, Frames, Seconds, ... |
| `indexunit` | Index Unit | nolabel shortvalues dropmenu | Specifies a unit type for Index. Changing this will convert the previous unit to the selected unit. |
| `play` | Play | toggle | A toggle that makes the animation to play when it sets to ON. This Parameter is only available/enabled if the Sequential mode is selected from the Play Mode. |
| `speed` | Speed | float | This is a speed multiplier which only works when Play Mode is Sequential. A value of 1 is the default playback speed. A value of 2 is double speed, 0.5 is half speed and so on. |
| `trim` | Trim | toggle | A toggle to enable the Trim Start and Trim End parameters. |
| `tstart` | Trim Start | joinpair float | Sets an in point from the beginning of the animation, allowing you to trim the starting index of the animation. The units menu on the right let you specify this position by index, frames, seconds, ... |
| `tstartunit` | Trim Start Unit | nolabel shortvalues dropmenu | Specifies a unit type for Trim Start. Changing this will convert the previous unit to the selected unit. |
| `tend` | Trim End | joinpair float | Sets an end point from the end of the movie, allowing you to trim the ending index of the animation. The units menu on the right let you specify this position by index, frames, seconds, or fraction... |
| `tendunit` | Trim End Unit | nolabel shortvalues dropmenu | Specifies a unit type for Trim End. Changing this will convert the previous unit to the selected unit. |
| `cue` | Cue | joinpair toggle | A toggle to jump to Cue Point when it is set to ON and it stays at that position. Only available when Play Mode is Sequential. |
| `cuepulse` | Cue Pulse | nolabel button | When pressed the animation jumps to the Cue Point and continues from that point. |
| `cuepoint` | Cue Point | joinpair float | Set any index in the animation as a point to jump to. |
| `cuepointunit` | Cue Point Unit | nolabel shortvalues dropmenu | Specifies a unit type for Cue Point. Changing this will convert the previous unit to the selected unit. |
| `textendleft` | Extend Left | dropmenu | Determines how the parent COMP handles animation positions that lie before the Trim Start position. For example, if Trim Start is set to 1, and the animation current index is -10, the Extend Left m... |
| `textendright` | Extend Right | dropmenu | Determines how the parent COMP handles animation positions that lie after the Trim End position. For example, if Trim End is set to 20, and the animation current index is 25, the Extend Right menu ... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP importselectCHOP operator
importselectchop_op = op('importselectchop1')

# Get/set parameters
freq_value = importselectchop_op.par.active.eval()
importselectchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
importselectchop_op = op('importselectchop1')
output_op = op('output1')

importselectchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(importselectchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **31** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
