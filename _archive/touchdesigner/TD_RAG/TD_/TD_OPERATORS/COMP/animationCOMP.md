# COMP animationCOMP

## Overview

The Animation Component is a special component used for creating keyframe animation channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `timeref` | Time Reference | OP | The location the Animation COMP looks to for its time information. This is used for default channel range and rate when the Type parameter on the Range page is set to Timeline. |
| `playmode` | Play Mode | Menu | Specifies the method used to playback the animation or allows the output the entire animation curve. |
| `play` | Play | Toggle | Animation plays when On and stops when Off. This animation playback control is only available when Play Mode is Sequential. |
| `speed` | Speed | Float | This is a speed multiplier which only works when Play Mode is Sequential. A value of 1 is the default playback speed. A value of 2 is double speed, 0.5 is half speed and so on. Negative values will... |
| `cue` | Cue | Toggle | Jumps to Cue Point when set to 1. Only available when Play Mode is Sequential. |
| `cuepulse` | Cue Pulse | Pulse | Instantly jumps to the Cue Point. |
| `cuepoint` | Cue Point | Float | Set any index in the animation as a point to jump to. Only available when Play Mode is Sequential. |
| `cuepointunit` | Cue Point Unit | Menu | Units used when setting the Cue Point parameter. |
| `inputindexunit` | Input Index Unit | Menu | When Play Mode is set to Use Input Index use this menu to choose the units for the index input channel. For example, choose between setting the index with frames or seconds. The Units X option sets... |
| `cyclic` | Cyclic Range | Menu | Adapts the range of the animation for cyclic or non-cyclic input indices. When using a cyclic input index the lookup value for index 0.0 and 1.0 result in the same value. To avoid this, set Cyclic ... |
| `specifyedit` | Specify Edit Attributes | Toggle | Turn this on to enable the edit attributes parameter below. |
| `editorigin` | Edit Origin | Float | Changes the origin of the animation channel edits. This does not change the data stored in the key DAT table, but it does effect the channels display in the graph and playback of the animation. |
| `editrate` | Edit Rate | Float | Changes the rate of the animation channel edits. This does not change the data stored in the key DAT table, but it does effect the channels display in the graph and playback of the animation. |
| `editanimation` | Edit Animation... | Pulse | Clicking this button will open this Animation COMP in the Animation Editor. |
| `rangetype` | Type | Menu | Set the working range for the Animation COMP. |
| `start` | Start | Float | Start of the Custom range, expressed in units seconds, frames or samples. |
| `startunit` | Start Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `end` | End | Float | End of the Custom range, expressed in units seconds, frames or samples. |
| `endunit` | End Unit | Menu | Select the units to use for this parameter, Samples, Frames, or Seconds. |
| `tleft` | Trim Left | Menu | Determines the output of the channels when past the 'End' position. Does not affect Play Mode = Output Full Range, to manipulate the Extend Conditions of that mode adjust the Extend parameters of t... |
| `tright` | Trim Right | Menu | Determines the output of the channels when before the 'Start' position. Does not affect Play Mode = Output Full Range, to manipulate the Extend Conditions of that mode adjust the Extend parameters ... |
| `tdefault` | Trim Default | Float | The value used for the Default Value trim conditio above. |
| `ext` | Extension | Sequence | Sequence of info for creating extensions on this component |
| `reinitextensions` | Re-Init Extensions | Pulse | Recompile all extension objects. Normally extension objects are compiled only when they are referenced and their definitions have changed. |
| `parentshortcut` | Parent Shortcut | COMP | Specifies a name you can use anywhere inside the component as the path to that component. See Parent Shortcut. |
| `opshortcut` | Global OP Shortcut | COMP | Specifies a name you can use anywhere at all as the path to that component. See Global OP Shortcut. |
| `iop` | Internal OP | Sequence | Sequence header for internal operators. |
| `opviewer` | Operator Viewer | OP | Select which operator's node viewer to use when the Node View parameter above is set to Operator Viewer. |
| `enablecloning` | Enable Cloning | Toggle | Control if the OP should be actively cloneing. Turning this off causes this node to stop cloning it's 'Clone Master'. |
| `enablecloningpulse` | Enable Cloning Pulse | Pulse | Instantaneously clone the contents. |
| `clone` | Clone Master | COMP | Path to a component used as the Master Clone. |
| `loadondemand` | Load on Demand | Toggle | Loads the component into memory only when required. Good to use for components that are not always used in the project. |
| `enableexternaltox` | Enable External .tox | Toggle | When on (default), the external .tox file will be loaded when the .toe starts and the contents of the COMP will match that of the external .tox. This can be turned off to avoid loading from the ref... |
| `enableexternaltoxpulse` | Enable External .tox Pulse | Pulse | This button will re-load from the external .tox file (if present). |
| `externaltox` | External .tox Path | File | Path to a .tox file on disk which will source the component's contents upon start of a .toe. This allows for components to contain networks that can be updated independently. If the .tox file can n... |
| `reloadcustom` | Reload Custom Parameters | Toggle | When this checkbox is enabled, the values of the component's Custom Parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on nod... |
| `reloadbuiltin` | Reload Built-In Parameters | Toggle | When this checkbox is enabled, the values of the component's built-in parameters are reloaded when the .tox is reloaded. This only affects top-level parameters on the component, all parameters on n... |
| `savebackup` | Save Backup of External | Toggle | When this checkbox is enabled, a backup copy of the component specified by the External .tox parameter is saved in the .toe file.  This backup copy will be used if the External .tox can not be foun... |
| `subcompname` | Sub-Component to Load | Str | When loading from an External .tox file, this option allows you to reach into the .tox and pull out a COMP and make that the top-level COMP, ignoring everything else in the file (except for the con... |
| `relpath` | Relative File Path Behavior | Menu | Set whether the child file paths within this COMP are relative to the .toe itself or the .tox, or inherit from parent. |

## Usage Examples

### Basic Usage

```python
# Access the COMP animationCOMP operator
animationcomp_op = op('animationcomp1')

# Get/set parameters
freq_value = animationcomp_op.par.active.eval()
animationcomp_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
animationcomp_op = op('animationcomp1')
output_op = op('output1')

animationcomp_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(animationcomp_op)
```

## Technical Details

### Operator Family

**COMP** - Component Operators - Container and UI components

### Parameter Count

This operator has **40** documented parameters.

## Navigation

- [Back to COMP Index](../COMP/COMP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
