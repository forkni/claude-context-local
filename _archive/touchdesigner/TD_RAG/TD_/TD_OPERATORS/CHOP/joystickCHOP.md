# CHOP joystickCHOP

## Overview

The Joystick CHOP outputs values for all 6 possible axes on any game controller (joysticks, game controllers, driving wheels, etc.), as well as up to 32 button, 2 sliders and 4 POV Hats.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `active` | Active | Toggle | While on, the CHOP receives information from joysticks and gamepads. While Off, no updating occurs. |
| `source` | Joystick Source | StrMenu | This menu will list up to 4 game controllers currently attached to the computer presented to the operating system as Player 1 through Player 4. The selected game controller is the one the CHOP read... |
| `axisrange` | Axis Range | Menu | Select between and axis range of 0 to 1 or -1 to 1. |
| `xaxis` | X Axis | Str | The name of the channel that records the X-axis position of the game controller. |
| `yaxis` | Y Axis | Str | The name of the channel that records the Y-axis position of the game controller. |
| `yaxisinvert` | Invert Y Axis | Toggle | Inverts the Y axis. |
| `zaxis` | Z Axis | Str | The name of the channel that records the Z-axis position of the game controller. |
| `xrot` | X Rotation | Str | The names of the channels that record the X-rotation axis position of the game controller. |
| `yrot` | Y Rotation | Str | The names of the channels that record the Y-rotation axis position of the game controller. |
| `yrotinvert` | Invert Y Rotation | Toggle | Invert the rotation direction around the Y axis. |
| `zrot` | Z Rotation | Str | The names of the channels that record the Z-rotation axis position of the game controller. |
| `slider0` | Slider 1 | Str | The name of the channel that records the position of the first slider on the game controller. |
| `slider1` | Slider 2 | Str | The name of the channel that records the position of the second slider on the game controller. |
| `buttonarray` | Button Array | Str | The names of the channels for the buttons on the game controller. This CHOP can handle up to 32 buttons. |
| `povarrray` | POV Hat Array | Str | The names of the channels for the POV Hats. This CHOP can handle up to 4 POV Hats. The channels a POV hat is split up into are POVHatName_X and POVHatName_Y. |
| `povstatearray` | POV Hat State Array | Str |  |
| `connected` | Connected | Str | Creates a channel that reports the state of connection of the controller. |
| `axisdeadzone` | Axis Dead Zone | Float | This value defines how much of the area in the center of the joystick is considered 'dead zone'. When a joystick axis is in this dead zone it is considered to be centered. This value applies to all... |
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
# Access the CHOP joystickCHOP operator
joystickchop_op = op('joystickchop1')

# Get/set parameters
freq_value = joystickchop_op.par.active.eval()
joystickchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
joystickchop_op = op('joystickchop1')
output_op = op('output1')

joystickchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(joystickchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **28** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
