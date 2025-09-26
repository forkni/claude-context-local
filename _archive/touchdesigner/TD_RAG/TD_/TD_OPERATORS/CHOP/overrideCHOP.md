# CHOP overrideCHOP

## Overview

The Override CHOP lets you take inputs from several CHOP sources, and uses the most-recently changed input channels to determine the output.

## Parameters

| Parameter | Label | Type | Description |
|-----------|-------|------|-------------|
| `match` | Match by | Menu | Monitors the channels in each input and matches them according to this menu. |
| `makeindex` | Create Input Index | Toggle | Creates a channel (specified by the Channel Name parameter below) that is an index indicating which input has the most recently changed channel. |
| `indexname` | Channel Name | Str | Specifies the name of the index channel. Only used if the Create Input Index checkbox is selected. |
| `cookmonitor` | Monitor on Input Cooks | Toggle | Deprecated. |
| `timeslice` | Time Slice | Toggle | Turning this on forces the channels to be "Time Sliced".  A Time Slice is the time between the last cook frame and the current cook frame. |
| `scope` | Scope | StrMenu | To determine which channels get affected, some CHOPs use a Scope string on the Common page. See :Pattern Matching. |
| `srselect` | Sample Rate Match | Menu | Handle cases where multiple input CHOPs' sample rates are different. When Resampling occurs, the curves are interpolated according to the Interpolation Method Option, or "Linear" if the Interpolate... |
| `exportmethod` | Export Method | Menu | This will determine how to connect the CHOP channel to the parameter. Refer to the Export article for more information. |
| `autoexportroot` | Export Root | OP | This path points to the root node where all of the paths that exporting by Channel Name is Path:Parameter are relative to. |
| `exporttable` | Export Table | DAT | The DAT used to hold the export information when using the DAT Table Export Methods (See above). |

## Usage Examples

### Basic Usage

```python
# Access the CHOP overrideCHOP operator
overridechop_op = op('overridechop1')

# Get/set parameters
freq_value = overridechop_op.par.active.eval()
overridechop_op.par.active = 1
```

### In Networks

```python
# Connect operators
input_op = op('source1')
overridechop_op = op('overridechop1')
output_op = op('output1')

overridechop_op.inputConnectors[0].connect(input_op)
output_op.inputConnectors[0].connect(overridechop_op)
```

## Technical Details

### Operator Family

**CHOP** - Channel Operators - Process and manipulate channel data

### Parameter Count

This operator has **10** documented parameters.

## Navigation

- [Back to CHOP Index](../CHOP/CHOP_INDEX.md)
- [Back to Main Index](../OPERATORS_INDEX.md)
- [Browse Other Families](../OPERATORS_INDEX.md#quick-navigation)

---
*Documentation generated from TouchDesigner parameter reference and summaries*
