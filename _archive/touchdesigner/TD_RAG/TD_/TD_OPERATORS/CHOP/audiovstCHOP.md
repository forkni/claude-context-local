# CHOP audiovstCHOP

## Overview

Loads VST3 Plugins.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `file` | File | File | The path to the VST3 plugin. Default install location for VST3 plugins is C:/Program Files/Common Files/VST3 on Windows and /Library/Audio/Plug-Ins/VST3 on macOS. |
| `reloadpulse` | Reload | Pulse | Reloads the VST3 plugin. |
| `loadpluginstate` | Load Plugin State on Start | Toggle | The plugin state (including preset value and other UI elements) is saved into the toe file and is restored on TouchDesigner start, if enabled. The toggle exists to provide a work-around to plugins ... |
| `rate` | Sample Rate | Float | Sets the sample rate of the VST3 plugin. |
| `alwaysontop` | Plugin GUI Always on Top | Toggle | When enabled, the plugin window will always be on top of other windows. |
| `displaygui` | Display Plugin GUI | Pulse | When pulsed, will open the plugin GUI in a separate window. Changing a parameter in the plugin GUI while the learn toggle is enabled will create the parameter on the Audio VST CHOP side. |
| `learnparms` | Learn Parameters | Toggle | When enabled, parameters that are interacted with in the VST Plugin window will be created as parameters on the Plugin page, ie. they will be learned. |
| `regularparms` | Regular Parameters | Toggle | When enabled, every Plugin parameter will be created on the Plugin page. |
| `readonlyparms` | Read-Only Parameters | Toggle | When enabled, all read-only Plugin parameters will be created on the Plugin page. If Regular Parameters is also toggled on then this toggle will have no effect. |
| `clearlearnedparms` | Clear Learned Parameters | Pulse | When pulsed, all learned parameters will be cleared. If neither Regular or Read-only parameters are toggled on then the parameters will be destroyed. |
| `callbacks` | Callbacks DAT | DAT | Reference to the DAT containing Audio VST CHOP supported callbacks. |
| `custombuslayout` | Custom Bus Layout | Toggle | Enables custom bus layout. If disabled the bus layout will be the plugin's default. |
| `outputbuslayout` | Output Bus Layout | StrMenu | Select the output bus layout (ie. number of channels) of the output bus. This will directly affect how many channels the Audio VST CHOP has. |
| `maininputlayout` | Main Input Bus Layout | StrMenu | Select the main input bus layout (ie. number of channels). The main input bus is always the CHOP's first input, and this selection determines how many channels it accepts from it. |
| `aux` | Aux Input | Sequence | This sequence describes the aux inputs to the VST plugin |
| `customplayhead` | Custom Playhead | Toggle | Enable the custom playhead. When disabled, the plugin will always sequentially step forward in time. Not all plugins support a custom playhead. |
| `timecodeop` | Timecode Object/CHOP/DAT | Str | Specifies the playhead time of the plugin. A reference to either a CHOP with channels 'hour', 'second', 'minute', 'frame', a DAT with a timecode string in its first cell, or a Timecode Class object. |
| `tempo` | Tempo (bpm) | Float | The tempo of the playhead. Not all plugins support changing of the tempo via the playhead. |
| `signature` | Signature | Int | The time signature of the playhead. Not all plugins support changing of the time signature via the playhead. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP audiovstCHOP operator
audiovstchop_op = op('audiovstchop1')

# Get/set parameters
freq_value = audiovstchop_op.par.active.eval()
audiovstchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
audiovstchop_op = op('audiovstchop1')
output_op = op('output1')

audiovstchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(audiovstchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **25** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
