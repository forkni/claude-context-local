# CHOP mathCHOP

## Overview

The Math CHOP performs arithmetic operations on channels. The channels of a CHOP can be combined into one channel, and several CHOPs can be combined into one CHOP.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `preop` | Channel Pre OP | Menu | Unary operations can be performed on individual channels. A menu of unary operations (as described above) that are performed on each channel as it comes in to the Math CHOP include: |
| `chanop` | Combine Channels | Menu | A choice of operations is performed between the channels of an input CHOP, for each input. The Nth sample of one channel is combined with the Nth sample of other channels: |
| `chopop` | Combine CHOPs | Menu | A menu of operations that is performed between the input CHOPs, combining several CHOPs into one. |
| `postop` | Channel Post OP | Menu | A menu (same as Channel Pre OP) is performed as the finale stage upon the channels resulting from the above operations. |
| `match` | Match by | Menu | Match channels between inputs by name or index. |
| `align` | Align | Menu | This menu handles cases where multiple input CHOPs have different start or end times. All channels output from a CHOP share the same start/end interval, so the inputs must be treated with the Align... |
| `interppars` | Interp Pars per Sample | Toggle | Use this option when the input is a higher frequency than the timeline (example: audio).  It will avoid any pops or crackles in the output when adjusting the multiply, add or  range parameters. |
| `integer` | Integer | Menu | The resulting values can be converted to integer. |
| `preoff` | Pre-Add | Float | First, add the value to each sample of each channel. |
| `gain` | Multiply | Float | Then multiply by this value. |
| `postoff` | Post-Add | Float | Then add this value. |
| `fromrange` | From Range | Float | Another way to multiply/add. Converts from one low-high range to another range. |
| `torange` | To Range | Float | Another way to multiply/add. Converts from one low-high range to another range. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP mathCHOP operator
mathchop_op = op('mathchop1')

# Get/set parameters
freq_value = mathchop_op.par.active.eval()
mathchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
mathchop_op = op('mathchop1')
output_op = op('output1')

mathchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(mathchop_op)
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
