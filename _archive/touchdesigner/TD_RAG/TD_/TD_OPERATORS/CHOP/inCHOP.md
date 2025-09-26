# CHOP inCHOP

## Overview

The In CHOP gets channels that are connected to one of the inputs of the component.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `label` | Label | Str | The label for this input on the COMP that will show up in a popup if the mouse is held over it. |
| `numchannels` | Num Channels | Int | If On, and the number of incoming channels does not match this value, an error is generated. |
| `channames` | Names | Str | When used with Num Channels the input is scanned for channels matching these names. All other channels are ignored and not passed through. This is a way of filtering out unnecessary channels withou... |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP inCHOP operator
inchop_op = op('inchop1')

# Get/set parameters
freq_value = inchop_op.par.active.eval()
inchop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
inchop_op = op('inchop1')
output_op = op('output1')

inchop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(inchop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **9** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
