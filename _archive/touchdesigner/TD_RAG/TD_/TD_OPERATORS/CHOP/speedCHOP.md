# CHOP speedCHOP

## Overview

The Speed CHOP converts speed (units per second) to distance (units) over a time range.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `order` | Order | Menu | Determines the order of the integral to use. If the input is a velocity, a First Order integral will return the position. If the input is an acceleration, a Second Order integral will return the po... |
| `constant1` | First Constant | Float | Constant to add to the entire result after integrating once. |
| `constant2` | Second Constant | Float | Constant to add to the entire result after integrating twice. |
| `constant3` | Third Constant | Float | Constant to add to the entire result after integrating three times. |
| `limittype` | Limit Type | Menu | Select limit options such as loop, clamp, or zigzag from the menu. The value will remain in the range from Min to less than Max. |
| `min` | Minimum | Float | The minimum value the output channel can have. |
| `max` | Maximum | Float | The maximum value the output channel can have. |
| `speedsamples` | Speed per Sample | Toggle | Applies the speed to each sample of the channel instead of across the whole channel. Useful for working with multi-sample channels. |
| `resetcondition` | Reset Condition | Menu | This menu determines how the Reset input triggers a reset of the channel(s). |
| `resetvalue` | Reset Value | Float | The channel(s) is set to this value when reset. |
| `reset` | Reset | Toggle | While On, this toggle resets the channel(s) to the Reset Value. |
| `resetpulse` | Reset Pulse | Pulse | Click to instantly resets the channel(s) to the Reset Value. |
| `resetonstart` | Reset On Start | Toggle | While On, the Speed CHOP will reset each time the .toe file is restarted. If the Speed CHOP's value gets too large it can start stepping as when it reaches the limit of CHOP's number resolution. Th... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP speedCHOP operator
speedchop_op = op('speedchop1')

# Get/set parameters
freq_value = speedchop_op.par.active.eval()
speedchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
speedchop_op = op('speedchop1')
output_op = op('output1')

speedchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(speedchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **19** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
