# CHOP trimCHOP

## Overview

The Trim CHOP shortens or lengthens the input's channels.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `relative` | Unit Values | Menu | Determines whether the Start/End parameters are expressed as absolute numbers (relative to time 0) or numbers that are relative to the start and end of the input channels. |
| `start` | Start | Float | The start of the range to trim. The numbers are expressed in seconds, frames or samples, depending on units menu for each parameter. |
| `startunit` | Start Unit | Menu |  |
| `end` | End | Float | The end of the range to trim. The numbers are expressed in seconds, frames or samples, depending on units menu for each parameter. |
| `endunit` | End Unit | Menu |  |
| `discard` | Discard | Menu | Which part of the channel to discard: |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP trimCHOP operator
trimchop_op = op('trimchop1')

# Get/set parameters
freq_value = trimchop_op.par.active.eval()
trimchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
trimchop_op = op('trimchop1')
output_op = op('output1')

trimchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(trimchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **12** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
