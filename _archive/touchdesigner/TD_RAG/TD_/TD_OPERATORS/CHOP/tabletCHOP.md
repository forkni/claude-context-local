# CHOP tabletCHOP

## Overview

The Tablet CHOP gets the Wacom tablet X and Y values, and also gets pen tip pressure, X tilt and Y tilt, and the various pen buttons.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `xcoord` | X Coordinate | Str | The channel name for the movement of the pen in the x direction. |
| `ycoord` | Y Coordinate | Str | The channel name for the movement of the pen in the y direction. |
| `pressure` | Pressure | Str | The channel name for the pressure reported by the pen. |
| `xtilt` | X Tilt | Str | The channel name for the tilt of the pen in the x direction. |
| `ytilt` | Y Tilt | Str | The channel name for the tilt of the pen in the y direction. |
| `tanpressure` | Finger Wheel | Str | The channel name for a finger rollar wheel if available. |
| `zcoord` | Thumb Wheel | Str | The channel name for a thumb rollar wheel if available. |
| `rotation` | Rotation | Str | The channel name for the rotation the pen is reporting. |
| `button1` | Button 1 | Str | The channel name for the button reported as Button 1. |
| `button2` | Button 2 | Str | The channel name for the button reported as Button 2. |
| `button3` | Button 3 | Str | The channel name for the button reported as Button 3. |
| `button4` | Button 4 | Str | The channel name for the button reported as Button 4. |
| `button5` | Button 5 | Str | The channel name for the button reported as Button 5. |
| `active` | Active | Menu | While On, the pen movement will be output from and the CHOP will cook every frame. When set to Off it will not cook and the values will not be updated. While Playing will capture pen events only wh... |
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
# Access the CHOP tabletCHOP operator
tabletchop_op = op('tabletchop1')

# Get/set parameters
freq_value = tabletchop_op.par.active.eval()
tabletchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
tabletchop_op = op('tabletchop1')
output_op = op('output1')

tabletchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(tabletchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **24** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
