# CHOP timesliceCHOP

## Overview

The Time Slice CHOP outputs a time slice of samples.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `method` | Method | Menu | How to sample the input CHOP to create the output time slice. If the input CHOP is not time sliced and lies outside the current time slice region, its extend regions will be sampled. |
| `quatrot` | Quaternion Blend | Toggle | Rotation channels blended using quaternions. Channels must be tagged as rotation channels (For example with the Attribute CHOP or Object CHOP). |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP timesliceCHOP operator
timeslicechop_op = op('timeslicechop1')

# Get/set parameters
freq_value = timeslicechop_op.par.active.eval()
timeslicechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
timeslicechop_op = op('timeslicechop1')
output_op = op('output1')

timeslicechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(timeslicechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **8** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
