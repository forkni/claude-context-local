# CHOP keyboardinCHOP

## Overview

The Keyboard In CHOP receives ASCII input from the keyboard, and outputs channels for the number of keys specified.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Menu | While On, the keyboard inputs will be monitored and the CHOP will cook every frame. When set to Off it will not cook and the current keyboard values will not be output. While Playing will capture k... |
| `keys` | Keys | StrMenu | Enter the keys to monitor create a channel for. Can be selected from the dropdown menu on the right. Valid keys are the numbers 0-9, letters A-Z, and keypad 0-9. |
| `modifiers` | Modifier Keys | Menu | If it is set to Ctrl, the keys will only go On if you are also pressing the Ctrl key. This works similarly for Alt and Shift modifiers. If it set to Ignore, it doesn't matter if the Ctrl/Alt/Shift ... |
| `channelnames` | Channel Names | Menu | Channel names are generated automatically using one of these criteria. |
| `panels` | Panels | PanelCOMP | When a path to a Panel COMP(s) is specified, only keyboard events that take place when that panel(s) has focus will reported by the Keyboard In CHOP. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before range). |
| `right` | Extend Right | Menu | The right extend conditions (after range). |
| `defval` | Default Value | Float | The value used for the Default Value extend condition. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP keyboardinCHOP operator
keyboardinchop_op = op('keyboardinchop1')

# Get/set parameters
freq_value = keyboardinchop_op.par.active.eval()
keyboardinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
keyboardinchop_op = op('keyboardinchop1')
output_op = op('output1')

keyboardinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(keyboardinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **15** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
