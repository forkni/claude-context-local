# CHOP mouseinCHOP

## Overview

The Mouse In CHOP outputs X and Y screen values for the mouse device and monitors the up/down state of the three mouse buttons.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Menu | While On, the mouse movement will be output from and the CHOP will cook every frame. When set to Off it will not cook and the current mouse X or Y values will not be output. While Playing will capt... |
| `output` | Output Coordinates | Menu | Controls the range of the mouse Position X and Position Y. |
| `posxname` | Position X | Str | The name of the channel that returns the horizontal movement of the mouse. |
| `posyname` | Position Y | Str | The name of the channel that returns the vertical movement of the mouse. |
| `lbuttonname` | Left Button | Str | The name of the channel that returns the state of the left button. |
| `rbuttonname` | Right Button | Str | The name of the channel that returns the state of the right button. |
| `mbuttonname` | Middle Button | Str | The name of the channel that returns the state of the middle button. |
| `wheel` | Wheel | Str | This channel goes up when the wheel is rolled away from the user and goes down when it is rolled the other way. |
| `wheelinc` | Wheel Increment | Float | The amount that is added or subtracted to the current value of the Wheel channel when the wheel is moved. |
| `monitor` | Monitor | Str | This channel returns which monitor the mouse cursor is currently on. |
| `panels` | Panels | PanelCOMP | Events are only triggered when the specified panel has focus. |
| `rate` | Sample Rate | Float | The sample rate of the channels, in samples per second. |
| `left` | Extend Left | Menu | The left extend conditions (before/after range). |
| `right` | Extend Right | Menu | The right extend conditions (before/after range). |
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
# Access the CHOP mouseinCHOP operator
mouseinchop_op = op('mouseinchop1')

# Get/set parameters
freq_value = mouseinchop_op.par.active.eval()
mouseinchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mouseinchop_op = op('mouseinchop1')
output_op = op('output1')

mouseinchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mouseinchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **21** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
