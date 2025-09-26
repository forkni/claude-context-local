# CHOP shiftCHOP

## Overview

The Shift CHOP time-shifts a CHOP, changing the start and end of the CHOP's interval. However, the contents of the channels remain the same.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `reference` | Reference | Menu | The start or the end of the channels can be used as the reference position. The channels are shifted by altering the reference position. |
| `relative` | Unit Values | Menu | Determines how the Start and End parameters are to be interpreted: |
| `start` | Start | Float | The start of the interval, absolute or relative to the input CHOP. |
| `startunit` | Start Unit | Menu |  |
| `end` | End | Float | The end of the interval, absolute or relative to the input CHOP. |
| `endunit` | End Unit | Menu |  |
| `scroll` | Scroll Offset | Float | Without changing the length of the CHOP, you can scroll the channels within its range, and scroll each channel a different amount. By using $C in the parameter, you can make the scroll amount depen... |
| `scrollunit` | Scroll Offset Unit | Menu |  |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP shiftCHOP operator
shiftchop_op = op('shiftchop1')

# Get/set parameters
freq_value = shiftchop_op.par.active.eval()
shiftchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
shiftchop_op = op('shiftchop1')
output_op = op('output1')

shiftchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(shiftchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **14** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
